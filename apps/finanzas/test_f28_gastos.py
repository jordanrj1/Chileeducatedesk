"""Pruebas de F28 B (specs/f28/spec.md, punto 5): gastos de la actividad. Una prueba por escenario GA-E1…GA-E10, más las
consultas fijas de la pestaña Gastos y del resumen del proyecto. Datos ficticios."""
import uuid
from datetime import date, time, timedelta
from io import BytesIO

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.test import Client

from apps.actividades import asistencia, servicios
from apps.finanzas.models import ItemPresupuesto, Movimiento
from apps.finanzas.resumen import gastos_actividad, gastos_proyecto
from apps.nucleo.models import CategoriaGasto

pytestmark = pytest.mark.django_db
HOY = date.today()
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.4\n" + b"\x00" * 64


@pytest.fixture
def proyecto(db):
    from apps.proyectos.models import Proyecto

    return Proyecto.objects.create(nombre="Huertos Ficticios")


@pytest.fixture
def taller(crear_actividad, proyecto, gestor):
    t = crear_actividad("Taller de compostaje", estado="confirmada", proyecto=proyecto)
    servicios.programar(t, gestor, HOY - timedelta(days=1), time(10), time(12), None, None)
    asistencia.nueva_jornada(t, gestor, HOY, time(10), time(12))
    return t


def _jornadas(t):
    return [j for j in asistencia.jornadas(t) if j.pk]


def _datos(**kw):
    d = {"categoria": CategoriaGasto.objects.get(codigo="alimentacion").pk, "concepto": "Colación para 20 personas", "monto": 45000,
         "fecha": HOY.isoformat(), "_envio": uuid.uuid4().hex}
    d.update(kw)
    return d


def _registrar(c, t, **kw):
    return c.post(f"/actividades/{t.pk}/gastos/nuevo", _datos(**kw))


def _gasto(t, **kw):
    datos = dict(actividad=t, tipo="gasto", monto=1000, concepto="Algo", categoria=CategoriaGasto.objects.get(codigo="materiales"))
    datos.update(kw)
    return Movimiento.objects.create(**datos)


def test_GA_E1_foto_de_la_boleta_al_cerrar_la_lista(cg, taller):
    j = _jornadas(taller)[1]
    r = cg.get(f"/actividades/{taller.pk}/gastos/nuevo?jornada={j.pk}")
    assert r.status_code == 200 and f'value="{j.pk}" selected' in r.content.decode()
    r = _registrar(cg, taller, sesion=j.pk, comprobante=SimpleUploadedFile("boleta.png", PNG))
    assert r.status_code == 302
    g = Movimiento.objects.get()
    assert g.sesion == j and g.actividad == taller and g.proyecto == taller.proyecto and g.estado == "registrado"
    d = g.documento
    assert d.restringido and d.actividad == taller and d.proyecto == taller.proyecto and d.sesion == j
    assert "boleta" not in d.archivo.name  # el nombre original no se conserva
    assert cg.get(f"/documentos/{d.pk}/archivo").status_code == 200  # solo por la vista protegida
    # el enlace «¿Hubo gastos este día?» aparece al cerrar la lista
    from apps.actividades.vistas_asistencia import url_gasto_de_jornada

    assert url_gasto_de_jornada(j) == f"/actividades/{taller.pk}/gastos/nuevo?jornada={j.pk}"
    assert url_gasto_de_jornada(j, type("U", (), {"has_perm": lambda self, p: False})()) is None


def test_GA_E2_sin_comprobante_se_guarda_y_se_marca(cg, taller, proyecto):
    assert _registrar(cg, taller).status_code == 302
    g = Movimiento.objects.get()
    assert g.sin_comprobante and g.documento is None
    assert "Sin comprobante" in cg.get(f"/actividades/{taller.pk}?tab=gastos").content.decode() or \
        "Sin comprobante" in cg.get(f"{taller.get_absolute_url()}?tab=gastos").content.decode()
    assert gastos_proyecto(proyecto)["sin_comprobante"] == 1
    assert "Sin comprobante" in cg.get(f"/proyectos/{proyecto.pk}?tab=gastos").content.decode()


def test_GA_E3_gasto_en_la_tarea_equivocada_se_edita(cg, gestor, taller, crear_actividad, proyecto):
    j1, j2 = _jornadas(taller)
    _registrar(cg, taller, sesion=j1.pk)
    g = Movimiento.objects.get()
    r = cg.post(f"/actividades/{taller.pk}/gastos/{g.pk}/editar", _datos(sesion=j2.pk, monto=47000, _version=cg.get(f"/actividades/{taller.pk}/gastos/{g.pk}/editar").context["version_registro"]))
    assert r.status_code == 302
    g.refresh_from_db()
    assert g.sesion == j2 and g.monto == 47000 and g.history.count() == 2
    # una jornada de otra tarea se rechaza
    otra = crear_actividad("Otra tarea", estado="confirmada", proyecto=proyecto)
    jo = asistencia.nueva_jornada(otra, gestor, HOY, time(9), time(10))
    r = cg.post(f"/actividades/{taller.pk}/gastos/{g.pk}/editar", _datos(sesion=jo.pk))
    assert r.status_code == 200
    g.refresh_from_db()
    assert g.sesion == j2


def test_GA_E4_gasto_revisado_no_se_edita_se_anula_y_se_registra_otro(cg, taller):
    _registrar(cg, taller, monto=450000)
    g = Movimiento.objects.get()
    assert cg.post(f"/actividades/{taller.pk}/gastos/{g.pk}/revisar", {}).status_code == 302
    g.refresh_from_db()
    assert g.estado == "revisado" and g.revisado_por and g.revisado_en
    assert cg.get(f"/actividades/{taller.pk}/gastos/{g.pk}/editar").status_code == 302  # no abre el formulario
    r = cg.post(f"/actividades/{taller.pk}/gastos/{g.pk}/editar", _datos(monto=45000))
    g.refresh_from_db()
    assert r.status_code == 302 and g.monto == 450000  # el servidor lo rechaza
    cg.post(f"/actividades/{taller.pk}/gastos/{g.pk}/anular", {"motivo": ""})
    g.refresh_from_db()
    assert g.estado == "revisado"  # sin motivo no se anula
    cg.post(f"/actividades/{taller.pk}/gastos/{g.pk}/anular", {"motivo": "Monto mal digitado"})
    g.refresh_from_db()
    assert g.estado == "anulado" and g.anulado and g.motivo_anulacion == "Monto mal digitado"
    _registrar(cg, taller, monto=45000)
    assert gastos_actividad(taller)["total"] == 45000 and Movimiento.objects.count() == 2


def test_GA_E5_traslado_semanal_es_de_la_tarea_sin_jornada(cg, taller):
    _registrar(cg, taller, concepto="Traslado semanal", categoria=CategoriaGasto.objects.get(codigo="traslado").pk, monto=30000)
    g = Movimiento.objects.get()
    assert g.sesion is None and g.actividad == taller
    assert gastos_actividad(taller)["grupos"][0]["jornada"] is None


def test_GA_E6_pagado_por_una_voluntaria(cg, taller, crear_persona):
    ana = crear_persona("Ana")
    _registrar(cg, taller, pagado_por=ana.pk)
    g = Movimiento.objects.get()
    assert g.pagado_por == ana
    assert "Pagó" in cg.get(f"{taller.get_absolute_url()}?tab=gastos").content.decode()
    assert not hasattr(Movimiento, "reembolsado")  # el reembolso queda fuera [V]


def test_GA_E7_proyecto_que_supera_su_presupuesto(cg, taller, proyecto):
    ItemPresupuesto.objects.create(proyecto=proyecto, concepto="Colaciones", monto_estimado=40000, categoria="operacional")
    _registrar(cg, taller, monto=45000)
    r = gastos_proyecto(proyecto)
    assert r["excedido"] and r["exceso"] == 5000
    html = cg.get(f"/proyectos/{proyecto.pk}?tab=gastos").content.decode()
    assert "supera el presupuesto en $5.000" in html and "$45.000" in html


def test_GA_E8_comprobante_invalido_se_rechaza(cg, taller):
    casos = [
        (SimpleUploadedFile("a.gif", b"GIF89a" + b"\x00" * 40), "JPG, PNG o WEBP"),
        (SimpleUploadedFile("a.exe", b"MZ" + b"\x00" * 40), "JPG, PNG o WEBP"),
        (SimpleUploadedFile("a.png", PDF), "no es una foto"),  # la extensión no coincide con el contenido
        (SimpleUploadedFile("a.pdf", PNG), "no es una foto"),
        (SimpleUploadedFile("grande.pdf", PDF + b"\x00" * (5 * 1024 * 1024)), "5 MB"),
    ]
    for archivo, mensaje in casos:
        r = _registrar(cg, taller, comprobante=archivo)
        assert r.status_code == 200 and mensaje in r.content.decode(), mensaje
    assert Movimiento.objects.count() == 0
    for nombre, contenido in [("a.pdf", PDF), ("a.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 40), ("a.jpg", b"\xff\xd8\xff" + b"\x00" * 40)]:
        assert _registrar(cg, taller, comprobante=SimpleUploadedFile(nombre, contenido)).status_code == 302


def test_GA_E9_actividad_suelta_sin_proyecto(cg, crear_actividad):
    suelta = crear_actividad("Charla suelta", estado="confirmada")
    assert _registrar(cg, suelta).status_code == 302
    g = Movimiento.objects.get()
    assert g.proyecto is None and g.actividad == suelta
    assert gastos_actividad(suelta)["total"] == 45000
    assert "$45.000" in cg.get(f"/actividades/{suelta.pk}?tab=gastos").content.decode()


def test_GA_E10_quien_solo_ve_no_exporta(cg, ca, administrador, taller, proyecto):
    _registrar(cg, taller)
    assert cg.get(f"/actividades/{taller.pk}/gastos/exportar").status_code == 200
    assert cg.get(f"/proyectos/{proyecto.pk}/gastos/exportar").status_code == 200
    administrador.groups.first().permissions.add(*Permission.objects.filter(codename__in=["view_movimiento"]))
    c = Client()
    c.force_login(type(administrador).objects.get(pk=administrador.pk))
    assert c.get(f"{taller.get_absolute_url()}?tab=gastos").status_code == 200  # puede ver
    assert c.get(f"/actividades/{taller.pk}/gastos/exportar").status_code == 200  # el Administrador sí exporta actividades
    from django.contrib.auth.models import User

    u = User.objects.create_user("solo_ve", password="clave-ficticia-123")
    u.user_permissions.add(*Permission.objects.filter(codename__in=["view_movimiento", "view_actividad", "view_proyecto"]))
    c2 = Client()
    c2.force_login(u)
    assert c2.get(f"/actividades/{taller.pk}/gastos/exportar").status_code == 403
    assert c2.get(f"/proyectos/{proyecto.pk}/gastos/exportar").status_code == 403
    assert c2.post(f"/actividades/{taller.pk}/gastos/nuevo", _datos()).status_code == 403


def test_pestana_gastos_y_resumen_del_proyecto_hacen_consultas_fijas(cg, taller, proyecto, crear_persona):
    j1, j2 = _jornadas(taller)

    def cargar(n):
        for i in range(n):
            _gasto(taller, sesion=j1 if i % 2 else j2, pagado_por=crear_persona(), monto=100 + i)

    def consultas():
        with CaptureQueriesContext(connection) as c:
            gastos_actividad(taller)
            gastos_proyecto(proyecto)
        return len(c)

    cargar(2)
    pocas = consultas()
    cargar(8)
    assert consultas() == pocas
    assert pocas <= 3


def test_gastos_visibles_sin_segunda_fase_y_aportes_ocultos(cg, taller, settings):
    settings.SEGUNDA_FASE = False
    assert cg.get(f"{taller.get_absolute_url()}?tab=gastos").status_code == 200
    assert cg.get("/finanzas").status_code == 404  # aportes y donaciones siguen en la segunda fase
    assert cg.get(f"/proyectos/{taller.proyecto_id}?tab=gastos").status_code == 200


def test_estado_y_anulado_no_se_contradicen(taller):
    g = _gasto(taller)
    g.anulado = True
    g.save()
    assert g.estado == "anulado"

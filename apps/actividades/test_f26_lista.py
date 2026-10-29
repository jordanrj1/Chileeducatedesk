"""Pruebas de F26 P1a (specs/f26/spec.md): «Pasar lista» único en «Equipo y asistencia», asistencia calculada desde las
sesiones y un solo «+ Agregar persona». Todos los datos son ficticios."""
from datetime import date, time, timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.actividades import servicios
from apps.actividades.models import Participacion, SesionActividad
from apps.personas.models import ContactoEmergencia, Persona

pytestmark = pytest.mark.django_db
HOY = date.today()
FUTURO = HOY + timedelta(days=10)


@pytest.fixture
def proyecto(db):
    from apps.proyectos.models import Proyecto

    return Proyecto.objects.create(nombre="Huertos Ficticios")


@pytest.fixture
def tarea_hoy(crear_actividad, proyecto, gestor):
    t = crear_actividad("Visita a la villa", estado="confirmada", proyecto=proyecto)
    servicios.programar(t, gestor, HOY, time(10), time(12), None, None)
    return t


def _p(a, persona, rol, estado, **kw):
    return Participacion.objects.create(actividad=a, persona=persona, rol=rol, estado=estado, **kw)


def _tres(tarea, crear_persona, rol, estado_part):
    return (_p(tarea, crear_persona("Tallerista"), rol("tallerista"), estado_part("confirmado")),
            _p(tarea, crear_persona("Alcaldesa"), rol("autoridad"), estado_part("confirmado")),
            _p(tarea, crear_persona("Vecina"), rol("beneficiario"), estado_part("confirmado")))


# --- Pasar lista ------------------------------------------------------------------------------
def test_pasar_lista_un_formulario_con_todos_por_grupo(cg, tarea_hoy, crear_persona, rol, estado_part):
    equipo, contacto, benef = _tres(tarea_hoy, crear_persona, rol, estado_part)
    erroneo = _p(tarea_hoy, crear_persona("Error"), rol("voluntario"), estado_part("registro_erroneo"))
    html = cg.get(f"{tarea_hoy.get_absolute_url()}?tab=participantes").content.decode()
    lista = html.split('id="pasar-lista"')[1].split("</section>", 1)[0]
    assert lista.count("<form") == 1 and lista.count("Guardar asistencia") == 1
    for etiqueta in ("Equipo ejecutor", "Invitados y contactos", "Beneficiarios", "Sin registro de asistencia", "Todos asistieron", "Marcar todos"):
        assert etiqueta in lista, etiqueta
    for p in (equipo, contacto, benef):
        assert f'name="asistio" value="{p.pk}"' in lista and f'for="asistio-{p.pk}"' in lista  # casilla con su etiqueta
    assert f'value="{erroneo.pk}"' not in lista
    assert "<table" not in lista  # lista apilable, no tabla ancha


def test_guardar_lista_marcada_asistio_y_sin_marcar_no_asistio(cg, tarea_hoy, crear_persona, rol, estado_part):
    equipo, contacto, benef = _tres(tarea_hoy, crear_persona, rol, estado_part)
    fuera = _p(tarea_hoy, crear_persona("Fuera"), rol("voluntario"), estado_part("confirmado"))  # no viene en el formulario
    r = cg.post(f"/actividades/{tarea_hoy.pk}/asistencia", {"en_lista": [equipo.pk, contacto.pk, benef.pk], "asistio": [benef.pk], "sin_registro": "0"})
    assert r.status_code == 302 and r["Location"].endswith("?tab=participantes")
    for p in (equipo, contacto, benef, fuera):
        p.refresh_from_db()
    assert (benef.asistencia, benef.estado.codigo) == (True, "asistio")
    assert (equipo.asistencia, equipo.estado.codigo) == (False, "no_asistio") and contacto.asistencia is False
    assert fuera.asistencia is None  # solo las filas incluidas
    # «Todos asistieron», sin JavaScript
    cg.post(f"/actividades/{tarea_hoy.pk}/asistencia", {"en_lista": [equipo.pk, contacto.pk, benef.pk], "todos": "1"})
    assert set(Participacion.objects.filter(pk__in=[equipo.pk, contacto.pk, benef.pk]).values_list("asistencia", flat=True)) == {True}


def test_sin_registro_no_marca_ausentes(cg, tarea_hoy, crear_persona, rol, estado_part):
    equipo, contacto, benef = _tres(tarea_hoy, crear_persona, rol, estado_part)
    cg.post(f"/actividades/{tarea_hoy.pk}/asistencia", {"en_lista": [equipo.pk, contacto.pk, benef.pk], "sin_registro": "1"})
    tarea_hoy.refresh_from_db()
    assert tarea_hoy.asistencia_sin_registro is True
    assert set(Participacion.objects.filter(actividad=tarea_hoy).values_list("asistencia", flat=True)) == {None}


def test_pasar_lista_solo_desde_el_dia(cg, gestor, crear_actividad, proyecto, crear_persona, rol, estado_part):
    t = crear_actividad("Futura", estado="confirmada", proyecto=proyecto)
    servicios.programar(t, gestor, FUTURO, time(10), time(12), None, None)
    p = _p(t, crear_persona(), rol("tallerista"), estado_part("confirmado"))
    html = cg.get(f"{t.get_absolute_url()}?tab=participantes").content.decode()
    assert 'id="pasar-lista"' in html and f'name="asistio" value="{p.pk}"' not in html and "La asistencia se marca desde el día" in html
    cg.post(f"/actividades/{t.pk}/asistencia", {"en_lista": [p.pk], "asistio": [p.pk]})
    p.refresh_from_db()
    assert p.asistencia is None


def test_lista_apilada_en_pantalla_angosta():
    css = (Path(settings.BASE_DIR) / "static" / "css" / "fche.css").read_text(encoding="utf-8")
    bloque = css[css.index("F26 P1a"):]
    assert "@media (max-width: 575.98px)" in bloque and ".fche-lista-asistencia__fila { grid-template-columns: 1.5rem minmax(0, 1fr); }" in bloque


def test_equipo_y_asistencia_con_consultas_fijas(cg, gestor, proyecto, crear_actividad, crear_persona, rol, estado_part):
    medidas = []
    for n in (1, 25):
        t = crear_actividad(f"Tarea {n}", estado="confirmada", proyecto=proyecto)
        servicios.programar(t, gestor, HOY, time(10), time(11), None, None)
        for i in range(n):
            _p(t, crear_persona(), rol("beneficiario" if i % 2 else "tallerista"), estado_part("confirmado"))
        SesionActividad.objects.create(actividad=t, numero=1, fecha=HOY, hora_inicio=time(10))
        url = f"{t.get_absolute_url()}?tab=participantes"
        cg.get(url)
        with CaptureQueriesContext(connection) as c:
            r = cg.get(url)
        assert r.status_code == 200 and 'id="pasar-lista"' in r.content.decode()
        medidas.append(len(c.captured_queries))
    assert medidas[0] == medidas[1], medidas


def test_beneficiarios_muestra_asistencia_y_enlaza_a_pasar_lista(cg, tarea_hoy, crear_persona, rol, estado_part):
    b = _p(tarea_hoy, crear_persona("Vecina"), rol("beneficiario"), estado_part("asistio"), asistencia=True)
    html = cg.get(f"{tarea_hoy.get_absolute_url()}?tab=beneficiarios").content.decode()
    assert "Asistió" in html and 'href="?tab=participantes#pasar-lista"' in html and "Pasar lista" in html
    assert f'name="asistencia_{b.pk}"' not in html and 'name="asistio"' not in html  # solo lectura
    assert f'href="/actividades/{tarea_hoy.pk}/participantes/nuevo?rol=beneficiario' in html  # «+ Registrar beneficiario»


# --- Asistencia desde las sesiones -------------------------------------------------------------
def test_asistencia_calculada_desde_las_sesiones_y_corregible(cg, tarea_hoy, crear_persona, rol, estado_part):
    a, b, c = (_p(tarea_hoy, crear_persona(n), rol("beneficiario"), estado_part("confirmado")) for n in ("Uno", "Dos", "Tres"))
    s1 = SesionActividad.objects.create(actividad=tarea_hoy, numero=1, fecha=HOY, hora_inicio=time(10))
    s2 = SesionActividad.objects.create(actividad=tarea_hoy, numero=2, fecha=HOY, hora_inicio=time(15))
    cg.post(f"/actividades/{tarea_hoy.pk}/sesiones/{s1.pk}/asistencia", {f"asistio_{a.pk}": "no", f"asistio_{b.pk}": "no", f"asistio_{c.pk}": ""})
    b.refresh_from_db()
    assert b.asistencia is False  # ausente en la única sesión con lista
    cg.post(f"/actividades/{tarea_hoy.pk}/sesiones/{s2.pk}/asistencia", {f"asistio_{a.pk}": "si", f"asistio_{b.pk}": "no", f"asistio_{c.pk}": ""})
    for p in (a, b, c):
        p.refresh_from_db()
    assert (a.asistencia, a.estado.codigo) == (True, "asistio")  # vino al menos a una
    assert (b.asistencia, b.estado.codigo) == (False, "no_asistio")  # faltó a todas
    assert c.asistencia is None  # sin datos de sesiones: no se toca
    html = cg.get(f"{tarea_hoy.get_absolute_url()}?tab=participantes").content.decode()
    assert "Calculada desde las sesiones" in html
    # corrección manual desde «Pasar lista»
    cg.post(f"/actividades/{tarea_hoy.pk}/asistencia", {"en_lista": [a.pk, b.pk, c.pk], "asistio": [a.pk, b.pk]})
    b.refresh_from_db()
    assert b.asistencia is True


# --- Un solo «+ Agregar persona» -----------------------------------------------------------------
def test_un_solo_boton_agregar_persona(cg, tarea_hoy, crear_persona, rol, estado_part):
    _tres(tarea_hoy, crear_persona, rol, estado_part)
    html = cg.get(f"{tarea_hoy.get_absolute_url()}?tab=participantes").content.decode()
    assert html.count("+ Agregar persona") == 1
    for duplicado in ("Crear persona nueva", "Agregar persona que llegó", "Crear y marcar asistencia"):
        assert duplicado not in html, duplicado


def test_formulario_unico_y_guardar_y_agregar_otra(cg, tarea_hoy, crear_persona, rol, estado_part, tipo_org, comuna):
    from apps.comunidades.models import Comunidad
    from apps.organizaciones.models import Organizacion

    junta = Organizacion.objects.create(nombre="Junta Ficticia", tipo=tipo_org("junta_de_vecinos_o_comite"))
    comunidad = Comunidad.objects.create(nombre="Vecinos Ficticios", comuna=comuna)
    url = f"/actividades/{tarea_hoy.pk}/participantes/nuevo"
    form = cg.get(url).content.decode()
    for texto in ("¿De qué grupo viene?", "Cargo o función", "Llegó / asistió", "Si es menor de edad", "Guardar y agregar otra", "crear=1"):
        assert texto in form, texto
    import re

    valores = re.search(r'data-mostrar-si-campo="rol" data-mostrar-si-valor="([0-9 ]+)"', form).group(1).split()
    assert str(rol("beneficiario").pk) in valores and str(rol("tallerista").pk) not in valores  # el bloque de menor, con rol de «Asistentes»
    datos = {"persona": crear_persona("Primera").pk, "rol": rol("beneficiario").pk, "estado": estado_part("confirmado").pk,
             "organizacion": junta.pk, "comunidad": comunidad.pk, "llego": "on", "volver": "beneficiarios", "otra": "1"}
    r = cg.post(url, datos)
    assert r.status_code == 302 and r["Location"].startswith(url + "?")
    p = Participacion.objects.get(actividad=tarea_hoy, persona__nombres="Primera")
    assert (p.asistencia, p.estado.codigo, p.institucion, p.comunidad) == (True, "asistio", junta, comunidad)
    siguiente = cg.get(r["Location"])
    f = siguiente.context["form"]
    assert (f["rol"].value(), f["organizacion"].value(), f["comunidad"].value(), f["llego"].value()) == (rol("beneficiario").pk, junta.pk, comunidad.pk, True)
    assert siguiente.context["volver_url"].endswith("?tab=beneficiarios")


def test_menor_beneficiario_pide_apoderado_y_lo_registra(cg, tarea_hoy, crear_persona, rol, estado_part):
    menor = crear_persona("Tomasito", fecha_nacimiento=HOY - timedelta(days=365 * 10))
    url = f"/actividades/{tarea_hoy.pk}/participantes/nuevo"
    datos = {"persona": menor.pk, "rol": rol("beneficiario").pk, "estado": estado_part("confirmado").pk}
    r = cg.post(url, datos)
    assert r.status_code == 400 and not Participacion.objects.filter(persona=menor).exists()
    assert 'data-mostrar-si-campo="rol"' not in r.content.decode()  # es menor: el bloque se ve sin depender del rol
    r = cg.post(url, {**datos, "apoderado_nombre": "Madre Ficticia", "apoderado_parentesco": "madre", "apoderado_telefono": "9 1111 2222"})
    assert r.status_code == 302
    c = ContactoEmergencia.objects.get(persona=menor)
    assert (c.nombre, c.parentesco, c.telefono_normalizado) == ("Madre Ficticia", "madre", "+56911112222")
    # ya tiene contacto de emergencia: con otro rol del grupo «Asistentes» no se vuelve a pedir
    r = cg.post(url, {"persona": menor.pk, "rol": rol("participante").pk, "estado": estado_part("confirmado").pk, "otro_rol": "on"})
    assert r.status_code == 302


def test_sin_permiso_de_sensibles_no_hay_bloque_de_menor(tarea_hoy, crear_persona, rol, estado_part):
    u = User.objects.create_user("digitador_ficticio", password="clave-ficticia-123")
    u.user_permissions.add(*Permission.objects.filter(content_type__app_label="actividades", codename__in=["add_participacion", "view_actividad"]))
    c = Client()
    c.force_login(u)
    url = f"/actividades/{tarea_hoy.pk}/participantes/nuevo"
    r = c.get(url)
    assert r.status_code == 200 and "Si es menor de edad" not in r.content.decode() and "apoderado_nombre" not in r.content.decode()
    menor = crear_persona("Menor", fecha_nacimiento=HOY - timedelta(days=365 * 8))
    r = c.post(url, {"persona": menor.pk, "rol": rol("beneficiario").pk, "estado": estado_part("confirmado").pk, "apoderado_nombre": "X", "apoderado_telefono": "9 1111 2222"})
    assert r.status_code == 302 and not ContactoEmergencia.objects.filter(persona=menor).exists()


def test_rutas_antiguas_llevan_al_formulario_unico(cg, tarea_hoy, rol):
    r = cg.get(f"/actividades/{tarea_hoy.pk}/beneficiarios/registrar")
    assert r.status_code == 302 and r["Location"].startswith(f"/actividades/{tarea_hoy.pk}/participantes/nuevo?rol=beneficiario")
    assert "llego=1" in r["Location"] and "volver=beneficiarios" in r["Location"]  # la tarea es hoy: queda «Asistió», como antes
    r = cg.get(f"/actividades/{tarea_hoy.pk}/participantes/rapido?llego=1")
    assert r.status_code == 302 and r["Location"] == f"/actividades/{tarea_hoy.pk}/participantes/nuevo?llego=1"
    assert Persona.objects.count() == 0

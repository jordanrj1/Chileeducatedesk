"""Pruebas de F26 P3a (specs/f26/spec.md, «Paquete 3 · Ficha 360° y orden»): resumen 360° de la persona, la actividad
suelta con las ocho pestañas de la tarea (y sus direcciones antiguas), Coordinación dentro de Información, «Finalizar
proyecto» con su informe en Excel e indicadores por período en el Inicio. Todos los datos son ficticios."""
import re
from datetime import date, time, timedelta
from io import BytesIO

import pytest
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from openpyxl import load_workbook

from apps.actividades import servicios
from apps.actividades.models import ActividadOrganizacion, Participacion
from apps.comunidades.models import Comunidad, ComunidadMiembro
from apps.coordinacion.models import Interaccion
from apps.nucleo.models import Canal, EstadoActividad, RolOrganizacion
from apps.personas.models import PersonaFormacion, PersonaOrganizacion
from apps.proyectos.models import Proyecto

pytestmark = pytest.mark.django_db
HOY = date.today()
OCHO = ["info", "participantes", "beneficiarios", "organizaciones", "sesiones", "resultados", "documentos", "historial"]


def _claves(html):
    return re.findall(r'<a class="nav-link[^"]*" href="\?tab=([a-z_]+)"', html)


def _activa(html):
    return re.search(r'class="nav-link active" href="\?tab=([a-z_]+)"', html).group(1)


def _consultas(cliente, url):
    with CaptureQueriesContext(connection) as c:
        r = cliente.get(url)
    assert r.status_code == 200, url
    return len(c.captured_queries)


def _realizar(a):
    a.estado = EstadoActividad.objects.get(codigo="realizada")
    a.save()


def _usuario(nombre, *permisos):
    u = User.objects.create_user(nombre, email=f"{nombre}@ejemplo.invalid", password="clave-ficticia-123")
    for codigo in permisos:
        u.user_permissions.add(Permission.objects.get(codename=codigo))
    c = Client()
    c.force_login(u)
    return c


# --- 1. Resumen 360° de la persona -------------------------------------------------------------
def _vincular_todo(persona, universidad, comuna, crear_actividad, rol, estado_part, n=1):
    PersonaOrganizacion.objects.create(persona=persona, organizacion=universidad, cargo="Encargada ficticia",
                                       rol=RolOrganizacion.objects.order_by("pk").first())
    PersonaFormacion.objects.create(persona=persona, organizacion=universidad, vigente=True)
    for i in range(n):
        com = Comunidad.objects.create(nombre=f"Junta Ficticia {i}", comuna=comuna, tipo="vecinal")
        ComunidadMiembro.objects.create(comunidad=com, persona=persona)
        a = crear_actividad(f"Taller ficticio {i}", estado="planificada")
        Participacion.objects.create(actividad=a, persona=persona, rol=rol("tallerista"), estado=estado_part("confirmado"))


def test_resumen_360_muestra_vinculos_participaciones_proxima_y_faltantes(cg, persona, universidad, comuna, lugar, gestor,
                                                                          crear_actividad, rol, estado_part):
    _vincular_todo(persona, universidad, comuna, crear_actividad, rol, estado_part, n=4)
    proxima = crear_actividad("Feria futura", estado="planificada")
    Participacion.objects.create(actividad=proxima, persona=persona, rol=rol("voluntario"), estado=estado_part("confirmado"))
    servicios.programar(proxima, gestor, HOY + timedelta(days=3), time(10), time(12), lugar, None)
    html = cg.get(persona.get_absolute_url()).content.decode()
    bloque = html[html.index('id="resumen-360"'):html.index('id="resumen-datos"')]
    assert universidad.nombre in bloque and "Encargada ficticia" in bloque
    assert "Junta Ficticia 0" in bloque and "Junta Ficticia 3" in bloque
    assert "Feria futura" in bloque and proxima.get_absolute_url() in bloque
    assert bloque.count("Taller ficticio") + bloque.count("Feria futura") >= 3 and "Últimas participaciones" in bloque
    assert "Le falta" in bloque and "un contacto" in bloque and "comuna de residencia" in bloque


def test_resumen_360_con_consultas_fijas(cg, crear_persona, universidad, comuna, crear_actividad, rol, estado_part):
    pocos, muchos = crear_persona("Pocos"), crear_persona("Muchos")
    _vincular_todo(pocos, universidad, comuna, crear_actividad, rol, estado_part, n=1)
    _vincular_todo(muchos, universidad, comuna, crear_actividad, rol, estado_part, n=8)
    assert _consultas(cg, pocos.get_absolute_url()) == _consultas(cg, muchos.get_absolute_url())


# --- 2. Actividad suelta con las ocho pestañas ------------------------------------------------
def test_actividad_suelta_tiene_las_ocho_pestanas_y_alias_viejos(cg, actividad):
    url = actividad.get_absolute_url()
    assert _claves(cg.get(url).content.decode()) == OCHO
    esperado = {"agenda": "info", "publico": "info", "coordinacion": "info", "alcance": "resultados", "origen": "historial",
                "asistencia": "participantes", "beneficiarios": "beneficiarios"}
    for vieja, nueva in esperado.items():
        assert _activa(cg.get(f"{url}?tab={vieja}").content.decode()) == nueva, vieja
    cierre = cg.get(f"{url}?tab=alcance").content.decode()
    assert 'id="titulo-alcance"' in cierre and "Total alcanzado" in cierre  # el Alcance sigue a la vista, en Cierre
    historial = cg.get(f"{url}?tab=origen").content.decode()
    assert "Origen de la información" in historial


def test_coordinacion_dentro_de_informacion_solo_en_la_suelta(cg, actividad, crear_actividad):
    canal = Canal.objects.order_by("pk").first()
    Interaccion.objects.create(canal=canal, actividad=actividad, resultado="Llamada ficticia a la junta")
    info = cg.get(f"{actividad.get_absolute_url()}?tab=coordinacion").content.decode()
    assert _activa(info) == "info" and 'id="titulo-coordinacion"' in info and "Llamada ficticia a la junta" in info
    assert "+ Nueva interacción" in info and "Fecha y reprogramaciones" in info and "Comunidades destinatarias" in info
    tarea = crear_actividad("Tarea ficticia", estado="planificada", proyecto=Proyecto.objects.create(nombre="Proyecto Ficticio"))
    Interaccion.objects.create(canal=canal, actividad=tarea, resultado="Correo ficticio de la tarea")
    info_tarea = cg.get(tarea.get_absolute_url()).content.decode()
    assert 'id="titulo-coordinacion"' not in info_tarea and "Correo ficticio de la tarea" not in info_tarea


# --- 3. Finalizar proyecto -------------------------------------------------------------------
@pytest.fixture
def proyecto_con_tareas(crear_actividad, crear_persona, universidad, rol, estado_part):
    pr = Proyecto.objects.create(nombre="Huertos Ficticios", estado="ejecucion")
    hecha = crear_actividad("Tarea hecha", estado="planificada", proyecto=pr)
    abierta = crear_actividad("Tarea abierta", estado="planificada", proyecto=pr)
    _realizar(hecha)
    adulta = crear_persona("Adulta", rut_numero=11111111, rut_dv="1", fecha_nacimiento=HOY.replace(year=HOY.year - 40))
    nina = crear_persona("Nina", fecha_nacimiento=HOY.replace(year=HOY.year - 10))
    Participacion.objects.create(actividad=hecha, persona=adulta, rol=rol("tallerista"), estado=estado_part("confirmado"), asistencia=True)
    Participacion.objects.create(actividad=hecha, persona=nina, rol=rol("beneficiario"), estado=estado_part("confirmado"), asistencia=True)
    ActividadOrganizacion.objects.create(actividad=hecha, organizacion=universidad)
    return pr, hecha, abierta


def test_finalizar_proyecto_avisa_tareas_abiertas_y_sugiere_estado(cg, proyecto_con_tareas):
    pr, hecha, abierta = proyecto_con_tareas
    ficha = cg.get(pr.get_absolute_url()).content.decode()
    assert f"/proyectos/{pr.pk}/finalizar" in ficha and "Finalizar proyecto" in ficha
    r = cg.get(f"/proyectos/{pr.pk}/finalizar")
    html = r.content.decode()
    assert "Queda <strong>1</strong>"  # F26 P: plural correcto in html and abierta.get_absolute_url() in html and "Tarea hecha" not in html.split("Estado sugerido")[0]
    assert r.context["form"].initial["estado"] == "suspendido"  # se sugiere, no se impone
    _realizar(abierta)
    r = cg.get(f"/proyectos/{pr.pk}/finalizar")
    assert r.context["form"].initial["estado"] == "finalizado" and "Todas sus tareas" in r.content.decode()
    assert cg.post(f"/proyectos/{pr.pk}/finalizar", {"estado": "finalizado", "conclusion": ""}).status_code == 200  # la conclusión es obligatoria
    r = cg.post(f"/proyectos/{pr.pk}/finalizar", {"estado": "ejecucion", "conclusion": "Se lograron los huertos ficticios."})
    pr.refresh_from_db()
    assert r.status_code == 302 and pr.estado == "ejecucion" and pr.conclusion == "Se lograron los huertos ficticios."  # elige el usuario
    assert "Se lograron los huertos ficticios." in cg.get(pr.get_absolute_url()).content.decode()


def test_finalizar_proyecto_exige_editar(proyecto_con_tareas):
    pr = proyecto_con_tareas[0]
    solo_ver = _usuario("solo_ver_proyecto", "view_proyecto")
    assert solo_ver.get(f"/proyectos/{pr.pk}/finalizar").status_code == 403
    assert solo_ver.post(f"/proyectos/{pr.pk}/finalizar", {"estado": "finalizado", "conclusion": "x"}).status_code == 403


def _libro(r):
    return load_workbook(BytesIO(r.content))


def test_informe_excel_con_permiso_y_sin_el(cg, proyecto_con_tareas):
    pr = proyecto_con_tareas[0]
    r = cg.get(f"/proyectos/{pr.pk}/informe")  # el Gestor exporta y tiene exportar_persona
    assert r.status_code == 200 and "attachment" in r["Content-Disposition"]
    libro = _libro(r)
    assert libro.sheetnames == ["Tareas", "Asistencia", "Alcance", "Aliados", "Aviso"]
    tareas = [f[0] for f in libro["Tareas"].iter_rows(min_row=2, values_only=True)]
    assert set(tareas) == {"Tarea hecha", "Tarea abierta"}
    asistencia = list(libro["Asistencia"].iter_rows(values_only=True))
    assert asistencia[0] == ("Persona", "Tarea", "Rol", "Asistió", "RUT") and any("Nina" in str(f[0]) for f in asistencia)
    assert any(f[0] == "Universidad Ficticia" for f in libro["Aliados"].iter_rows(values_only=True))
    # sin exportar_persona: sin RUT y la menor no se nombra
    sin_rut = _usuario("exporta_proyectos", "view_proyecto", "exportar_proyecto")
    libro = _libro(sin_rut.get(f"/proyectos/{pr.pk}/informe"))
    filas = list(libro["Asistencia"].iter_rows(values_only=True))
    assert filas[0] == ("Persona", "Tarea", "Rol", "Asistió") and not any("Nina" in str(f[0]) for f in filas)
    assert any("Menores de edad" in str(f[0]) for f in filas) and not any("11111111" in str(c) for f in filas for c in f)
    # sin permiso de exportar: 403
    assert _usuario("solo_ver", "view_proyecto").get(f"/proyectos/{pr.pk}/informe").status_code == 403


def test_informe_con_consultas_fijas(cg, crear_actividad, crear_persona, rol, estado_part):
    medidas = []
    for n in (1, 6):
        pr = Proyecto.objects.create(nombre=f"Proyecto {n}")
        for i in range(n):
            t = crear_actividad(f"Tarea {n}-{i}", estado="planificada", proyecto=pr)
            Participacion.objects.create(actividad=t, persona=crear_persona(), rol=rol("beneficiario"), estado=estado_part("confirmado"))
        medidas.append(_consultas(cg, f"/proyectos/{pr.pk}/informe"))
    assert medidas[0] == medidas[1]


# --- 4. Indicadores por período en el Inicio --------------------------------------------------
def _realizada_hoy(crear_actividad, gestor, lugar, persona, rol, estado_part, nombre, proyecto=None):
    a = crear_actividad(nombre, estado="planificada", proyecto=proyecto)
    servicios.programar(a, gestor, HOY, time(9), time(11), lugar, None)
    Participacion.objects.create(actividad=a, persona=persona, rol=rol("beneficiario"), estado=estado_part("confirmado"), asistencia=True, horas=2)
    _realizar(a)
    return a


def test_indicadores_del_periodo(cg, gestor, lugar, crear_actividad, crear_persona, universidad, rol, estado_part):
    vecina = crear_persona("Vecina")
    a = _realizada_hoy(crear_actividad, gestor, lugar, vecina, rol, estado_part, "Charla ficticia")
    _realizada_hoy(crear_actividad, gestor, lugar, vecina, rol, estado_part, "Tarea ficticia", Proyecto.objects.create(nombre="P"))
    ActividadOrganizacion.objects.create(actividad=a, organizacion=universidad)
    crear_actividad("Sin realizar", estado="planificada")
    for periodo in ("mes", "trimestre", "anio"):
        r = cg.get(f"/dashboard?periodo={periodo}")
        ind = r.context["periodo"]
        valores = {k["titulo"]: k["valor"] for k in ind["items"]}
        assert ind["periodo"] == periodo
        assert valores == {"Realizadas": 2, "Personas alcanzadas": 1, "Horas": 4, "Organizaciones aliadas": 1, "Comunas atendidas": 1}
        assert "1 actividades y 1 tareas" in r.content.decode()
    html = cg.get("/dashboard?periodo=otro").content.decode()  # un valor desconocido vale «mes», sin error
    assert "Indicadores del período" in html and 'href="?periodo=trimestre#indicadores-periodo"' in html


def test_indicadores_del_periodo_con_consultas_fijas(cg, gestor, lugar, crear_actividad, crear_persona, rol, estado_part):
    _realizada_hoy(crear_actividad, gestor, lugar, crear_persona(), rol, estado_part, "Primera")
    antes = _consultas(cg, "/dashboard?periodo=anio")
    for i in range(5):
        _realizada_hoy(crear_actividad, gestor, lugar, crear_persona(), rol, estado_part, f"Otra {i}")
    assert _consultas(cg, "/dashboard?periodo=anio") == antes


def test_indicadores_del_periodo_sin_permiso_no_aparecen(sin_rol):
    from apps.nucleo.tablero import indicadores_periodo

    assert indicadores_periodo(sin_rol) is None

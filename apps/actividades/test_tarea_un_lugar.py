"""Pruebas de F25 F: la tarea en un solo lugar (specs/f25/spec.md, sección F).
F1 ocho pestañas en la tarea (las actividades sueltas no cambian) · F2 Equipo y asistencia, Beneficiarios y su registro
(con el apoderado de un menor) · F3 cargo o función libre y roles «Invitado o invitada» y «Autoridad» · F4 resultados de
las tareas en el Resumen del proyecto. Todos los datos son ficticios."""
import re
from datetime import date, time, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.actividades import servicios
from apps.actividades.models import Participacion
from apps.personas.models import ContactoEmergencia, Persona

pytestmark = pytest.mark.django_db
HOY = date.today()
FUTURO = HOY + timedelta(days=10)


@pytest.fixture
def proyecto(db):
    from apps.proyectos.models import Proyecto

    return Proyecto.objects.create(nombre="Huertos Ficticios")


@pytest.fixture
def tarea(crear_actividad, proyecto):
    return crear_actividad("Visita a la villa", estado="planificada", proyecto=proyecto)


def _pestanas(html):
    """Etiquetas de las pestañas de la ficha, en orden."""
    return [t.strip() for t in re.findall(r'<a class="nav-link[^"]*" href="\?tab=[a-z_]+"[^>]*>(.*?)</a>', html, re.S)]


def _activa(html):
    """Clave de la pestaña abierta."""
    return re.search(r'class="nav-link active" href="\?tab=([a-z_]+)"', html).group(1)


def _participar(a, persona, rol, estado, **kw):
    return Participacion.objects.create(actividad=a, persona=persona, rol=rol, estado=estado, **kw)


# --- F1 · pestañas ------------------------------------------------------------------
def test_tarea_tiene_exactamente_ocho_pestanas_y_la_suelta_conserva_las_suyas(cg, tarea, actividad):
    assert _pestanas(cg.get(tarea.get_absolute_url()).content.decode()) == [
        "Información", "Equipo y asistencia", "Beneficiarios", "Organizaciones", "Sesiones", "Cierre", "Documentos", "Historial"]
    # la misma tarea abierta por /actividades/<id> también es tarea
    assert "Equipo y asistencia" in _pestanas(cg.get(f"/actividades/{tarea.pk}").content.decode())
    sueltas = _pestanas(cg.get(actividad.get_absolute_url()).content.decode())
    for etiqueta in ("Público y comunidades", "Participantes", "Agenda", "Coordinación", "Resultados", "Alcance", "Origen", "Historial"):
        assert etiqueta in sueltas, etiqueta
    assert "Equipo y asistencia" not in sueltas and "Cierre" not in sueltas


def test_beneficiarios_de_la_tarea_se_ve_sin_segunda_fase(cg, tarea, actividad, sin_segunda_fase):
    assert "Beneficiarios" in _pestanas(cg.get(tarea.get_absolute_url()).content.decode())
    assert "Beneficiarios" not in _pestanas(cg.get(actividad.get_absolute_url()).content.decode())  # la suelta sigue como estaba


def test_tab_agenda_en_una_tarea_abre_informacion_con_el_historial_de_reprogramaciones(cg, gestor, tarea, lugar):
    servicios.programar(tarea, gestor, FUTURO, time(10), time(12), lugar, None)
    servicios.programar(tarea, gestor, FUTURO + timedelta(days=1), time(10), time(12), lugar, None, "La sede no estaba disponible")
    html = cg.get(f"{tarea.get_absolute_url()}?tab=agenda").content.decode()
    assert _activa(html) == "info" and "Fecha y reprogramaciones" in html
    assert "La sede no estaba disponible" in html and gestor.get_username() in html and "v1" in html and "v2" in html
    assert "Público y comunidades" in html and "Comunidades destinatarias" in html  # público también en Información
    for antigua in ("publico", "coordinacion", "alcance"):
        assert _activa(cg.get(f"{tarea.get_absolute_url()}?tab={antigua}").content.decode()) == "info", antigua
    assert _activa(cg.get(f"{tarea.get_absolute_url()}?tab=asistencia").content.decode()) == "participantes"
    historial = cg.get(f"{tarea.get_absolute_url()}?tab=origen").content.decode()
    assert _activa(historial) == "historial" and "Cambios de la actividad" in historial and "Origen de la información" in historial


# --- F2 · Equipo y asistencia, Beneficiarios ----------------------------------------
def test_equipo_y_asistencia_separa_equipo_e_invitados_y_beneficiarios_va_aparte(cg, tarea, crear_persona, rol, estado_part):
    _participar(tarea, crear_persona("Tallerista"), rol("tallerista"), estado_part("confirmado"))
    _participar(tarea, crear_persona("Alcalde"), rol("autoridad"), estado_part("confirmado"), cargo="Alcalde de Comuna Ficticia")
    _participar(tarea, crear_persona("Vecina", fecha_nacimiento=HOY.replace(year=HOY.year - 30) - timedelta(days=1)), rol("beneficiario"),
                estado_part("confirmado"))
    equipo = cg.get(f"{tarea.get_absolute_url()}?tab=participantes").content.decode()
    assert "Equipo ejecutor" in equipo and "Invitados y contactos" in equipo
    assert "Tallerista" in equipo and "Autoridad · Alcalde de Comuna Ficticia" in equipo and "Vecina" not in equipo
    benef = cg.get(f"{tarea.get_absolute_url()}?tab=beneficiarios").content.decode()
    assert "Vecina" in benef and "Tallerista" not in benef and "30 años" in benef and "Inscrito" in benef
    assert "+ Registrar beneficiario" in benef


def test_registrar_beneficiario_menor_crea_su_contacto_de_emergencia(cg, tarea, comuna, rol):
    url = f"/actividades/{tarea.pk}/beneficiarios/registrar"
    assert "Si es menor de edad" in cg.get(url).content.decode()
    datos = {"nombres": "Tomasito", "apellido_paterno": "Ficticio", "sin_rut": "on", "comuna": comuna.pk, "rol": rol("beneficiario").pk,
             "fecha_nacimiento": (HOY - timedelta(days=365 * 10)).isoformat()}
    r = cg.post(url, datos)  # menor (por la fecha) sin apoderado: se pide
    assert r.status_code == 400 and not Persona.objects.filter(nombres="Tomasito").exists()
    r = cg.post(url, {**datos, "apoderado_nombre": "Madre Ficticia", "apoderado_parentesco": "madre", "apoderado_telefono": "9 1111 2222"})
    assert r.status_code == 302 and r["Location"].endswith("?tab=beneficiarios")
    p = Participacion.objects.get(actividad=tarea, persona__nombres="Tomasito")
    assert p.rol.codigo == "beneficiario" and p.estado.codigo == "confirmado" and p.asistencia is None  # la tarea aún no tiene fecha pasada
    c = ContactoEmergencia.objects.get(persona=p.persona)
    assert (c.nombre, c.parentesco, c.telefono_normalizado) == ("Madre Ficticia", "madre", "+56911112222")


def test_registrar_beneficiario_el_dia_de_la_tarea_queda_asistio_y_usar_persona_no_duplica(cg, gestor, tarea, rol):
    servicios.programar(tarea, gestor, HOY, time(10), time(12), None, None)
    existente = Persona.objects.create(nombres="Rosa", apellido_paterno="Inventada")
    url = f"/actividades/{tarea.pk}/beneficiarios/registrar"
    datos = {"nombres": "Rosa", "apellido_paterno": "Inventada", "sin_rut": "on", "rol": rol("participante").pk, "cargo": "Vecina de la Etapa 2"}
    aviso = cg.post(url, datos).content.decode()
    assert "Esta persona podría ya existir" in aviso and "Usar esta persona" in aviso
    r = cg.post(url, {**datos, "usar_persona": existente.pk})
    assert r.status_code == 302
    assert Persona.objects.filter(nombres="Rosa").count() == 1
    p = Participacion.objects.get(actividad=tarea, persona=existente)
    assert p.estado.codigo == "asistio" and p.asistencia is True and p.cargo == "Vecina de la Etapa 2"


def test_pestana_beneficiarios_con_consultas_fijas(cg, gestor, proyecto, crear_actividad, crear_persona, rol, estado_part, comuna):
    from apps.comunidades.models import Comunidad

    comunidad = Comunidad.objects.create(nombre="Vecinos Ficticios", comuna=comuna)
    medidas = []
    for n in (1, 20):
        t = crear_actividad(f"Tarea {n}", estado="confirmada", proyecto=proyecto)
        servicios.programar(t, gestor, HOY, time(10), time(11), None, None)
        for i in range(n):
            per = crear_persona(fecha_nacimiento=HOY - timedelta(days=365 * 12))
            ContactoEmergencia.objects.create(persona=per, nombre=f"Apoderada {i}", telefono="+56 9 0000 0000")
            _participar(t, per, rol("beneficiario"), estado_part("asistio"), asistencia=True, comunidad=comunidad, cargo="Estudiante")
        url = f"{t.get_absolute_url()}?tab=beneficiarios"
        cg.get(url)
        with CaptureQueriesContext(connection) as c:
            r = cg.get(url)
        assert r.status_code == 200 and "Apoderada 0" in r.content.decode()
        medidas.append(len(c.captured_queries))
    assert medidas[0] == medidas[1], medidas


# --- F3 · cargo o función libre -------------------------------------------------------
def test_cargo_en_los_formularios_y_roles_nuevos(cg, actividad, persona, rol, estado_part):
    from apps.nucleo.models import RolParticipacion

    assert {r.codigo: (r.nombre, r.grupo) for r in RolParticipacion.objects.filter(codigo__in=["invitado", "autoridad"])} == {
        "invitado": ("Invitado o invitada", "contacto"), "autoridad": ("Autoridad", "contacto")}
    form = cg.get(f"/actividades/{actividad.pk}/participantes/nuevo").content.decode()
    assert "Cargo o función" in form and "Alcalde de Hualpén" in form
    assert "Cargo o función" in cg.get(f"/actividades/{actividad.pk}/participantes/rapido").content.decode()
    r = cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", {"persona": persona.pk, "rol": rol("autoridad").pk,
                                                                        "estado": estado_part("confirmado").pk, "cargo": "Seremi ficticio"})
    assert r.status_code == 302
    p = Participacion.objects.get(actividad=actividad, persona=persona)
    assert p.cargo == "Seremi ficticio" and p.institucion is None  # el cargo libre no exige organización
    assert "Autoridad · Seremi ficticio" in cg.get(f"{actividad.get_absolute_url()}?tab=participantes").content.decode()
    assert "Cargo o función" in cg.get(f"/actividades/{actividad.pk}/participantes/{p.pk}/editar").content.decode()


# --- F4 · resultados en el proyecto ---------------------------------------------------
def test_resumen_del_proyecto_muestra_resultados_de_las_tareas_con_consultas_fijas(cg, gestor, proyecto, crear_actividad):
    medidas = []
    for n in (1, 10):
        for i in range(n):
            t = crear_actividad(f"Tarea {n}-{i}", estado="confirmada", proyecto=proyecto, resultado=f"Se logró el objetivo {n}-{i}")
            servicios.programar(t, gestor, FUTURO, time(10), time(11), None, None)
        cg.get(proyecto.get_absolute_url())
        with CaptureQueriesContext(connection) as c:
            html = cg.get(proyecto.get_absolute_url()).content.decode()
        medidas.append(len(c.captured_queries))
    assert "Resultados de las tareas" in html and "Se logró el objetivo 10-9" in html and FUTURO.strftime("%d-%m-%Y") in html
    assert medidas[0] == medidas[1], medidas

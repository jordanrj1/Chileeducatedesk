"""Pruebas de F25: tareas del proyecto (crear en un paso, pestaña Tareas, calendario y listado de actividades)
y ficha rápida de terreno para participantes (RUT, comuna, organización con cargo y comunidad).
Todos los datos son ficticios."""
from datetime import date, time, timedelta

import pytest

from apps.actividades.models import Actividad, Participacion, SesionActividad, SesionAsistencia

pytestmark = pytest.mark.django_db
FUTURO = date.today() + timedelta(days=7)


@pytest.fixture
def proyecto(db):
    from apps.proyectos.models import Proyecto

    return Proyecto.objects.create(nombre="Huertos Ficticios")


@pytest.fixture
def comunidad(comuna):
    from apps.comunidades.models import Comunidad

    return Comunidad.objects.create(nombre="Vecinos Ficticios", comuna=comuna)


@pytest.fixture
def junta(tipo_org):
    from apps.organizaciones.models import Organizacion

    return Organizacion.objects.create(nombre="Junta Ficticia", tipo=tipo_org("junta_de_vecinos_o_comite"))


def _tarea(cg, proyecto, **extra):
    datos = {"nombre": "Visita a la villa", "objetivo": "Conocer a las familias", "fecha": FUTURO.isoformat(), "hora_inicio": "10:00", "hora_fin": "12:00"}
    datos.update(extra)
    return cg.post(f"/proyectos/{proyecto.pk}/tareas/nueva", datos)


# --- Criterio 1: tarea completa ----------------------------------------------------
def test_nueva_tarea_en_un_paso_queda_programada_con_comunidad(cg, proyecto, comunidad, lugar):
    assert "Nueva tarea" in cg.get(f"/proyectos/{proyecto.pk}/tareas/nueva").content.decode()
    r = _tarea(cg, proyecto, lugar=lugar.pk, comunidad=comunidad.pk)
    t = Actividad.objects.get()
    assert r.status_code == 302 and r["Location"] == t.get_absolute_url()
    assert t.proyecto == proyecto and t.estado.codigo == "planificada"
    assert t.agenda_vigente.fecha == FUTURO and t.agenda_vigente.lugar == lugar
    assert t.comunidades_destino.filter(comunidad=comunidad).exists() and t.territorios.filter(comuna=comunidad.comuna).exists()
    html = cg.get(f"/proyectos/{proyecto.pk}?tab=actividades").content.decode()
    assert "Tareas" in html and "Visita a la villa" in html and "+ Nueva tarea" in html and comunidad.nombre in html
    ficha = cg.get(t.get_absolute_url()).content.decode()
    assert t.get_absolute_url() == f"/proyectos/{proyecto.pk}/tareas/{t.pk}"  # la tarea se abre dentro de su proyecto
    assert "Tarea del proyecto" in ficha and f'href="{proyecto.get_absolute_url()}?tab=tareas"' in ficha and "Editar tarea" in ficha


def test_tarea_sin_hora_no_se_guarda_y_no_queda_a_medias(cg, proyecto):
    r = _tarea(cg, proyecto, hora_inicio="", hora_fin="")
    assert r.status_code == 200 and not Actividad.objects.exists()


def test_actividades_muestra_actividades_y_tareas_con_filtro_y_calendario(cg, proyecto, crear_actividad):
    """/actividades muestra las actividades sueltas y las tareas de proyectos; «Qué ver» separa unas de otras."""
    _tarea(cg, proyecto)
    crear_actividad("Charla suelta")
    html = cg.get("/actividades").content.decode()
    assert "Charla suelta" in html and "Visita a la villa" in html
    solo_sueltas = cg.get("/actividades?tareas=no").content.decode()
    assert "Charla suelta" in solo_sueltas and "Visita a la villa" not in solo_sueltas
    solo_tareas = cg.get("/actividades?tareas=solo").content.decode()
    assert "Visita a la villa" in solo_tareas and "Charla suelta" not in solo_tareas
    assert "Visita a la villa" in cg.get(f"/proyectos/{proyecto.pk}?tab=actividades").content.decode()  # enlace antiguo sigue sirviendo
    eventos = cg.get(f"/calendario/eventos?start={FUTURO}&end={FUTURO + timedelta(days=1)}").json()
    assert [e["title"] for e in eventos] == ["Tarea · Huertos Ficticios · Visita a la villa"]


def test_pestana_tareas_con_consultas_fijas(cg, proyecto, crear_actividad, crear_persona, rol, estado_part, django_assert_max_num_queries):
    for i in range(3):
        t = crear_actividad(f"Tarea {i}", proyecto=proyecto)
        Participacion.objects.create(actividad=t, persona=crear_persona(), rol=rol("voluntario"), estado=estado_part("asistio"), asistencia=True)
    cg.get(f"/proyectos/{proyecto.pk}?tab=actividades")  # calienta caché de sesión y permisos
    with django_assert_max_num_queries(40) as consultas:
        html = cg.get(f"/proyectos/{proyecto.pk}?tab=actividades").content.decode()
    n = len(consultas.captured_queries)
    crear_actividad("Tarea extra", proyecto=proyecto)
    with django_assert_max_num_queries(n):
        cg.get(f"/proyectos/{proyecto.pk}?tab=actividades")
    assert "Tarea 2" in html


# --- Criterio 2: participantes en la tarea -----------------------------------------
def test_ficha_rapida_crea_persona_con_rut_comuna_organizacion_y_comunidad(cg, proyecto, crear_actividad, comuna, comunidad, junta, rol):
    from apps.comunidades.models import ComunidadMiembro
    from apps.personas.models import Persona, PersonaOrganizacion

    t = crear_actividad("Tarea", proyecto=proyecto)
    form = cg.get(f"/actividades/{t.pk}/participantes/rapido?llego=1").content.decode()
    assert "¿De qué grupo viene?" in form and "Comuna donde vive" in form
    assert "¿De qué grupo viene?" in cg.get(f"/actividades/{t.pk}/participantes/nuevo").content.decode()
    datos = {"nombres": "Rosa", "apellido_paterno": "Ficticia", "rut": "11.111.111-1", "nacionalidad": "Chilena", "sexo": "mujer",
             "comuna": comuna.pk, "rol": rol("voluntario").pk, "organizacion": junta.pk, "cargo": "Dirigente", "comunidad": comunidad.pk}
    r = cg.post(f"/actividades/{t.pk}/participantes/rapido", datos)
    assert r.status_code == 302
    p = Persona.objects.get(nombres="Rosa")
    assert (p.rut_numero, p.rut_dv, p.nacionalidad, p.sexo) == (11111111, "1", "Chilena", "mujer")
    assert p.direcciones.get(tipo="residencia").direccion.comuna == comuna
    part = Participacion.objects.get(persona=p, actividad=t)
    assert part.institucion == junta and part.comunidad == comunidad
    assert PersonaOrganizacion.objects.get(persona=p, organizacion=junta).cargo == "Dirigente"
    assert ComunidadMiembro.objects.get(persona=p, comunidad=comunidad).rol == "integrante"
    # El RUT ya registrado no crea otra persona
    r = cg.post(f"/actividades/{t.pk}/participantes/rapido", {**datos, "nombres": "Otra"})
    assert r.status_code == 400 and Persona.objects.filter(rut_numero=11111111).count() == 1


def test_persona_existente_con_grupo_sin_duplicar_vinculos(cg, crear_actividad, persona, junta, comunidad, rol, estado_part):
    from apps.comunidades.models import ComunidadMiembro
    from apps.personas.models import PersonaOrganizacion

    PersonaOrganizacion.objects.create(persona=persona, organizacion=junta, cargo="Dirigente")
    ComunidadMiembro.objects.create(persona=persona, comunidad=comunidad, rol="dirigente")
    t = crear_actividad("Tarea")
    r = cg.post(f"/actividades/{t.pk}/participantes/nuevo", {
        "persona": persona.pk, "rol": rol("voluntario").pk, "estado": estado_part("invitado").pk,
        "organizacion": junta.pk, "cargo": "dirigente", "comunidad": comunidad.pk, "llego": "1"})
    assert r.status_code == 302
    part = Participacion.objects.get(persona=persona, actividad=t)
    assert part.institucion == junta and part.comunidad == comunidad and part.asistencia is True
    assert PersonaOrganizacion.objects.filter(persona=persona).count() == 1
    assert ComunidadMiembro.objects.get(persona=persona).rol == "dirigente"


# --- Criterio 3: sesiones --------------------------------------------------------------
def test_segunda_sesion_tiene_su_propia_lista(cg, crear_actividad, crear_persona, rol, estado_part):
    t = crear_actividad("Tarea con sesiones")
    a, b = (Participacion.objects.create(actividad=t, persona=crear_persona(), rol=rol("voluntario"), estado=estado_part("invitado")) for _ in range(2))
    s1 = SesionActividad.objects.create(actividad=t, numero=1, fecha=FUTURO, hora_inicio=time(10))
    s2 = SesionActividad.objects.create(actividad=t, numero=2, fecha=FUTURO + timedelta(days=2), hora_inicio=time(10))
    cg.post(f"/actividades/{t.pk}/sesiones/{s1.pk}/asistencia", {f"asistio_{a.pk}": "si", f"asistio_{b.pk}": "si"})
    cg.post(f"/actividades/{t.pk}/sesiones/{s2.pk}/asistencia", {f"asistio_{a.pk}": "si", f"asistio_{b.pk}": "no"})
    assert SesionAsistencia.objects.filter(sesion=s1, asistio=True).count() == 2
    assert SesionAsistencia.objects.get(sesion=s2, participacion=b).asistio is False
    html = cg.get(f"/actividades/{t.pk}/sesiones/{s2.pk}").content.decode()
    assert str(a.persona) in html and str(b.persona) in html

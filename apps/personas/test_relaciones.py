"""Pruebas de F25 (partes C y D): relaciones al registrar una persona (organizaciones, comunidad, proyecto, actividad)
y la pestaña Experiencia que se arma sola con los cargos terminados. Todos los datos son ficticios."""
from datetime import date

import pytest

from apps.comunidades.models import Comunidad, ComunidadMiembro
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona, PersonaFormacion, PersonaOrganizacion

pytestmark = pytest.mark.django_db


def _datos(filas, **extra):
    datos = {"modo": "completa", "nombres": "Rocío", "apellido_paterno": "Inventada", "relaciones-TOTAL_FORMS": str(len(filas)),
             "relaciones-INITIAL_FORMS": "0", "relaciones-MIN_NUM_FORMS": "0", "relaciones-MAX_NUM_FORMS": "30"}
    for i, fila in enumerate(filas):
        datos.update({f"relaciones-{i}-{k}": getattr(v, "pk", v) for k, v in fila.items()})
    datos.update(extra)
    return datos


@pytest.fixture
def junta(tipo_org):
    return Organizacion.objects.create(nombre="Junta Vecinal Ficticia", tipo=tipo_org("junta_de_vecinos_o_comite"))


@pytest.fixture
def comunidad(comuna):
    return Comunidad.objects.create(nombre="Vecinos de la Etapa Ficticia", comuna=comuna)


@pytest.fixture
def proyecto(db):
    from apps.proyectos.models import Proyecto

    return Proyecto.objects.create(nombre="Huertos Inventados")


def test_relaciones_al_registrar_se_ven_en_ambos_lados(cg, universidad, junta, comunidad, proyecto, rol):
    html = cg.get("/personas/nueva?modo=completa").content.decode()
    assert "Relaciones" in html and 'name="relaciones-TOTAL_FORMS"' in html and "+ Agregar relación" in html
    filas = [
        {"tipo": "organizacion", "organizacion": universidad, "rol_organizacion": "docente", "cargo": "Lenguaje", "desde": "2024-03-01"},
        {"tipo": "organizacion", "organizacion": junta, "rol_organizacion": "socio"},
        {"tipo": "comunidad", "comunidad": comunidad, "rol_comunidad": "dirigente"},
        {"tipo": "proyecto", "proyecto": proyecto, "como": "equipo", "rol": rol("voluntario"), "es_responsable": "on"},
        {"tipo": "", "como": "equipo"},  # fila vacía: se ignora
    ]
    r = cg.post("/personas/nueva", _datos(filas))
    p = Persona.objects.get()
    assert r.status_code == 302 and r["Location"] == p.get_absolute_url()
    assert set(PersonaOrganizacion.objects.filter(persona=p).values_list("cargo", flat=True)) == {"Docente · Lenguaje", "Socio/a"}
    assert ComunidadMiembro.objects.get(persona=p).rol == "dirigente"
    pp = p.proyectos.get()
    assert pp.tipo == "equipo" and pp.rol.codigo == "voluntario" and pp.es_responsable
    vinculos = cg.get(f"{p.get_absolute_url()}?tab=vinculos").content.decode()
    for texto in ("Universidad Ficticia", "Junta Vecinal Ficticia", "Vecinos de la Etapa Ficticia", "Huertos Inventados"):
        assert texto in vinculos
    assert "Rocío" in cg.get(f"{universidad.get_absolute_url()}?tab=personas").content.decode()
    assert "Rocío" in cg.get(f"{junta.get_absolute_url()}?tab=personas").content.decode()
    assert "Rocío" in cg.get(f"{comunidad.get_absolute_url()}?tab=integrantes").content.decode()
    assert "Rocío" in cg.get(f"{proyecto.get_absolute_url()}?tab=equipo").content.decode()


def test_estudiante_en_organizacion_no_educativa_da_error_y_no_guarda_nada(cg, junta):
    r = cg.post("/personas/nueva", _datos([{"tipo": "organizacion", "organizacion": junta, "rol_organizacion": "estudiante"}]))
    assert r.status_code == 200 and not Persona.objects.exists()
    assert "no es una institución educativa" in r.content.decode()


def test_estudiante_en_institucion_crea_formacion_y_practicante_suma_a_la_actividad(cg, universidad, actividad):
    filas = [{"tipo": "organizacion", "organizacion": universidad, "rol_organizacion": "estudiante"},
             {"tipo": "organizacion", "organizacion": universidad, "rol_organizacion": "practicante", "viene_actividad": actividad}]
    assert cg.post("/personas/nueva", _datos(filas)).status_code == 302
    p = Persona.objects.get()
    assert PersonaFormacion.objects.get(persona=p).estado == "estudiante"
    assert p.participaciones.get(actividad=actividad).rol.codigo == "practicante"


def test_fila_con_tipo_sin_datos_pide_completarla(cg):
    r = cg.post("/personas/nueva", _datos([{"tipo": "actividad"}]))
    assert r.status_code == 200 and "Elige la actividad." in r.content.decode() and not Persona.objects.exists()


def test_experiencia_muestra_cargo_terminado_y_la_externa_aparte(cg, persona, junta):
    PersonaOrganizacion.objects.create(persona=persona, organizacion=junta, cargo="Tesorera", tipo_cargo="directorio",
                                       fecha_inicio=date(2020, 1, 1), fecha_termino=date(2022, 12, 31))
    PersonaOrganizacion.objects.create(persona=persona, organizacion=junta, cargo="Secretaria vigente")
    html = cg.get(f"{persona.get_absolute_url()}?tab=experiencia").content.decode()
    assert "Tesorera" in html and "01-01-2020 a 31-12-2022" in html and junta.get_absolute_url() in html
    assert "Secretaria vigente" not in html
    assert "Experiencia fuera de la Fundación" in html

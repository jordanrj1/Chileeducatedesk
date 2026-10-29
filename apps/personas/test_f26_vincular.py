"""Pruebas de F26 P2 (parte A): vincular() como única puerta, catálogo «Rol en la organización» y su migración por
prefijo, procedencia calculada, «Actualizar también su vínculo» e informe de diferencias (solo lectura).
Todos los datos son ficticios."""
from importlib import import_module

import pytest
from django.apps import apps as registro
from django.core.management import call_command

from apps.actividades.models import Participacion
from apps.comunidades.models import Comunidad, ComunidadMiembro
from apps.nucleo.models import CATALOGOS, RolOrganizacion
from apps.organizaciones.models import Carrera, Organizacion
from apps.personas.models import PersonaFormacion, PersonaOrganizacion
from apps.personas.rol_organizacion import codigo_desde_cargo
from apps.personas.vinculos import cargos_y_vinculos, vincular

pytestmark = pytest.mark.django_db


@pytest.fixture
def junta(tipo_org):
    return Organizacion.objects.create(nombre="Junta Ficticia", tipo=tipo_org("junta_de_vecinos_o_comite"))


@pytest.fixture
def comunidad(comuna):
    return Comunidad.objects.create(nombre="Vecinos Ficticios", comuna=comuna)


# --- Catálogo ---------------------------------------------------------------------------------------
def test_catalogo_rol_en_la_organizacion_sembrado_y_editable():
    assert CATALOGOS["rol-organizacion"] is RolOrganizacion
    assert list(RolOrganizacion.objects.values_list("codigo", flat=True)) == [
        "estudiante", "docente", "funcionario", "dirigente", "socio", "practicante", "autoridad", "otro"]


def test_catalogo_aparece_en_catalogos(cg):
    assert "Roles en la organización" in cg.get("/administracion/catalogos/").content.decode()
    assert "Funcionario o funcionaria" in cg.get("/administracion/catalogos/rol-organizacion/").content.decode()


# --- vincular() ---------------------------------------------------------------------------------------
def test_vincular_no_duplica_y_completa_sin_pisar(persona, junta):
    v1 = vincular(persona, organizacion=junta)["vinculo"]
    res = vincular(persona, organizacion=junta, cargo="Dirigente de la villa")
    assert res["vinculo"] == v1 and res["creados"] == []
    v1.refresh_from_db()
    assert v1.cargo == "Dirigente de la villa" and v1.rol.codigo == "dirigente"  # el rol se deduce del cargo
    # el mismo cargo (sin importar mayúsculas) se reutiliza; un cargo distinto no pisa el existente: es otro vínculo
    assert vincular(persona, organizacion=junta, cargo="dirigente de la villa")["vinculo"] == v1
    otro = vincular(persona, organizacion=junta, cargo="Tesorera")["vinculo"]
    assert otro != v1 and PersonaOrganizacion.objects.filter(persona=persona).count() == 2
    v1.refresh_from_db()
    assert v1.cargo == "Dirigente de la villa"


def test_vincular_elige_formacion_vinculo_o_comunidad(persona, universidad, junta, comunidad):
    # estudiante en institución educativa → formación (una sola, aunque se repita)
    r = vincular(persona, organizacion=universidad, rol="estudiante")
    assert r["formacion"] and r["vinculo"] is None
    carrera = Carrera.objects.create(organizacion=universidad, nombre="Carrera Ficticia")
    assert vincular(persona, organizacion=universidad, carrera=carrera)["formacion"] == r["formacion"]
    assert PersonaFormacion.objects.get(persona=persona).carrera == carrera  # completó la carrera vacía
    # docente en la misma institución → vínculo con rol del catálogo
    r = vincular(persona, organizacion=universidad, rol="docente", cargo="Profesora de Lenguaje")
    assert r["vinculo"].rol.codigo == "docente" and r["formacion"] is None
    # estudiante en una organización que no es educativa → vínculo, no formación
    assert vincular(persona, organizacion=junta, rol="estudiante")["vinculo"].rol.codigo == "estudiante"
    # comunidad → padrón, sin duplicar
    m = vincular(persona, comunidad=comunidad, rol_comunidad="dirigente")["miembro"]
    assert vincular(persona, comunidad=comunidad)["miembro"] == m and ComunidadMiembro.objects.get().rol == "dirigente"
    assert PersonaFormacion.objects.count() == 1


def test_cargos_y_vinculos_muestra_el_rol_del_catalogo(persona, junta):
    vincular(persona, organizacion=junta, rol=RolOrganizacion.objects.get(codigo="socio"), cargo="Socia fundadora")
    fila = dict(cargos_y_vinculos(persona))["Organizaciones y cargos"][0]
    assert fila["rol"] == "Socio o socia" and "Socia fundadora" in fila["detalle"]


# --- Migración del rol por prefijo -------------------------------------------------------------------
@pytest.mark.parametrize("cargo, codigo", [
    ("Docente de Lenguaje", "docente"), ("Socio/a", "socio"), ("Funcionario/a · Aseo", "funcionario"), ("dirigenta", "dirigente"),
    ("Estudiante", "estudiante"), ("Autoridad comunal", "autoridad"), ("Presidenta", ""), ("", ""),
])
def test_codigo_desde_cargo(cargo, codigo):
    assert codigo_desde_cargo(cargo) == codigo


def test_migracion_rellena_el_rol_por_prefijo(persona, junta):
    a = PersonaOrganizacion.objects.create(persona=persona, organizacion=junta, cargo="Docente de Matemática")
    b = PersonaOrganizacion.objects.create(persona=persona, organizacion=junta, cargo="Presidenta")
    import_module("apps.personas.migrations.0007_vinculo_rol").rellenar_rol(registro, None)
    a.refresh_from_db()
    b.refresh_from_db()
    assert a.rol.codigo == "docente" and a.cargo == "Docente de Matemática" and b.rol is None


# --- Puertas que usan vincular() ---------------------------------------------------------------------
def test_grupo_del_participante_con_rol_en_la_organizacion(cg, crear_actividad, persona, junta, rol, estado_part):
    a = crear_actividad("Tarea ficticia")
    r = cg.post(f"/actividades/{a.pk}/participantes/nuevo", {
        "persona": persona.pk, "rol": rol("voluntario").pk, "estado": estado_part("confirmado").pk,
        "organizacion": junta.pk, "rol_organizacion": RolOrganizacion.objects.get(codigo="socio").pk})
    assert r.status_code == 302
    assert PersonaOrganizacion.objects.get(persona=persona, organizacion=junta).rol.codigo == "socio"


def test_contacto_de_organizacion_en_actividad_queda_vinculado(cg, actividad, persona, junta):
    r = cg.post(f"/actividades/{actividad.pk}/organizaciones/nuevo", {"organizacion": junta.pk, "contacto": persona.pk, "vigente": "on"})
    assert r.status_code == 302
    assert PersonaOrganizacion.objects.filter(persona=persona, organizacion=junta).count() == 1


# --- Procedencia calculada y «Actualizar también su vínculo» ----------------------------------------
def test_procedencia_calculada_desde_el_vinculo(cg, actividad, persona, junta, comunidad, rol, estado_part):
    PersonaOrganizacion.objects.create(persona=persona, organizacion=junta, cargo="Tesorera ficticia")
    ComunidadMiembro.objects.create(persona=persona, comunidad=comunidad)
    p = Participacion.objects.create(actividad=actividad, persona=persona, rol=rol("voluntario"), estado=estado_part("confirmado"))
    assert p.institucion_id is None and p.comunidad_id is None  # la participación no las guarda
    html = cg.get(f"/actividades/{actividad.pk}?tab=participantes").content.decode()
    assert f'href="{junta.get_absolute_url()}"' in html and "Tesorera ficticia" in html
    assert f'href="{comunidad.get_absolute_url()}"' in html and "(de su ficha)" in html


def test_procedencia_sin_consultas_por_fila(cg, actividad, junta, crear_persona, rol, estado_part):
    def agregar(n):
        for _ in range(n):
            per = crear_persona()
            PersonaOrganizacion.objects.create(persona=per, organizacion=junta, cargo="Socio")
            Participacion.objects.create(actividad=actividad, persona=per, rol=rol("voluntario"), estado=estado_part("confirmado"))

    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    agregar(2)
    with CaptureQueriesContext(connection) as pocas:
        cg.get(f"/actividades/{actividad.pk}?tab=participantes")
    agregar(6)
    with CaptureQueriesContext(connection) as muchas:
        cg.get(f"/actividades/{actividad.pk}?tab=participantes")
    assert len(muchas) == len(pocas)


def test_editar_participacion_actualiza_tambien_su_vinculo(cg, actividad, persona, universidad, comunidad, rol, estado_part):
    p = Participacion.objects.create(actividad=actividad, persona=persona, rol=rol("voluntario"), estado=estado_part("confirmado"))
    url = f"/actividades/{actividad.pk}/participantes/{p.pk}/editar"
    assert "Actualizar también su vínculo" in cg.get(url).content.decode()
    # sin la casilla: solo cambia la participación
    cg.post(url, {"rol": p.rol_id, "estado": p.estado_id, "institucion": universidad.pk})
    assert not PersonaOrganizacion.objects.filter(persona=persona).exists()
    # con la casilla: también el vínculo y el padrón, sin duplicar
    for _ in range(2):
        cg.post(url, {"rol": p.rol_id, "estado": p.estado_id, "institucion": "", "comunidad": ""})
        r = cg.post(url, {"rol": p.rol_id, "estado": p.estado_id, "institucion": universidad.pk, "comunidad": comunidad.pk, "actualizar_vinculo": "on"})
        assert r.status_code == 302
    assert PersonaOrganizacion.objects.filter(persona=persona, organizacion=universidad).count() == 1
    assert ComunidadMiembro.objects.filter(persona=persona, comunidad=comunidad).count() == 1


# --- Informe de diferencias ----------------------------------------------------------------------------
def test_diferencias_datos_informa_y_no_escribe(actividad, persona, junta, comunidad, universidad, rol, estado_part, capsys):
    Participacion.objects.create(actividad=actividad, persona=persona, rol=rol("voluntario"), estado=estado_part("confirmado"),
                                 institucion=junta, comunidad=comunidad)
    comunidad.referente = persona
    comunidad.save()
    actividad.responsable = persona
    actividad.save()
    PersonaFormacion.objects.create(persona=persona, organizacion=universidad, sede="Campus Ficticio")
    modelos = [PersonaOrganizacion, PersonaFormacion, ComunidadMiembro, Participacion]
    antes = [m.objects.count() for m in modelos]
    call_command("diferencias_datos")
    salida = capsys.readouterr().out
    assert [m.objects.count() for m in modelos] == antes
    assert "[participacion_institucion]" in salida and "[participacion_comunidad]" in salida
    assert "[referente_fuera_padron]" in salida and f"/comunidades/{comunidad.pk}" in salida
    assert "[sede_en_texto]" in salida and "Campus Ficticio" in salida
    # la persona participa: su actividad no aparece como «responsable fuera del equipo»
    assert "responsable_actividad_fuera_equipo] Actividades o tareas cuyo responsable no está entre sus participantes: 0" in salida

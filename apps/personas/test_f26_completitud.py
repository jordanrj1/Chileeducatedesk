"""Pruebas de F26 P2 (parte B): formulario de persona sin datos dobles, completitud calculada (faltantes, estado y la
tarjeta del Inicio), responsable y referente en su equipo o padrón (con la migración de datos), apoderado por contacto
de emergencia e institución no educativa en la participación. Todos los datos son ficticios."""
import re
from datetime import date
from importlib import import_module

import pytest
from django.apps import apps as registro
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.actividades.models import Participacion
from apps.comunidades.models import Comunidad, ComunidadMiembro
from apps.nucleo.models import EstadoParticipacion, EstadoRegistro, PerfilPersona, TipoContacto
from apps.organizaciones.models import Organizacion
from apps.personas.diferencias import diferencias
from apps.personas.models import Contacto, ContactoEmergencia, FichaVoluntario, Persona, PersonaDireccion, PersonaFormacion
from apps.personas.servicios import recalcular_estado
from apps.territorio.models import Direccion

pytestmark = pytest.mark.django_db


def _perfil(ficha):
    return PerfilPersona.objects.filter(ficha=ficha).order_by("orden").first()


def _correo(p, valor="ficticia@ejemplo.invalid"):
    return Contacto.objects.create(persona=p, tipo=TipoContacto.objects.get(codigo="correo"), valor=valor)


def _residencia(p, comuna):
    return PersonaDireccion.objects.create(persona=p, direccion=Direccion.objects.create(comuna=comuna), tipo="residencia")


def _codigo(p):
    p.refresh_from_db()
    return p.estado_registro.codigo if p.estado_registro_id else None


@pytest.fixture
def junta(tipo_org):
    return Organizacion.objects.create(nombre="Junta Ficticia del Cerro", tipo=tipo_org("junta_de_vecinos_o_comite"))


@pytest.fixture
def comunidad(comuna):
    return Comunidad.objects.create(nombre="Vecinos Ficticios del Cerro", comuna=comuna)


# --- Completitud ------------------------------------------------------------------------------------------------------

def test_faltantes_generales_y_por_tipo(crear_persona, comuna, universidad, comunidad):
    p = Persona.objects.create(nombres="Sin Nada")
    assert p.faltantes() == ["apellido", "un contacto", "comuna de residencia"]
    p = crear_persona()
    _correo(p)
    _residencia(p, comuna)
    assert p.faltantes() == []
    p.perfiles.add(_perfil("estudiante"), _perfil("voluntario"), _perfil("invitado"))
    assert p.faltantes() == ["formación vigente", "ficha de voluntariado", "ficha de invitado"]
    PersonaFormacion.objects.create(persona=p, organizacion=universidad)
    FichaVoluntario.objects.create(persona=p)
    p = Persona.objects.get(pk=p.pk)
    assert p.faltantes() == ["ficha de invitado"]
    # vecino: basta su comuna (residencia) o su comunidad
    v = crear_persona()
    _correo(v, "vecina@ejemplo.invalid")
    v.perfiles.add(_perfil("vecino"))
    assert v.faltantes() == ["comuna donde vive o su comunidad"]
    ComunidadMiembro.objects.create(comunidad=comunidad, persona=v)
    assert Persona.objects.get(pk=v.pk).faltantes() == []


def test_faltantes_sin_consultas_extra_con_lo_precargado(crear_persona, comuna):
    for _ in range(3):
        p = crear_persona()
        p.perfiles.add(_perfil("voluntario"))
    qs = Persona.objects.con_completitud()
    with CaptureQueriesContext(connection) as c:
        personas = list(qs)
        [p.faltantes() for p in personas]
    n = len(c)
    crear_persona().perfiles.add(_perfil("estudiante"))
    with CaptureQueriesContext(connection) as c:
        [p.faltantes() for p in list(Persona.objects.con_completitud())]
    assert len(c) == n  # una persona más, mismas consultas


def test_recalcular_al_agregar_contacto_y_al_desactivarlo(crear_persona, comuna):
    p = crear_persona()
    _residencia(p, comuna)
    assert _codigo(p) == "incompleto"
    c = _correo(p)
    assert _codigo(p) == "activo"
    c.vigente = False
    c.save()  # lo que hace «Desactivar» en la pestaña Contacto
    assert _codigo(p) == "incompleto"


def test_estados_manuales_no_se_pisan(crear_persona, comuna):
    p = crear_persona()
    for codigo in ("por_verificar", "desactualizado", "fallecida", "fusionada"):
        estado = EstadoRegistro.objects.filter(codigo=codigo).first()
        if estado is None:
            continue
        Persona.objects.filter(pk=p.pk).update(estado_registro=estado)
        p.refresh_from_db()
        _correo(p, f"{codigo}@ejemplo.invalid")
        assert recalcular_estado(p) == codigo and _codigo(p) == codigo


def test_editar_eligiendo_activo_con_faltantes_queda_incompleto(cg, persona):
    activo = EstadoRegistro.objects.get(codigo="activo")
    cg.post(f"/personas/{persona.pk}/editar", {"nombres": persona.nombres, "apellido_paterno": persona.apellido_paterno, "estado_registro": activo.pk})
    assert _codigo(persona) == "incompleto"


def test_inicio_muestra_le_falta_con_consultas_fijas(cg, crear_persona):
    for _ in range(2):
        crear_persona()
    with CaptureQueriesContext(connection) as c:
        html = cg.get("/dashboard").content.decode()
    n = len(c)
    assert "le falta: un contacto, comuna de residencia" in html
    for _ in range(3):
        crear_persona()
    with CaptureQueriesContext(connection) as c:
        cg.get("/dashboard")
    assert len(c) == n


# --- Formulario de persona sin datos dobles ---------------------------------------------------------------------------

def test_formulario_de_persona_sin_campos_repetidos(cg, persona):
    html = cg.get("/personas/nueva?modo=completa").content.decode()
    # «Tipo de persona» reúne el tipo principal y los otros perfiles; ya no hay «Tipo de registro» aparte
    assert "<legend class=\"fche-bloque__titulo\">Tipo de persona</legend>" in html and ">Tipo de registro<" not in html
    bloque = html.split('<legend class="fche-bloque__titulo">Tipo de persona</legend>')[1].split("</fieldset>")[0]
    assert "Otros perfiles" in bloque and 'name="vin-organizacion"' in bloque and 'name="vin-comunidad"' in bloque
    # cada campo se pide una sola vez; «Relaciones» ya no ofrece organización ni comunidad
    assert html.count('name="vin-organizacion"') == 1 and html.count('name="vin-comunidad"') == 1
    assert not re.search(r'name="relaciones-\d+-(organizacion|comunidad)"', html)
    relaciones = re.search(r'name="relaciones-0-tipo".*?</select>', html, re.S).group(0)
    assert 'value="organizacion"' not in relaciones and 'value="comunidad"' not in relaciones
    # lo que pide la sección de un tipo se oculta aquí al marcarlo (con JavaScript)
    assert 'data-ocultar-si-tipo="estudiante invitado"' in html and 'data-ocultar-si-tipo="vecino"' in html
    # en Editar: un solo bloque, con «Otros perfiles» dentro
    html = cg.get(f"/personas/{persona.pk}/editar").content.decode()
    bloque = html.split('<legend class="fche-bloque__titulo">Tipo de persona</legend>')[1].split("</fieldset>")[0]
    assert "Otros perfiles" in bloque and html.count('data-etiqueta="Otros perfiles"') == 1


def test_formulario_guarda_organizacion_y_comunidad_con_vincular(cg, junta, comunidad, comuna):
    r = cg.post("/personas/nueva", {"modo": "completa", "nombres": "Elena", "apellido_paterno": "Inventada", "correo": "elena@ejemplo.invalid",
                                    "comuna": comuna.pk, "vin-organizacion": junta.pk, "vin-rol_organizacion": "dirigente", "vin-cargo": "Presidenta",
                                    "vin-comunidad": comunidad.pk, "vin-rol_comunidad": "referente"})
    p = Persona.objects.get(nombres="Elena")
    assert r.status_code == 302
    v = p.vinculos.get()
    assert (v.organizacion, v.rol.codigo, v.cargo, v.tipo_cargo) == (junta, "dirigente", "Presidenta", "directorio")
    assert p.comunidades.get().rol == "referente"
    assert _codigo(p) == "activo"  # apellido, contacto y comuna: completa


# --- Responsable y referente ------------------------------------------------------------------------------------------

def test_responsable_de_proyecto_queda_en_el_equipo(cg, crear_persona):
    from apps.proyectos.models import Proyecto, ProyectoPersona

    a, b = crear_persona(), crear_persona()
    assert cg.post("/proyectos/nuevo", {"nombre": "Huertos Ficticios", "estado": "preparacion", "responsable": a.pk}).status_code == 302
    proy = Proyecto.objects.get()
    assert ProyectoPersona.objects.get(proyecto=proy, persona=a, tipo="equipo").es_responsable
    r = cg.post(f"/proyectos/{proy.pk}/editar", {"nombre": proy.nombre, "estado": "preparacion", "responsable": b.pk})
    assert r.status_code == 302
    equipo = {pp.persona_id: pp.es_responsable for pp in ProyectoPersona.objects.filter(proyecto=proy, tipo="equipo")}
    assert equipo == {a.pk: False, b.pk: True}  # el anterior sigue en el equipo, ya no como responsable
    html = cg.get(f"{proy.get_absolute_url()}?tab=equipo").content.decode()
    assert f"{b} (responsable)" in html and f"{a} (responsable)" not in html


def test_responsable_de_actividad_queda_en_el_equipo_ejecutor(actividad, crear_persona):
    from apps.actividades.servicios import asegurar_responsable_en_equipo

    p = crear_persona()
    actividad.responsable = p
    actividad.save()
    part = asegurar_responsable_en_equipo(actividad)
    assert part.rol.grupo == "ejecutor" and part.rol.codigo == "coordinador" and part.estado.codigo == "confirmado"
    assert asegurar_responsable_en_equipo(actividad) == part  # nunca duplica
    assert Participacion.objects.filter(actividad=actividad, persona=p).count() == 1


def test_editar_actividad_suma_al_responsable(cg, actividad, crear_persona):
    p = crear_persona()
    r = cg.post(f"/actividades/{actividad.pk}/editar", {"nombre": actividad.nombre, "responsable": p.pk})
    assert r.status_code == 302
    assert Participacion.objects.get(actividad=actividad, persona=p).rol.grupo == "ejecutor"


def test_referente_queda_en_el_padron_y_la_ficha_usa_el_del_padron(cg, comuna, crear_persona):
    ref, dir_ = crear_persona(), crear_persona()
    r = cg.post("/comunidades/nueva", {"nombre": "Comunidad Ficticia Norte", "tipo": "vecinal", "comuna": comuna.pk, "referente": ref.pk})
    assert r.status_code == 302
    c = Comunidad.objects.get(nombre="Comunidad Ficticia Norte")
    assert ComunidadMiembro.objects.get(comunidad=c, persona=ref).rol == "referente"
    # sin referente en el campo: la ficha muestra el dirigente del padrón
    otra = Comunidad.objects.create(nombre="Comunidad Ficticia Sur", comuna=comuna)
    ComunidadMiembro.objects.create(comunidad=otra, persona=dir_, rol="dirigente")
    html = cg.get(otra.get_absolute_url()).content.decode()
    assert str(dir_) in html and "según su padrón" in html


def test_migracion_de_datos_deja_sin_diferencias_de_responsables_ni_referentes(actividad, comuna, crear_persona):
    from apps.proyectos.models import Proyecto

    a, b, c = crear_persona(), crear_persona(), crear_persona()
    Proyecto.objects.create(nombre="Proyecto Ficticio", responsable=a)  # creados sin pasar por las pantallas
    actividad.responsable = b
    actividad.save()
    Comunidad.objects.create(nombre="Comunidad Ficticia", comuna=comuna, referente=c)
    claves = {"responsable_proyecto_fuera_equipo", "responsable_actividad_fuera_equipo", "referente_fuera_padron"}
    antes = {d["clave"]: d["cifra"] for d in diferencias() if d["clave"] in claves}
    assert antes == dict.fromkeys(claves, 1)
    migracion = import_module("apps.personas.migrations.0008_responsables_y_referentes")
    migracion.aplicar(registro, None)
    migracion.aplicar(registro, None)  # repetirla no cambia nada
    despues = {d["clave"]: d["cifra"] for d in diferencias() if d["clave"] in claves}
    assert despues == dict.fromkeys(claves, 0)
    assert Participacion.objects.filter(actividad=actividad, persona=b).count() == 1


# --- Apoderado --------------------------------------------------------------------------------------------------------

def test_apoderado_por_contacto_de_emergencia(crear_persona):
    menor = crear_persona(fecha_nacimiento=date(date.today().year - 10, 1, 1))
    assert "Es menor de edad y no tiene apoderado registrado." in menor.avisos_consentimiento()
    ContactoEmergencia.objects.create(persona=menor, nombre="Tía Ficticia", parentesco="Tía", telefono="+56 9 1111 2222")
    assert "Es menor de edad y no tiene apoderado registrado." in menor.avisos_consentimiento()
    ContactoEmergencia.objects.create(persona=menor, nombre="Madre Ficticia", parentesco="Mamá", telefono="+56 9 3333 4444")
    assert "Es menor de edad y no tiene apoderado registrado." not in menor.avisos_consentimiento()


# --- Participación: institución u organización de procedencia ---------------------------------------------------------

def test_participacion_acepta_organizacion_no_educativa_y_actualiza_su_vinculo(cg, actividad, persona, rol, junta):
    p = Participacion.objects.create(actividad=actividad, persona=persona, rol=rol("voluntario"), estado=EstadoParticipacion.objects.get(codigo="confirmado"))
    html = cg.get(f"/actividades/{actividad.pk}/participantes/{p.pk}/editar").content.decode()
    assert "Institución u organización de procedencia" in html
    r = cg.post(f"/actividades/{actividad.pk}/participantes/{p.pk}/editar",
                {"rol": p.rol_id, "estado": p.estado_id, "institucion": junta.pk, "actualizar_vinculo": "on"})
    assert r.status_code == 302
    p.refresh_from_db()
    assert p.institucion == junta and persona.vinculos.filter(organizacion=junta).count() == 1

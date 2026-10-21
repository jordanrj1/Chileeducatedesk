"""Pruebas de los buscadores de los formularios: muestran a los registrados sin escribir, conservan el valor elegido
(también si quedó desactivado), un valor inválido no provoca un error 500, «+ Crear…» avisa de parecidos y deja
elegido lo creado, el equipo de la Fundación aparece primero y la lista de organizaciones no hace consultas en bucle.
Todos los datos son ficticios."""
import json
import re

import pytest

from apps.nucleo.models import EstadoActividad, TipoOrganizacion
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona, PersonaOrganizacion

pytestmark = pytest.mark.django_db


def _select(html, nombre):
    m = re.search(rf'<select name="{nombre}"[^>]*>(.*?)</select>', html, re.S)
    assert m, f"no se encontró el campo {nombre}"
    return m.group(0)


# --- muestran a los registrados sin escribir -----------------------------------
def test_formularios_muestran_registrados_sin_escribir(cg, persona, universidad, crear_actividad):
    html = cg.get("/solicitudes/nueva").content.decode()
    assert "Ana María Pérez Soto" in _select(html, "persona")
    assert "Universidad Ficticia" in _select(html, "organizacion")
    assert 'data-opciones-url="/personas/opciones?crear=1"' in html  # el buscador puede crear en el momento
    jornada = crear_actividad("Jornada de prueba")
    otra = crear_actividad("Charla aparte")
    html = cg.get(f"/actividades/{otra.pk}/editar").content.decode()
    padre = _select(html, "actividad_padre")
    assert "Jornada de prueba" in padre and f'value="{otra.pk}"' not in padre  # no se ofrece como su propia padre
    assert "Ana María Pérez Soto" in _select(cg.get("/proyectos/nuevo").content.decode(), "responsable")


def test_opciones_con_total_y_la_actual_primero(cg, crear_persona):
    personas = [crear_persona(f"Nombre{i:02d}", apellido_paterno="Inventado") for i in range(30)]
    ultima = personas[-1]
    html = cg.get(f"/personas/opciones?actual={ultima.pk}").content.decode()
    primera = re.search(r'role="option" aria-selected="(\w+)" data-valor="(\d+)"', html)
    assert primera.groups() == ("true", str(ultima.pk))
    assert "Mostrando 26 de 30. Escribe para filtrar" in html  # las primeras 25 más la elegida
    html = cg.get("/personas/opciones?q=Nombre07").content.decode()
    assert "Nombre07 Inventado" in html and "Nombre08" not in html and "Mostrando 1 de 1." in html


# --- defectos corregidos -------------------------------------------------------
def test_responsable_desactivado_se_conserva_al_editar(cg, actividad, persona):
    actividad.responsable = persona
    actividad.save()
    persona.activo = False
    persona.save()
    html = cg.get(f"/actividades/{actividad.pk}/editar").content.decode()
    campo = _select(html, "responsable")
    assert re.search(rf'<option value="{persona.pk}"[^>]*selected[^>]*>Ana María Pérez Soto · sin RUT \(desactivada\)', campo)
    r = cg.post(f"/actividades/{actividad.pk}/editar", {"nombre": "Taller renombrado", "responsable": persona.pk})
    assert r.status_code == 302
    actividad.refresh_from_db()
    assert actividad.nombre == "Taller renombrado" and actividad.responsable_id == persona.pk
    # otra persona desactivada no se puede elegir
    otra = Persona.objects.create(nombres="Otra", apellido_paterno="Desactivada", activo=False)
    r = cg.post(f"/actividades/{actividad.pk}/editar", {"nombre": "Taller", "responsable": otra.pk})
    assert r.status_code == 200 and "Escoja una opción válida" in r.content.decode()


def test_valor_no_numerico_no_provoca_error_500(cg, ca, persona, crear_persona):
    r = cg.post("/solicitudes/nueva", {"persona": "abc", "organizacion": "1 OR 1=1"})
    assert r.status_code == 200 and "Escoja una opción válida" in r.content.decode()
    otra = crear_persona("Repetida")
    r = ca.post(f"/personas/{otra.pk}/fusionar", {"destino": "abc", "motivo": "prueba", "confirmo": "on"})
    assert r.status_code == 400


def test_lo_que_se_ofrece_es_lo_que_se_valida(cg, crear_actividad):
    abierta = crear_actividad("Taller abierto")
    cancelada = crear_actividad("Taller cancelado", estado="cancelada")
    html = cg.get("/importaciones/nueva").content.decode()
    assert 'data-opciones-url="/actividades/opciones?abiertas=1"' in html
    lista = cg.get("/actividades/opciones?abiertas=1").content.decode()
    assert "Taller abierto" in lista and "Taller cancelado" not in lista
    hija = crear_actividad("Charla de la jornada", actividad_padre=abierta)
    assert "Charla de la jornada" in cg.get("/actividades/opciones").content.decode()  # documentos e invitaciones aceptan hijas
    assert "Charla de la jornada" not in cg.get("/actividades/opciones?raiz=1").content.decode()
    assert cancelada.estado == EstadoActividad.objects.get(codigo="cancelada") and hija.actividad_padre_id == abierta.pk


def test_excluir_al_editar_no_afecta_a_otros_formularios(cg, crear_actividad):
    """Editar una jornada la excluye solo de su propio formulario: después se puede crear una charla dentro de ella."""
    from apps.actividades.forms import ActividadForm
    from apps.actividades.models import Actividad

    jornada = crear_actividad("Jornada inventada")
    assert cg.get(f"/actividades/{jornada.pk}/editar").status_code == 200
    r = cg.post("/actividades/nueva", {"nombre": "Charla de la jornada", "actividad_padre": jornada.pk})
    assert r.status_code == 302
    assert Actividad.objects.get(nombre="Charla de la jornada").actividad_padre_id == jornada.pk
    assert ActividadForm.base_fields["actividad_padre"].filtros == {"raiz": "1"}


# --- «+ Crear…» sin salir del formulario ----------------------------------------
def test_crear_persona_rapida_avisa_parecida_y_deja_elegida(cg, persona):
    datos = {"campo": "id_responsable", "rapida-nombres": "Ana María", "rapida-apellido_paterno": "Pérez"}
    r = cg.post("/personas/crear-rapida", datos)
    html = r.content.decode()
    assert r.status_code == 200 and "Esta persona podría ya existir" in html
    assert f'data-usar-existente data-campo="id_responsable" data-valor="{persona.pk}"' in html
    r = cg.post("/personas/crear-rapida", {**datos, "confirmar_duplicado": "1"})
    assert "Escribe qué la distingue" in r.content.decode() and Persona.objects.count() == 1
    r = cg.post("/personas/crear-rapida", {**datos, "confirmar_duplicado": "1", "nota_distincion": "es la sobrina", "rapida-correo": "ana.sobrina@ejemplo.invalid"})
    assert r.status_code == 200 and r["HX-Reswap"] == "none"
    elegido = json.loads(r["HX-Trigger"])["fche:elegido"]
    nueva = Persona.objects.get(pk=elegido["valor"])
    assert elegido["campo"] == "id_responsable" and elegido["texto"] == "Ana María Pérez"
    assert "es la sobrina" in nueva.observaciones and nueva.estado_registro.codigo == "incompleto" and nueva.contactos.count() == 1
    from apps.documentos.origen import origenes_de

    assert origenes_de(nueva).count() == 1


def test_crear_rapido_exige_permiso(cs):
    assert cs.post("/personas/crear-rapida", {"rapida-nombres": "Sin permiso"}).status_code == 403
    assert cs.get("/organizaciones/crear-rapida").status_code == 403
    assert cs.get("/personas/opciones").status_code == 403


def test_crear_organizacion_rapida_con_tipo_fijo(cg, tipo_org):
    educativa, junta = tipo_org("institucion_educativa"), tipo_org("junta_de_vecinos_o_comite")
    html = cg.get("/organizaciones/crear-rapida?q=Liceo+Inventado&tipo=institucion_educativa&campo=id_institucion").content.decode()
    assert 'value="Liceo Inventado"' in html and f'<option value="{junta.pk}"' not in html
    datos = {"campo": "id_institucion", "tipo": "institucion_educativa", "rapida-nombre": "Liceo Inventado"}
    r = cg.post("/organizaciones/crear-rapida", {**datos, "rapida-tipo": junta.pk})
    assert r.status_code == 200 and not Organizacion.objects.exists()  # un tipo distinto del que acepta el campo
    r = cg.post("/organizaciones/crear-rapida", {**datos, "rapida-tipo": educativa.pk})
    elegido = json.loads(r["HX-Trigger"])["fche:elegido"]
    org = Organizacion.objects.get(pk=elegido["valor"])
    assert org.tipo == educativa and org.estado_registro.codigo == "incompleto" and elegido["campo"] == "id_institucion"


# --- responsable: equipo de la Fundación ----------------------------------------
def _equipo(tipo_org):
    fundacion = Organizacion.objects.create(nombre="Fundación Inventada", tipo=tipo_org("fundacion_u_ong"), es_propia=True)
    zoe = Persona.objects.create(nombres="Zoe", apellido_paterno="Zapata")
    PersonaOrganizacion.objects.create(persona=zoe, organizacion=fundacion, cargo="Coordinadora")
    return zoe


def test_equipo_de_la_fundacion_aparece_primero(cg, persona, tipo_org):
    zoe = _equipo(tipo_org)
    html = cg.get("/personas/opciones?equipo_primero=1").content.decode()
    assert html.index("Equipo de la Fundación") < html.index("Zoe Zapata") < html.index("Otras personas") < html.index("Ana María")
    assert "Coordinadora en Fundación Inventada" in html
    responsable = _select(cg.get("/proyectos/nuevo").content.decode(), "responsable")
    assert responsable.index('<optgroup label="Equipo de la Fundación">') < responsable.index(f'value="{zoe.pk}"') < responsable.index("Ana María")


def test_responsable_solo_equipo_si_se_activa(cg, persona, tipo_org, settings):
    zoe = _equipo(tipo_org)
    settings.RESPONSABLE_SOLO_EQUIPO = True
    assert cg.post("/proyectos/nuevo", {"nombre": "Proyecto X", "estado": "preparacion", "responsable": persona.pk}).status_code == 200
    html = cg.get("/personas/opciones?equipo_primero=1&crear=1").content.decode()
    assert "Zoe Zapata" in html and "Ana María" not in html and "+ Crear" not in html


# --- sin consultas en bucle ---------------------------------------------------
def test_opciones_de_organizaciones_sin_consultas_en_bucle(cg, tipo_org, comuna, django_assert_max_num_queries):
    from apps.territorio.models import Direccion

    for i in range(30):
        d = Direccion.objects.create(calle="Calle Inventada", numero=str(i), comuna=comuna)
        Organizacion.objects.create(nombre=f"Junta Inventada {i:02d}", tipo=tipo_org("junta_de_vecinos_o_comite"), direccion=d)
    # 2 consultas para la lista (total y opciones con tipo y comuna); el resto es sesión y permisos. Con consultas en bucle serían más de 30.
    with django_assert_max_num_queries(10):
        html = cg.get("/organizaciones/opciones").content.decode()
    assert html.count('role="option"') == 25 and "Comuna Ficticia" in html

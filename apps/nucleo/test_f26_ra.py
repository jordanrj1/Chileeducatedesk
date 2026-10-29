"""F26 Ra: envío único, aviso de posibles duplicados y límite de peticiones. Todos los datos son ficticios."""
import json
import re
import uuid
from datetime import date, timedelta

import pytest
from django.test import Client

from apps.actividades.models import Actividad
from apps.comunidades.models import Comunidad
from apps.lugares.models import Lugar
from apps.nucleo.models import EstadoSolicitud, TipoLugar, TipoOrganizacion
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona
from apps.proyectos.models import Proyecto
from apps.solicitudes.models import Solicitud
from apps.territorio.models import Direccion

FUTURO = date.today() + timedelta(days=20)


def marca():
    return uuid.uuid4().hex


def _marca_de(html):
    m = re.search(r'name="_envio" value="([0-9a-f]{32})"', html)
    return m.group(1) if m else None


# --- Envío único -----------------------------------------------------------------------------------
@pytest.mark.parametrize("ruta, datos, modelo", [
    ("/personas/nueva", {"nombres": "Rocío", "apellido_paterno": "Ficticia", "apellido_materno": "Prueba"}, Persona),
    ("/actividades/nueva", {"nombre": "Charla de envío único"}, Actividad),
    ("/organizaciones/nueva", {"nombre": "Empresa Envío Único Ficticia"}, Organizacion),
])
def test_doble_envio_crea_una_sola_vez(cg, ruta, datos, modelo):
    if modelo is Organizacion:
        datos = {**datos, "tipo": TipoOrganizacion.objects.get(codigo="empresa_o_partner").pk}
    m = _marca_de(cg.get(ruta).content.decode())
    assert m, "el formulario de creación lleva su marca de un solo uso"
    antes = modelo.objects.count()
    r1 = cg.post(ruta, {**datos, "_envio": m})
    r2 = cg.post(ruta, {**datos, "_envio": m})
    assert r1.status_code == r2.status_code == 302 and r1["Location"] == r2["Location"]
    assert modelo.objects.count() == antes + 1
    assert "Ya estaba guardado" in cg.get(r2["Location"]).content.decode()


def test_envio_con_errores_no_gasta_la_marca(cg):
    m = marca()
    r = cg.post("/personas/nueva", {"nombres": "", "_envio": m})
    assert r.status_code == 200 and Persona.objects.count() == 0
    r = cg.post("/personas/nueva", {"nombres": "Tomás", "apellido_paterno": "Inventado", "_envio": m})
    assert r.status_code == 302 and Persona.objects.count() == 1


def test_crear_rapido_htmx_doble_envio_responde_lo_mismo(cg):
    html = cg.get("/personas/crear-rapida", {"campo": "id_responsable", "q": "Elena"}).content.decode()
    m = _marca_de(html)
    assert m and 'hx-sync="this:drop"' in html and "hx-disabled-elt" in html
    datos = {"campo": "id_responsable", "rapida-nombres": "Elena", "rapida-apellido_paterno": "Envío", "_envio": m}
    r1 = cg.post("/personas/crear-rapida", datos, HTTP_HX_REQUEST="true")
    r2 = cg.post("/personas/crear-rapida", datos, HTTP_HX_REQUEST="true")
    assert Persona.objects.count() == 1
    assert r2.status_code == 200 and r2["HX-Trigger"] == r1["HX-Trigger"] and r2["HX-Reswap"] == "none"
    assert json.loads(r2["HX-Trigger"])["fche:elegido"]["valor"] == Persona.objects.get().pk


def test_edicion_sigue_con_version_y_sin_marca(cg, persona):
    html = cg.get(f"/personas/{persona.pk}/editar").content.decode()
    assert 'name="_version"' in html and _marca_de(html) is None
    version = re.search(r'name="_version" value="(\d+)"', html).group(1)
    base = {"nombres": "Ana María", "apellido_paterno": "Pérez", "apellido_materno": "Soto"}
    assert cg.post(f"/personas/{persona.pk}/editar", {**base, "profesion": "Docente", "_version": version}).status_code == 302
    r = cg.post(f"/personas/{persona.pk}/editar", {**base, "profesion": "Enfermera", "_version": version})
    persona.refresh_from_db()
    assert r.status_code == 200 and "cambió mientras lo editabas" in r.content.decode() and persona.profesion == "Docente"


# --- Aviso de posibles duplicados ------------------------------------------------------------------
def _avisa(r):
    html = r.content.decode()
    return r.status_code == 200 and "Es distinto, guardar" in html and ("podría ya estar registrad" in html or "Ya hay una solicitud abierta" in html)


def test_duplicado_lugar_mismo_nombre_en_la_comuna(cg, lugar, comuna):
    datos = {"nombre": "SALA ficticia", "tipo": TipoLugar.objects.get(codigo="sala").pk, "dir-comuna": comuna.pk, "dir-calle": "Otra Calle"}
    direcciones = Direccion.objects.count()
    r = cg.post("/lugares/nuevo", datos)
    assert _avisa(r) and lugar.get_absolute_url() in r.content.decode()
    assert Lugar.objects.count() == 1 and Direccion.objects.count() == direcciones  # el aviso no deja una dirección suelta
    assert cg.post("/lugares/nuevo", {**datos, "confirmar_duplicado": "1"}).status_code == 302 and Lugar.objects.count() == 2


def test_duplicado_comunidad_mismo_nombre_en_la_comuna(cg, comuna):
    existente = Comunidad.objects.create(nombre="Vecinos del Cerro Ficticio", comuna=comuna)
    datos = {"nombre": "Vecinos del cerro ficticio", "tipo": "vecinal", "comuna": comuna.pk}
    r = cg.post("/comunidades/nueva", datos)
    assert _avisa(r) and existente.get_absolute_url() in r.content.decode() and Comunidad.objects.count() == 1
    assert cg.post("/comunidades/nueva", {**datos, "confirmar_duplicado": "1"}).status_code == 302 and Comunidad.objects.count() == 2


def test_duplicado_proyecto_mismo_nombre(cg):
    existente = Proyecto.objects.create(nombre="Alfabetización Digital Ficticia")
    datos = {"nombre": "alfabetizacion digital ficticia", "estado": "preparacion"}
    r = cg.post("/proyectos/nuevo", datos)
    assert _avisa(r) and existente.get_absolute_url() in r.content.decode() and Proyecto.objects.count() == 1
    assert cg.post("/proyectos/nuevo", {**datos, "confirmar_duplicado": "1"}).status_code == 302 and Proyecto.objects.count() == 2


def test_duplicado_actividad_mismo_nombre_en_el_proyecto(cg, crear_actividad):
    p = Proyecto.objects.create(nombre="Proyecto Ficticio")
    existente = crear_actividad(nombre="Taller de huertos", proyecto=p)
    r = cg.post("/actividades/nueva", {"nombre": "Taller de Huertos", "proyecto": p.pk})
    assert _avisa(r) and existente.get_absolute_url() in r.content.decode() and Actividad.objects.count() == 1
    assert cg.post("/actividades/nueva", {"nombre": "Taller de Huertos"}).status_code == 302  # sin proyecto ni fecha: no hay aviso
    r = cg.post("/actividades/nueva", {"nombre": "Taller de Huertos", "proyecto": p.pk, "confirmar_duplicado": "1"})
    assert r.status_code == 302 and Actividad.objects.count() == 3


def test_duplicado_tarea_mismo_nombre_y_fecha(cg):
    p = Proyecto.objects.create(nombre="Proyecto de Tareas Ficticio")
    datos = {"nombre": "Visita a la villa", "objetivo": "Conocer a las familias", "fecha": FUTURO.isoformat(), "hora_inicio": "10:00", "hora_fin": "12:00"}
    assert cg.post(f"/proyectos/{p.pk}/tareas/nueva", datos).status_code == 302
    r = cg.post(f"/proyectos/{p.pk}/tareas/nueva", datos)
    assert _avisa(r) and "misma fecha" in r.content.decode() and Actividad.objects.count() == 1
    assert cg.post(f"/proyectos/{p.pk}/tareas/nueva", {**datos, "confirmar_duplicado": "1"}).status_code == 302 and Actividad.objects.count() == 2


def test_duplicado_solicitud_motivo_parecido_en_30_dias(cg, universidad):
    anterior = Solicitud.objects.create(organizacion=universidad, motivo="Charla de orientación vocacional", fecha=date.today() - timedelta(days=10),
                                        estado=EstadoSolicitud.objects.get(codigo="descartada"))
    base = {"origen": "solicitud_externa", "fecha": date.today().isoformat(), "organizacion": universidad.pk}
    r = cg.post("/solicitudes/nueva", {**base, "motivo": "Charla de orientacion vocacional 2026"})
    assert _avisa(r) and "motivo parecido" in r.content.decode() and anterior.get_absolute_url() in r.content.decode()
    assert Solicitud.objects.count() == 1
    assert cg.post("/solicitudes/nueva", {**base, "motivo": "Préstamo de sala para reunión"}).status_code == 302  # motivo distinto
    r = cg.post("/solicitudes/nueva", {**base, "motivo": "Charla de orientacion vocacional 2026", "confirmar_duplicado": "1"})
    assert r.status_code == 302 and Solicitud.objects.count() == 3


# --- Límite de peticiones --------------------------------------------------------------------------
@pytest.fixture
def reloj(monkeypatch):
    """Mitad de un minuto fijo: la ventana no cambia durante la prueba."""
    monkeypatch.setattr("apps.nucleo.limites.ahora", lambda: 1_800_000_030.0)


def test_limite_de_envios_responde_429_con_retry_after(cg, settings, reloj):
    settings.LIMITE_ENVIOS_MINUTO = 2
    assert cg.post("/dashboard").status_code != 429
    assert cg.post("/dashboard").status_code != 429
    r = cg.post("/dashboard")
    assert r.status_code == 429 and r["Retry-After"] == "30" and "Vas demasiado rápido" in r.content.decode()


def test_limite_de_busquedas_y_fragmento_htmx(cg, settings, reloj):
    settings.LIMITE_BUSQUEDAS_MINUTO = 2
    assert cg.get("/buscar", {"q": "ana"}).status_code == 200
    assert cg.get("/personas/opciones", {"q": "ana"}).status_code == 200
    r = cg.get("/personas/opciones", {"q": "ana"}, HTTP_HX_REQUEST="true")
    html = r.content.decode()
    assert r.status_code == 429 and r["Retry-After"] == "30" and "<html" not in html and "Espera 30 segundos" in html
    assert cg.get("/personas").status_code == 200  # un listado normal no cuenta como búsqueda


def test_limite_de_exportaciones(cg, settings, reloj):
    settings.LIMITE_EXPORTACIONES_MINUTO = 1
    assert cg.get("/personas/exportar").status_code == 200
    r = cg.get("/organizaciones/exportar")
    assert r.status_code == 429 and r.has_header("Retry-After")


def test_el_limite_es_por_usuario(cg, ca, settings, reloj):
    settings.LIMITE_ENVIOS_MINUTO = 1
    cg.post("/dashboard")
    assert cg.post("/dashboard").status_code == 429
    assert ca.post("/dashboard").status_code != 429


def test_el_ingreso_mantiene_su_bloqueo_propio(gestor, settings, reloj):
    settings.LIMITE_ENVIOS_MINUTO = 1
    c = Client()
    for _ in range(settings.INTENTOS_MAXIMOS):
        assert c.post("/login", {"username": "gestor_prueba", "password": "mala-clave"}).status_code == 200
    r = c.post("/login", {"username": "gestor_prueba", "password": "clave-ficticia-123"})
    assert r.status_code == 200 and "Demasiados intentos fallidos" in r.content.decode()


def test_aviso_de_organizacion_no_deja_direccion_suelta(cg, comuna):
    t = TipoOrganizacion.objects.get(codigo="empresa_o_partner")
    Organizacion.objects.create(nombre="Panadería Ficticia del Sur", tipo=t)
    direcciones = Direccion.objects.count()
    r = cg.post("/organizaciones/nueva", {"nombre": "Panadería Ficticia del Sur", "tipo": t.pk, "dir-comuna": comuna.pk, "dir-calle": "Calle Inventada"})
    assert r.status_code == 200 and "podría ya existir" in r.content.decode()
    assert Direccion.objects.count() == direcciones and Organizacion.objects.count() == 1

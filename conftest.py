"""Fixtures compartidas. Todos los datos son ficticios."""
import pytest
from django.contrib.auth.models import Group, User
from django.test import Client


def _usuario(nombre, grupo=None, **kw):
    u = User.objects.create_user(nombre, email=f"{nombre}@ejemplo.invalid", password="clave-ficticia-123", **kw)
    if grupo:
        u.groups.add(Group.objects.get(name=grupo))
    return u


@pytest.fixture
def gestor(db):
    return _usuario("gestor_prueba", "Gestor")


def _permisos_consulta(p):
    """Rol de prueba de solo lectura (las reglas del antiguo «Administrador», anterior a F29): ve todo lo operativo, exporta,
    importa y administra cuentas y roles, pero no digita. Las pruebas existentes de «quien solo lee» siguen usándolo;
    el Superadministrador real (todos los permisos) se prueba con el fixture `superadmin`."""
    app, cod = p.content_type.app_label, p.codename
    accion = cod.split("_", 1)[0]
    modelo = cod.split("_", 1)[1] if "_" in cod else ""
    from apps.cuentas.roles import CATALOGOS_MODELOS, OPERATIVAS

    if app == "auth":
        return modelo in {"user", "group", "permission"} and accion in {"view", "add", "change"}
    if app == "cuentas":
        return accion in {"view", "add", "change"} or cod == "respaldar"
    if app == "finanzas" or app not in OPERATIVAS:
        return False
    if accion in {"view", "fusionar"} or (app == "nucleo" and accion == "desactivar"):
        return True
    if app == "nucleo" and modelo in CATALOGOS_MODELOS and accion in {"add", "change"}:
        return True
    return accion in {"exportar", "importar", "ver"}


@pytest.fixture
def administrador(db):
    """Cuenta de solo lectura con acceso a Administración (rol de prueba «Consulta»). No es el Superadministrador: ver `superadmin`."""
    from django.contrib.auth.models import Permission

    g, _ = Group.objects.get_or_create(name="Consulta")
    g.permissions.set([p for p in Permission.objects.select_related("content_type") if _permisos_consulta(p)])
    return _usuario("admin_prueba", "Consulta")


@pytest.fixture
def superadmin(db):
    return _usuario("superadmin_prueba", "Superadministrador")


@pytest.fixture
def sin_rol(db):
    return _usuario("sin_rol_prueba")


def _cliente(usuario):
    c = Client()
    c.force_login(usuario)
    return c


@pytest.fixture
def cg(gestor):
    return _cliente(gestor)


@pytest.fixture
def ca(administrador):
    return _cliente(administrador)


@pytest.fixture
def csa(superadmin):
    return _cliente(superadmin)


@pytest.fixture
def cs(sin_rol):
    return _cliente(sin_rol)


@pytest.fixture
def comuna(db):
    from apps.territorio.models import Comuna, Provincia, Region

    r = Region.objects.create(codigo="99", nombre="Región de Prueba")
    p = Provincia.objects.create(region=r, codigo="990", nombre="Provincia de Prueba")
    return Comuna.objects.create(provincia=p, codigo="99001", nombre="Comuna Ficticia")


@pytest.fixture
def tipo_org(db):
    from apps.nucleo.models import TipoOrganizacion

    return lambda codigo: TipoOrganizacion.objects.get(codigo=codigo)


@pytest.fixture
def universidad(db):
    from apps.nucleo.models import TipoOrganizacion
    from apps.organizaciones.models import Organizacion

    return Organizacion.objects.create(nombre="Universidad Ficticia", tipo=TipoOrganizacion.objects.get(codigo="institucion_educativa"))


@pytest.fixture
def persona(db):
    from apps.personas.models import Persona

    return Persona.objects.create(nombres="Ana María", apellido_paterno="Pérez", apellido_materno="Soto")


@pytest.fixture(autouse=True)
def _media_temporal(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture(autouse=True)
def _sin_limite_de_peticiones(settings):
    """F26 Ra: las pruebas no chocan con el límite de peticiones (apps/nucleo/limites.py); se prueba aparte, encendido a propósito."""
    from django.core.cache import cache

    settings.LIMITE_ENVIOS_MINUTO = settings.LIMITE_BUSQUEDAS_MINUTO = settings.LIMITE_EXPORTACIONES_MINUTO = 0
    cache.clear()


@pytest.fixture
def lugar(db, comuna):
    from apps.lugares.models import Lugar
    from apps.nucleo.models import TipoLugar
    from apps.territorio.models import Direccion

    d = Direccion.objects.create(calle="Calle Inventada", numero="100", comuna=comuna)
    return Lugar.objects.create(nombre="Sala Ficticia", tipo=TipoLugar.objects.get(codigo="sala"), direccion=d, capacidad=20)


@pytest.fixture
def crear_actividad(db):
    from apps.actividades.models import Actividad
    from apps.nucleo.models import EstadoActividad

    def hacer(nombre="Taller de prueba", estado="pendiente", **kw):
        return Actividad.objects.create(nombre=nombre, estado=EstadoActividad.objects.get(codigo=estado), **kw)

    return hacer


@pytest.fixture
def actividad(crear_actividad):
    return crear_actividad()


@pytest.fixture
def crear_persona(db):
    from apps.personas.models import Persona

    n = {"i": 0}

    def hacer(nombres=None, **kw):
        n["i"] += 1
        return Persona.objects.create(nombres=nombres or f"Persona{n['i']}", apellido_paterno=kw.pop("apellido_paterno", f"Apellido{n['i']}"), **kw)

    return hacer


@pytest.fixture
def rol(db):
    from apps.nucleo.models import RolParticipacion

    return lambda codigo: RolParticipacion.objects.get(codigo=codigo)


@pytest.fixture
def estado_part(db):
    from apps.nucleo.models import EstadoParticipacion

    return lambda codigo: EstadoParticipacion.objects.get(codigo=codigo)


@pytest.fixture(autouse=True)
def _segunda_fase_activa(settings, request):
    """Las pruebas existentes cubren también los módulos de segunda fase; las que prueban el ajuste apagado usan `sin_segunda_fase`."""
    settings.SEGUNDA_FASE = "sin_segunda_fase" not in request.fixturenames


@pytest.fixture
def sin_segunda_fase(settings):
    settings.SEGUNDA_FASE = False

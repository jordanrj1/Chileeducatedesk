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


@pytest.fixture
def administrador(db):
    return _usuario("admin_prueba", "Administrador")


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

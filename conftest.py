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

"""Pruebas automáticas de organizaciones: crear con lo mínimo, RUT, aviso de duplicados, una sola «Fundación»,
carreras, municipalidad por comuna, contactos con propósito, historial y desactivar sin borrar."""
import pytest
from django.db import IntegrityError, transaction

from apps.nucleo.models import TipoOrganizacion
from apps.organizaciones.models import Carrera, Organizacion

pytestmark = pytest.mark.django_db


def crear(c, **extra):
    t = TipoOrganizacion.objects.get(codigo="empresa_o_partner")
    datos = {"nombre": "Empresa Ficticia", "tipo": t.pk}
    datos.update(extra)
    return c.post("/organizaciones/nueva", datos)


def test_crea_organizacion_minima(cg):
    r = crear(cg)
    o = Organizacion.objects.get()
    assert r.status_code == 302 and o.estado_registro.codigo == "activo" and o.creado_por


def test_crea_organizacion_con_direccion(cg, comuna):
    r = crear(cg, **{"dir-calle": "Calle Falsa", "dir-numero": "123", "dir-comuna": comuna.pk})
    o = Organizacion.objects.get()
    assert r.status_code == 302 and str(o.direccion) == "Calle Falsa 123, Comuna Ficticia"


def test_direccion_parcial_sin_comuna_rechazada(cg):
    r = crear(cg, **{"dir-calle": "Calle Falsa"})
    assert r.status_code == 200 and not Organizacion.objects.exists()


def test_rut_de_organizacion_valido_y_unico(cg):
    from apps.nucleo.utilidades import calcular_dv

    dv = calcular_dv(76123456)
    malo = "1" if dv != "1" else "2"
    assert crear(cg, rut=f"76.123.456-{malo}").status_code == 200  # dígito incorrecto
    rut = f"76123456-{dv}"
    assert crear(cg, rut=rut).status_code == 302
    assert crear(cg, nombre="Otra", rut=rut, confirmar_duplicado="1").status_code == 200
    assert Organizacion.objects.count() == 1


def test_duplicado_por_nombre_parecido(cg):
    crear(cg, nombre="Junta de Vecinos San Pedro de la Costa")
    r = crear(cg, nombre="Junta de Vecinos San Pedro de la Costa II")
    assert r.status_code == 200 and "podría ya existir" in r.content.decode()
    r = crear(cg, nombre="Junta de Vecinos San Pedro de la Costa II", confirmar_duplicado="1")
    assert r.status_code == 302 and Organizacion.objects.count() == 2


def test_una_sola_organizacion_propia(db):
    t = TipoOrganizacion.objects.get(codigo="fundacion_u_ong")
    Organizacion.objects.create(nombre="FCHE", tipo=t, es_propia=True)
    with pytest.raises(IntegrityError), transaction.atomic():
        Organizacion.objects.create(nombre="Otra", tipo=t, es_propia=True)


def test_carreras_solo_en_instituciones_educativas(cg, universidad):
    emp = Organizacion.objects.create(nombre="Emp", tipo=TipoOrganizacion.objects.get(codigo="empresa_o_partner"))
    assert cg.post(f"/organizaciones/{universidad.pk}/carreras/nuevo", {"nombre": "Psicología", "activo": "on"}).status_code == 302
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        Carrera(organizacion=emp, nombre="X").full_clean()
    assert cg.get(f"/organizaciones/{emp.pk}?tab=carreras").status_code == 200
    assert b"Carreras" not in cg.get(f"/organizaciones/{emp.pk}").content.split(b"nav-tabs")[1].split(b"</ul>")[0]


def test_carrera_repetida_rechazada(cg, universidad):
    cg.post(f"/organizaciones/{universidad.pk}/carreras/nuevo", {"nombre": "Psicología", "activo": "on"})
    r = cg.post(f"/organizaciones/{universidad.pk}/carreras/nuevo", {"nombre": "psicología", "activo": "on"})
    assert r.status_code == 200 and universidad.carreras.count() == 1


def test_municipalidad_se_relaciona_con_una_comuna(cg, comuna):
    t = TipoOrganizacion.objects.get(codigo="municipalidad")
    assert crear(cg, nombre="Muni 1", tipo=t.pk, comuna_municipal=comuna.pk).status_code == 302
    assert crear(cg, nombre="Muni 2", tipo=t.pk, comuna_municipal=comuna.pk).status_code == 200  # una por comuna
    r = crear(cg, nombre="Empresa con comuna", comuna_municipal=comuna.pk)
    assert r.status_code == 200  # solo una municipalidad


def test_multiples_contactos_con_proposito(cg, universidad):
    from apps.nucleo.models import TipoContacto

    for valor, prop in [("9 1111 2222", "cartas"), ("9 3333 4444", "donaciones")]:
        cg.post(f"/organizaciones/{universidad.pk}/contactos/nuevo", {"tipo": TipoContacto.objects.get(codigo="telefono_movil").pk, "valor": valor, "proposito": prop, "vigente": "on"})
    assert universidad.contactos.count() == 2


def test_pestanas_y_historial(cg, universidad):
    for tab in ["info", "contactos", "carreras", "personas", "historial"]:
        assert cg.get(f"/organizaciones/{universidad.pk}?tab={tab}").status_code == 200, tab
    cg.post(f"/organizaciones/{universidad.pk}/editar", {"nombre": "Universidad Ficticia Renombrada", "tipo": universidad.tipo.pk})
    assert "Renombrada" in cg.get(f"/organizaciones/{universidad.pk}?tab=historial").content.decode()


def test_persona_vinculada_aparece_en_la_organizacion(cg, universidad, persona):
    cg.post(f"/personas/{persona.pk}/vinculos/nuevo", {"organizacion": universidad.pk, "cargo": "Coordinadora", "tipo_cargo": "funcional"})
    assert "Coordinadora" in cg.get(f"/organizaciones/{universidad.pk}?tab=personas").content.decode()


def test_desactivar_organizacion_no_borra(cg, universidad):
    cg.post(f"/organizaciones/{universidad.pk}/alternar")
    universidad.refresh_from_db()
    assert not universidad.activo


def test_admin_solo_lectura(ca):
    assert ca.get("/organizaciones").status_code == 200
    assert ca.get("/organizaciones/nueva").status_code == 403

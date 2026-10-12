import pytest
from django.contrib.auth.models import Group, User
from django.test import Client

from apps.nucleo.models import Auditoria

pytestmark = pytest.mark.django_db
MSG = "No fue posible iniciar sesión. Revisa tus datos."


def test_ingresa_con_usuario_o_correo(gestor):
    for ident in ("gestor_prueba", "GESTOR_PRUEBA@ejemplo.invalid"):
        r = Client().post("/login", {"username": ident, "password": "clave-ficticia-123"})
        assert r.status_code == 302, ident


def test_clave_incorrecta_mensaje_claro(gestor):
    r = Client().post("/login", {"username": "gestor_prueba", "password": "mala"})
    assert r.status_code == 200 and MSG in r.content.decode()


def test_cuenta_desactivada_no_ingresa(gestor):
    gestor.is_active = False
    gestor.save()
    c = Client()
    r = c.post("/login", {"username": "gestor_prueba", "password": "clave-ficticia-123"})
    assert r.status_code == 200 and MSG in r.content.decode()
    assert c.get("/dashboard").status_code == 302


def test_sesion_activa_se_invalida_al_desactivar(cg, gestor):
    assert cg.get("/dashboard").status_code == 200
    gestor.is_active = False
    gestor.save()
    assert cg.get("/dashboard").status_code == 302


def test_ingresos_quedan_en_auditoria(gestor):
    Client().post("/login", {"username": "gestor_prueba", "password": "clave-ficticia-123"})
    Client().post("/login", {"username": "gestor_prueba", "password": "mala"})
    acciones = set(Auditoria.objects.values_list("accion", flat=True))
    assert {"ingreso", "ingreso_fallido"} <= acciones


def test_roles_semilla_con_permisos():
    g = Group.objects.get(name="Gestor")
    a = Group.objects.get(name="Administrador")
    assert g.permissions.filter(codename="add_persona").exists()
    assert not g.permissions.filter(codename__startswith="delete_").exists()
    assert a.permissions.filter(codename="view_persona").exists()
    assert not a.permissions.filter(codename="add_persona").exists()  # solo mantenimiento
    assert a.permissions.filter(codename="add_user").exists()
    assert not g.permissions.filter(codename="add_user").exists()


@pytest.mark.parametrize("ruta", ["/administracion/usuarios", "/administracion/roles", "/administracion/auditoria", "/administracion/usuarios/nuevo"])
def test_gestor_no_administra(cg, ruta):
    assert cg.get(ruta).status_code == 403


@pytest.mark.parametrize("ruta", ["/administracion/usuarios", "/administracion/roles", "/administracion/auditoria", "/administracion/usuarios/nuevo", "/administracion/catalogos/"])
def test_administrador_si_administra(ca, ruta):
    assert ca.get(ruta).status_code == 200


def test_usuario_sin_rol_bloqueado_aunque_acceda_directo(cs):
    for ruta in ["/personas", "/organizaciones", "/administracion/", "/dashboard", "/territorio"]:
        assert cs.get(ruta).status_code == 403, ruta


def test_admin_crea_usuario_con_persona_y_rol(ca, persona):
    r = ca.post("/administracion/usuarios/nuevo", {
        "username": "nueva_cuenta", "first_name": "", "last_name": "", "email": "Nueva@Ejemplo.invalid",
        "rol": Group.objects.get(name="Gestor").pk, "persona": persona.pk, "password1": "una-clave-larga-123", "password2": "una-clave-larga-123",
    })
    assert r.status_code == 302
    u = User.objects.get(username="nueva_cuenta")
    assert u.email == "nueva@ejemplo.invalid" and u.groups.get().name == "Gestor"
    assert u.perfil.persona == persona and persona.cuenta.usuario == u
    assert u.first_name == "Ana María"
    assert Auditoria.objects.filter(accion="usuario_creado").exists()


def test_persona_sin_cuenta_sigue_existiendo(persona):
    assert not hasattr(persona, "cuenta")


def test_una_persona_no_puede_tener_dos_cuentas(ca, persona):
    datos = {"first_name": "", "last_name": "", "rol": Group.objects.get(name="Gestor").pk, "persona": persona.pk, "password1": "una-clave-larga-123", "password2": "una-clave-larga-123"}
    ca.post("/administracion/usuarios/nuevo", {**datos, "username": "u1", "email": "u1@ejemplo.invalid"})
    r = ca.post("/administracion/usuarios/nuevo", {**datos, "username": "u2", "email": "u2@ejemplo.invalid"})
    assert r.status_code == 200 and not User.objects.filter(username="u2").exists()


def test_clave_debil_rechazada(ca):
    r = ca.post("/administracion/usuarios/nuevo", {
        "username": "debil", "email": "d@ejemplo.invalid", "rol": Group.objects.get(name="Gestor").pk, "password1": "12345", "password2": "12345",
    })
    assert r.status_code == 200 and not User.objects.filter(username="debil").exists()


def test_cambiar_rol_y_desactivar(ca, gestor):
    admin_g = Group.objects.get(name="Administrador")
    ca.post(f"/administracion/usuarios/{gestor.pk}/editar", {"username": gestor.username, "first_name": "", "last_name": "", "email": gestor.email, "rol": admin_g.pk})
    gestor.refresh_from_db()
    assert gestor.groups.get().name == "Administrador"
    assert Auditoria.objects.filter(accion="rol_cambiado").exists()
    ca.post(f"/administracion/usuarios/{gestor.pk}/alternar")
    gestor.refresh_from_db()
    assert gestor.is_active is False


def test_no_puede_desactivarse_a_si_mismo(ca, administrador):
    ca.post(f"/administracion/usuarios/{administrador.pk}/alternar")
    administrador.refresh_from_db()
    assert administrador.is_active


def test_restablecer_clave_solo_admin(ca, cg, gestor):
    assert cg.get(f"/administracion/usuarios/{gestor.pk}/clave").status_code == 403
    r = ca.post(f"/administracion/usuarios/{gestor.pk}/clave", {"password1": "otra-clave-larga-456", "password2": "otra-clave-larga-456"})
    assert r.status_code == 302
    gestor.refresh_from_db()
    assert gestor.check_password("otra-clave-larga-456")


def test_editar_permisos_de_rol_y_no_perder_acceso_admin(ca):
    admin_g = Group.objects.get(name="Administrador")
    ca.post(f"/administracion/roles/{admin_g.pk}", {"permisos": []})
    assert admin_g.permissions.filter(codename="change_user").exists()  # protegido
    gestor_g = Group.objects.get(name="Gestor")
    ver = gestor_g.permissions.get(codename="view_persona")
    ca.post(f"/administracion/roles/{gestor_g.pk}", {"permisos": [ver.pk]})
    assert not gestor_g.permissions.filter(codename="add_persona").exists()
    assert gestor_g.permissions.filter(codename="view_persona").exists()
    assert Auditoria.objects.filter(accion="permisos_modificados").exists()


def test_cambio_de_permisos_sobrevive_a_migraciones(ca):
    from apps.cuentas.roles import sembrar_roles

    gestor_g = Group.objects.get(name="Gestor")
    ver = gestor_g.permissions.get(codename="view_persona")
    ca.post(f"/administracion/roles/{gestor_g.pk}", {"permisos": [ver.pk]})
    sembrar_roles()
    assert not gestor_g.permissions.filter(codename="add_persona").exists()


def test_roles_no_ofrecen_eliminar(ca):
    html = ca.get(f"/administracion/roles/{Group.objects.get(name='Gestor').pk}").content.decode()
    assert "Eliminar" not in html


def test_mi_cuenta_y_cambio_de_clave(cg, gestor):
    assert cg.get("/mi-cuenta").status_code == 200
    r = cg.post("/mi-cuenta/clave", {"old_password": "clave-ficticia-123", "new_password1": "nueva-clave-larga-789", "new_password2": "nueva-clave-larga-789"})
    assert r.status_code == 302
    gestor.refresh_from_db()
    assert gestor.check_password("nueva-clave-larga-789")

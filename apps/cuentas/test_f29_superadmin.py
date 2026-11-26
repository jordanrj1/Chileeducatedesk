"""F29: el Superadministrador reemplaza al Administrador. Todos los datos son ficticios."""
import importlib
from io import StringIO

import pytest
from django.apps import apps as registro
from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command

from apps.cuentas import roles
from apps.nucleo.models import Auditoria

pytestmark = pytest.mark.django_db

PANTALLAS_SUPER = [
    "/administracion/",
    "/administracion/usuarios",
    "/administracion/usuarios/nuevo",
    "/administracion/roles",
    "/administracion/auditoria",
    "/administracion/respaldos",
]


@pytest.mark.parametrize("ruta", PANTALLAS_SUPER)
def test_gestor_recibe_403_en_pantallas_de_superadmin(cg, ruta):
    assert cg.get(ruta).status_code == 403


def test_gestor_recibe_403_en_rol_matriz_y_respaldar_ahora(cg):
    g = Group.objects.get(name="Gestor")
    assert cg.get(f"/administracion/roles/{g.pk}").status_code == 403
    assert cg.post(f"/administracion/roles/{g.pk}", {"restablecer": "1"}).status_code == 403
    assert cg.post("/administracion/respaldos/ahora").status_code == 403


@pytest.mark.parametrize("ruta", PANTALLAS_SUPER + ["/administracion/catalogos/"])
def test_superadmin_accede_a_todo(csa, ruta):
    assert csa.get(ruta).status_code == 200


def test_gestor_ve_catalogos_y_agrega_pero_no_desactiva(cg):
    from apps.nucleo.models import Canal

    assert cg.get("/administracion/catalogos/").status_code == 200
    assert cg.get("/administracion/catalogos/canal/").status_code == 200
    assert cg.post("/administracion/catalogos/canal/", {"nombre": "Canal ficticio", "orden": 99, "activo": "on"}).status_code == 302
    c = Canal.objects.get(nombre="Canal ficticio")
    assert cg.post(f"/administracion/catalogos/canal/{c.pk}/alternar").status_code == 403
    assert cg.get(f"/administracion/catalogos/canal/{c.pk}/unir").status_code == 403


def test_superadmin_desactiva_y_une_catalogos_y_queda_en_auditoria(csa):
    from apps.nucleo.models import Canal

    c = Canal.objects.create(codigo="ficticio_1", nombre="Canal ficticio uno")
    assert csa.post(f"/administracion/catalogos/canal/{c.pk}/alternar").status_code == 302
    c.refresh_from_db()
    assert not c.activo
    assert Auditoria.objects.filter(accion="catalogo_desactivado").exists()
    assert csa.post("/administracion/catalogos/canal/", {"nombre": "Canal ficticio dos", "orden": 98, "activo": "on"}).status_code == 302
    assert Auditoria.objects.filter(accion="catalogo_agregado").exists()


def test_superadmin_tiene_todos_los_permisos_incluidos_los_de_excepcion(superadmin):
    todos = set(Permission.objects.values_list("codename", flat=True))
    suyos = set(Group.objects.get(name="Superadministrador").permissions.values_list("codename", flat=True))
    assert todos == suyos
    assert "reabrir_actividad" in suyos and "respaldar" in suyos
    assert any(c.startswith("desactivar_") for c in suyos) and any(c.startswith("fusionar_") for c in suyos)
    gestor = Group.objects.get(name="Gestor").permissions.values_list("codename", flat=True)
    assert "reabrir_actividad" not in gestor and "respaldar" not in gestor
    assert not any(c.startswith(("desactivar_", "fusionar_")) for c in gestor)


# --- último Superadministrador -----------------------------------------
def test_ultimo_superadmin_no_se_desactiva_desde_otra_cuenta(ca, superadmin):
    """`ca` es una cuenta de prueba con permiso sobre usuarios que no es Superadministrador."""
    r = ca.post(f"/administracion/usuarios/{superadmin.pk}/alternar", follow=True)
    superadmin.refresh_from_db()
    assert superadmin.is_active
    assert "al menos un Superadministrador activo" in r.content.decode()
    assert Auditoria.objects.filter(accion="usuario_desactivacion_rechazada", objeto=superadmin.username).exists()


def test_con_dos_superadmins_se_puede_desactivar_uno_pero_no_el_ultimo(ca, superadmin):
    segundo = User.objects.create_user("segundo_super", email="segundo@ejemplo.invalid", password="clave-ficticia-123")
    segundo.groups.add(Group.objects.get(name="Superadministrador"))
    ca.post(f"/administracion/usuarios/{segundo.pk}/alternar")
    segundo.refresh_from_db()
    assert not segundo.is_active
    ca.post(f"/administracion/usuarios/{superadmin.pk}/alternar")  # ahora es el último
    superadmin.refresh_from_db()
    assert superadmin.is_active


def test_un_superadmin_inactivo_no_cuenta_como_otro(ca, superadmin):
    inactivo = User.objects.create_user("inactivo_super", email="inactivo@ejemplo.invalid", password="clave-ficticia-123", is_active=False)
    inactivo.groups.add(Group.objects.get(name="Superadministrador"))
    from apps.cuentas.protecciones import es_el_ultimo

    assert es_el_ultimo(superadmin)


def test_ultimo_superadmin_no_pierde_el_rol_desde_el_formulario(csa, superadmin):
    gestor_g = Group.objects.get(name="Gestor")
    r = csa.post(f"/administracion/usuarios/{superadmin.pk}/editar", {
        "username": superadmin.username, "first_name": "", "last_name": "", "email": superadmin.email, "rol": gestor_g.pk,
    })
    assert r.status_code == 200 and "al menos un Superadministrador activo" in r.content.decode()
    assert superadmin.groups.get().name == "Superadministrador"


def test_superadmin_si_puede_cambiar_rol_a_otro_superadmin_cuando_hay_dos(csa, superadmin):
    segundo = User.objects.create_user("segundo_super", email="segundo@ejemplo.invalid", password="clave-ficticia-123")
    segundo.groups.add(Group.objects.get(name="Superadministrador"))
    gestor_g = Group.objects.get(name="Gestor")
    r = csa.post(f"/administracion/usuarios/{segundo.pk}/editar", {
        "username": segundo.username, "first_name": "", "last_name": "", "email": segundo.email, "rol": gestor_g.pk,
    })
    assert r.status_code == 302
    assert segundo.groups.get().name == "Gestor"


# --- permisos nuevos y migración ---------------------------------------
def test_permiso_nuevo_se_asigna_solo_al_superadmin(superadmin):
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(User)
    nuevo = Permission.objects.create(codename="permiso_ficticio_nuevo", name="Permiso ficticio", content_type=ct)
    g = Group.objects.get(name="Superadministrador")
    assert not g.permissions.filter(pk=nuevo.pk).exists()
    roles.asegurar_permisos_superadmin()
    assert g.permissions.filter(pk=nuevo.pk).exists()
    assert not Group.objects.get(name="Gestor").permissions.filter(pk=nuevo.pk).exists()
    roles.sembrar_roles()  # el arranque (post_migrate) hace lo mismo
    assert g.permissions.filter(pk=nuevo.pk).exists()


def test_asegurar_permisos_crea_el_rol_si_falta():
    Group.objects.filter(name="Superadministrador").delete()
    roles.asegurar_permisos_superadmin()
    assert Group.objects.get(name="Superadministrador").permissions.count() == Permission.objects.count()


def test_migracion_renombra_el_grupo_y_conserva_usuarios():
    mig = importlib.import_module("apps.cuentas.migrations.0004_superadministrador")
    g = Group.objects.get(name="Superadministrador")
    u = User.objects.create_user("antiguo_admin", email="antiguo@ejemplo.invalid", password="clave-ficticia-123")
    u.groups.add(g)
    mig.a_administrador(registro, None)  # reversa
    assert not Group.objects.filter(name="Superadministrador").exists()
    assert list(Group.objects.get(name="Administrador").user_set.values_list("username", flat=True)) == ["antiguo_admin"]
    mig.a_superadmin(registro, None)
    g = Group.objects.get(name="Superadministrador")
    assert not Group.objects.filter(name="Administrador").exists()
    assert list(g.user_set.values_list("username", flat=True)) == ["antiguo_admin"]
    assert g.permissions.count() == Permission.objects.count()


def test_migracion_une_si_existian_ambos_grupos():
    mig = importlib.import_module("apps.cuentas.migrations.0004_superadministrador")
    viejo = Group.objects.create(name="Administrador")
    u = User.objects.create_user("viejo", email="viejo@ejemplo.invalid", password="clave-ficticia-123")
    u.groups.add(viejo)
    mig.a_superadmin(registro, None)
    assert not Group.objects.filter(name="Administrador").exists()
    assert Group.objects.get(name="Superadministrador").user_set.filter(pk=u.pk).exists()


# --- crear_usuario -----------------------------------------------------
def test_crear_usuario_con_rol_superadministrador():
    call_command("crear_usuario", "super_nueva", correo="super@ejemplo.invalid", rol="Superadministrador", password="una-clave-larga-123", stdout=StringIO())
    assert User.objects.get(username="super_nueva").groups.get().name == "Superadministrador"


def test_crear_usuario_ya_no_acepta_administrador():
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("crear_usuario", "x_antiguo", correo="x@ejemplo.invalid", rol="Administrador", password="una-clave-larga-123", stdout=StringIO())


# --- roles y permisos, respaldos --------------------------------------
def test_matriz_de_roles_muestra_modulos_y_acciones(csa):
    g = Group.objects.get(name="Gestor")
    html = csa.get(f"/administracion/roles/{g.pk}").content.decode()
    assert "Restablecer permisos iniciales" in html and "Otras acciones" in html and "persona" in html


def test_restablecer_permisos_iniciales_del_gestor(csa):
    g = Group.objects.get(name="Gestor")
    inicial = set(g.permissions.values_list("pk", flat=True))
    csa.post(f"/administracion/roles/{g.pk}", {"permisos": [Permission.objects.get(codename="view_persona").pk]})
    assert set(g.permissions.values_list("pk", flat=True)) != inicial
    r = csa.post(f"/administracion/roles/{g.pk}", {"restablecer": "1"})
    assert r.status_code == 302
    assert set(g.permissions.values_list("pk", flat=True)) == inicial
    assert Auditoria.objects.filter(accion="permisos_restablecidos", objeto="Gestor").exists()


def test_respaldar_ahora_solo_post(csa):
    assert csa.get("/administracion/respaldos/ahora").status_code == 405


def test_respaldar_ahora_ejecuta_el_comando(csa, monkeypatch, tmp_path):
    monkeypatch.setenv("RESPALDO_DIR", str(tmp_path))
    llamadas = []

    def falso(nombre, *a, **kw):
        llamadas.append((nombre, kw.get("destino")))
        (tmp_path / "fche_bd_20260101_000000.dump").write_bytes(b"x" * 2048)
        kw["stdout"].write("Respaldo listo.")

    monkeypatch.setattr("django.core.management.call_command", falso)
    r = csa.post("/administracion/respaldos/ahora", follow=True)
    assert llamadas == [("respaldar", str(tmp_path))]
    html = r.content.decode()
    assert "Respaldo listo" in html and "fche_bd_20260101_000000.dump" in html and "2 KB" in html
    assert Auditoria.objects.filter(accion="respaldo_manual").exists()


def test_respaldos_lista_vacia_y_con_archivos(csa, monkeypatch, tmp_path):
    monkeypatch.setenv("RESPALDO_DIR", str(tmp_path / "no_existe"))
    assert "Aún no hay respaldos" in csa.get("/administracion/respaldos").content.decode()
    monkeypatch.setenv("RESPALDO_DIR", str(tmp_path))
    (tmp_path / "fche_documentos_20260101_000000.zip").write_bytes(b"z" * 10)
    assert "fche_documentos_20260101_000000.zip" in csa.get("/administracion/respaldos").content.decode()


def test_respaldar_ahora_con_error_informa_y_no_cae(csa, monkeypatch, tmp_path):
    from django.core.management.base import CommandError

    monkeypatch.setenv("RESPALDO_DIR", str(tmp_path))

    def falla(*a, **kw):
        raise CommandError("No se encontró pg_dump.")

    monkeypatch.setattr("django.core.management.call_command", falla)
    r = csa.post("/administracion/respaldos/ahora", follow=True)
    assert r.status_code == 200 and "No se pudo respaldar" in r.content.decode()
    assert Auditoria.objects.filter(accion="respaldo_fallido").exists()


def test_el_codigo_ya_no_menciona_administrador_como_rol():
    import pathlib

    base = pathlib.Path(__file__).resolve().parents[2]
    for ruta in [base / "apps/cuentas/roles.py", base / "apps/cuentas/views_admin.py", base / "apps/nucleo/permisos.py", base / "templates/administracion"]:
        archivos = [ruta] if ruta.is_file() else list(ruta.glob("*.html"))
        for f in archivos:
            assert "Administrador" not in f.read_text().replace("Superadministrador", ""), f

"""Escenarios del catálogo «FCHE — Escenarios hipotéticos». Cada prueba lleva el ID del escenario. Datos ficticios."""
import pytest
from django.contrib.auth.models import User
from django.test import Client

pytestmark = pytest.mark.django_db
CLAVE = "clave-ficticia-123"


# --- AC: acceso ---------------------------------------------------------------------------------------
def _fallar(ident, veces):
    for _ in range(veces):
        Client().post("/login", {"username": ident, "password": "mala"})


def test_AC_E1_bloqueo_tras_5_intentos_y_desbloqueo(gestor, ca):
    _fallar("gestor_prueba", 5)
    r = Client().post("/login", {"username": "gestor_prueba", "password": CLAVE})
    assert r.status_code == 200 and "Demasiados intentos fallidos" in r.content.decode()
    # también con el correo (la misma cuenta)
    assert "Demasiados intentos" in Client().post("/login", {"username": "gestor_prueba@ejemplo.invalid", "password": CLAVE}).content.decode()
    html = ca.get("/administracion/usuarios").content.decode()
    assert "Bloqueado por intentos fallidos" in html
    assert "Desbloquear acceso" in ca.get(f"/administracion/usuarios/{gestor.pk}/editar").content.decode()
    ca.post(f"/administracion/usuarios/{gestor.pk}/desbloquear")
    assert Client().post("/login", {"username": "gestor_prueba", "password": CLAVE}).status_code == 302


def test_AC_E1_el_bloqueo_no_revela_si_la_cuenta_existe():
    _fallar("no-existe@ejemplo.invalid", 5)
    html = Client().post("/login", {"username": "no-existe@ejemplo.invalid", "password": "x"}).content.decode()
    assert "Demasiados intentos fallidos" in html  # el mismo trato que una cuenta real


def test_AC_E1_ingreso_correcto_reinicia_el_conteo(gestor):
    _fallar("gestor_prueba", 4)
    assert Client().post("/login", {"username": "gestor_prueba", "password": CLAVE}).status_code == 302
    _fallar("gestor_prueba", 4)
    assert Client().post("/login", {"username": "gestor_prueba", "password": CLAVE}).status_code == 302


def test_AC_E1_bloqueo_vence_solo(gestor, settings):
    from datetime import timedelta

    from django.utils import timezone

    from apps.nucleo.models import Auditoria

    _fallar("gestor_prueba", 5)
    Auditoria.objects.filter(accion="ingreso_fallido").update(fecha=timezone.now() - timedelta(minutes=settings.BLOQUEO_MINUTOS + 1))
    assert Client().post("/login", {"username": "gestor_prueba", "password": CLAVE}).status_code == 302


def test_AC_E4_tras_ingresar_vuelve_al_enlace_guardado(gestor, persona):
    c = Client()
    r = c.get(persona.get_absolute_url())
    assert r.status_code == 302 and "next=" in r["Location"]
    r = c.post("/login?next=" + persona.get_absolute_url(), {"username": "gestor_prueba", "password": CLAVE, "next": persona.get_absolute_url()})
    assert r["Location"] == persona.get_absolute_url()


def test_AC_E5_desactivar_cuenta_cierra_su_sesion(cg, gestor):
    gestor.is_active = False
    gestor.save()
    assert cg.get("/dashboard").status_code == 302


def test_AC_E8_contrasena_1234_rechazada(cg):
    r = cg.post("/mi-cuenta/clave", {"old_password": CLAVE, "new_password1": "1234", "new_password2": "1234"})
    assert r.status_code == 200 and User.objects.get(username="gestor_prueba").check_password(CLAVE)


def test_AC_E7_usuario_activo_y_cerrar_sesion_visibles(cg):
    html = cg.get("/dashboard").content.decode()
    assert "gestor_prueba" in html and "Cerrar sesión" in html and "data-cerrar-sesion" in html


# --- UI: formularios -----------------------------------------------------------------------------------
def test_UI_E5_edicion_simultanea_no_pisa_cambios(cg, persona):
    html = cg.get(f"/personas/{persona.pk}/editar").content.decode()
    import re

    version = re.search(r'name="_version" value="(\d+)"', html).group(1)
    base = {"nombres": "Ana María", "apellido_paterno": "Pérez", "apellido_materno": "Soto"}
    # otra pestaña guarda primero
    assert cg.post(f"/personas/{persona.pk}/editar", {**base, "profesion": "Docente", "_version": version}).status_code == 302
    # la primera pestaña intenta guardar con la versión vieja
    r = cg.post(f"/personas/{persona.pk}/editar", {**base, "profesion": "Enfermera", "_version": version})
    persona.refresh_from_db()
    assert r.status_code == 200 and "cambió mientras lo editabas" in r.content.decode() and persona.profesion == "Docente"


def test_UI_E5_tambien_en_organizacion_y_lugar(cg, universidad, lugar):
    import re

    for url, datos in ((f"/organizaciones/{universidad.pk}/editar", {"nombre": "U2", "tipo": universidad.tipo_id}),
                       (f"/lugares/{lugar.pk}/editar", {"nombre": "Sala 2", "tipo": lugar.tipo_id, "dir-comuna": lugar.direccion.comuna_id, "dir-calle": "X"})):
        v = re.search(r'name="_version" value="(\d+)"', cg.get(url).content.decode()).group(1)
        cg.post(url, {**datos, "_version": v})
        r = cg.post(url, {**datos, "nombre": "Otro", "_version": v})
        assert "cambió mientras lo editabas" in r.content.decode(), url


def test_UI_E1_formularios_preparados_contra_doble_envio(cg):
    assert "/static/js/fche.js" in cg.get("/personas/nueva").content.decode()
    from pathlib import Path

    js = Path("static/js/fche.js").read_text()
    assert "dataset.enviando" in js and "sessionStorage" in js


def test_UI_E2_E3_tras_guardar_se_redirige(cg):
    r = cg.post("/personas/nueva", {"modo": "rapida", "nombres": "Una Vez"})
    assert r.status_code == 302  # post-redirección: F5 o «Atrás» no reenvían


def test_UI_E10_volver_conserva_filtros(cg, persona):
    cg.get("/personas?q=ana&activo=*&page=1")
    html = cg.get(persona.get_absolute_url()).content.decode()
    assert 'href="/personas?q=ana&amp;activo=*&amp;page=1"' in html


def test_UI_E13_listado_vacio_con_boton_para_crear(cg):
    html = cg.get("/lugares").content.decode()
    assert "Aún no hay registros" in html and "+ Nuevo lugar" in html

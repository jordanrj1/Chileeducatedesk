"""Pruebas automáticas básicas del sistema: arranca, /salud responde, ingreso y cierre de sesión,
pantallas 403 y 404 propias, roles, y que no se cargue nada desde internet."""
import pytest
from django.contrib.auth.models import Group, User
from django.db.utils import OperationalError
from django.test import Client
from unittest import mock

pytestmark = pytest.mark.django_db


def crear_usuario(grupo=None):
    usuario = User.objects.create_user("usuario_prueba", password="clave-ficticia-123")
    if grupo:
        usuario.groups.add(Group.objects.get(name=grupo))
    return usuario


def test_sistema_arranca_y_salud_responde():
    r = Client().get("/salud")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok"}


def test_salud_503_si_la_base_falla():
    with mock.patch("apps.nucleo.views.connection.cursor", side_effect=OperationalError):
        assert Client().get("/salud").status_code == 503


def test_anonimo_va_al_login():
    r = Client().get("/dashboard")
    assert r.status_code == 302 and r["Location"].startswith("/login")


def test_grupos_existen():
    assert set(Group.objects.values_list("name", flat=True)) >= {"Gestor", "Administrador"}


def test_ingreso_correcto_lleva_al_dashboard():
    crear_usuario("Gestor")
    c = Client()
    r = c.post("/login", {"username": "usuario_prueba", "password": "clave-ficticia-123"})
    assert r.status_code == 302 and r["Location"] == "/dashboard"
    assert c.get("/dashboard").status_code == 200


def test_ingreso_incorrecto_no_entra():
    crear_usuario("Gestor")
    r = Client().post("/login", {"username": "usuario_prueba", "password": "mala"})
    assert r.status_code == 200


def test_usuario_sin_grupo_recibe_403_propio():
    c = Client()
    c.force_login(crear_usuario())
    r = c.get("/dashboard")
    assert r.status_code == 403
    assert "403" in r.content.decode()


def test_gestor_no_entra_a_administracion():
    c = Client()
    c.force_login(crear_usuario("Gestor"))
    assert c.get("/administracion/").status_code == 403


def test_administrador_entra_a_administracion():
    c = Client()
    c.force_login(crear_usuario("Administrador"))
    assert c.get("/administracion/").status_code == 200


def test_ruta_inexistente_da_404_propio():
    c = Client()
    c.force_login(crear_usuario("Gestor"))
    r = c.get("/no-existe")
    assert r.status_code == 404 and "404" in r.content.decode()


def test_cierre_de_sesion():
    c = Client()
    c.force_login(crear_usuario("Gestor"))
    assert c.post("/logout").status_code == 302
    assert c.get("/dashboard").status_code == 302


def test_sin_recursos_externos():
    c = Client()
    c.force_login(crear_usuario("Gestor"))
    html = c.get("/dashboard").content.decode()
    assert "http://" not in html and "https://" not in html


def test_paginas_con_sesion_no_se_guardan_en_el_navegador(cg):
    """Con sesión iniciada, el navegador no guarda las páginas: «Atrás» y una pestaña reabierta muestran lo actual."""
    assert "no-store" in cg.get("/dashboard")["Cache-Control"]

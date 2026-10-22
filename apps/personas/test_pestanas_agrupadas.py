"""Ficha de persona en 8 pestañas (antes 17): los nombres antiguos abren la pestaña que ahora los reúne, con su contenido,
y sin permiso de datos sensibles no se ve el contacto de emergencia ni la pestaña Privacidad. Datos ficticios."""
import re

import pytest
from django.contrib.auth.models import Permission
from django.test import Client

OCHO = ["resumen", "contacto", "estudios", "vinculos", "participaciones", "documentos", "privacidad", "historial"]


def _pestanas(html):
    return re.findall(r'<a class="nav-link[^"]*" href="\?tab=([a-z_]+)"', html)


def _activa(html):
    return re.search(r'class="nav-link active" href="\?tab=([a-z_]+)"', html).group(1)


def _cuerpo(html):
    return html.split('id="pestana"')[1]


def test_la_ficha_tiene_8_pestanas(cg, persona):
    html = cg.get(persona.get_absolute_url()).content.decode()
    assert _pestanas(html) == OCHO
    assert _activa(html) == "resumen"


@pytest.mark.parametrize("antigua, nueva, texto", [
    ("datos", "resumen", "Datos de la persona"),
    ("contactos", "contacto", "Contactos"),
    ("direcciones", "contacto", "Direcciones 🔒"),
    ("emergencia", "contacto", "Contacto de emergencia 🔒"),
    ("formacion", "estudios", "Formación"),
    ("experiencia", "estudios", "Experiencia en la Fundación"),
    ("disponibilidad", "estudios", "Disponibilidad"),
    ("comunidades", "vinculos", "+ Comunidad"),
    ("trayectoria", "participaciones", "Actividades en las que ha participado"),
    ("interacciones", "participaciones", "Interacciones"),
    ("sensibles", "privacidad", "Datos sensibles (Ley 21.719)"),
    ("apoderados", "privacidad", "Apoderados 🔒"),
    ("consentimientos", "privacidad", "Consentimientos y autorizaciones"),
    ("origen", "historial", "Origen de la información"),
])
def test_cada_nombre_antiguo_abre_su_pestana_con_el_contenido(cg, persona, antigua, nueva, texto):
    html = cg.get(f"{persona.get_absolute_url()}?tab={antigua}").content.decode()
    assert _activa(html) == nueva
    assert texto in _cuerpo(html)


def test_resumen_muestra_solo_lo_completado_y_agrupa_lo_vacio(cg, persona):
    persona.profesion = "Profesora ficticia"
    persona.save()
    cuerpo = _cuerpo(cg.get(persona.get_absolute_url()).content.decode())
    assert "Profesora ficticia" in cuerpo
    assert "<dd>—</dd>" not in cuerpo  # nada de campos vacíos con guion
    sin_completar = cuerpo.split("Sin completar (")[1]
    assert "Nacionalidad" in sin_completar and "Completar ficha" in sin_completar


def test_sin_ver_sensibles_no_hay_privacidad_ni_contacto_de_emergencia(gestor, persona):
    grupo = gestor.groups.first()
    grupo.permissions.remove(*Permission.objects.filter(codename__in=["ver_sensibles", "view_consentimiento"]))
    c = Client()
    c.force_login(gestor)
    html = c.get(persona.get_absolute_url()).content.decode()
    assert "privacidad" not in _pestanas(html)
    contacto = _cuerpo(c.get(f"{persona.get_absolute_url()}?tab=emergencia").content.decode())
    assert "Contactos" in contacto and "Contacto de emergencia" not in contacto
    # un enlace antiguo a una pestaña restringida no muestra nada de ella: abre la primera pestaña
    assert _activa(c.get(f"{persona.get_absolute_url()}?tab=sensibles").content.decode()) == "resumen"


def test_privacidad_se_ve_con_solo_consentimientos(gestor, persona):
    gestor.groups.first().permissions.remove(Permission.objects.get(codename="ver_sensibles"))
    c = Client()
    c.force_login(gestor)
    cuerpo = _cuerpo(c.get(f"{persona.get_absolute_url()}?tab=privacidad").content.decode())
    assert "Consentimientos y autorizaciones" in cuerpo
    assert "Datos sensibles (Ley 21.719)" not in cuerpo and "Apoderados" not in cuerpo

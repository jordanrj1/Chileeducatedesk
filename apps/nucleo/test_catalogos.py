"""Pruebas automáticas de catálogos: el Gestor agrega y edita, el Administrador desactiva,
nada se borra y un valor usado se conserva."""
import pytest
from django.db.models import ProtectedError

from apps.nucleo.models import CATALOGOS, Canal, EstadoActividad, RolParticipacion, TipoActividad
from apps.nucleo.vistas_catalogos import dependencias

pytestmark = pytest.mark.django_db


def test_catalogos_iniciales_cargados():
    assert set(EstadoActividad.objects.values_list("codigo", flat=True)) >= {"planificada", "confirmada", "reprogramada", "suspendida", "cancelada", "realizada", "pendiente"}
    assert RolParticipacion.objects.filter(codigo="contacto_institucional").exists()
    assert TipoActividad.objects.count() == 6 and Canal.objects.exists()
    assert all(m.objects.exists() for m in CATALOGOS.values())


def test_crear_opcion_genera_codigo(cg):
    r = cg.post("/administracion/catalogos/tipo-actividad/", {"nombre": "Evaluación final", "orden": 9, "activo": "on"})
    assert r.status_code == 302
    assert TipoActividad.objects.get(nombre="Evaluación final").codigo == "evaluacion_final"


def test_nombre_vacio_rechazado(cg):
    cg.post("/administracion/catalogos/tipo-actividad/", {"nombre": "", "orden": 1})
    assert not TipoActividad.objects.filter(nombre="").exists()


def test_desactivar_y_reactivar(ca):
    cg = ca
    t = TipoActividad.objects.get(codigo="taller")
    cg.post(f"/administracion/catalogos/tipo-actividad/{t.pk}/alternar")
    t.refresh_from_db()
    assert not t.activo
    cg.post(f"/administracion/catalogos/tipo-actividad/{t.pk}/alternar")
    t.refresh_from_db()
    assert t.activo


def test_editar_no_cambia_codigo(cg):
    t = TipoActividad.objects.get(codigo="taller")
    cg.post(f"/administracion/catalogos/tipo-actividad/{t.pk}/editar", {"nombre": "Taller práctico", "orden": 1, "activo": "on"})
    t.refresh_from_db()
    assert t.nombre == "Taller práctico" and t.codigo == "taller"


def test_catalogo_inexistente_404(cg):
    assert cg.get("/administracion/catalogos/no-existe/").status_code == 404


def test_sin_permiso_403(cs):
    assert cs.get("/administracion/catalogos/").status_code == 403
    assert cs.post("/administracion/catalogos/canal/", {"nombre": "X", "orden": 1}).status_code == 403


def test_opcion_usada_no_se_puede_eliminar(persona):
    from apps.nucleo.models import OrigenPersona

    o = OrigenPersona.objects.get(codigo="invitacion")
    persona.origen = o
    persona.save()
    assert dependencias(o) == [("personas", 1)] or dependencias(o)[0][1] == 1
    with pytest.raises(ProtectedError):
        o.delete()


def test_la_interfaz_no_ofrece_eliminar(cg):
    html = cg.get("/administracion/catalogos/canal/").content.decode()
    assert "Eliminar" not in html


def test_el_gestor_agrega_pero_no_desactiva(cg):
    t = TipoActividad.objects.get(codigo="taller")
    assert cg.post(f"/administracion/catalogos/tipo-actividad/{t.pk}/alternar").status_code == 403
    t.refresh_from_db()
    assert t.activo
    html = cg.get("/administracion/catalogos/tipo-actividad/").content.decode()
    assert "+ Agregar valor" in html and ">Desactivar<" not in html

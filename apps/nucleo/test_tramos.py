"""Pruebas de los tramos de edad: el catálogo viene cargado y se edita en Catálogos, la actividad y la comunidad
guardan varios tramos, el texto anterior se conserva para revisarlo y el intérprete no inventa ante un texto ambiguo."""
import pytest

from apps.actividades.models import Actividad
from apps.comunidades.models import Comunidad
from apps.nucleo.models import CATALOGOS, TramoEtario
from apps.nucleo.tramos import asignar_desde_texto, interpretar
from apps.nucleo.vistas_catalogos import dependencias

pytestmark = pytest.mark.django_db


def _tramos():
    return list(TramoEtario.objects.values_list("codigo", "edad_min", "edad_max"))


def test_catalogo_cargado_y_editable(cg, ca):
    assert CATALOGOS["tramo-etario"] is TramoEtario
    assert list(TramoEtario.objects.values_list("codigo", "edad_min", "edad_max")) == [
        ("primera_infancia", 0, 5), ("ninez", 6, 12), ("adolescencia", 13, 17), ("jovenes", 18, 29), ("personas_adultas", 30, 59), ("personas_mayores", 60, None),
    ]
    html = cg.get("/administracion/catalogos/tramo-etario/").content.decode()
    assert "<th>Edades</th>" in html and "60 años o más" in html
    # el Gestor agrega; una edad máxima menor que la mínima se rechaza
    cg.post("/administracion/catalogos/tramo-etario/", {"nombre": "Adultez temprana", "edad_min": 25, "edad_max": 20, "orden": 7, "activo": "on"})
    assert not TramoEtario.objects.filter(nombre="Adultez temprana").exists()
    cg.post("/administracion/catalogos/tramo-etario/", {"nombre": "Adultez temprana", "edad_min": 20, "edad_max": 25, "orden": 7, "activo": "on"})
    assert TramoEtario.objects.get(nombre="Adultez temprana").edades == "20 a 25 años"
    # desactivar es solo del Administrador
    t = TramoEtario.objects.get(codigo="ninez")
    assert cg.post(f"/administracion/catalogos/tramo-etario/{t.pk}/alternar").status_code == 403
    ca.post(f"/administracion/catalogos/tramo-etario/{t.pk}/alternar")
    t.refresh_from_db()
    assert not t.activo


def test_seleccion_multiple_guarda_en_actividad_y_comunidad(cg, comuna, actividad):
    jov, adu = TramoEtario.objects.filter(codigo__in=["jovenes", "personas_adultas"]).order_by("orden")
    html = cg.get(f"/actividades/{actividad.pk}/editar").content.decode()
    assert 'type="checkbox" name="tramos_etarios"' in html and "Jóvenes (18 a 29 años)" in html
    assert 'name="rango_etario"' not in html  # sin texto anterior, el campo no aparece
    r = cg.post(f"/actividades/{actividad.pk}/editar", {"nombre": actividad.nombre, "tramos_etarios": [jov.pk, adu.pk]})
    assert r.status_code == 302
    assert set(actividad.tramos_etarios.all()) == {jov, adu}
    assert dependencias(jov) == [("actividades", 1)]
    r = cg.post("/comunidades/nueva", {"nombre": "Vecinos Ficticios", "tipo": "vecinal", "comuna": comuna.pk, "tramos_etarios": [adu.pk]})
    assert r.status_code == 302
    com = Comunidad.objects.get()
    assert list(com.tramos_etarios.all()) == [adu]
    assert "Personas adultas (30 a 59 años)" in cg.get(f"/comunidades/{com.pk}").content.decode()


def test_texto_anterior_se_convierte_sin_borrarse_y_se_puede_revisar(cg, crear_actividad):
    a = crear_actividad(rango_etario="jóvenes de 15 a 29")
    b = crear_actividad(nombre="Otra", rango_etario="familias del sector")
    asignar_desde_texto(Actividad, TramoEtario)
    asignar_desde_texto(Actividad, TramoEtario)  # repetirla no duplica ni cambia nada
    assert set(a.tramos_etarios.values_list("codigo", flat=True)) == {"adolescencia", "jovenes"}
    assert not b.tramos_etarios.exists()
    b.refresh_from_db()
    assert b.rango_etario == "familias del sector"
    html = cg.get(f"/actividades/{b.pk}?tab=publico").content.decode()
    assert "Antes decía: «familias del sector»" in html and "Por revisar" in html
    html = cg.get(f"/actividades/{b.pk}/editar").content.decode()
    assert "Rango etario (texto anterior)" in html and 'name="rango_etario"' in html


@pytest.mark.parametrize("texto, esperado", [
    ("jóvenes de 15 a 29", {"adolescencia", "jovenes"}),
    ("Personas adultas y mayores", {"personas_adultas", "personas_mayores"}),
    ("Adultos mayores", {"personas_mayores"}),
    ("mayores de 60", {"personas_mayores"}),
    ("menores de edad", {"primera_infancia", "ninez", "adolescencia"}),
    ("niños de 6 a 12 años", {"ninez"}),
    # ambiguo o sin edades: no inventa
    ("familias del sector", set()),
    ("estudiantes de 1 a 4 medio", set()),
    ("todo público", set()),
    ("", set()),
])
def test_interprete_conservador(texto, esperado):
    assert interpretar(texto, _tramos()) == esperado

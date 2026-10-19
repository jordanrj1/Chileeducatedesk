"""Pruebas de la selección múltiple desplegable: los formularios dibujan un botón con el resumen de lo elegido, un buscador
y las casillas dentro de un bloque plegable (en vez de casillas a la vista); enviar varias opciones guarda igual que antes;
el resumen se entiende sin JavaScript y dibujar más opciones no suma consultas. Todos los datos son ficticios."""
import re

import pytest
from django import forms
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.comunidades.models import Comunidad
from apps.nucleo.formularios import BootstrapMixin, SelectorMultiple
from apps.nucleo.models import AreaTematica, PerfilPersona
from apps.personas.models import Persona

pytestmark = pytest.mark.django_db


def _bloques(html):
    return re.findall(r'<div class="fche-multi" data-multi data-etiqueta="([^"]*)">(.*?)</details>', html, re.S)


def test_formularios_dibujan_la_seleccion_multiple_desplegable(cg):
    html = cg.get("/comunidades/nueva").content.decode()
    bloques = dict(_bloques(html))
    assert "class=\"fche-opciones\"" not in html
    areas = bloques["Áreas de interés"]
    assert '<summary class="form-select fche-multi__boton"' in areas and ">Elegir…</span>" in areas
    assert areas.count('type="checkbox" name="areas_interes"') == AreaTematica.objects.filter(activo=True).count()
    # el buscador solo aparece con JavaScript y no se envía (no tiene nombre)
    assert re.search(r'data-multi-filtro hidden>\s*<span[^>]*>.*?</span>\s*<input type="search" class="form-control fche-selector__entrada" placeholder', areas, re.S)
    html = cg.get("/personas/nueva?modo=completa").content.decode()
    # los perfiles con ficha propia (estudiante, vecino…) se marcan aparte, en «Tipo de registro»; aquí quedan los demás
    assert [e for e, _ in _bloques(html)] == ["Otros perfiles", "Áreas de interés"]
    assert 'aria-labelledby="id_perfiles_etiqueta id_perfiles_resumen" aria-describedby="id_perfiles_helptext"' in html


def test_enviar_varias_opciones_guarda_igual(cg, comuna):
    a1, a2 = AreaTematica.objects.filter(activo=True)[:2]
    p1, p2 = PerfilPersona.objects.filter(activo=True)[:2]
    r = cg.post("/comunidades/nueva", {"nombre": "Vecinos Ficticios", "tipo": "vecinal", "comuna": comuna.pk, "areas_interes": [a1.pk, a2.pk]})
    assert r.status_code == 302
    assert set(Comunidad.objects.get().areas_interes.all()) == {a1, a2}
    r = cg.post("/personas/nueva", {"modo": "completa", "nombres": "Rocío", "apellido_paterno": "Inventada", "perfiles": [p1.pk, p2.pk],
                                    "areas_interes": [a1.pk, a2.pk], "correo": "rocio@ejemplo.invalid"})
    assert r.status_code == 302
    p = Persona.objects.get(nombres="Rocío")
    assert set(p.perfiles.all()) == {p1, p2} and set(p.areas_interes.all()) == {a1, a2}


def test_resumen_de_lo_elegido_sin_javascript(cg, persona):
    perfiles = list(PerfilPersona.objects.filter(activo=True, ficha="")[:3])  # los de la lista (los con ficha van en «Tipo de registro»)
    persona.perfiles.set(perfiles)
    html = cg.get(f"/personas/{persona.pk}/editar").content.decode()
    bloques = dict(_bloques(html))
    nombres = [str(p) for p in PerfilPersona.objects.filter(pk__in=[p.pk for p in perfiles])]  # en el orden del catálogo
    assert f">3 opciones elegidas: {nombres[0]}, {nombres[1]} y 1 más</span>" in bloques["Otros perfiles"]
    assert bloques["Otros perfiles"].count(" checked") == 3
    assert 'class="fche-multi__resumen is-vacio"' in bloques["Áreas de interés"]


def test_toda_seleccion_multiple_pasa_a_desplegable(persona, crear_persona):
    class Formulario(BootstrapMixin, forms.Form):
        temas = forms.MultipleChoiceField(choices=[("a", "Arte"), ("b", "Baile")], required=False)  # lista múltiple de Django
        personas = forms.ModelMultipleChoiceField(Persona.objects.none(), widget=forms.CheckboxSelectMultiple, required=False)

    f = Formulario()
    f.fields["personas"].queryset = Persona.objects.filter(pk=persona.pk)  # como hace la bitácora con sus facilitadores
    crear_persona("Fuera de la lista")
    assert isinstance(f.fields["temas"].widget, SelectorMultiple) and isinstance(f["personas"].field.widget, SelectorMultiple)
    assert f["temas"].widget_type == "selectormultiple"
    assert [o.choice_label for o in f["personas"]] == [str(persona)]
    assert 'class="form-check-input"' in str(f["temas"]) and Formulario.base_fields["temas"].widget.__class__ is forms.SelectMultiple


def test_mas_opciones_no_suman_consultas(cg):
    def contar():
        with CaptureQueriesContext(connection) as c:
            assert cg.get("/personas/nueva?modo=completa").status_code == 200
        return len(c)

    antes = contar()
    for i in range(15):
        AreaTematica.objects.create(codigo=f"tema_ficticio_{i}", nombre=f"Tema ficticio {i}")
    assert contar() == antes

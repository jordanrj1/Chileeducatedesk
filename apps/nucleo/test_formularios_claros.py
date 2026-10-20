"""Pruebas de claridad de los formularios (F24 T8): ninguna etiqueta ni ayuda muestra códigos internos del proyecto
(como «HU-PE-03», «RF-08» o «F22»), que Claudio no tiene por qué conocer. Recorre todos los formularios de todas las apps,
así que también vigila los que se agreguen después."""
import importlib
import inspect
import re

import pytest
from django import forms

pytestmark = pytest.mark.django_db

CODIGO_INTERNO = re.compile(r"\b(HU|RF|RNF|PE|OR|LU|DO|AT|AG|VA|IG|DA|CA|SE|UI|AC|NR|CO|OP|BU|IN|RE|HI|TE|SO|US)-?E?\d|\bF\d{2}\b")
APPS = ["actividades", "comunidades", "coordinacion", "cuentas", "documentos", "finanzas", "importaciones", "lugares",
        "nucleo", "organizaciones", "personas", "proyectos", "solicitudes", "territorio"]


def _formularios():
    for app in APPS:
        for modulo in ("forms", "forms_admin", "formularios"):
            try:
                m = importlib.import_module(f"apps.{app}.{modulo}")
            except ImportError:
                continue
            for _, clase in inspect.getmembers(m, inspect.isclass):
                if issubclass(clase, forms.BaseForm) and clase.__module__ == m.__name__:
                    yield clase


def test_ninguna_etiqueta_ni_ayuda_muestra_codigos_internos():
    revisados, malos = 0, []
    for clase in _formularios():
        try:
            form = clase()
        except TypeError:  # formularios que exigen argumentos propios (p. ej. la actividad): se revisa su declaración
            campos = getattr(clase, "base_fields", {})
        else:
            campos = form.fields
        revisados += 1
        for nombre, campo in campos.items():
            for texto in (str(campo.label or ""), str(campo.help_text or "")):
                if CODIGO_INTERNO.search(texto):
                    malos.append(f"{clase.__module__}.{clase.__name__}.{nombre}: {texto}")
    assert revisados > 40, "La prueba debe recorrer los formularios del proyecto"
    assert not malos, "Etiquetas o ayudas con códigos internos:\n" + "\n".join(malos)


def test_organizacion_explica_los_datos_legales(cg):
    html = cg.get("/organizaciones/nueva").content.decode()
    assert "Datos legales" in html and "<details" in html
    assert "Qué tipo de entidad es ante la ley" in html
    assert 'name="naturaleza"' in html and 'name="domicilio_legal"' in html

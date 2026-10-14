"""Campo de formulario para el RUT chileno: acepta con o sin puntos, revisa el dígito verificador
y lo entrega separado en número y dígito. Es opcional: hay personas sin RUT."""
from django import forms

from .utilidades import separar_rut


class CampoRut(forms.CharField):
    """Campo de texto que valida RUT chileno (módulo 11) y entrega (numero, dv)."""

    def __init__(self, **kw):
        kw.setdefault("required", False)
        kw.setdefault("max_length", 15)
        kw.setdefault("help_text", "Opcional. Ej.: 12.345.678-5")
        super().__init__(**kw)

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return None
        try:
            return separar_rut(value)
        except Exception as e:  # ValidationError
            raise forms.ValidationError(getattr(e, "messages", [str(e)])[0])

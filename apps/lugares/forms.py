"""Formulario de lugar: nombre, tipo, capacidad, condiciones y organización dueña (la dirección va aparte)."""
from django import forms

from apps.nucleo.formularios import BootstrapMixin
from apps.nucleo.models import TipoLugar
from apps.organizaciones.models import Organizacion

from .models import Lugar


class LugarForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Lugar
        fields = ["nombre", "tipo", "capacidad", "condiciones"]
        labels = {"nombre": "Nombre del lugar", "tipo": "Tipo de lugar", "capacidad": "Capacidad (personas)",
                  "organizacion_propietaria": "¿De quién es el lugar?"}
        help_texts = {
            "nombre": "Ej.: Sede vecinal Villa Los Aromos.",
            "capacidad": "Cuántas personas caben como máximo. Ej.: 40.",
            "condiciones": "Accesibilidad, equipamiento, restricciones u horarios. Ej.: acceso con rampa; tiene proyector; cierra a las 21:00.",
            "organizacion_propietaria": "Opcional. Ej.: la junta de vecinos dueña de la sede.",
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["tipo"].queryset = TipoLugar.objects.filter(activo=True)

    def clean_capacidad(self):
        c = self.cleaned_data.get("capacidad")
        if c is not None and c < 1:
            raise forms.ValidationError("La capacidad debe ser al menos 1.")
        return c

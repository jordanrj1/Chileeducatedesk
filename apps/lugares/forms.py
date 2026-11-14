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


class LugarRapidoForm(BootstrapMixin, forms.Form):
    """F27: ventana «+ Crear lugar» de los buscadores: nombre, tipo y comuna; el resto se completa en su ficha."""

    nombre = forms.CharField(max_length=200, label="Nombre del lugar", help_text="Ej.: Sede vecinal Villa Los Aromos.")
    tipo = forms.ModelChoiceField(TipoLugar.objects.filter(activo=True), label="Tipo de lugar")
    comuna = forms.ModelChoiceField(None, label="Comuna")
    capacidad = forms.IntegerField(min_value=1, required=False, label="Capacidad (personas)", help_text="Opcional. Ej.: 40.")

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.territorio.models import Comuna

        self.fields["comuna"].queryset = Comuna.objects.order_by("nombre")

    def clean_nombre(self):
        return self.cleaned_data["nombre"].strip()

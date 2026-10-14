"""Formulario de lugar: nombre, tipo, capacidad, condiciones y organización dueña (la dirección va aparte)."""
from django import forms

from apps.nucleo.formularios import BootstrapMixin
from apps.nucleo.models import TipoLugar
from apps.organizaciones.models import Organizacion

from .models import Lugar


class LugarForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Lugar
        fields = ["nombre", "tipo", "capacidad", "condiciones", "organizacion_propietaria"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["tipo"].queryset = TipoLugar.objects.filter(activo=True)
        self.fields["organizacion_propietaria"].queryset = Organizacion.objects.filter(activo=True)

    def clean_capacidad(self):
        c = self.cleaned_data.get("capacidad")
        if c is not None and c < 1:
            raise forms.ValidationError("La capacidad debe ser al menos 1.")
        return c

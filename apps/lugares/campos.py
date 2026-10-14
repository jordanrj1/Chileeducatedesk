"""Campo para elegir un lugar que muestra su comuna y capacidad,
para distinguir lugares con el mismo nombre."""
from django import forms

from .models import Lugar


class LugarChoiceField(forms.ModelChoiceField):
    """Muestra la comuna y la capacidad: distingue lugares con el mismo nombre (LU-E11)."""

    def __init__(self, queryset=None, **kw):
        super().__init__(queryset if queryset is not None else Lugar.objects.filter(activo=True).select_related("direccion__comuna"), **kw)

    def label_from_instance(self, l):
        return f"{l.nombre} — {l.direccion.comuna}" + (f" (capacidad {l.capacidad})" if l.capacidad else " (capacidad sin registrar)")

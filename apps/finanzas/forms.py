"""Formularios de finanzas (2.ª fase, oculta): ítems de presupuesto de un proyecto y movimientos de dinero."""
from django import forms
from django.urls import reverse_lazy

from apps.documentos.models import Documento
from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona
from apps.proyectos.models import Proyecto

from .models import ItemPresupuesto, Movimiento


class ItemForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ItemPresupuesto
        fields = ["categoria", "concepto", "monto_estimado", "vigente"]


class MovimientoForm(BootstrapMixin, forms.ModelForm):
    persona = SelectorField(Persona.objects.filter(activo=True), reverse_lazy("personas:opciones"), required=False)
    organizacion = SelectorField(Organizacion.objects.filter(activo=True), reverse_lazy("organizaciones:opciones"), required=False, label="Organización")

    class Meta:
        model = Movimiento
        fields = ["proyecto", "tipo", "monto", "fecha", "persona", "organizacion", "concepto", "documento"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["proyecto"].queryset = Proyecto.objects.all()
        self.fields["documento"].queryset = Documento.objects.filter(activo=True)
        self.fields["documento"].help_text = "Respaldo documental. Los documentos financieros deben subirse como restringidos."

    def clean_monto(self):
        m = self.cleaned_data["monto"]
        if m <= 0:
            raise forms.ValidationError("El monto debe ser mayor que cero.")
        return m

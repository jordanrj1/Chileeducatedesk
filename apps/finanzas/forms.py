"""Formularios de finanzas (2.ª fase, oculta): ítems de presupuesto de un proyecto y movimientos de dinero."""
from django import forms

from apps.documentos.models import Documento
from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.organizaciones.selector import ORGANIZACIONES
from apps.personas.selector import PERSONAS
from apps.proyectos.models import Proyecto

from .models import ItemPresupuesto, Movimiento


class ItemForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ItemPresupuesto
        fields = ["categoria", "concepto", "monto_estimado", "vigente"]
        labels = {"categoria": "Categoría"}
        help_texts = {"concepto": "Ej.: materiales para el taller de huertos.", "monto_estimado": "En pesos, sin puntos. Ej.: 150000."}


class MovimientoForm(BootstrapMixin, forms.ModelForm):
    persona = SelectorField(PERSONAS, required=False)
    organizacion = SelectorField(ORGANIZACIONES, required=False, label="Organización")

    class Meta:
        model = Movimiento
        fields = ["proyecto", "tipo", "monto", "fecha", "persona", "organizacion", "concepto", "documento"]
        help_texts = {"monto": "En pesos, sin puntos. Ej.: 45000.", "concepto": "Ej.: compra de semillas y tierra de hoja."}

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

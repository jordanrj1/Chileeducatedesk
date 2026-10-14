"""Formulario de solicitud u oportunidad: origen, canal, fecha, motivo y contacto (que puede quedar «por identificar»)."""
from django import forms

from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import Canal
from apps.organizaciones.selector import ORGANIZACIONES
from apps.personas.selector import PERSONAS

from .models import Solicitud


class SolicitudForm(BootstrapMixin, forms.ModelForm):
    persona = SelectorField(PERSONAS, required=False, label="Persona de contacto")
    organizacion = SelectorField(ORGANIZACIONES, required=False, label="Organización")

    class Meta:
        model = Solicitud
        fields = ["origen", "canal", "fecha", "persona", "organizacion", "motivo", "descripcion", "observaciones"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["canal"].queryset = Canal.objects.filter(activo=True)

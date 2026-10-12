from django import forms
from django.urls import reverse_lazy

from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import Canal
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona

from .models import Solicitud


class SolicitudForm(BootstrapMixin, forms.ModelForm):
    persona = SelectorField(Persona.objects.filter(activo=True), reverse_lazy("personas:opciones"), required=False, label="Persona de contacto")
    organizacion = SelectorField(Organizacion.objects.filter(activo=True), reverse_lazy("organizaciones:opciones"), required=False, label="Organización")

    class Meta:
        model = Solicitud
        fields = ["origen", "canal", "fecha", "persona", "organizacion", "motivo", "descripcion", "observaciones"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["canal"].queryset = Canal.objects.filter(activo=True)

from django import forms
from django.urls import reverse_lazy

from apps.actividades.models import Actividad
from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import TipoDocumento
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona
from apps.proyectos.models import Proyecto

from .models import Documento, OrigenDato


class DocumentoForm(BootstrapMixin, forms.ModelForm):
    actividad = SelectorField(Actividad.objects.all(), reverse_lazy("actividades:opciones"), required=False)
    persona = SelectorField(Persona.objects.filter(activo=True), reverse_lazy("personas:opciones"), required=False)
    organizacion = SelectorField(Organizacion.objects.filter(activo=True), reverse_lazy("organizaciones:opciones"), required=False, label="Organización")
    proyecto = forms.ModelChoiceField(Proyecto.objects.all(), required=False)

    class Meta:
        model = Documento
        fields = ["nombre", "archivo", "tipo", "fecha", "descripcion", "actividad", "proyecto", "persona", "organizacion", "restringido", "folio", "emisor", "fecha_emision"]

    def __init__(self, *a, puede_restringir=True, **kw):
        super().__init__(*a, **kw)
        self.fields["tipo"].queryset = TipoDocumento.objects.filter(activo=True)
        if self.instance.pk:
            self.fields["archivo"].required = False  # al editar, el archivo se conserva si no se sube otro
        if not puede_restringir:
            del self.fields["restringido"]

    def clean(self):
        d = super().clean()
        if not any(d.get(n) for n in ("actividad", "proyecto", "persona", "organizacion")):
            raise forms.ValidationError("Asocia el documento a una actividad, proyecto, persona u organización.")
        return d


class OrigenForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = OrigenDato
        fields = ["fuente", "documento", "detalle", "fecha", "estado_verificacion"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["documento"].queryset = Documento.objects.filter(restringido=False, activo=True)
        self.fields["documento"].required = False

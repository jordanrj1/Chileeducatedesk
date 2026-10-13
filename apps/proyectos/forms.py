from django import forms
from django.urls import reverse_lazy

from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import RolParticipacion, TipoIntervencion
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona

from .models import Postulacion, Proyecto, ProyectoComunidad, ProyectoOrganizacion, ProyectoPersona


def _persona(**kw):
    return SelectorField(Persona.objects.filter(activo=True), reverse_lazy("personas:opciones"), **kw)


class ProyectoForm(BootstrapMixin, forms.ModelForm):
    responsable = _persona(required=False)
    secciones = [
        ("Identificación", "", ["nombre", "estado", "area_tematica", "responsable", "fecha_inicio", "fecha_termino"]),
        ("Propósito", "Qué busca el proyecto y para quién. Las comunidades destinatarias se agregan en su ficha.",
         ["descripcion", "objetivo_general", "objetivos_especificos", "diagnostico", "poblacion_objetivo", "zona"]),
    ]

    class Meta:
        model = Proyecto
        fields = [
            "nombre", "estado", "area_tematica", "descripcion", "objetivo_general", "objetivos_especificos", "diagnostico", "poblacion_objetivo",
            "zona", "fecha_inicio", "fecha_termino", "responsable",
        ]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.nucleo.models import AreaTematica

        self.fields["area_tematica"].queryset = AreaTematica.objects.filter(activo=True)


class ProyectoComunidadForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ProyectoComunidad
        fields = ["comunidad", "observaciones", "vigente"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.comunidades.models import Comunidad

        self.fields["comunidad"].queryset = Comunidad.objects.filter(activo=True).select_related("comuna")

    def clean_comunidad(self):
        c = self.cleaned_data["comunidad"]
        if ProyectoComunidad.objects.filter(proyecto_id=self.instance.proyecto_id, comunidad=c).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa comunidad ya está entre las destinatarias del proyecto.")
        return c

    def validate_unique(self):
        pass


class _PersonaProyectoForm(BootstrapMixin, forms.ModelForm):
    tipo_fijo = "equipo"
    persona = _persona()

    class Meta:
        model = ProyectoPersona
        fields = ["persona", "rol", "es_responsable", "desde", "hasta", "vigente"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        if "rol" in self.fields:
            self.fields["rol"].queryset = RolParticipacion.objects.filter(activo=True)
            self.fields["rol"].required = False
        self.instance.tipo = self.tipo_fijo

    def clean(self):
        d = super().clean()
        if d.get("persona") and ProyectoPersona.objects.filter(proyecto_id=self.proyecto_id(), persona=d["persona"], tipo=self.tipo_fijo).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa persona ya está en esta lista del proyecto.")
        return d

    def proyecto_id(self):
        return self.instance.proyecto_id or self.initial.get("_proyecto")

    def validate_unique(self):
        pass


class EquipoForm(_PersonaProyectoForm):
    tipo_fijo = "equipo"


class BeneficiarioForm(_PersonaProyectoForm):
    tipo_fijo = "beneficiario"

    class Meta(_PersonaProyectoForm.Meta):
        fields = ["persona", "desde", "hasta", "vigente"]


class ProyectoOrganizacionForm(BootstrapMixin, forms.ModelForm):
    organizacion = SelectorField(Organizacion.objects.filter(activo=True), reverse_lazy("organizaciones:opciones"))
    contacto = _persona(required=False, label="Persona de contacto")

    class Meta:
        model = ProyectoOrganizacion
        fields = ["organizacion", "tipo_intervencion", "contacto", "observaciones", "vigente"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["tipo_intervencion"].queryset = TipoIntervencion.objects.filter(activo=True)

    def clean(self):
        d = super().clean()
        # La restricción única trata NULL como distinto; aquí «sin tipo» también cuenta como repetido.
        if d.get("organizacion") and ProyectoOrganizacion.objects.filter(
            proyecto_id=self.instance.proyecto_id, organizacion=d["organizacion"], tipo_intervencion=d.get("tipo_intervencion")
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa organización ya está relacionada con ese tipo de intervención.")
        return d

    def validate_unique(self):
        pass


class PostulacionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Postulacion
        fields = ["fondo", "fecha", "estado", "resultado", "observaciones", "vigente"]

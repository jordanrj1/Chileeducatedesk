"""Formularios de proyecto: datos del proyecto, su equipo, organizaciones, comunidades, beneficiarios y postulaciones."""
from django import forms

from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import RolParticipacion, TipoIntervencion
from apps.organizaciones.selector import ORGANIZACIONES
from apps.personas.selector import AYUDA_RESPONSABLE_EQUIPO, PERSONAS
from apps.territorio.destinos import DestinosMixin

from .models import Postulacion, Proyecto, ProyectoComunidad, ProyectoOrganizacion, ProyectoPersona


def _persona(**kw):
    return SelectorField(PERSONAS, **kw)


class ProyectoForm(DestinosMixin, BootstrapMixin, forms.ModelForm):
    """Crear y editar el proyecto. «¿Dónde?» guarda una o más comunas o sectores (apps/territorio/destinos.py); la zona
    escrita a mano antes solo aparece si tiene texto, para revisarla y borrarla."""

    responsable = _persona(required=False, filtros={"equipo_primero": 1}, help_text=AYUDA_RESPONSABLE_EQUIPO)
    secciones = [
        ("Identificación", "", ["nombre", "estado", "area_tematica", "responsable", "fecha_inicio", "fecha_termino"]),
        ("¿Dónde se desarrolla o a quién va dirigido?", "Las comunas o sectores donde se desarrolla; puedes agregar varios. No es obligatorio.",
         ["donde", "zona"]),
        ("Propósito", "Qué busca el proyecto y para quién. Las comunidades destinatarias se agregan en su ficha.",
         ["descripcion", "objetivo_general", "objetivos_especificos", "diagnostico", "poblacion_objetivo"]),
    ]

    class Meta:
        model = Proyecto
        fields = [
            "nombre", "estado", "area_tematica", "descripcion", "objetivo_general", "objetivos_especificos", "diagnostico", "poblacion_objetivo",
            "zona", "fecha_inicio", "fecha_termino", "responsable",
        ]
        labels = {"nombre": "Nombre del proyecto", "estado": "Etapa del proyecto", "area_tematica": "Tema principal",
                  "descripcion": "Descripción", "diagnostico": "¿Qué problema atiende?", "poblacion_objetivo": "¿A quién va dirigido?",
                  "fecha_inicio": "Fecha de inicio", "fecha_termino": "Fecha de término", "zona": "Zona (texto anterior)"}
        help_texts = {
            "nombre": "Ej.: Alfabetización digital 2026.",
            "estado": "Ej.: Postulado, mientras se espera el resultado del fondo.",
            "area_tematica": "Sirve para buscar e informar por línea de trabajo. Ej.: Educación financiera.",
            "descripcion": "En pocas líneas, de qué se trata.",
            "objetivo_general": "El gran propósito, en una frase. Ej.: reducir la brecha digital de las personas mayores de la comuna.",
            "objetivos_especificos": "Uno por línea. Ej.: realizar 8 talleres; formar 10 monitores.",
            "diagnostico": "La situación que motivó el proyecto, con datos si los hay.",
            "poblacion_objetivo": "Ej.: personas mayores socias de las juntas de vecinos de la comuna.",
            "zona": "Se escribió antes de poder elegir comunas y sectores. Elige arriba la comuna o el sector y luego borra este texto.",
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.nucleo.models import AreaTematica

        self.fields["area_tematica"].queryset = AreaTematica.objects.filter(activo=True)
        if not self.instance.zona:  # el texto anterior solo se muestra si hay algo que revisar
            self.fields.pop("zona", None)


class ProyectoComunidadForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ProyectoComunidad
        fields = ["comunidad", "observaciones", "vigente"]
        help_texts = {"comunidad": "Si no está, créala antes en Comunidades."}

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
        labels = {"rol": "Rol en el proyecto", "es_responsable": "Es responsable del proyecto"}
        help_texts = {"rol": "Ej.: Coordinador.", "hasta": "Solo si dejó el proyecto: el registro se conserva."}

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

    def save(self, commit=True):
        obj = super().save(commit)
        if commit:  # F26 P2: marcarlo responsable aquí cambia también el responsable del proyecto (una sola verdad)
            from .servicios import responsable_desde_equipo

            responsable_desde_equipo(obj)
        return obj


class BeneficiarioForm(_PersonaProyectoForm):
    tipo_fijo = "beneficiario"

    class Meta(_PersonaProyectoForm.Meta):
        fields = ["persona", "desde", "hasta", "vigente"]


class ProyectoOrganizacionForm(BootstrapMixin, forms.ModelForm):
    organizacion = SelectorField(ORGANIZACIONES, label="Organización")
    contacto = _persona(required=False, label="Persona de contacto", help_text="Con quién se coordina en esa organización, si se sabe.")

    class Meta:
        model = ProyectoOrganizacion
        fields = ["organizacion", "tipo_intervencion", "contacto", "observaciones", "vigente"]
        labels = {"tipo_intervencion": "¿Qué aporta esta organización?"}
        help_texts = {"tipo_intervencion": "Ej.: Financia; Facilita espacio (presta la sede)."}

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

    def save(self, commit=True):
        obj = super().save(commit)
        if commit:  # F26 P2: la persona de contacto queda vinculada a la organización
            from apps.personas.vinculos import vincular_contacto

            vincular_contacto(obj.contacto, obj.organizacion)
        return obj


class PostulacionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Postulacion
        fields = ["fondo", "fecha", "estado", "resultado", "observaciones", "vigente"]
        help_texts = {"fondo": "Ej.: Fondo Social Presidente de la República 2026.", "resultado": "Ej.: adjudicado por $3.000.000."}

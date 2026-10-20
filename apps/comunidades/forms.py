"""Formularios de comunidades: crear o editar una comunidad (con la ubicación en cascada: región → comuna → sector)
y agregar integrantes, desde la comunidad o desde la ficha de la persona."""
from django import forms

from apps.nucleo.formularios import BootstrapMixin, SelectorField, fijar_valores_selectores, preparar_tramos
from apps.nucleo.models import AreaTematica
from apps.organizaciones.selector import ORGANIZACIONES
from apps.personas.selector import PERSONAS
from apps.territorio.ubicacion import UbicacionMixin

from .models import Comunidad, ComunidadMiembro


def selector_persona(**kw):
    return SelectorField(PERSONAS, **kw)


class ComunidadForm(UbicacionMixin, BootstrapMixin, forms.ModelForm):
    ubicacion_modo = "comunidad"  # la comuna es obligatoria; el sector, opcional
    organizacion = SelectorField(ORGANIZACIONES, required=False,
                                 label="Organización que la representa", help_text="Ej.: la junta de vecinos o el establecimiento.")
    referente = selector_persona(required=False, label="Referente o dirigente principal",
                                 help_text="Persona con quien se coordina. Ej.: la presidenta de la junta de vecinos.")
    secciones = [
        ("Identificación", "", ["nombre", "tipo", "descripcion"]),
        ("Territorio", "Dónde vive o se reúne esta comunidad.", ["ubicacion", "organizacion", "referente"]),
        ("Caracterización", "Lo levantado en terreno: sirve para diseñar actividades pertinentes y medir el alcance.",
         ["poblacion_estimada", "tramos_etarios", "rango_etario", "areas_interes", "diagnostico"]),
    ]

    class Meta:
        model = Comunidad
        fields = ["nombre", "tipo", "descripcion", "comuna", "sector", "organizacion", "referente", "poblacion_estimada", "tramos_etarios", "rango_etario",
                  "areas_interes", "diagnostico"]
        widgets = {"areas_interes": forms.CheckboxSelectMultiple, "descripcion": forms.Textarea(attrs={"rows": 2})}
        labels = {"nombre": "Nombre de la comunidad", "tipo": "Tipo de comunidad", "descripcion": "¿Quiénes la forman?",
                  "poblacion_estimada": "¿Cuántas personas son, aprox.?", "tramos_etarios": "Edades principales",
                  "areas_interes": "Temas que le interesan", "diagnostico": "Diagnóstico y necesidades"}
        help_texts = {
            "nombre": "Ej.: Vecinos de la Villa Los Aromos.",
            "tipo": "Ej.: Vecinal o barrial, para los vecinos de una villa.",
            "descripcion": "Ej.: familias de la Etapa 3 que se organizan en torno a la sede vecinal.",
            "poblacion_estimada": "Personas, no familias. Ej.: 120.",
            "tramos_etarios": "Las edades que más se ven en esta comunidad. Marca uno o más. Ej.: Personas adultas y Personas mayores.",
            "areas_interes": "Sirven para proponerle actividades. Ej.: Salud y bienestar.",
            "diagnostico": "Qué necesita, según lo levantado en terreno. Ej.: no hay plaza; muchas personas mayores viven solas.",
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        # la comuna y el sector los arma UbicacionMixin: solo sectores activos de la comuna elegida; al editar se conserva
        # el que la comunidad ya tenía aunque esté desactivado
        self.fields["areas_interes"].queryset = AreaTematica.objects.filter(activo=True)
        preparar_tramos(self, "Rango etario predominante (texto anterior)")
        fijar_valores_selectores(self)


class IntegranteForm(BootstrapMixin, forms.ModelForm):
    persona = selector_persona(label="Persona")

    class Meta:
        model = ComunidadMiembro
        fields = ["persona", "rol", "desde", "hasta", "observaciones", "vigente"]
        labels = {"rol": "Rol en la comunidad"}
        help_texts = {"rol": "Ej.: Dirigente.", "hasta": "Solo si dejó de participar: el registro se conserva."}

    def clean_persona(self):
        p = self.cleaned_data["persona"]
        if ComunidadMiembro.objects.filter(comunidad_id=self.instance.comunidad_id, persona=p).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa persona ya integra la comunidad.")
        return p

    def validate_unique(self):
        pass


class MembresiaDesdePersonaForm(BootstrapMixin, forms.ModelForm):
    """Agregar a la persona a una comunidad desde su ficha."""

    class Meta:
        model = ComunidadMiembro
        fields = ["comunidad", "rol", "desde", "hasta", "observaciones", "vigente"]
        labels = {"rol": "Rol en la comunidad"}
        help_texts = {"rol": "Ej.: Dirigente.", "hasta": "Solo si dejó de participar: el registro se conserva."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["comunidad"].queryset = Comunidad.objects.filter(activo=True).select_related("comuna")

    def clean_comunidad(self):
        c = self.cleaned_data["comunidad"]
        if ComunidadMiembro.objects.filter(persona_id=self.instance.persona_id, comunidad=c).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("La persona ya integra esa comunidad.")
        return c

    def validate_unique(self):
        pass

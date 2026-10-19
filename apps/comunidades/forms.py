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
                                 label="Organización que la representa", help_text="Por ejemplo, la junta de vecinos o el establecimiento.")
    referente = selector_persona(required=False, label="Referente o dirigente principal")
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
        labels = {"tramos_etarios": "Edades principales"}
        help_texts = {"tramos_etarios": "Las edades que más se ven en esta comunidad. Marca uno o más. Ej.: Personas adultas y Personas mayores."}

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

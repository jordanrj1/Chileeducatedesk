"""Formulario de solicitud u oportunidad: origen, canal, fecha, motivo y contacto (que puede quedar «por identificar»)."""
from django import forms

from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import Canal
from apps.organizaciones.selector import ORGANIZACIONES
from apps.personas.selector import PERSONAS

from .models import Solicitud


class SolicitudForm(BootstrapMixin, forms.ModelForm):
    persona = SelectorField(PERSONAS, required=False, label="Persona de contacto", help_text="Quién la pidió o avisó. Si aún no se sabe, déjalo vacío.")
    organizacion = SelectorField(ORGANIZACIONES, required=False, label="Organización", help_text="Ej.: el liceo que pide la charla.")

    class Meta:
        model = Solicitud
        fields = ["origen", "canal", "fecha", "persona", "organizacion", "motivo", "descripcion", "observaciones"]
        labels = {"origen": "¿Cómo surgió?", "canal": "¿Por dónde llegó?", "fecha": "Fecha en que llegó", "motivo": "¿Qué se pide?"}
        help_texts = {
            "origen": "Solicitud externa: alguien pidió algo. Búsqueda activa: la Fundación detectó la oportunidad.",
            "canal": "Ej.: Correo electrónico.",
            "motivo": "Qué se necesita o qué oportunidad apareció, en una frase. Ej.: un liceo pide una charla sobre reciclaje.",
            "descripcion": "Los detalles que vengan en el mensaje: fechas posibles, cantidad de personas, lugar.",
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["canal"].queryset = Canal.objects.filter(activo=True)

    def save(self, commit=True):
        obj = super().save(commit)
        if commit:  # F26 P2: la persona de contacto queda vinculada a la organización
            from apps.personas.vinculos import vincular_contacto

            vincular_contacto(obj.persona, obj.organizacion)
        return obj

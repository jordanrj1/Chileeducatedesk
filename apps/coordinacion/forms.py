"""Formularios de coordinación: interacción (con quién, canal, resultado y próxima acción),
invitación, solicitud de apoyo, y los de 2.ª fase (reunión, asistentes, tarea y responsables)."""
from django import forms

from apps.actividades.selector import ACTIVIDADES
from apps.lugares.models import Lugar
from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import Canal, Modalidad, RolParticipacion, TipoIntervencion
from apps.organizaciones.selector import ORGANIZACIONES
from apps.personas.selector import AYUDA_RESPONSABLE, PERSONAS
from apps.proyectos.models import Proyecto

from .models import Colaboracion, Interaccion, Invitacion, Reunion, ReunionAsistente, Tarea, TareaResponsable


def _p(**kw):
    return SelectorField(PERSONAS, **kw)


def _o(**kw):
    return SelectorField(ORGANIZACIONES, **kw)


def _a(**kw):
    return SelectorField(ACTIVIDADES, **kw)


class InteraccionForm(BootstrapMixin, forms.ModelForm):
    persona = _p(required=False, label="Persona", help_text="Con quién se habló. Puede ser una persona, una organización o ambas.")
    organizacion = _o(required=False, label="Organización")
    fecha = forms.DateTimeField(label="Fecha y hora", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"), input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"])

    class Meta:
        model = Interaccion
        fields = ["fecha", "canal", "persona", "organizacion", "motivo", "resultado", "proxima_accion", "proxima_fecha", "accion_cumplida", "solicitud", "actividad"]
        widgets = {"solicitud": forms.HiddenInput(), "actividad": forms.HiddenInput()}
        labels = {"canal": "¿Por qué medio?", "motivo": "¿Para qué fue el contacto?", "resultado": "¿Qué se conversó o acordó?",
                  "proxima_accion": "Próximo paso", "proxima_fecha": "¿Para cuándo?", "accion_cumplida": "El próximo paso ya se hizo"}
        help_texts = {
            "canal": "Ej.: Llamada telefónica.",
            "motivo": "Ej.: confirmar la fecha del taller.",
            "resultado": "Ej.: confirma la sede para el sábado; pide 30 sillas.",
            "proxima_accion": "Lo que queda pendiente. Ej.: enviar la carta de invitación.",
            "proxima_fecha": "Aparece en el Inicio cuando se acerque.",
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["canal"].queryset = Canal.objects.filter(activo=True)
        self.fields["solicitud"].required = self.fields["actividad"].required = False


class ReunionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Reunion
        fields = ["titulo", "fecha", "hora_inicio", "hora_fin", "lugar", "modalidad", "objetivo", "temas", "acuerdos", "actividad", "proyecto"]
        widgets = {"actividad": forms.HiddenInput(), "proyecto": forms.HiddenInput()}
        labels = {"titulo": "Título", "hora_inicio": "Hora de inicio", "hora_fin": "Hora de término"}
        help_texts = {"titulo": "Ej.: Coordinación con la junta de vecinos.", "objetivo": "Para qué se reúnen. Ej.: definir la fecha de la feria.",
                      "acuerdos": "Los compromisos con responsable se agregan después, como tareas de la reunión."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.lugares.campos import LugarChoiceField

        self.fields["lugar"] = LugarChoiceField(required=False)
        self.fields["lugar"].widget.attrs["class"] = "form-select"
        self.fields["modalidad"].queryset = Modalidad.objects.filter(activo=True)
        self.fields["actividad"].required = self.fields["proyecto"].required = False


class AsistenteForm(BootstrapMixin, forms.ModelForm):
    persona = _p()

    class Meta:
        model = ReunionAsistente
        fields = ["persona", "asistio", "observaciones", "vigente"]
        widgets = {"asistio": forms.NullBooleanSelect()}
        labels = {"asistio": "¿Asistió?"}

    def clean(self):
        d = super().clean()
        if d.get("persona") and ReunionAsistente.objects.filter(reunion=self.instance.reunion_id, persona=d["persona"]).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa persona ya figura como asistente.")
        return d

    def validate_unique(self):
        pass


class TareaForm(BootstrapMixin, forms.ModelForm):
    responsable = _p(required=False, filtros={"equipo_primero": 1}, label="Responsable", help_text="Obligatorio para los compromisos de una reunión. " + AYUDA_RESPONSABLE)

    class Meta:
        model = Tarea
        fields = ["titulo", "descripcion", "estado", "fecha_limite", "responsable", "reunion", "actividad", "proyecto"]
        widgets = {"reunion": forms.HiddenInput(), "actividad": forms.HiddenInput(), "proyecto": forms.HiddenInput()}
        labels = {"titulo": "¿Qué hay que hacer?"}
        help_texts = {"titulo": "Ej.: reservar la sede para el 15 de noviembre.", "fecha_limite": "El Inicio avisa cuando se acerque."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for n in ("reunion", "actividad", "proyecto"):
            self.fields[n].required = False
        if self.instance.pk:
            del self.fields["responsable"]

    def clean(self):
        d = super().clean()
        if d.get("reunion") and "responsable" in self.fields and not d.get("responsable"):
            self.add_error("responsable", "Un compromiso de reunión necesita un responsable.")
        return d


class ResponsableForm(BootstrapMixin, forms.ModelForm):
    persona = _p()

    class Meta:
        model = TareaResponsable
        fields = ["persona", "vigente"]

    def clean(self):
        d = super().clean()
        if d.get("persona") and TareaResponsable.objects.filter(tarea=self.instance.tarea_id, persona=d["persona"]).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa persona ya es responsable de la tarea.")
        return d

    def validate_unique(self):
        pass


class InvitacionForm(BootstrapMixin, forms.ModelForm):
    persona = _p()
    actividad = _a()

    class Meta:
        model = Invitacion
        fields = ["persona", "actividad", "rol", "fecha", "estado", "respuesta", "fecha_respuesta"]
        labels = {"fecha": "Fecha de la invitación", "fecha_respuesta": "Fecha de la respuesta"}
        help_texts = {"rol": "Ej.: Tallerista.", "respuesta": "Lo que respondió, con sus palabras. Ej.: puede solo los sábados."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["rol"].queryset = RolParticipacion.objects.filter(activo=True)

    def clean(self):
        d = super().clean()
        if d.get("estado") in ("respondio", "aceptada", "rechazada") and not d.get("fecha_respuesta"):
            self.add_error("fecha_respuesta", "Indica la fecha de la respuesta.")
        return d


class ColaboracionForm(BootstrapMixin, forms.ModelForm):
    organizacion = _o()
    actividad = _a()

    class Meta:
        model = Colaboracion
        fields = ["organizacion", "actividad", "tipo_apoyo", "estado", "resultado", "observaciones"]
        labels = {"tipo_apoyo": "¿Qué apoyo se pide?"}
        help_texts = {"tipo_apoyo": "Ej.: Facilita espacio.", "resultado": "Ej.: presta la sede y 30 sillas."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["tipo_apoyo"].queryset = TipoIntervencion.objects.filter(activo=True)

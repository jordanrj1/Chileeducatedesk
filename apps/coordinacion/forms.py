"""Formularios de coordinación: interacción (con quién, canal, resultado y próxima acción),
invitación, solicitud de apoyo, y los de 2.ª fase (reunión, asistentes, tarea y responsables)."""
from django import forms
from django.urls import reverse_lazy

from apps.actividades.models import Actividad
from apps.lugares.models import Lugar
from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import Canal, Modalidad, RolParticipacion, TipoIntervencion
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona
from apps.proyectos.models import Proyecto

from .models import Colaboracion, Interaccion, Invitacion, Reunion, ReunionAsistente, Tarea, TareaResponsable


def _p(**kw):
    return SelectorField(Persona.objects.filter(activo=True), reverse_lazy("personas:opciones"), **kw)


def _o(**kw):
    return SelectorField(Organizacion.objects.filter(activo=True), reverse_lazy("organizaciones:opciones"), **kw)


def _a(**kw):
    return SelectorField(Actividad.objects.all(), reverse_lazy("actividades:opciones"), **kw)


class InteraccionForm(BootstrapMixin, forms.ModelForm):
    persona = _p(required=False)
    organizacion = _o(required=False)
    fecha = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"), input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"])

    class Meta:
        model = Interaccion
        fields = ["fecha", "canal", "persona", "organizacion", "motivo", "resultado", "proxima_accion", "proxima_fecha", "accion_cumplida", "solicitud", "actividad"]
        widgets = {"solicitud": forms.HiddenInput(), "actividad": forms.HiddenInput()}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["canal"].queryset = Canal.objects.filter(activo=True)
        self.fields["solicitud"].required = self.fields["actividad"].required = False


class ReunionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Reunion
        fields = ["titulo", "fecha", "hora_inicio", "hora_fin", "lugar", "modalidad", "objetivo", "temas", "acuerdos", "actividad", "proyecto"]
        widgets = {"actividad": forms.HiddenInput(), "proyecto": forms.HiddenInput()}

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

    def clean(self):
        d = super().clean()
        if d.get("persona") and ReunionAsistente.objects.filter(reunion=self.instance.reunion_id, persona=d["persona"]).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa persona ya figura como asistente.")
        return d

    def validate_unique(self):
        pass


class TareaForm(BootstrapMixin, forms.ModelForm):
    responsable = _p(required=False, label="Responsable", help_text="Obligatorio para los compromisos de una reunión.")

    class Meta:
        model = Tarea
        fields = ["titulo", "descripcion", "estado", "fecha_limite", "responsable", "reunion", "actividad", "proyecto"]
        widgets = {"reunion": forms.HiddenInput(), "actividad": forms.HiddenInput(), "proyecto": forms.HiddenInput()}

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

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["tipo_apoyo"].queryset = TipoIntervencion.objects.filter(activo=True)

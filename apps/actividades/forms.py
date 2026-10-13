from django import forms
from django.urls import reverse_lazy

from apps.lugares.campos import LugarChoiceField
from apps.lugares.models import Lugar
from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import EstadoParticipacion, Modalidad, RolParticipacion, TipoActividad, TipoIntervencion
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona
from apps.proyectos.models import Proyecto
from apps.territorio.models import Comuna, Provincia, Region, Sector

from .models import Actividad, ActividadOrganizacion, ActividadTerritorio, Participacion, SesionActividad


def selector_persona(**kw):
    return SelectorField(Persona.objects.filter(activo=True), reverse_lazy("personas:opciones"), **kw)


class ActividadForm(BootstrapMixin, forms.ModelForm):
    responsable = selector_persona(required=False)
    actividad_padre = SelectorField(Actividad.objects.filter(actividad_padre__isnull=True), reverse_lazy("actividades:opciones"), required=False, label="Actividad padre (jornada)")

    class Meta:
        model = Actividad
        fields = ["nombre", "proyecto", "actividad_padre", "tipo", "objetivo", "descripcion", "modalidad", "responsable", "condiciones"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["proyecto"].queryset = Proyecto.objects.exclude(estado__in=["finalizado", "cancelado"]) | Proyecto.objects.filter(pk=self.instance.proyecto_id or 0)
        self.fields["tipo"].queryset = TipoActividad.objects.filter(activo=True)
        self.fields["modalidad"].queryset = Modalidad.objects.filter(activo=True)

    def clean_actividad_padre(self):
        p = self.cleaned_data.get("actividad_padre")
        if p and self.instance.pk and p.pk == self.instance.pk:
            raise forms.ValidationError("Una actividad no puede ser su propia padre.")
        return p


class ProgramarForm(BootstrapMixin, forms.Form):
    fecha = forms.DateField(widget=forms.DateInput)
    hora_inicio = forms.TimeField(label="Hora de inicio", widget=forms.TimeInput)
    hora_fin = forms.TimeField(label="Hora de término", widget=forms.TimeInput, required=False)
    duracion = forms.IntegerField(label="o duración (minutos)", required=False, min_value=1, max_value=24 * 60, help_text="Si indicas la duración, se calcula la hora de término.")
    lugar = LugarChoiceField(required=False)
    modalidad = forms.ModelChoiceField(Modalidad.objects.filter(activo=True), required=False)
    motivo = forms.CharField(label="Motivo del cambio", max_length=250, required=False, help_text="Obligatorio al reprogramar.")

    def clean(self):
        d = super().clean()
        ini, fin, dur = d.get("hora_inicio"), d.get("hora_fin"), d.get("duracion")
        if ini and dur and not fin:
            minutos = ini.hour * 60 + ini.minute + dur
            if minutos >= 24 * 60:
                self.add_error("duracion", "La actividad no puede terminar al día siguiente.")
            else:
                from datetime import time

                d["hora_fin"] = time(minutos // 60, minutos % 60)
        elif ini and fin and dur:
            if (fin.hour * 60 + fin.minute) - (ini.hour * 60 + ini.minute) != dur:
                self.add_error("duracion", "No coincide con la hora de término; indica solo una de las dos.")
        if ini and d.get("hora_fin") and d["hora_fin"] <= ini:
            self.add_error("hora_fin", "La hora de término debe ser posterior a la de inicio.")
        return d


class SerieForm(BootstrapMixin, forms.Form):
    """Crear una serie de actividades repetidas (AG-07 [P]): cada repetición es una actividad propia dentro de la original."""

    FRECUENCIAS = [(7, "Cada semana"), (14, "Cada dos semanas"), (1, "Cada día"), (28, "Cada cuatro semanas")]
    primera_fecha = forms.DateField(widget=forms.DateInput)
    frecuencia = forms.TypedChoiceField(choices=FRECUENCIAS, coerce=int, initial=7)
    repeticiones = forms.IntegerField(min_value=2, max_value=52, initial=4, help_text="Entre 2 y 52.")
    hora_inicio = forms.TimeField(widget=forms.TimeInput)
    hora_fin = forms.TimeField(widget=forms.TimeInput, required=False)
    lugar = LugarChoiceField(required=False)

    def clean(self):
        d = super().clean()
        if d.get("hora_inicio") and d.get("hora_fin") and d["hora_fin"] <= d["hora_inicio"]:
            self.add_error("hora_fin", "La hora de término debe ser posterior a la de inicio.")
        return d


class EstadoForm(BootstrapMixin, forms.Form):
    estado = forms.ChoiceField(choices=[])
    motivo = forms.CharField(max_length=250, required=False, help_text="Obligatorio para suspender o cancelar.")

    def __init__(self, *a, opciones=(), **kw):
        super().__init__(*a, **kw)
        self.fields["estado"].choices = opciones


class ParticipanteNuevoForm(BootstrapMixin, forms.ModelForm):
    persona = selector_persona()

    class Meta:
        model = Participacion
        fields = ["persona", "rol", "estado", "observaciones"]

    def __init__(self, *a, actividad=None, **kw):
        super().__init__(*a, **kw)
        self.actividad = actividad
        self.fields["rol"].queryset = RolParticipacion.objects.filter(activo=True)
        self.fields["estado"].queryset = EstadoParticipacion.objects.filter(activo=True)
        self.fields["estado"].initial = EstadoParticipacion.objects.filter(codigo="invitado").first()

    def clean(self):
        d = super().clean()
        if d.get("persona") and d.get("rol") and Participacion.objects.filter(actividad=self.actividad, persona=d["persona"], rol=d["rol"]).exists():
            raise forms.ValidationError("Esa persona ya participa en la actividad con ese rol.")
        return d

    def validate_unique(self):
        pass


class ParticipacionEditarForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Participacion
        fields = ["rol", "estado", "observaciones"]

    def clean_rol(self):
        rol = self.cleaned_data["rol"]
        if Participacion.objects.filter(actividad=self.instance.actividad, persona=self.instance.persona, rol=rol).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa persona ya participa con ese rol.")
        return rol

    def validate_unique(self):
        pass


class PersonaRapidaForm(BootstrapMixin, forms.Form):
    nombres = forms.CharField(max_length=150)
    apellido_paterno = forms.CharField(max_length=100, required=False)
    apellido_materno = forms.CharField(max_length=100, required=False)
    correo = forms.EmailField(required=False)
    telefono = forms.CharField(max_length=40, required=False, label="Teléfono")
    rol = forms.ModelChoiceField(RolParticipacion.objects.filter(activo=True))


class ActividadOrganizacionForm(BootstrapMixin, forms.ModelForm):
    organizacion = SelectorField(Organizacion.objects.filter(activo=True), reverse_lazy("organizaciones:opciones"))
    contacto = selector_persona(required=False, label="Persona de contacto")

    class Meta:
        model = ActividadOrganizacion
        fields = ["organizacion", "tipo_intervencion", "contacto", "observaciones", "vigente"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["tipo_intervencion"].queryset = TipoIntervencion.objects.filter(activo=True)

    def clean(self):
        d = super().clean()
        if d.get("organizacion") and ActividadOrganizacion.objects.filter(
            actividad_id=self.instance.actividad_id, organizacion=d["organizacion"], tipo_intervencion=d.get("tipo_intervencion")
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa organización ya está relacionada con ese tipo de intervención.")
        return d

    def validate_unique(self):
        pass


class SesionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = SesionActividad
        fields = ["numero", "nombre", "fecha", "hora_inicio", "hora_fin", "lugar", "observaciones", "vigente"]

    def clean_numero(self):
        n = self.cleaned_data["numero"]
        if SesionActividad.objects.filter(actividad_id=self.instance.actividad_id, numero=n).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe una sesión con ese número.")
        return n

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["lugar"] = LugarChoiceField(required=False)
        self.fields["lugar"].widget.attrs["class"] = "form-select"


class TerritorioForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ActividadTerritorio
        fields = ["region", "provincia", "comuna", "sector", "vigente"]
        help_texts = {"region": "Elige un único nivel: región, provincia, comuna o sector."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["comuna"].queryset = Comuna.objects.select_related("provincia")
        self.fields["sector"].queryset = Sector.objects.select_related("comuna")

    def clean(self):
        d = super().clean()
        elegidos = [n for n in ("region", "provincia", "comuna", "sector") if d.get(n)]
        if len(elegidos) != 1:
            raise forms.ValidationError("Elige exactamente un nivel territorial.")
        return d


class ResultadoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ["observaciones", "incidencias", "resultado", "indicadores", "asistencia_sin_registro"]
        widgets = {f: forms.Textarea(attrs={"rows": 4}) for f in ["observaciones", "incidencias", "resultado", "indicadores"]}

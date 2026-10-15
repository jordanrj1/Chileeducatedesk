"""Formularios de la actividad: crear y editar, programar o reprogramar, crear una serie, cambiar el estado,
agregar participantes (o crearlos en el momento), organizaciones, comunidades, territorios, sesiones y resultado.
Cada formulario valida en el servidor lo mismo que se ve en pantalla."""
from django import forms

from apps.lugares.campos import LugarChoiceField
from apps.lugares.models import Lugar
from apps.nucleo.formularios import BootstrapMixin, SelectorField, fijar_valores_selectores, preparar_tramos
from apps.nucleo.models import AreaTematica, EstadoParticipacion, Modalidad, RolParticipacion, TipoActividad, TipoIntervencion
from apps.organizaciones.selector import ORGANIZACIONES
from apps.personas.models import Persona
from apps.personas.selector import AYUDA_RESPONSABLE, PERSONAS
from apps.proyectos.models import Proyecto
from apps.territorio.models import Comuna, Provincia, Region, Sector

from .selector import ACTIVIDADES
from .models import Actividad, ActividadComunidad, ActividadOrganizacion, ActividadTerritorio, Participacion, SesionActividad, SesionFacilitador


def selector_persona(**kw):
    return SelectorField(PERSONAS, **kw)


class ActividadForm(BootstrapMixin, forms.ModelForm):
    responsable = SelectorField(PERSONAS, filtros={"equipo_primero": 1}, required=False, help_text=AYUDA_RESPONSABLE)
    actividad_padre = SelectorField(ACTIVIDADES, filtros={"raiz": 1}, required=False, label="Actividad padre (jornada)")

    secciones = [
        ("Qué es", "Solo el nombre es obligatorio; la fecha y el lugar se definen al programar.", ["nombre", "tipo", "area_tematica", "proyecto", "actividad_padre", "modalidad", "responsable"]),
        ("Para qué y para quién", "A quién va dirigida y qué se espera lograr. Las comunidades destinatarias se agregan en la pestaña «Público y comunidades».",
         ["objetivo", "publico_objetivo", "tramos_etarios", "rango_etario", "beneficiarios_estimados"]),
        ("Detalle", "", ["descripcion", "condiciones"]),
    ]

    class Meta:
        model = Actividad
        fields = ["nombre", "proyecto", "actividad_padre", "tipo", "area_tematica", "objetivo", "publico_objetivo", "tramos_etarios", "rango_etario",
                  "beneficiarios_estimados", "descripcion", "modalidad", "responsable", "condiciones"]
        labels = {"tramos_etarios": "Tramos de edad"}
        help_texts = {"tramos_etarios": "A qué edades va dirigida. Marca uno o más. Ej.: Personas adultas y Personas mayores."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["proyecto"].queryset = Proyecto.objects.exclude(estado__in=["finalizado", "cancelado"]) | Proyecto.objects.filter(pk=self.instance.proyecto_id or 0)
        self.fields["tipo"].queryset = TipoActividad.objects.filter(activo=True)
        self.fields["modalidad"].queryset = Modalidad.objects.filter(activo=True)
        self.fields["area_tematica"].queryset = AreaTematica.objects.filter(activo=True)
        preparar_tramos(self)
        if self.instance.pk:  # una actividad no se ofrece como su propia actividad padre
            self.fields["actividad_padre"].con_filtros(excluir=self.instance.pk)
            fijar_valores_selectores(self)

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
    enlace = forms.URLField(label="Enlace (si es virtual)", required=False, assume_scheme="https")
    motivo = forms.CharField(label="Motivo del cambio", max_length=250, required=False, help_text="Obligatorio al reprogramar o reanudar.")

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
    institucion = SelectorField(ORGANIZACIONES, filtros={"tipo": "institucion_educativa"}, required=False, label="Institución de procedencia",
                                help_text="Universidad, instituto o liceo del que viene (estudiantes). Se completa sola con la formación vigente.")
    secciones = [
        ("Participación", "", ["rol", "estado", "observaciones"]),
        ("Procedencia y horas", "Para los informes: de qué institución y comunidad viene, y cuántas horas aportó o recibió.", ["institucion", "comunidad", "horas"]),
    ]

    class Meta:
        model = Participacion
        fields = ["rol", "estado", "observaciones", "institucion", "comunidad", "horas"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.comunidades.models import Comunidad

        self.fields["comunidad"].queryset = Comunidad.objects.filter(activo=True).select_related("comuna")
        from apps.nucleo.formularios import fijar_valores_selectores

        fijar_valores_selectores(self)

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
    organizacion = SelectorField(ORGANIZACIONES)
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


class ActividadComunidadForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ActividadComunidad
        fields = ["comunidad", "beneficiarios_estimados", "observaciones", "vigente"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.comunidades.models import Comunidad

        self.fields["comunidad"].queryset = Comunidad.objects.filter(activo=True).select_related("comuna", "sector")
        self.fields["comunidad"].label_from_instance = lambda c: f"{c.nombre} · {c.territorio}"

    def clean_comunidad(self):
        c = self.cleaned_data["comunidad"]
        if ActividadComunidad.objects.filter(actividad_id=self.instance.actividad_id, comunidad=c).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa comunidad ya está entre las destinatarias.")
        return c

    def validate_unique(self):
        pass


class SesionForm(BootstrapMixin, forms.ModelForm):
    """Bitácora de la sesión (F22): datos, facilitadores, minuta y asistentes sin registro individual."""

    facilitadores = forms.ModelMultipleChoiceField(Persona.objects.none(), required=False, widget=forms.CheckboxSelectMultiple,
                                                   help_text="Equipo de la actividad y responsable. Si falta alguien, agrégalo antes como participante del equipo.")
    secciones = [
        ("Sesión", "", ["numero", "nombre", "fecha", "hora_inicio", "hora_fin", "lugar", "facilitadores"]),
        ("Minuta", "Lo que se hizo y se acordó: queda como registro de la actividad y del proyecto.",
         ["objetivo", "desarrollo", "avances", "acuerdos", "incidencias", "proximos_pasos"]),
        ("Asistentes sin registro individual", "Cuando asiste gente que no se registra una por una (p. ej. vecinos en una feria): solo cifras, sin datos personales.",
         ["asistentes_sin_registro", "conteo_menores", "conteo_jovenes", "conteo_adultos", "conteo_mayores", "conteo_mujeres", "conteo_hombres", "conteo_otros"]),
        ("Otros", "", ["observaciones", "vigente"]),
    ]

    class Meta:
        model = SesionActividad
        fields = ["numero", "nombre", "fecha", "hora_inicio", "hora_fin", "lugar", "objetivo", "desarrollo", "avances", "acuerdos", "incidencias", "proximos_pasos",
                  "asistentes_sin_registro", "conteo_menores", "conteo_jovenes", "conteo_adultos", "conteo_mayores", "conteo_mujeres", "conteo_hombres", "conteo_otros",
                  "observaciones", "vigente"]

    def clean_numero(self):
        n = self.cleaned_data["numero"]
        if SesionActividad.objects.filter(actividad_id=self.instance.actividad_id, numero=n).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe una sesión con ese número.")
        return n

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["lugar"] = LugarChoiceField(required=False)
        self.fields["lugar"].widget.attrs["class"] = "form-select"
        a = self.instance.actividad if self.instance.actividad_id else None
        if a:
            ids = set(a.participaciones.filter(rol__grupo="ejecutor").values_list("persona_id", flat=True))
            if a.responsable_id:
                ids.add(a.responsable_id)
            if self.instance.pk:
                ids |= set(self.instance.facilitadores.values_list("persona_id", flat=True))
                self.initial.setdefault("facilitadores", list(self.instance.facilitadores.values_list("persona_id", flat=True)))
            self.fields["facilitadores"].queryset = Persona.objects.filter(pk__in=ids)
            if not self.instance.pk:
                ultimo = a.sesiones.order_by("-numero").values_list("numero", flat=True).first()
                self.initial.setdefault("numero", (ultimo or 0) + 1)

    def save(self, commit=True):
        obj = super().save(commit=commit)
        if commit:
            elegidos = set(self.cleaned_data.get("facilitadores") or [])
            actuales = {f.persona: f for f in obj.facilitadores.select_related("persona")}
            for persona, f in actuales.items():
                if persona not in elegidos:
                    f.delete()  # tabla de relación sin historia propia: la sesión conserva su historial
            for persona in elegidos - set(actuales):
                SesionFacilitador.objects.create(sesion=obj, persona=persona)
        return obj


class TerritorioForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ActividadTerritorio
        fields = ["region", "provincia", "comuna", "sector", "vigente"]
        help_texts = {"region": "Elige un único nivel: región, provincia, comuna o sector."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["comuna"].queryset = Comuna.objects.select_related("provincia")
        # solo sectores activos; al editar se conserva el que la fila ya tenía aunque esté desactivado
        self.fields["sector"].queryset = Sector.para_elegir(conservar=self.instance.sector_id).select_related("comuna", "sector_padre__sector_padre")
        self.fields["sector"].label_from_instance = Sector.etiqueta

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

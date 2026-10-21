"""Formularios de la actividad: crear y editar, programar o reprogramar, crear una serie, cambiar el estado,
agregar participantes (o crearlos en el momento), organizaciones, comunidades, territorios, sesiones y resultado.
Cada formulario valida en el servidor lo mismo que se ve en pantalla."""
from django import forms

from apps.comunidades.selector import COMUNIDADES
from apps.lugares.campos import LugarChoiceField
from apps.lugares.models import Lugar
from apps.nucleo.formularios import BootstrapMixin, SelectorField, fijar_valores_selectores, preparar_tramos
from apps.nucleo.rut import CampoRut
from apps.nucleo.models import AreaTematica, EstadoParticipacion, Modalidad, RolParticipacion, TipoActividad, TipoIntervencion
from apps.organizaciones.selector import ORGANIZACIONES
from apps.personas.models import Persona
from apps.personas.selector import AYUDA_RESPONSABLE, PERSONAS
from apps.proyectos.models import Proyecto
from apps.territorio.destinos import DestinosMixin
from apps.territorio.models import Comuna, Sector

from .selector import ACTIVIDADES
from .models import Actividad, ActividadComunidad, ActividadOrganizacion, ActividadTerritorio, Participacion, SesionActividad, SesionFacilitador


def selector_persona(**kw):
    return SelectorField(PERSONAS, **kw)


class ActividadForm(DestinosMixin, BootstrapMixin, forms.ModelForm):
    """Crear y editar la actividad: qué es, para qué y para quién, y dónde (a la vista); los detalles van plegados.
    «¿Dónde?» guarda uno o más territorios (apps/territorio/destinos.py) junto con la actividad."""

    responsable = SelectorField(PERSONAS, filtros={"equipo_primero": 1}, required=False, help_text=AYUDA_RESPONSABLE)
    actividad_padre = SelectorField(
        ACTIVIDADES, filtros={"raiz": 1}, required=False, label="Jornada a la que pertenece",
        help_text="Solo si esta charla o taller ocurre dentro de una jornada ya registrada. Ej.: una feria con varios talleres.",
    )

    secciones = [
        ("Qué es", "Solo el nombre es obligatorio; la fecha y el lugar se definen al programar.", ["nombre", "tipo", "modalidad", "responsable"]),
        ("Para qué y para quién", "A quién va dirigida y qué se espera lograr. Las comunidades destinatarias se agregan en la pestaña «Público y comunidades».",
         ["objetivo", "publico_objetivo", "tramos_etarios", "rango_etario", "beneficiarios_estimados"]),
        ("¿Dónde se realiza o a quién va dirigida?", "La comuna o el sector, aunque aún no haya lugar; la sala o sede se elige al programar. No es obligatorio.",
         ["donde"]),
        ("Detalles", "Tema, proyecto, jornada, cómo se hará y requisitos. Todo es opcional.",
         ["area_tematica", "proyecto", "actividad_padre", "descripcion", "condiciones"], {"plegada": True}),
    ]

    class Meta:
        model = Actividad
        fields = ["nombre", "proyecto", "actividad_padre", "tipo", "area_tematica", "objetivo", "publico_objetivo", "tramos_etarios", "rango_etario",
                  "beneficiarios_estimados", "descripcion", "modalidad", "responsable", "condiciones"]
        labels = {
            "tramos_etarios": "Tramos de edad", "area_tematica": "Tema", "publico_objetivo": "¿Quiénes?, en palabras",
            "beneficiarios_estimados": "Personas esperadas", "descripcion": "Cómo se hará", "condiciones": "Requisitos y cuidados",
        }
        help_texts = {
            "nombre": "Cómo la reconocerás en listas y calendario. Ej.: «Taller de huertos · Villa Los Aromos».",
            "tipo": "Taller, charla, jornada… Si falta uno, se agrega en Catálogos.",
            "modalidad": "Presencial, virtual o híbrida. Al programar una fecha se puede cambiar solo para esa vez.",
            "objetivo": "Qué se quiere lograr, en una o dos frases. Ej.: «Que las familias armen su propia huerta».",
            "publico_objetivo": "Solo si hace falta precisar. Ej.: «apoderados de 1.º básico», «dirigentes de juntas de vecinos».",
            "tramos_etarios": "A qué edades va dirigida. Marca uno o más. Ej.: Personas adultas y Personas mayores.",
            "beneficiarios_estimados": "Cuántas personas crees que asistirán en total. Basta un número aproximado. Ej.: 30.",
            "area_tematica": "El tema principal: sirve para agrupar actividades y encontrar personas interesadas. Ej.: Medio ambiente.",
            "proyecto": "Si es parte de un proyecto, elígelo; si no, déjalo vacío. Ej.: «Alfabetización digital 2026».",
            "descripcion": "Contenidos, dinámica y materiales. Ej.: «Tres estaciones: semillas, compost y riego».",
            "condiciones": "Accesibilidad, materiales que deben traer, autorización de apoderados, etc. Ej.: «Traer ropa cómoda».",
        }

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


class TareaForm(BootstrapMixin, forms.ModelForm):
    """F25: «Nueva tarea» del proyecto en un solo paso. Una tarea es una actividad con proyecto: aquí se piden sus datos,
    su fecha (que la deja programada) y su destino (lugar o comunidad); la vista guarda todo junto."""

    responsable = SelectorField(PERSONAS, filtros={"equipo_primero": 1}, required=False, help_text=AYUDA_RESPONSABLE)
    fecha = forms.DateField(widget=forms.DateInput, required=False, label="Fecha", help_text="Si aún no se sabe, déjala vacía y prográmala después.")
    hora_inicio = forms.TimeField(widget=forms.TimeInput, required=False, label="Hora de inicio", help_text="Ej.: 10:00.")
    hora_fin = forms.TimeField(widget=forms.TimeInput, required=False, label="Hora de término", help_text="Ej.: 12:00.")
    lugar = LugarChoiceField(required=False, help_text="Sala, sede o espacio, si ya se sabe.")
    comunidad = SelectorField(COMUNIDADES, required=False, label="Comunidad", crear=False,
                              help_text="Si la tarea va a una comunidad (con o sin lugar). Ej.: Vecinos de la Etapa 2.")
    secciones = [
        ("Qué es", "Solo el nombre es obligatorio.", ["nombre", "objetivo", "descripcion", "responsable"]),
        ("Cuándo", "Con fecha y hora de inicio la tarea queda programada y aparece en el calendario.", ["fecha", "hora_inicio", "hora_fin"]),
        ("Dónde o con quién", "Un lugar, una comunidad o ambos. No es obligatorio.", ["lugar", "comunidad"]),
        ("Para quién", "", ["tramos_etarios", "publico_objetivo"]),
    ]

    class Meta:
        model = Actividad
        fields = ["nombre", "objetivo", "descripcion", "responsable", "tramos_etarios", "publico_objetivo", "rango_etario"]
        labels = {"objetivo": "Propósito", "descripcion": "Descripción", "tramos_etarios": "Tramos de edad", "publico_objetivo": "Público objetivo, en palabras"}
        help_texts = {
            "nombre": "Ej.: «Visita a la Etapa 2».",
            "objetivo": "Para qué se hace, en una o dos frases. Ej.: «Conocer a las familias interesadas en el taller».",
            "descripcion": "Qué se hará. Ej.: «Puerta a puerta con la dirigenta».",
            "tramos_etarios": "A qué edades va dirigida. Marca uno o más.",
            "publico_objetivo": "Ej.: «dirigentes de juntas de vecinos».",
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        preparar_tramos(self)

    def clean(self):
        d = super().clean()
        fecha, ini, fin = d.get("fecha"), d.get("hora_inicio"), d.get("hora_fin")
        if fecha and not ini:
            self.add_error("hora_inicio", "Indica la hora de inicio (o deja la fecha vacía).")
        if (ini or fin) and not fecha:
            self.add_error("fecha", "Indica la fecha de la tarea.")
        if ini and fin and fin <= ini:
            self.add_error("hora_fin", "La hora de término debe ser posterior a la de inicio.")
        return d


class ProgramarForm(BootstrapMixin, forms.Form):
    fecha = forms.DateField(widget=forms.DateInput, label="Fecha")
    hora_inicio = forms.TimeField(label="Hora de inicio", widget=forms.TimeInput, help_text="Ej.: 10:00.")
    hora_fin = forms.TimeField(label="Hora de término", widget=forms.TimeInput, required=False, help_text="O indica la duración, más abajo.")
    duracion = forms.IntegerField(label="Duración (minutos)", required=False, min_value=1, max_value=24 * 60,
                                  help_text="En vez de la hora de término: se calcula sola. Ej.: 90.")
    lugar = LugarChoiceField(required=False, help_text="Sala, sede o espacio. Si es virtual, déjalo vacío.")
    modalidad = forms.ModelChoiceField(Modalidad.objects.filter(activo=True), required=False, label="Modalidad de esta fecha",
                                       help_text="Solo si esta vez es distinta de la de la actividad. Ej.: Virtual.")
    enlace = forms.URLField(label="Enlace (si es virtual)", required=False, assume_scheme="https",
                            help_text="El enlace de la reunión virtual. Ej.: https://meet.ejemplo.cl/taller")
    motivo = forms.CharField(label="Motivo del cambio", max_length=250, required=False,
                             help_text="Obligatorio al reprogramar o reanudar. Ej.: la sede no estaba disponible.")

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
    """Crear una serie de actividades repetidas: cada repetición es una actividad propia dentro de la original."""

    FRECUENCIAS = [(7, "Cada semana"), (14, "Cada dos semanas"), (1, "Cada día"), (28, "Cada cuatro semanas")]
    primera_fecha = forms.DateField(widget=forms.DateInput, label="Primera fecha")
    frecuencia = forms.TypedChoiceField(choices=FRECUENCIAS, coerce=int, initial=7, label="¿Cada cuánto se repite?")
    repeticiones = forms.IntegerField(min_value=2, max_value=52, initial=4, label="¿Cuántas veces en total?", help_text="Entre 2 y 52. Ej.: 8.")
    hora_inicio = forms.TimeField(widget=forms.TimeInput, label="Hora de inicio", help_text="Ej.: 18:30.")
    hora_fin = forms.TimeField(widget=forms.TimeInput, required=False, label="Hora de término")
    lugar = LugarChoiceField(required=False, help_text="El mismo para todas las fechas; después se puede cambiar en cada una.")

    def clean(self):
        d = super().clean()
        if d.get("hora_inicio") and d.get("hora_fin") and d["hora_fin"] <= d["hora_inicio"]:
            self.add_error("hora_fin", "La hora de término debe ser posterior a la de inicio.")
        return d


class EstadoForm(BootstrapMixin, forms.Form):
    estado = forms.ChoiceField(choices=[], label="Nuevo estado")
    motivo = forms.CharField(max_length=250, required=False, label="Motivo",
                             help_text="Obligatorio para suspender o cancelar. Ej.: lluvia; se avisó a los participantes.")

    def __init__(self, *a, opciones=(), **kw):
        super().__init__(*a, **kw)
        self.fields["estado"].choices = opciones


ETIQUETAS_PARTICIPACION = {"rol": "Rol en la actividad", "estado": "Estado de la participación", "horas": "Horas"}
AYUDAS_PARTICIPACION = {
    "rol": "Ej.: Tallerista (parte del equipo) o Participante (asiste).",
    "estado": "Ej.: Invitado → Confirmado → Asistió.",
    "observaciones": "Ej.: llega 15 minutos tarde por su trabajo.",
    "comunidad": "La comunidad de la que viene, si corresponde. Ej.: Vecinos de la Etapa 2.",
    "horas": "Si se deja vacío, se usa la duración de la programación. Ej.: 4.",
}


class GrupoMixin(forms.Form):
    """F25: «¿De qué grupo viene?» (opcional). La organización con su cargo crea el vínculo de la persona con ella;
    la comunidad la suma a su padrón. Ambas quedan como procedencia en la participación."""

    organizacion = SelectorField(ORGANIZACIONES, required=False, label="Organización de la que viene",
                                 help_text="Junta de vecinos, colegio, municipalidad, negocio… Si no está, créala desde aquí.")
    cargo = forms.CharField(max_length=120, required=False, label="Cargo o relación con esa organización",
                            help_text="Ej.: Dirigente, Dueña de la panadería, Profesor.")
    comunidad = SelectorField(COMUNIDADES, required=False, label="Comunidad de la que viene", help_text="Ej.: Vecinos de la Etapa 2.")

    SECCION_GRUPO = ("¿De qué grupo viene?", "Opcional. Queda en la ficha de la persona y en la de la organización o comunidad.",
                     ["organizacion", "cargo", "comunidad"])

    def clean(self):
        d = super().clean()
        if d.get("cargo") and not d.get("organizacion"):
            self.add_error("organizacion", "Elige la organización a la que corresponde el cargo.")
        return d


class ParticipanteNuevoForm(GrupoMixin, BootstrapMixin, forms.ModelForm):
    persona = selector_persona()
    secciones = [("Participante", "", ["persona", "rol", "estado", "observaciones"]), GrupoMixin.SECCION_GRUPO]

    class Meta:
        model = Participacion
        fields = ["persona", "rol", "estado", "observaciones"]
        labels = ETIQUETAS_PARTICIPACION
        help_texts = AYUDAS_PARTICIPACION

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
        labels = ETIQUETAS_PARTICIPACION
        help_texts = AYUDAS_PARTICIPACION

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


class PersonaRapidaForm(GrupoMixin, BootstrapMixin, forms.Form):
    """Ficha rápida de terreno (F25): solo el nombre es obligatorio; lo demás se completa si se sabe."""

    nombres = forms.CharField(max_length=150, label="Nombres", help_text="Ej.: María José.")
    apellido_paterno = forms.CharField(max_length=100, required=False, label="Apellido paterno")
    apellido_materno = forms.CharField(max_length=100, required=False, label="Apellido materno")
    rut = CampoRut(label="RUT")
    documento = forms.CharField(max_length=40, required=False, label="Documento extranjero",
                                help_text="Solo si no tiene RUT chileno: el número de su pasaporte o documento. Ej.: AB123456.")
    nacionalidad = forms.CharField(max_length=60, required=False, label="Nacionalidad", help_text="Ej.: Chilena, Venezolana.")
    sexo = forms.ChoiceField(choices=[("", "—")] + Persona.SEXOS, required=False, label="Sexo")
    correo = forms.EmailField(required=False, label="Correo electrónico", help_text="Ej.: nombre@ejemplo.cl")
    telefono = forms.CharField(max_length=40, required=False, label="Teléfono", help_text="Ej.: +56 9 1234 5678.")
    comuna = forms.ModelChoiceField(Comuna.objects.select_related("provincia__region").order_by("nombre"), required=False, label="Comuna donde vive",
                                    help_text="Así aparece en el territorio. Ej.: Hualpén.")
    rol = forms.ModelChoiceField(RolParticipacion.objects.filter(activo=True), label="Rol en la actividad",
                                 help_text=AYUDAS_PARTICIPACION["rol"])
    secciones = [
        ("Persona", "Solo el nombre es obligatorio.", ["nombres", "apellido_paterno", "apellido_materno", "rut", "documento", "nacionalidad", "sexo"]),
        ("Contacto y comuna", "", ["telefono", "correo", "comuna"]),
        ("En esta actividad", "", ["rol"]),
        GrupoMixin.SECCION_GRUPO,
    ]

    def clean_rut(self):
        rut = self.cleaned_data.get("rut")
        if rut and Persona.objects.filter(rut_numero=rut[0]).exists():
            raise forms.ValidationError("Ya hay una persona registrada con ese RUT. Búscala en «Agregar participante».")
        return rut

    def clean_documento(self):
        doc = self.cleaned_data.get("documento", "").strip().upper()
        if doc and Persona.objects.filter(tipo_documento="extranjero", numero_documento__iexact=doc).exists():
            raise forms.ValidationError("Ya hay una persona registrada con ese documento. Búscala en «Agregar participante».")
        return doc


class ActividadOrganizacionForm(BootstrapMixin, forms.ModelForm):
    organizacion = SelectorField(ORGANIZACIONES, label="Organización")
    contacto = selector_persona(required=False, label="Persona de contacto", help_text="Con quién se coordina en esa organización, si se sabe.")

    class Meta:
        model = ActividadOrganizacion
        fields = ["organizacion", "tipo_intervencion", "contacto", "observaciones", "vigente"]
        labels = {"tipo_intervencion": "¿Qué aporta esta organización?"}
        help_texts = {"tipo_intervencion": "Ej.: Facilita espacio (presta la sede)."}

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
        labels = {"beneficiarios_estimados": "Personas esperadas de esta comunidad"}
        help_texts = {"comunidad": "Si no está, créala antes en Comunidades.", "beneficiarios_estimados": "Un número aproximado. Ej.: 15."}

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

    facilitadores = forms.ModelMultipleChoiceField(Persona.objects.none(), required=False, widget=forms.CheckboxSelectMultiple, label="Quiénes la dirigieron",
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
        labels = {"numero": "N.º de sesión", "nombre": "Nombre de la sesión", "hora_inicio": "Hora de inicio", "hora_fin": "Hora de término",
                  "asistentes_sin_registro": "¿Cuántas personas asistieron sin registrarse?"}
        help_texts = {"numero": "Se propone el siguiente. Ej.: 3.", "nombre": "Opcional. Ej.: Compostaje en casa.",
                      "objetivo": "Qué se buscaba en esta sesión. Ej.: que cada familia arme su compostera.",
                      "acuerdos": "Ej.: la próxima sesión cada familia trae un frasco de vidrio.",
                      "incidencias": "Imprevistos. Ej.: corte de luz; se empezó 30 minutos tarde.",
                      "proximos_pasos": "Ej.: confirmar la sede para la sesión 4.",
                      "asistentes_sin_registro": "Total aproximado. Si quieres, desglósalo abajo por edad y por sexo. Ej.: 40."}

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
        labels = {"region": "Región", "provincia": "Provincia", "comuna": "Comuna", "sector": "Sector, villa o población"}
        help_texts = {"region": "Elige solo una de las cuatro listas: la región, la provincia, la comuna o el sector. Ej.: la comuna Hualpén."}

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
        fields = ["resultado", "indicadores", "incidencias", "observaciones", "asistencia_sin_registro"]
        widgets = {f: forms.Textarea(attrs={"rows": 4}) for f in ["observaciones", "incidencias", "resultado", "indicadores"]}
        labels = {"resultado": "¿Qué se logró?", "indicadores": "Cifras logradas", "incidencias": "Imprevistos",
                  "observaciones": "Otras observaciones", "asistencia_sin_registro": "No se tomó asistencia persona por persona"}
        help_texts = {
            "resultado": "Resumen para el informe. Ej.: se realizaron las 4 sesiones; 18 de 20 personas terminaron el taller.",
            "indicadores": "Números que muestran el resultado. Ej.: 18 constancias entregadas.",
            "incidencias": "Ej.: corte de luz; se empezó 30 minutos tarde.",
            "observaciones": "Lo que convenga recordar para la próxima vez.",
            "asistencia_sin_registro": "Márcalo si no hubo lista; así igual se puede finalizar la actividad.",
        }

"""Tablas del centro del sistema: la actividad y todo lo que se le vincula.
Actividad; Participacion (persona en la actividad, con rol, estado y asistencia); ActividadOrganizacion
(cómo intervino una organización); ActividadComunidad y ActividadTerritorio (a quién y dónde va dirigida);
SesionActividad (cada jornada o encuentro, con su minuta y su lista del día), SesionAsistencia (la marca de cada persona
en una jornada), CambioLista (cierres y reaperturas de la lista) y AgendaActividad (cada programación es una versión;
solo una vigente). F28: la inscripción (Participacion) no cambia al pasar lista; la asistencia es por jornada."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Exists, F, OuterRef, Q
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.nucleo.models import (
    AreaTematica, EstadoActividad, EstadoParticipacion, Modalidad, RolParticipacion, TipoActividad, TipoIntervencion, TramoEtario,
)
from apps.territorio.models import DestinoTerritorial, un_solo_nivel


class ActividadQuerySet(models.QuerySet):
    def incompletas(self):
        """Actividades aún no confirmadas a las que les falta lo mínimo para confirmar."""
        vigente = AgendaActividad.objects.filter(actividad=OuterRef("pk"), vigente=True, hora_inicio__isnull=False)
        return (
            self.filter(estado__codigo__in=["pendiente", "planificada", "reprogramada"])
            .annotate(_tiene_agenda=Exists(vigente))
            .filter(Q(responsable__isnull=True) | Q(_tiene_agenda=False))
        )


class Actividad(models.Model):
    proyecto = models.ForeignKey("proyectos.Proyecto", null=True, blank=True, on_delete=models.PROTECT, related_name="actividades")
    actividad_padre = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="hijas", verbose_name="actividad padre")
    nombre = models.CharField(max_length=200)
    tipo = models.ForeignKey(TipoActividad, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    objetivo = models.TextField(blank=True)
    descripcion = models.TextField("descripción", blank=True)
    estado = models.ForeignKey(EstadoActividad, on_delete=models.PROTECT, related_name="+")
    motivo_estado = models.CharField("motivo del último cambio de estado", max_length=250, blank=True)
    modalidad = models.ForeignKey(Modalidad, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    responsable = models.ForeignKey("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="actividades_a_cargo")
    condiciones = models.TextField(blank=True)
    # F22: a quién va dirigida
    area_tematica = models.ForeignKey(AreaTematica, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="línea o área temática")
    publico_objetivo = models.TextField("público objetivo", blank=True, help_text="A quién va dirigida: por ejemplo, vecinos del sector, estudiantes de 3.º medio, personas mayores.")
    rango_etario = models.CharField("rango etario", max_length=100, blank=True)  # texto anterior a los tramos; se conserva para revisarlo
    tramos_etarios = models.ManyToManyField(TramoEtario, blank=True, related_name="actividades", verbose_name="tramos de edad")
    beneficiarios_estimados = models.PositiveIntegerField("beneficiarios estimados", null=True, blank=True)
    # Ejecución y cierre (F13)
    observaciones = models.TextField(blank=True)
    incidencias = models.TextField(blank=True)
    resultado = models.TextField(blank=True)
    indicadores = models.TextField(blank=True)
    asistencia_sin_registro = models.BooleanField("asistencia sin registro (explícito)", default=False)
    finalizada_en = models.DateTimeField(null=True, blank=True)
    finalizada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()
    objects = ActividadQuerySet.as_manager()

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "actividad"
        verbose_name_plural = "actividades"
        permissions = [
            ("reprogramar_actividad", "Puede programar y reprogramar actividades"),
            ("cerrar_actividad", "Puede finalizar actividades"),
            ("reabrir_actividad", "Puede reabrir actividades realizadas"),
            ("exportar_actividad", "Puede exportar actividades"),
        ]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        if self.proyecto_id:  # una tarea se abre dentro de su proyecto: /proyectos/<id>/tareas/<id>
            return reverse("actividades:tarea_ficha", args=[self.proyecto_id, self.pk])
        return reverse("actividades:ficha", args=[self.pk])

    @property
    def agenda_vigente(self):
        if "_agenda_vigente_fija" in self.__dict__:  # F26 Rb: leída una vez por la ficha (ver fijar_agenda_vigente)
            return self.__dict__["_agenda_vigente_fija"]
        return self.agendas.filter(vigente=True).select_related("lugar").first()

    def fijar_agenda_vigente(self):
        """F26 Rb: la ficha (solo lectura) lee la agenda vigente una sola vez; las demás lecturas de esta instancia la reutilizan.
        No se usa donde se reprograma: ahí cada lectura consulta la base."""
        self._agenda_vigente_fija = self.agendas.filter(vigente=True).select_related("lugar").first()
        return self._agenda_vigente_fija

    @property
    def es_virtual(self):
        return bool(self.modalidad_id and self.modalidad.codigo == "virtual")

    def faltantes(self):
        res = []
        if not self.responsable_id:
            res.append("responsable")
        ag = self.agenda_vigente
        if not ag or not ag.hora_inicio:
            res.append("fecha y hora")
        elif not ag.lugar_id and not self.es_virtual:
            res.append("lugar")
        return res

    def clean(self):
        if self.actividad_padre_id:
            if self.pk and self.actividad_padre_id == self.pk:
                raise ValidationError({"actividad_padre": "Una actividad no puede ser su propia padre."})
            if self.actividad_padre.actividad_padre_id:
                raise ValidationError({"actividad_padre": "Solo se admite un nivel (jornada → charlas y talleres)."})


class ActividadTerritorio(DestinoTerritorial):
    """A qué territorio se dirige la actividad; exactamente un nivel por fila (ver DestinoTerritorial)."""

    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="territorios")

    class Meta:
        verbose_name = "territorio de la actividad"
        verbose_name_plural = "territorios de la actividad"
        constraints = [un_solo_nivel("actividad_territorio_un_nivel")]


class Participacion(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="participaciones")
    persona = models.ForeignKey("personas.Persona", on_delete=models.PROTECT, related_name="participaciones")
    rol = models.ForeignKey(RolParticipacion, on_delete=models.PROTECT, related_name="+")
    estado = models.ForeignKey(EstadoParticipacion, on_delete=models.PROTECT, related_name="+")
    asistencia = models.BooleanField(null=True, blank=True, help_text="Vacío = sin registro.")
    observaciones = models.CharField(max_length=250, blank=True)
    # F22: de dónde viene y cuánto aportó
    institucion = models.ForeignKey("organizaciones.Organizacion", null=True, blank=True, on_delete=models.PROTECT, related_name="participaciones",
                                    verbose_name="institución de procedencia", help_text="Se completa sola con la formación vigente de la persona.")
    comunidad = models.ForeignKey("comunidades.Comunidad", null=True, blank=True, on_delete=models.PROTECT, related_name="participaciones",
                                  verbose_name="comunidad de procedencia", help_text="Se completa sola si la persona integra una comunidad a la que va dirigida la actividad.")
    horas = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, help_text="Horas de participación. Si se deja vacío se usa la duración de la programación.")
    # F25 F3: el rol es corto (Autoridad, Invitado o invitada…); el detalle va aquí, libre
    cargo = models.CharField("cargo o función", max_length=120, blank=True, help_text="Ej.: Alcalde de Hualpén, Prevencionista de obras públicas.")
    fecha = models.DateField(auto_now_add=True)
    # F28: desde qué día está inscrita (aparece en las listas de las jornadas desde esa fecha) y, si se retiró, hasta cuándo
    inscrito_en = models.DateField("inscrita desde", null=True, blank=True,
                                   help_text="Aparece en las listas de las jornadas desde esta fecha. Si ya venía desde el inicio, pon la fecha de la primera jornada.")
    retirado_en = models.DateField("retirada el", null=True, blank=True)
    motivo_retiro = models.CharField("motivo del retiro", max_length=250, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    history = HistoricalRecords()

    class Meta:
        ordering = ["rol__orden", "persona__apellido_paterno", "persona__nombres"]
        verbose_name = "participación"
        verbose_name_plural = "participaciones"
        constraints = [models.UniqueConstraint(fields=["actividad", "persona", "rol"], name="participacion_unica")]

    def __str__(self):
        return f"{self.persona} · {self.rol} · {self.actividad}"

    # F28: «Asistió» y «No asistió» ya no son estados de inscripción (la asistencia va por jornada): no sacan a nadie de
    # la tarea. «Retirado» deja de ocupar cupo desde su retiro (y sigue en las listas de las jornadas anteriores).
    INACTIVOS = ("rechazo", "cancelo", "lista_espera", "registro_erroneo", "retirado")

    @property
    def activa(self):
        """Ocupa cupo. «En lista de espera» no ocupa cupo hasta que se confirme [P]."""
        return self.estado.codigo not in self.INACTIVOS

    @property
    def retirada(self):
        return self.estado.codigo == "retirado"

    def en_lista_de(self, fecha):
        """F28: ¿aparece en la lista de una jornada de esa fecha? Inscripción activa en esa fecha: inscrita desde antes
        (o el mismo día) y, si se retiró, no antes de ese día. Faltar nunca la saca de la lista."""
        codigo = self.estado.codigo
        if codigo == "retirado":
            if not (self.retirado_en and fecha and fecha <= self.retirado_en):
                return False
        elif codigo in self.INACTIVOS:
            return False
        return not (self.inscrito_en and fecha and fecha < self.inscrito_en)

    @property
    def en_espera(self):
        return self.estado.codigo == "lista_espera"

    @property
    def es_beneficiario(self):
        return self.rol.codigo == "beneficiario"

    @property
    def grupo(self):
        return self.rol.grupo

    @property
    def rol_y_cargo(self):
        """«Rol · cargo» para las tablas (F25 F3)."""
        return f"{self.rol} · {self.cargo}" if self.cargo else str(self.rol)

    def completar_procedencia(self):
        """Institución desde la formación vigente y comunidad desde el padrón, si no se indicaron (F22)."""
        if not self.institucion_id:
            f = self.persona.formaciones.filter(vigente=True).order_by("-anio_inicio", "-pk").first()
            if f:
                self.institucion_id = f.organizacion_id
        if not self.comunidad_id:
            destino = self.actividad.comunidades_destino.filter(vigente=True).values_list("comunidad_id", flat=True)
            m = self.persona.comunidades.filter(vigente=True, comunidad_id__in=list(destino)).first()
            if m:
                self.comunidad_id = m.comunidad_id

    def save(self, *args, **kwargs):
        if self.persona_id and self.actividad_id and (not self.institucion_id or not self.comunidad_id):
            self.completar_procedencia()
        if self._state.adding and not self.inscrito_en:  # F28: inscrita desde hoy, si no se indica otra fecha
            from django.utils import timezone

            self.inscrito_en = timezone.localdate()
        super().save(*args, **kwargs)


class ActividadOrganizacion(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="organizaciones")
    organizacion = models.ForeignKey("organizaciones.Organizacion", on_delete=models.PROTECT, related_name="actividades")
    tipo_intervencion = models.ForeignKey(TipoIntervencion, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="tipo de intervención")
    contacto = models.ForeignKey("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="persona de contacto")
    observaciones = models.CharField(max_length=250, blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "organización de la actividad"
        verbose_name_plural = "organizaciones de la actividad"
        constraints = [models.UniqueConstraint(fields=["actividad", "organizacion", "tipo_intervencion"], name="actividad_org_unica")]

    def __str__(self):
        return f"{self.organizacion} · {self.actividad}"


class ActividadComunidad(models.Model):
    """Comunidades a las que va dirigida la actividad (F22)."""

    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="comunidades_destino")
    comunidad = models.ForeignKey("comunidades.Comunidad", on_delete=models.PROTECT, related_name="actividades_dirigidas")
    beneficiarios_estimados = models.PositiveIntegerField("beneficiarios estimados", null=True, blank=True)
    observaciones = models.CharField(max_length=250, blank=True)
    vigente = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "comunidad destinataria"
        verbose_name_plural = "comunidades destinatarias"
        constraints = [models.UniqueConstraint(fields=["actividad", "comunidad"], name="actividad_comunidad_unica")]

    def __str__(self):
        return f"{self.comunidad} · {self.actividad}"


class SesionActividad(models.Model):
    """Bitácora de una sesión: minuta, avances, asistencia y evidencias (F22; visible sin segunda fase)."""

    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="sesiones")
    numero = models.PositiveSmallIntegerField("n.º", default=1)
    nombre = models.CharField(max_length=150, blank=True)
    fecha = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField("desde", null=True, blank=True)
    hora_fin = models.TimeField("hasta", null=True, blank=True)
    lugar = models.ForeignKey("lugares.Lugar", null=True, blank=True, on_delete=models.PROTECT, related_name="sesiones")
    objetivo = models.TextField("objetivo de la sesión", blank=True)
    desarrollo = models.TextField("desarrollo", blank=True, help_text="Qué se hizo, en orden.")
    avances = models.TextField(blank=True, help_text="Qué se logró respecto del objetivo de la actividad o del proyecto.")
    acuerdos = models.TextField(blank=True)
    incidencias = models.TextField(blank=True)
    proximos_pasos = models.TextField("próximos pasos", blank=True)
    # Asistentes sin registro individual: solo cifras, sin datos personales
    asistentes_sin_registro = models.PositiveIntegerField("asistentes sin registro individual", null=True, blank=True,
                                                          help_text="Personas que asistieron y no quedaron registradas una por una.")
    conteo_menores = models.PositiveIntegerField("0 a 17 años", null=True, blank=True)
    conteo_jovenes = models.PositiveIntegerField("18 a 29 años", null=True, blank=True)
    conteo_adultos = models.PositiveIntegerField("30 a 59 años", null=True, blank=True)
    conteo_mayores = models.PositiveIntegerField("60 años o más", null=True, blank=True)
    conteo_mujeres = models.PositiveIntegerField("mujeres", null=True, blank=True)
    conteo_hombres = models.PositiveIntegerField("hombres", null=True, blank=True)
    conteo_otros = models.PositiveIntegerField("otro o no informado", null=True, blank=True)
    observaciones = models.CharField(max_length=250, blank=True)
    vigente = models.BooleanField(default=True)
    redactada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True, null=True)
    # F28: la lista del día (en pantalla, la sesión es una «jornada»)
    LISTA_ABIERTA, LISTA_CERRADA, SUSPENDIDA = "abierta", "cerrada", "suspendida"
    ESTADOS_LISTA = [(LISTA_ABIERTA, "Abierta"), (LISTA_CERRADA, "Cerrada"), (SUSPENDIDA, "Suspendida")]
    estado_lista = models.CharField("estado de la lista", max_length=12, choices=ESTADOS_LISTA, default=LISTA_ABIERTA)
    cerrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
                                    verbose_name="lista cerrada por")
    cerrada_en = models.DateTimeField("lista cerrada el", null=True, blank=True)
    motivo_suspension = models.CharField("motivo de la suspensión", max_length=250, blank=True)
    version_lista = models.PositiveIntegerField("versión de la lista", default=0, editable=False,
                                                help_text="Sube con cada cambio de la lista: avisa si otra pestaña la cambió (F28).")
    history = HistoricalRecords()

    class Meta:
        ordering = ["numero"]
        verbose_name = "sesión"
        verbose_name_plural = "sesiones"
        constraints = [models.UniqueConstraint(fields=["actividad", "numero"], name="sesion_numero_unico")]

    def __str__(self):
        return f"Sesión {self.numero}" + (f": {self.nombre}" if self.nombre else "")

    def get_absolute_url(self):
        return reverse("actividades:sesion", args=[self.actividad_id, self.pk])

    @property
    def nombre_jornada(self):
        """F28: cómo se nombra en las listas y la matriz: «Jornada 2» (o «Jornada programada» si aún no se guarda)."""
        return f"Jornada {self.numero}" if self.pk else "Jornada programada"

    @property
    def lista_abierta(self):
        return self.estado_lista == self.LISTA_ABIERTA

    @property
    def lista_cerrada(self):
        return self.estado_lista == self.LISTA_CERRADA

    @property
    def suspendida(self):
        return self.estado_lista == self.SUSPENDIDA

    @property
    def tiene_conteo(self):
        return self.asistentes_sin_registro is not None

    @property
    def asistentes_registrados(self):
        return self.asistencias.filter(asistio=True).count()

    @property
    def total_asistentes(self):
        return self.asistentes_registrados + (self.asistentes_sin_registro or 0)

    @property
    def duracion_horas(self):
        from datetime import datetime

        if self.hora_inicio and self.hora_fin:
            return round((datetime.combine(self.fecha or datetime.today(), self.hora_fin) - datetime.combine(self.fecha or datetime.today(), self.hora_inicio)).seconds / 3600, 1)
        return None

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de término debe ser posterior a la de inicio."})
        total = self.asistentes_sin_registro
        if total is not None:
            edades = [self.conteo_menores, self.conteo_jovenes, self.conteo_adultos, self.conteo_mayores]
            generos = [self.conteo_mujeres, self.conteo_hombres, self.conteo_otros]
            if any(v is not None for v in edades) and sum(v or 0 for v in edades) > total:
                raise ValidationError({"conteo_menores": "La suma por tramo de edad supera el total de asistentes sin registro."})
            if any(v is not None for v in generos) and sum(v or 0 for v in generos) > total:
                raise ValidationError({"conteo_mujeres": "La suma por género supera el total de asistentes sin registro."})


class SesionFacilitador(models.Model):
    """Quién dirigió o facilitó la sesión."""

    sesion = models.ForeignKey(SesionActividad, on_delete=models.PROTECT, related_name="facilitadores")
    persona = models.ForeignKey("personas.Persona", on_delete=models.PROTECT, related_name="sesiones_facilitadas")

    class Meta:
        verbose_name = "facilitador de sesión"
        verbose_name_plural = "facilitadores de sesión"
        constraints = [models.UniqueConstraint(fields=["sesion", "persona"], name="facilitador_unico")]

    def __str__(self):
        return str(self.persona)


class SesionAsistencia(models.Model):
    """Asistencia del día (F28): la marca de una persona inscrita en una jornada, con observación, quién y cuándo.
    Una sola por persona y jornada (ver apps/actividades/asistencia.py). `asistio` se deduce de la marca."""

    PRESENTE, ATRASADO, RETIRO_ANTICIPADO, JUSTIFICADO, AUSENTE = "presente", "atrasado", "retiro_anticipado", "justificado", "ausente"
    MARCAS = [(PRESENTE, "Presente"), (ATRASADO, "Atrasado"), (RETIRO_ANTICIPADO, "Se retiró antes"), (JUSTIFICADO, "Justificado"), (AUSENTE, "Ausente")]
    CUENTAN = (PRESENTE, ATRASADO, RETIRO_ANTICIPADO)  # cuentan como asistencia; «Justificado» no cuenta para el porcentaje [P]

    sesion = models.ForeignKey(SesionActividad, on_delete=models.PROTECT, related_name="asistencias")
    participacion = models.ForeignKey(Participacion, on_delete=models.PROTECT, related_name="asistencias_sesion")
    asistio = models.BooleanField("asistió", null=True, blank=True)
    marca = models.CharField(max_length=20, choices=MARCAS, blank=True, help_text="Vacío = sin marcar.")
    observacion = models.CharField("observación", max_length=250, blank=True, help_text="Ej.: trae certificado médico.")
    marcado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    marcado_en = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "asistencia a sesión"
        verbose_name_plural = "asistencias a sesiones"
        constraints = [models.UniqueConstraint(fields=["sesion", "participacion"], name="asistencia_sesion_unica")]

    def __str__(self):
        return f"{self.participacion.persona} · {self.sesion}"

    @staticmethod
    def asistio_de(marca):
        if marca in SesionAsistencia.CUENTAN:
            return True
        return False if marca in (SesionAsistencia.AUSENTE, SesionAsistencia.JUSTIFICADO) else None

    def save(self, *args, **kwargs):
        if not self.marca and self.asistio is not None:  # registros con el formato anterior (asistió sí / no)
            self.marca = self.PRESENTE if self.asistio else self.AUSENTE
        self.asistio = self.asistio_de(self.marca)
        super().save(*args, **kwargs)


class CambioLista(models.Model):
    """F28: cierres, reaperturas y suspensiones de la lista de una jornada, con quién, cuándo y por qué."""

    ACCIONES = [("cerrada", "Lista cerrada"), ("reabierta", "Lista reabierta"), ("suspendida", "Jornada suspendida"), ("migrada", "Lista migrada")]
    sesion = models.ForeignKey(SesionActividad, on_delete=models.PROTECT, related_name="cambios_lista")
    accion = models.CharField(max_length=12, choices=ACCIONES)
    motivo = models.CharField(max_length=250, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        verbose_name = "cambio de la lista"
        verbose_name_plural = "cambios de las listas"

    def __str__(self):
        return f"{self.get_accion_display()} · {self.sesion}"


class AgendaActividad(models.Model):
    """Cada fila es una versión de la programación. Reprogramar agrega una versión; nunca sobrescribe."""

    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="agendas")
    version = models.PositiveSmallIntegerField(default=1)
    vigente = models.BooleanField(default=True)
    fecha = models.DateField()
    hora_inicio = models.TimeField("hora de inicio", null=True, blank=True)
    hora_fin = models.TimeField("hora de término", null=True, blank=True)
    lugar = models.ForeignKey("lugares.Lugar", null=True, blank=True, on_delete=models.PROTECT, related_name="agendas")
    modalidad = models.ForeignKey(Modalidad, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    estado = models.ForeignKey(EstadoActividad, on_delete=models.PROTECT, related_name="+")
    motivo_cambio = models.CharField("motivo del cambio", max_length=250, blank=True)
    enlace = models.URLField("enlace (actividad virtual)", blank=True, help_text="Plataforma y enlace de la reunión virtual (LU-E8).")
    ultimo_minuto = models.BooleanField("cambio de último minuto", default=False)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["actividad_id", "-version"]
        verbose_name = "programación"
        verbose_name_plural = "programaciones"
        constraints = [
            models.UniqueConstraint(fields=["actividad", "version"], name="agenda_version_unica"),
            models.UniqueConstraint(fields=["actividad"], condition=Q(vigente=True), name="agenda_una_sola_vigente"),
            models.CheckConstraint(
                condition=Q(hora_inicio__isnull=True) | Q(hora_fin__isnull=True) | Q(hora_fin__gt=F("hora_inicio")), name="agenda_horas_coherentes"
            ),
        ]

    def __str__(self):
        return f"{self.actividad} v{self.version} ({self.fecha:%d-%m-%Y})"

    @property
    def duracion_minutos(self):
        if self.hora_inicio and self.hora_fin:
            return (self.hora_fin.hour * 60 + self.hora_fin.minute) - (self.hora_inicio.hour * 60 + self.hora_inicio.minute)
        return None

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de término debe ser posterior a la de inicio."})

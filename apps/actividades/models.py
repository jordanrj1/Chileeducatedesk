from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Exists, F, OuterRef, Q
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.nucleo.models import (
    EstadoActividad, EstadoParticipacion, Modalidad, RolParticipacion, TipoActividad, TipoIntervencion,
)


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
        return reverse("actividades:ficha", args=[self.pk])

    @property
    def agenda_vigente(self):
        return self.agendas.filter(vigente=True).select_related("lugar").first()

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


class ActividadTerritorio(models.Model):
    """A qué territorio se dirige la actividad; exactamente un nivel por fila."""

    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="territorios")
    region = models.ForeignKey("territorio.Region", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    provincia = models.ForeignKey("territorio.Provincia", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    comuna = models.ForeignKey("territorio.Comuna", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    sector = models.ForeignKey("territorio.Sector", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "territorio de la actividad"
        verbose_name_plural = "territorios de la actividad"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(region__isnull=False, provincia__isnull=True, comuna__isnull=True, sector__isnull=True)
                    | Q(region__isnull=True, provincia__isnull=False, comuna__isnull=True, sector__isnull=True)
                    | Q(region__isnull=True, provincia__isnull=True, comuna__isnull=False, sector__isnull=True)
                    | Q(region__isnull=True, provincia__isnull=True, comuna__isnull=True, sector__isnull=False)
                ),
                name="actividad_territorio_un_nivel",
            )
        ]

    def __str__(self):
        return str(self.region or self.provincia or self.comuna or self.sector)

    @property
    def nivel(self):
        for n in ("sector", "comuna", "provincia", "region"):
            if getattr(self, f"{n}_id"):
                return n


class Participacion(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="participaciones")
    persona = models.ForeignKey("personas.Persona", on_delete=models.PROTECT, related_name="participaciones")
    rol = models.ForeignKey(RolParticipacion, on_delete=models.PROTECT, related_name="+")
    estado = models.ForeignKey(EstadoParticipacion, on_delete=models.PROTECT, related_name="+")
    asistencia = models.BooleanField(null=True, blank=True, help_text="Vacío = sin registro.")
    observaciones = models.CharField(max_length=250, blank=True)
    fecha = models.DateField(auto_now_add=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    history = HistoricalRecords()

    class Meta:
        ordering = ["rol__orden", "persona__apellido_paterno", "persona__nombres"]
        verbose_name = "participación"
        verbose_name_plural = "participaciones"
        constraints = [models.UniqueConstraint(fields=["actividad", "persona", "rol"], name="participacion_unica")]

    def __str__(self):
        return f"{self.persona} · {self.rol} · {self.actividad}"

    @property
    def activa(self):
        """Ocupa cupo. «En lista de espera» no ocupa cupo hasta que se confirme [P]."""
        return self.estado.codigo not in ("rechazo", "cancelo", "no_asistio", "lista_espera", "registro_erroneo")

    @property
    def en_espera(self):
        return self.estado.codigo == "lista_espera"

    @property
    def es_beneficiario(self):
        return self.rol.codigo == "beneficiario"


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


class SesionActividad(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="sesiones")
    numero = models.PositiveSmallIntegerField("n.º", default=1)
    nombre = models.CharField(max_length=150, blank=True)
    fecha = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField("desde", null=True, blank=True)
    hora_fin = models.TimeField("hasta", null=True, blank=True)
    lugar = models.ForeignKey("lugares.Lugar", null=True, blank=True, on_delete=models.PROTECT, related_name="sesiones")
    observaciones = models.CharField(max_length=250, blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        ordering = ["numero"]
        verbose_name = "sesión"
        verbose_name_plural = "sesiones"
        constraints = [models.UniqueConstraint(fields=["actividad", "numero"], name="sesion_numero_unico")]

    def __str__(self):
        return f"Sesión {self.numero}" + (f": {self.nombre}" if self.nombre else "")

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de término debe ser posterior a la de inicio."})


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

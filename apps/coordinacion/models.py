from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.nucleo.models import Canal, Modalidad, RolParticipacion, TipoIntervencion


def _creado_por():
    return models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")


class InteraccionQuerySet(models.QuerySet):
    def proximas_acciones(self, hoy=None, dias=7):
        """Próximas acciones no cumplidas que vencen en los próximos días (o ya vencieron): IN-02."""
        hoy = hoy or timezone.localdate()
        return self.filter(accion_cumplida=False, proxima_fecha__isnull=False, proxima_fecha__lte=hoy + timedelta(days=dias)).exclude(proxima_accion="").order_by("proxima_fecha")


class Interaccion(models.Model):
    """Llamado, correo, mensaje o contacto con una persona u organización, con su próximo paso."""

    fecha = models.DateTimeField(default=timezone.now)
    canal = models.ForeignKey(Canal, on_delete=models.PROTECT, related_name="+")
    persona = models.ForeignKey("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="interacciones")
    organizacion = models.ForeignKey("organizaciones.Organizacion", null=True, blank=True, on_delete=models.PROTECT, related_name="interacciones", verbose_name="organización")
    solicitud = models.ForeignKey("solicitudes.Solicitud", null=True, blank=True, on_delete=models.PROTECT, related_name="interacciones")
    actividad = models.ForeignKey("actividades.Actividad", null=True, blank=True, on_delete=models.PROTECT, related_name="interacciones")
    motivo = models.CharField(max_length=250, blank=True)
    resultado = models.TextField(blank=True)
    proxima_accion = models.CharField("próxima acción", max_length=250, blank=True)
    proxima_fecha = models.DateField("fecha de la próxima acción", null=True, blank=True)
    accion_cumplida = models.BooleanField("próxima acción cumplida", default=False)
    creado_por = _creado_por()
    objects = InteraccionQuerySet.as_manager()

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "interacción"
        verbose_name_plural = "interacciones"
        permissions = [("exportar_interaccion", "Puede exportar interacciones")]

    def __str__(self):
        return f"{self.fecha:%d-%m-%Y} {self.canal} {self.persona or self.organizacion or ''}".strip()

    def get_absolute_url(self):
        return reverse("coordinacion:interaccion_ficha", args=[self.pk])

    def clean(self):
        if not self.persona_id and not self.organizacion_id:
            raise ValidationError("Indica con qué persona u organización fue el contacto.")
        if self.proxima_fecha and not self.proxima_accion:
            raise ValidationError({"proxima_accion": "Describe la próxima acción."})


class Reunion(models.Model):
    titulo = models.CharField(max_length=200)
    fecha = models.DateField()
    hora_inicio = models.TimeField("desde", null=True, blank=True)
    hora_fin = models.TimeField("hasta", null=True, blank=True)
    lugar = models.ForeignKey("lugares.Lugar", null=True, blank=True, on_delete=models.PROTECT, related_name="reuniones")
    modalidad = models.ForeignKey(Modalidad, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    objetivo = models.TextField(blank=True)
    temas = models.TextField("temas tratados", blank=True)
    acuerdos = models.TextField(blank=True)
    actividad = models.ForeignKey("actividades.Actividad", null=True, blank=True, on_delete=models.PROTECT, related_name="reuniones")
    proyecto = models.ForeignKey("proyectos.Proyecto", null=True, blank=True, on_delete=models.PROTECT, related_name="reuniones")
    creado_por = _creado_por()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-hora_inicio"]
        verbose_name = "reunión"
        verbose_name_plural = "reuniones"

    def __str__(self):
        return f"{self.titulo} ({self.fecha:%d-%m-%Y})"

    def get_absolute_url(self):
        return reverse("coordinacion:reunion_ficha", args=[self.pk])

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de término debe ser posterior a la de inicio."})


class ReunionAsistente(models.Model):
    reunion = models.ForeignKey(Reunion, on_delete=models.PROTECT, related_name="asistentes")
    persona = models.ForeignKey("personas.Persona", on_delete=models.PROTECT, related_name="reuniones")
    asistio = models.BooleanField("asistió", null=True, blank=True)
    observaciones = models.CharField(max_length=200, blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "asistente de reunión"
        verbose_name_plural = "asistentes de reunión"
        constraints = [models.UniqueConstraint(fields=["reunion", "persona"], name="asistente_unico")]

    def __str__(self):
        return str(self.persona)


class TareaQuerySet(models.QuerySet):
    def por_vencer(self, hoy=None, dias=7):
        hoy = hoy or timezone.localdate()
        return self.filter(estado__in=["pendiente", "en_curso"], fecha_limite__isnull=False, fecha_limite__lte=hoy + timedelta(days=dias)).order_by("fecha_limite")


class Tarea(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("en_curso", "En curso"), ("hecha", "Hecha"), ("cancelada", "Cancelada")]
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default="pendiente")
    fecha_limite = models.DateField("fecha límite", null=True, blank=True)
    reunion = models.ForeignKey(Reunion, null=True, blank=True, on_delete=models.PROTECT, related_name="compromisos")
    actividad = models.ForeignKey("actividades.Actividad", null=True, blank=True, on_delete=models.PROTECT, related_name="tareas")
    proyecto = models.ForeignKey("proyectos.Proyecto", null=True, blank=True, on_delete=models.PROTECT, related_name="tareas")
    hecha_en = models.DateTimeField(null=True, blank=True)
    creado_por = _creado_por()
    creado_en = models.DateTimeField(auto_now_add=True)
    objects = TareaQuerySet.as_manager()

    class Meta:
        ordering = ["fecha_limite", "-creado_en"]
        verbose_name = "tarea"
        verbose_name_plural = "tareas"
        permissions = [("exportar_tarea", "Puede exportar tareas")]

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse("coordinacion:tarea_ficha", args=[self.pk])

    @property
    def vencida(self):
        return bool(self.fecha_limite and self.estado in ("pendiente", "en_curso") and self.fecha_limite < timezone.localdate())

    @property
    def responsables(self):
        from apps.personas.models import Persona

        return Persona.objects.filter(tareas_asignadas__tarea=self)


class TareaResponsable(models.Model):
    tarea = models.ForeignKey(Tarea, on_delete=models.PROTECT, related_name="asignaciones")
    persona = models.ForeignKey("personas.Persona", on_delete=models.PROTECT, related_name="tareas_asignadas")
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "responsable de tarea"
        verbose_name_plural = "responsables de tarea"
        constraints = [models.UniqueConstraint(fields=["tarea", "persona"], name="responsable_unico")]

    def __str__(self):
        return str(self.persona)


class Invitacion(models.Model):
    ESTADOS = [("enviada", "Enviada"), ("respondio", "Respondió"), ("aceptada", "Aceptó"), ("rechazada", "Rechazó"), ("sin_respuesta", "Sin respuesta")]
    persona = models.ForeignKey("personas.Persona", on_delete=models.PROTECT, related_name="invitaciones")
    actividad = models.ForeignKey("actividades.Actividad", on_delete=models.PROTECT, related_name="invitaciones")
    rol = models.ForeignKey(RolParticipacion, on_delete=models.PROTECT, related_name="+", verbose_name="rol propuesto")
    fecha = models.DateField(default=timezone.localdate)
    estado = models.CharField(max_length=14, choices=ESTADOS, default="enviada")
    respuesta = models.TextField(blank=True)
    fecha_respuesta = models.DateField(null=True, blank=True)
    creado_por = _creado_por()

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "invitación"
        verbose_name_plural = "invitaciones"

    def __str__(self):
        return f"{self.persona} → {self.actividad}"

    def get_absolute_url(self):
        return reverse("coordinacion:invitacion_ficha", args=[self.pk])


class Colaboracion(models.Model):
    """Solicitud de apoyo a una organización (IN-05)."""

    ESTADOS = [("enviada", "Enviada"), ("respondio", "Respondió"), ("aceptada", "Aceptó"), ("rechazada", "Rechazó"), ("sin_respuesta", "Sin respuesta"), ("cumplida", "Cumplida")]
    organizacion = models.ForeignKey("organizaciones.Organizacion", on_delete=models.PROTECT, related_name="colaboraciones", verbose_name="organización")
    actividad = models.ForeignKey("actividades.Actividad", on_delete=models.PROTECT, related_name="colaboraciones")
    tipo_apoyo = models.ForeignKey(TipoIntervencion, on_delete=models.PROTECT, related_name="+", verbose_name="tipo de apoyo")
    estado = models.CharField(max_length=14, choices=ESTADOS, default="enviada")
    resultado = models.TextField(blank=True)
    observaciones = models.CharField(max_length=250, blank=True)
    creado_por = _creado_por()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "solicitud de apoyo"
        verbose_name_plural = "solicitudes de apoyo"

    def __str__(self):
        return f"{self.organizacion} · {self.tipo_apoyo}"

    def get_absolute_url(self):
        return reverse("coordinacion:colaboracion_ficha", args=[self.pk])

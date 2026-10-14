"""Tabla de solicitudes: origen, canal, fecha, motivo, estado, contacto opcional y la actividad o el proyecto
en que se convirtió (puede quedar sin ninguno). Sabe cuántos días lleva abierta."""
from django.conf import settings
from django.db import models
from django.db.models import Exists, OuterRef
from django.urls import reverse
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.nucleo.models import Canal, EstadoSolicitud


class SolicitudQuerySet(models.QuerySet):
    def sin_respuesta(self):
        """Pendientes que nadie ha contactado todavía (sin ninguna interacción registrada)."""
        from apps.coordinacion.models import Interaccion

        return self.filter(estado__codigo="pendiente").annotate(_hay=Exists(Interaccion.objects.filter(solicitud=OuterRef("pk")))).filter(_hay=False).order_by("fecha")


class Solicitud(models.Model):
    ORIGENES = [("solicitud_externa", "Solicitud externa"), ("busqueda_activa", "Búsqueda activa (oportunidad)"), ("campana", "Campaña temática")]
    origen = models.CharField(max_length=20, choices=ORIGENES, default="solicitud_externa")
    canal = models.ForeignKey(Canal, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="canal de contacto")
    fecha = models.DateField(default=timezone.localdate)
    persona = models.ForeignKey("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="solicitudes", verbose_name="persona de contacto")
    organizacion = models.ForeignKey("organizaciones.Organizacion", null=True, blank=True, on_delete=models.PROTECT, related_name="solicitudes", verbose_name="organización")
    motivo = models.CharField(max_length=250, blank=True, help_text="Qué se necesita o qué oportunidad apareció.")
    descripcion = models.TextField("descripción", blank=True)
    estado = models.ForeignKey(EstadoSolicitud, on_delete=models.PROTECT, related_name="+")
    observaciones = models.TextField(blank=True)
    proyecto = models.ForeignKey("proyectos.Proyecto", null=True, blank=True, on_delete=models.PROTECT, related_name="solicitudes")
    actividad = models.OneToOneField("actividades.Actividad", null=True, blank=True, on_delete=models.PROTECT, related_name="solicitud")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()
    objects = SolicitudQuerySet.as_manager()

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "solicitud"
        verbose_name_plural = "solicitudes"
        permissions = [("exportar_solicitud", "Puede exportar solicitudes")]

    def __str__(self):
        return self.titulo

    @property
    def titulo(self):
        return (self.motivo[:70] if self.motivo else f"Solicitud #{self.pk}")

    def get_absolute_url(self):
        return reverse("solicitudes:ficha", args=[self.pk])

    @property
    def dias_abierta(self):
        """SO-E6: días desde la fecha de la solicitud, mientras siga abierta."""
        if self.estado.codigo in ("pendiente", "en_seguimiento"):
            return (timezone.localdate() - self.fecha).days
        return None

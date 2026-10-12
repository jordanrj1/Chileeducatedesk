from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.nucleo.models import RolParticipacion, TipoIntervencion


class Proyecto(models.Model):
    """Contexto general de una iniciativa: reúne actividades, equipo, organizaciones, documentos y resultados."""

    ESTADOS = [("preparacion", "En preparación"), ("postulado", "Postulado"), ("ejecucion", "En ejecución"), ("finalizado", "Finalizado"), ("suspendido", "Suspendido"), ("cancelado", "Cancelado")]
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    objetivo_general = models.TextField(blank=True)
    objetivos_especificos = models.TextField("objetivos específicos", blank=True)
    diagnostico = models.TextField("diagnóstico", blank=True)
    poblacion_objetivo = models.TextField("población objetivo", blank=True)
    zona = models.CharField(max_length=200, blank=True, help_text="Comuna, sector o territorio donde se desarrolla.")
    fecha_inicio = models.DateField("inicio", null=True, blank=True)
    fecha_termino = models.DateField("término", null=True, blank=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default="preparacion")
    responsable = models.ForeignKey("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="proyectos_a_cargo")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "proyecto"
        verbose_name_plural = "proyectos"
        permissions = [("exportar_proyecto", "Puede exportar proyectos")]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("proyectos:ficha", args=[self.pk])

    def clean(self):
        if self.fecha_inicio and self.fecha_termino and self.fecha_termino < self.fecha_inicio:
            raise ValidationError({"fecha_termino": "El término no puede ser anterior al inicio."})


class ProyectoPersona(models.Model):
    TIPOS = [("equipo", "Equipo"), ("beneficiario", "Beneficiario")]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name="personas")
    persona = models.ForeignKey("personas.Persona", on_delete=models.PROTECT, related_name="proyectos")
    tipo = models.CharField(max_length=12, choices=TIPOS, default="equipo")
    rol = models.ForeignKey(RolParticipacion, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    es_responsable = models.BooleanField("responsable", default=False)
    desde = models.DateField(null=True, blank=True)
    hasta = models.DateField(null=True, blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "persona del proyecto"
        verbose_name_plural = "personas del proyecto"
        constraints = [models.UniqueConstraint(fields=["proyecto", "persona", "tipo"], name="proyecto_persona_unica")]

    def __str__(self):
        return f"{self.persona} · {self.proyecto}"


class ProyectoOrganizacion(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name="organizaciones")
    organizacion = models.ForeignKey("organizaciones.Organizacion", on_delete=models.PROTECT, related_name="proyectos")
    tipo_intervencion = models.ForeignKey(TipoIntervencion, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="tipo de intervención")
    contacto = models.ForeignKey("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="persona de contacto")
    observaciones = models.CharField(max_length=250, blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "organización del proyecto"
        verbose_name_plural = "organizaciones del proyecto"
        constraints = [models.UniqueConstraint(fields=["proyecto", "organizacion", "tipo_intervencion"], name="proyecto_org_unica")]

    def __str__(self):
        return f"{self.organizacion} · {self.proyecto}"


class Postulacion(models.Model):
    ESTADOS = [("borrador", "Borrador"), ("enviada", "Enviada"), ("adjudicada", "Adjudicada"), ("rechazada", "Rechazada")]
    proyecto = models.ForeignKey(Proyecto, on_delete=models.PROTECT, related_name="postulaciones")
    fondo = models.CharField("fondo o convocatoria", max_length=200)
    fecha = models.DateField("fecha de postulación", null=True, blank=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default="borrador")
    resultado = models.CharField(max_length=250, blank=True)
    observaciones = models.TextField(blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "postulación"
        verbose_name_plural = "postulaciones"

    def __str__(self):
        return f"{self.fondo} ({self.get_estado_display()})"

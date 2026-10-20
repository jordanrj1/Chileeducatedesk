"""Tablas de organizaciones: Organizacion (nombre, tipo, identificadores, dirección, si es la Fundación,
comuna si es municipalidad) y Carrera (solo en instituciones educativas). Nunca se borran: se desactivan."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.nucleo.models import EstadoRegistro, NaturalezaJuridica, TipoOrganizacion
from apps.nucleo.utilidades import formatear_rut


class Organizacion(models.Model):
    nombre = models.CharField(max_length=200)
    tipo = models.ForeignKey(TipoOrganizacion, on_delete=models.PROTECT, related_name="organizaciones")
    rut_numero = models.PositiveIntegerField("RUT (número)", null=True, blank=True)
    rut_dv = models.CharField("RUT (dígito)", max_length=1, null=True, blank=True)
    otro_identificador = models.CharField("otro identificador", max_length=60, blank=True)
    estado_registro = models.ForeignKey(EstadoRegistro, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="estado")
    descripcion = models.TextField("descripción", blank=True)
    sitio_web = models.URLField(blank=True)
    direccion = models.ForeignKey("territorio.Direccion", null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="dirección")
    comuna_municipal = models.OneToOneField(
        "territorio.Comuna", null=True, blank=True, on_delete=models.PROTECT, related_name="municipalidad", verbose_name="comuna (si es municipalidad)"
    )
    es_propia = models.BooleanField("es la Fundación", default=False)
    # Datos legales, cuando corresponda (certificados de directorio/vigencia). La naturaleza jurídica se elige del catálogo;
    # el texto escrito antes se conserva como «texto anterior» hasta que se revise.
    naturaleza = models.ForeignKey(NaturalezaJuridica, null=True, blank=True, on_delete=models.PROTECT, related_name="+",
                                   verbose_name="naturaleza jurídica")
    naturaleza_juridica = models.CharField("naturaleza jurídica (texto anterior)", max_length=120, blank=True)
    domicilio_legal = models.CharField(max_length=200, blank=True)
    vigencia_desde = models.DateField("vigencia desde", null=True, blank=True)
    vigencia_hasta = models.DateField("vigencia hasta", null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["nombre"]
        verbose_name = "organización"
        verbose_name_plural = "organizaciones"
        permissions = [("exportar_organizacion", "Puede exportar organizaciones"), ("fusionar_organizacion", "Puede fusionar organizaciones duplicadas")]
        constraints = [
            models.UniqueConstraint(fields=["rut_numero"], condition=models.Q(rut_numero__isnull=False), name="organizacion_rut_unico"),
            models.UniqueConstraint(fields=["es_propia"], condition=models.Q(es_propia=True), name="una_sola_organizacion_propia"),
            models.CheckConstraint(
                condition=models.Q(rut_numero__isnull=True) | models.Q(rut_dv__isnull=False), name="organizacion_rut_con_dv"
            ),
        ]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("organizaciones:ficha", args=[self.pk])

    @property
    def rut(self):
        return formatear_rut(self.rut_numero, self.rut_dv)

    @property
    def es_educativa(self):
        return self.tipo.codigo == "institucion_educativa"

    def clean(self):
        if self.comuna_municipal_id and self.tipo_id and self.tipo.codigo != "municipalidad":
            raise ValidationError({"comuna_municipal": "Solo una municipalidad se relaciona con una comuna."})


class Carrera(models.Model):
    organizacion = models.ForeignKey(Organizacion, on_delete=models.PROTECT, related_name="carreras", verbose_name="institución")
    nombre = models.CharField(max_length=200)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "carrera"
        verbose_name_plural = "carreras"
        constraints = [models.UniqueConstraint(fields=["organizacion", "nombre"], name="carrera_unica_por_institucion")]

    def __str__(self):
        return f"{self.nombre} ({self.organizacion})"

    def clean(self):
        if self.organizacion_id and not self.organizacion.es_educativa:
            raise ValidationError({"organizacion": "Las carreras solo se asocian a instituciones educativas."})

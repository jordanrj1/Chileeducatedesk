"""Tabla de lugares: nombre, tipo, dirección, capacidad, condiciones y organización dueña.
La capacidad se usa al revisar si se puede confirmar una actividad."""
from django.conf import settings
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.nucleo.models import TipoLugar


class Lugar(models.Model):
    nombre = models.CharField(max_length=200)
    tipo = models.ForeignKey(TipoLugar, on_delete=models.PROTECT, related_name="lugares")
    direccion = models.ForeignKey("territorio.Direccion", on_delete=models.PROTECT, related_name="+", verbose_name="dirección")
    capacidad = models.PositiveIntegerField(null=True, blank=True, help_text="Cantidad máxima de personas.")
    condiciones = models.TextField(blank=True, help_text="Accesibilidad, equipamiento, restricciones, horarios.")
    organizacion_propietaria = models.ForeignKey(
        "organizaciones.Organizacion", null=True, blank=True, on_delete=models.PROTECT, related_name="lugares", verbose_name="organización propietaria"
    )
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["nombre"]
        verbose_name = "lugar"
        verbose_name_plural = "lugares"
        permissions = [("exportar_lugar", "Puede exportar lugares")]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("lugares:ficha", args=[self.pk])

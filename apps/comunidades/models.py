"""Comunidad (F22): grupo de personas que viven en un sector o comparten un espacio, a quienes van dirigidas las actividades."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords

from apps.nucleo.models import AreaTematica, TramoEtario


class Comunidad(models.Model):
    TIPOS = [
        ("vecinal", "Vecinal o barrial"), ("escolar", "Comunidad educativa"), ("personas_mayores", "Personas mayores"),
        ("juventud", "Infancia y juventud"), ("indigena", "Comunidad indígena"), ("agrupacion", "Agrupación o grupo de interés"), ("otra", "Otra"),
    ]
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=16, choices=TIPOS, default="vecinal")
    descripcion = models.TextField("descripción", blank=True)
    comuna = models.ForeignKey("territorio.Comuna", on_delete=models.PROTECT, related_name="comunidades")
    sector = models.ForeignKey("territorio.Sector", null=True, blank=True, on_delete=models.PROTECT, related_name="comunidades",
                               help_text="Sector, villa o población, si corresponde. Debe ser de la comuna.")
    organizacion = models.ForeignKey("organizaciones.Organizacion", null=True, blank=True, on_delete=models.PROTECT, related_name="comunidades",
                                     verbose_name="organización que la representa", help_text="Por ejemplo, la junta de vecinos o el establecimiento.")
    referente = models.ForeignKey("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="comunidades_referente",
                                  verbose_name="referente o dirigente principal")
    poblacion_estimada = models.PositiveIntegerField("población estimada (personas)", null=True, blank=True)
    rango_etario = models.CharField("rango etario predominante", max_length=100, blank=True, help_text="Ej.: familias con niños, personas mayores, jóvenes de 15 a 29 años.")  # texto anterior a los tramos
    tramos_etarios = models.ManyToManyField(TramoEtario, blank=True, related_name="comunidades", verbose_name="edades principales")
    areas_interes = models.ManyToManyField(AreaTematica, blank=True, related_name="+", verbose_name="áreas de interés")
    diagnostico = models.TextField("diagnóstico y necesidades", blank=True, help_text="Qué necesita esta comunidad, según lo levantado en terreno.")
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["nombre"]
        verbose_name = "comunidad"
        verbose_name_plural = "comunidades"
        permissions = [("exportar_comunidad", "Puede exportar comunidades")]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("comunidades:ficha", args=[self.pk])

    @property
    def territorio(self):
        return f"{self.sector}, {self.comuna}" if self.sector_id else str(self.comuna)

    def clean(self):
        if self.sector_id and self.comuna_id and self.sector.comuna_id != self.comuna_id:
            raise ValidationError({"sector": "El sector debe pertenecer a la comuna elegida."})


class ComunidadMiembro(models.Model):
    """Padrón de la comunidad. Las membresías se cierran con fecha; no se borran."""

    ROLES = [("integrante", "Integrante"), ("dirigente", "Dirigente/a"), ("referente", "Referente"), ("vocero", "Vocero/a")]
    comunidad = models.ForeignKey(Comunidad, on_delete=models.PROTECT, related_name="miembros")
    persona = models.ForeignKey("personas.Persona", on_delete=models.PROTECT, related_name="comunidades")
    rol = models.CharField(max_length=12, choices=ROLES, default="integrante")
    desde = models.DateField(null=True, blank=True)
    hasta = models.DateField(null=True, blank=True)
    observaciones = models.CharField(max_length=250, blank=True)
    vigente = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-vigente", "rol", "persona__apellido_paterno", "persona__nombres"]
        verbose_name = "integrante de comunidad"
        verbose_name_plural = "integrantes de comunidad"
        constraints = [models.UniqueConstraint(fields=["comunidad", "persona"], name="miembro_comunidad_unico")]

    def __str__(self):
        return f"{self.persona} · {self.get_rol_display()} · {self.comunidad}"

    def clean(self):
        if self.desde and self.hasta and self.hasta < self.desde:
            raise ValidationError({"hasta": "La fecha de término no puede ser anterior a la de inicio."})

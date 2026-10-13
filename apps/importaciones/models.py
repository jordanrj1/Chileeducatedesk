import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

EXT = {".csv", ".txt", ".xlsx"}


def validar_listado(archivo):
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in EXT:
        raise ValidationError(f"Formato no admitido ({ext or 'sin extensión'}). Usa CSV, TXT (separado por tabulaciones) o XLSX.")
    if archivo.size > 10 * 1024 * 1024:
        raise ValidationError("El archivo supera 10 MB.")


def ruta_lote(instancia, nombre):
    return f"importaciones/{timezone.now():%Y/%m}/{os.path.basename(nombre)}"


class Lote(models.Model):
    TIPOS = [
        ("listado_actividad", "Listado de participantes de una actividad"),
        ("personas", "Personas (banco histórico)"),
        ("organizaciones", "Organizaciones"),
        ("lugares", "Lugares"),
    ]
    ESTADOS = [("previa", "En revisión"), ("confirmado", "Confirmado"), ("revertido", "Revertido"), ("descartado", "Descartado")]
    tipo = models.CharField(max_length=20, choices=TIPOS)
    archivo = models.FileField(upload_to=ruta_lote, validators=[validar_listado], null=True, blank=True)
    nombre_archivo = models.CharField("archivo / origen", max_length=200, blank=True)
    fuente = models.CharField("fuente de los datos", max_length=250, blank=True, help_text="Ej.: planilla enviada por la institución, minuta, carta.")
    estado = models.CharField(max_length=10, choices=ESTADOS, default="previa")
    actividad = models.ForeignKey("actividades.Actividad", null=True, blank=True, on_delete=models.PROTECT, related_name="lotes")
    rol = models.ForeignKey("nucleo.RolParticipacion", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    filas = models.JSONField(default=list)
    resumen = models.JSONField(default=dict)
    encabezados = models.JSONField(default=list)
    crudas = models.JSONField(default=list)
    mapeo = models.JSONField(default=list)
    huella = models.CharField(max_length=64, blank=True, db_index=True)
    crear_carreras = models.BooleanField("crear las carreras que no existan", default=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    confirmado_en = models.DateTimeField(null=True, blank=True)
    revertido_en = models.DateTimeField(null=True, blank=True)
    revertido_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "lote de importación"
        verbose_name_plural = "lotes de importación"
        permissions = [
            ("importar_listado", "Puede importar listados y datos históricos"),
            ("revertir_lote", "Puede revertir un lote importado"),
        ]

    def __str__(self):
        return f"Lote {self.pk} · {self.get_tipo_display()}"

    def get_absolute_url(self):
        return reverse("importaciones:ficha", args=[self.pk])


class LoteItem(models.Model):
    """Qué creó (o a qué se vinculó) un lote. Permite revertirlo."""

    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name="items")
    tipo_objeto = models.CharField(max_length=20)  # persona, organizacion, lugar, participacion, contacto, formacion, direccion
    objeto_id = models.PositiveBigIntegerField()
    creado = models.BooleanField(default=True)
    fila = models.PositiveIntegerField(default=0)
    antes = models.JSONField(null=True, blank=True)  # valores previos cuando el lote actualizó un registro existente

    class Meta:
        ordering = ["id"]

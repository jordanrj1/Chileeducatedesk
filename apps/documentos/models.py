import os

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.nucleo.models import TipoDocumento

EXTENSIONES_PERMITIDAS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".mp4", ".mp3", ".odt", ".ods"}
TAMANO_MAXIMO_MB = 25


def ruta_documento(instancia, nombre):
    return f"documentos/{timezone.now():%Y/%m}/{os.path.basename(nombre)}"


def validar_archivo(archivo):
    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise ValidationError(f"Tipo de archivo no permitido ({ext or 'sin extensión'}). Permitidos: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}.")
    if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise ValidationError(f"El archivo supera el máximo de {TAMANO_MAXIMO_MB} MB.")
    if archivo.size == 0:
        raise ValidationError("El archivo está vacío.")


class Documento(models.Model):
    """Evidencia. Los documentos históricos (PDF, Word) no se convierten en tablas: se extrae el dato y se vincula el original."""

    nombre = models.CharField(max_length=200)
    archivo = models.FileField(upload_to=ruta_documento, validators=[validar_archivo])
    tipo = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT, related_name="documentos")
    fecha = models.DateField(default=timezone.localdate)
    descripcion = models.TextField("descripción", blank=True)
    actividad = models.ForeignKey("actividades.Actividad", null=True, blank=True, on_delete=models.PROTECT, related_name="documentos")
    proyecto = models.ForeignKey("proyectos.Proyecto", null=True, blank=True, on_delete=models.PROTECT, related_name="documentos")
    persona = models.ForeignKey("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="documentos")
    organizacion = models.ForeignKey("organizaciones.Organizacion", null=True, blank=True, on_delete=models.PROTECT, related_name="documentos", verbose_name="organización")
    solicitud = models.ForeignKey("solicitudes.Solicitud", null=True, blank=True, on_delete=models.PROTECT, related_name="documentos")
    restringido = models.BooleanField(default=False, help_text="Solo lo ven quienes tienen permiso para documentos restringidos.")
    folio = models.CharField(max_length=60, blank=True)
    emisor = models.CharField(max_length=150, blank=True)
    fecha_emision = models.DateField("fecha de emisión", null=True, blank=True)
    fecha_vencimiento = models.DateField("vence el", null=True, blank=True, help_text="Para certificados y documentos con vigencia (DO-06).")
    activo = models.BooleanField(default=True)
    huella = models.CharField("huella del archivo (SHA-256)", max_length=64, blank=True, db_index=True, editable=False)
    reemplaza = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="reemplazado_por", verbose_name="versión anterior")
    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    subido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "documento"
        verbose_name_plural = "documentos"
        permissions = [
            ("ver_restringido", "Puede ver documentos restringidos"),
            ("exportar_documento", "Puede exportar el listado de documentos"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(actividad__isnull=False) | Q(proyecto__isnull=False) | Q(persona__isnull=False) | Q(organizacion__isnull=False) | Q(solicitud__isnull=False),
                name="documento_con_asociacion",
            )
        ]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("documentos:ficha", args=[self.pk])

    @staticmethod
    def calcular_huella(archivo):
        """SHA-256 del contenido: detecta el mismo archivo aunque tenga otro nombre (DO-E3)."""
        import hashlib

        h = hashlib.sha256()
        pos = archivo.tell() if hasattr(archivo, "tell") else 0
        archivo.seek(0)
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            h.update(bloque)
        archivo.seek(pos)
        return h.hexdigest()

    def save(self, *args, **kwargs):
        if not self.huella and self.archivo:
            try:
                self.huella = self.calcular_huella(self.archivo)
            except (FileNotFoundError, ValueError, OSError):
                pass
        super().save(*args, **kwargs)

    @property
    def archivo_existe(self):
        try:
            return bool(self.archivo) and self.archivo.storage.exists(self.archivo.name)
        except Exception:
            return False

    @property
    def vencido(self):
        return bool(self.fecha_vencimiento and self.fecha_vencimiento < timezone.localdate())

    @property
    def visible_en_navegador(self):
        return self.extension in ("pdf", "png", "jpg", "jpeg", "txt")

    @property
    def extension(self):
        return os.path.splitext(self.archivo.name)[1].lower().lstrip(".")

    def clean(self):
        if not any([self.actividad_id, self.proyecto_id, self.persona_id, self.organizacion_id, self.solicitud_id]):
            raise ValidationError("El documento debe asociarse a una actividad, proyecto, persona, organización o solicitud.")


class OrigenDato(models.Model):
    """Fuente de un dato (F14): de dónde salió, cuándo, quién lo registró y si está verificado."""

    FUENTES = [
        ("formulario", "Ingreso en el sistema"), ("documento", "Documento"), ("importacion", "Importación de listado"),
        ("llamado", "Llamado"), ("correo", "Correo"), ("reunion", "Reunión"), ("otro", "Otra"),
    ]
    VERIFICACION = [("sin_verificar", "Sin verificar"), ("por_revisar", "Por revisar"), ("verificado", "Verificado")]
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="+")
    object_id = models.PositiveBigIntegerField()
    objeto = GenericForeignKey("content_type", "object_id")
    fuente = models.CharField(max_length=14, choices=FUENTES, default="formulario")
    documento = models.ForeignKey(Documento, null=True, blank=True, on_delete=models.PROTECT, related_name="origenes", verbose_name="documento de origen")
    lote = models.PositiveBigIntegerField("lote de importación", null=True, blank=True)
    detalle = models.CharField(max_length=250, blank=True)
    fecha = models.DateField(default=timezone.localdate)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    estado_verificacion = models.CharField("verificación", max_length=14, choices=VERIFICACION, default="sin_verificar")

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "origen del dato"
        verbose_name_plural = "orígenes de datos"
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return f"{self.get_fuente_display()} · {self.fecha:%d-%m-%Y}"

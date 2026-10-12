from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from simple_history.models import HistoricalRecords


class ItemPresupuesto(models.Model):
    CATEGORIAS = [("recursos_humanos", "Recursos humanos"), ("operacional", "Gastos operacionales"), ("materiales", "Materiales"), ("difusion", "Difusión"), ("otros", "Otros")]
    proyecto = models.ForeignKey("proyectos.Proyecto", on_delete=models.PROTECT, related_name="items_presupuesto")
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default="otros")
    concepto = models.CharField(max_length=200)
    monto_estimado = models.PositiveBigIntegerField("monto estimado (CLP)")
    vigente = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["categoria", "concepto"]
        verbose_name = "ítem de presupuesto"
        verbose_name_plural = "ítems de presupuesto"

    def __str__(self):
        return f"{self.concepto} (${self.monto_estimado:,})".replace(",", ".")


class Movimiento(models.Model):
    """Gasto, aporte o donación. Nunca se borra: se anula con motivo. No registrar cuentas bancarias ni datos reales de prueba."""

    TIPOS = [("gasto", "Gasto"), ("aporte", "Aporte"), ("donacion", "Donación")]
    proyecto = models.ForeignKey("proyectos.Proyecto", on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=10, choices=TIPOS)
    monto = models.PositiveBigIntegerField("monto (CLP)")
    fecha = models.DateField(default=timezone.localdate)
    persona = models.ForeignKey("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="movimientos")
    organizacion = models.ForeignKey("organizaciones.Organizacion", null=True, blank=True, on_delete=models.PROTECT, related_name="movimientos", verbose_name="organización")
    concepto = models.CharField(max_length=250)
    documento = models.ForeignKey("documentos.Documento", null=True, blank=True, on_delete=models.PROTECT, related_name="movimientos", verbose_name="documento de respaldo")
    anulado = models.BooleanField(default=False)
    motivo_anulacion = models.CharField(max_length=250, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "movimiento"
        verbose_name_plural = "movimientos"
        permissions = [("exportar_movimiento", "Puede exportar movimientos")]
        constraints = [models.CheckConstraint(condition=Q(monto__gt=0), name="movimiento_monto_positivo")]

    def __str__(self):
        return f"{self.get_tipo_display()} ${self.monto:,} · {self.concepto}".replace(",", ".")

    def get_absolute_url(self):
        return reverse("finanzas:ficha", args=[self.pk])

    def clean(self):
        if self.tipo in ("aporte", "donacion") and not (self.persona_id or self.organizacion_id):
            raise ValidationError("Indica quién aportó o donó (persona u organización).")

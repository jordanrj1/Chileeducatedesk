"""Tablas de finanzas: ItemPresupuesto (monto estimado por proyecto) y Movimiento (gasto, aporte o donación, con monto
en pesos). Un movimiento no se borra: se anula. Los gastos de una actividad o de una de sus jornadas (F28 B) son visibles
siempre; los aportes y donaciones siguen en la segunda fase (oculta). Registrado -> revisado -> anulado; lo revisado no se edita."""
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
    REGISTRADO, REVISADO, ANULADO = "registrado", "revisado", "anulado"
    ESTADOS = [(REGISTRADO, "Registrado"), (REVISADO, "Revisado"), (ANULADO, "Anulado")]
    # F28 B: el gasto de una tarea fija el proyecto de la tarea; una actividad suelta (sin proyecto) también puede tener gastos
    proyecto = models.ForeignKey("proyectos.Proyecto", null=True, blank=True, on_delete=models.PROTECT, related_name="movimientos")
    actividad = models.ForeignKey("actividades.Actividad", null=True, blank=True, on_delete=models.PROTECT, related_name="movimientos")
    sesion = models.ForeignKey("actividades.SesionActividad", null=True, blank=True, on_delete=models.PROTECT, related_name="gastos",
                               verbose_name="jornada", help_text="Vacío: el gasto es de toda la tarea (p. ej. un traslado semanal).")
    categoria = models.ForeignKey("nucleo.CategoriaGasto", null=True, blank=True, on_delete=models.PROTECT, related_name="movimientos", verbose_name="categoría")
    pagado_por = models.ForeignKey("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="gastos_pagados", verbose_name="pagado por",
                                   help_text="Quién puso el dinero, si no fue la Fundación. El reembolso queda fuera de esta etapa [V].")
    proveedor = models.CharField(max_length=150, blank=True, help_text="Dónde o a quién se compró. Si es una organización registrada, elígela abajo.")
    estado = models.CharField(max_length=10, choices=ESTADOS, default=REGISTRADO)
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    revisado_en = models.DateTimeField(null=True, blank=True)
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
        constraints = [
            models.CheckConstraint(condition=Q(monto__gt=0), name="movimiento_monto_positivo"),
            models.CheckConstraint(condition=Q(proyecto__isnull=False) | Q(actividad__isnull=False), name="movimiento_con_proyecto_o_actividad"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} ${self.monto:,} · {self.concepto}".replace(",", ".")

    def get_absolute_url(self):
        return reverse("finanzas:ficha", args=[self.pk])

    @property
    def editable(self):
        """Solo un gasto «registrado» se edita; uno revisado se anula con motivo y se registra de nuevo."""
        return self.estado == self.REGISTRADO and not self.anulado

    @property
    def sin_comprobante(self):
        return self.documento_id is None

    def clean(self):
        if self.tipo in ("aporte", "donacion"):
            if not (self.persona_id or self.organizacion_id):
                raise ValidationError("Indica quién aportó o donó (persona u organización).")
            if not self.proyecto_id:
                raise ValidationError("Un aporte o una donación se registra en un proyecto.")
        if self.sesion_id:
            if not self.actividad_id:
                raise ValidationError({"sesion": "La jornada pertenece a una tarea: indica cuál."})
            if self.sesion.actividad_id != self.actividad_id:
                raise ValidationError({"sesion": "La jornada no pertenece a esta tarea."})
        if self.actividad_id and self.actividad.proyecto_id:
            self.proyecto_id = self.actividad.proyecto_id  # la tarea fija el proyecto del gasto
        if not (self.proyecto_id or self.actividad_id):
            raise ValidationError("El gasto va en una actividad o en un proyecto.")

    def save(self, *args, **kwargs):
        if self.actividad_id and self.actividad.proyecto_id:
            self.proyecto_id = self.actividad.proyecto_id
        if self.anulado or self.estado == self.ANULADO:  # `anulado` y `estado` no se contradicen
            self.anulado, self.estado = True, self.ANULADO
        super().save(*args, **kwargs)

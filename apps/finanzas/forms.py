"""Formularios de finanzas: ítems de presupuesto de un proyecto, movimientos de dinero (2.ª fase, oculta) y el gasto de una
actividad o de una de sus jornadas, con su comprobante (F28 B, visible siempre)."""
from django import forms
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.documentos.models import Documento
from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import CategoriaGasto
from apps.organizaciones.selector import ORGANIZACIONES
from apps.personas.selector import PERSONAS
from apps.proyectos.models import Proyecto

from . import comprobante
from .models import ItemPresupuesto, Movimiento


class ItemForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ItemPresupuesto
        fields = ["categoria", "concepto", "monto_estimado", "vigente"]
        labels = {"categoria": "Categoría"}
        help_texts = {"concepto": "Ej.: materiales para el taller de huertos.", "monto_estimado": "En pesos, sin puntos. Ej.: 150000."}


class MovimientoForm(BootstrapMixin, forms.ModelForm):
    persona = SelectorField(PERSONAS, required=False)
    organizacion = SelectorField(ORGANIZACIONES, required=False, label="Organización")

    class Meta:
        model = Movimiento
        fields = ["proyecto", "tipo", "monto", "fecha", "persona", "organizacion", "concepto", "documento"]
        help_texts = {"monto": "En pesos, sin puntos. Ej.: 45000.", "concepto": "Ej.: compra de semillas y tierra de hoja."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["proyecto"].queryset = Proyecto.objects.all()
        self.fields["documento"].queryset = Documento.objects.filter(activo=True)
        self.fields["documento"].help_text = "Respaldo documental. Los documentos financieros deben subirse como restringidos."

    def clean_monto(self):
        m = self.cleaned_data["monto"]
        if m <= 0:
            raise forms.ValidationError("El monto debe ser mayor que cero.")
        return m

    def clean(self):
        datos = super().clean()
        if self.instance.pk and not self.instance.editable:
            raise forms.ValidationError("Un movimiento revisado o anulado no se edita: anúlalo con un motivo y registra otro.")
        return datos


class GastoForm(BootstrapMixin, forms.ModelForm):
    """Gasto de una actividad o tarea (F28 B). La jornada es opcional: sin ella, el gasto es de toda la tarea. El proyecto lo
    fija la tarea. El comprobante se sube aquí (queda como documento restringido) o se elige un documento que ya existe."""

    sesion = forms.ModelChoiceField(queryset=None, required=False, label="Jornada", empty_label="Toda la tarea (sin jornada)",
                                    help_text="Elige el día del gasto, o déjalo en «Toda la tarea» si cubre varios días (p. ej. un traslado semanal).")
    monto = forms.IntegerField(min_value=1, label="Monto (CLP)", help_text="En pesos, sin puntos. Ej.: 45000.",
                               widget=forms.NumberInput(attrs={"inputmode": "numeric", "min": 1}))
    categoria = forms.ModelChoiceField(queryset=CategoriaGasto.objects.none(), label="Categoría", empty_label="Elige una categoría")
    pagado_por = SelectorField(PERSONAS, required=False, label="Pagado por", help_text="Solo si lo pagó una persona de su bolsillo. El reembolso queda fuera de esta etapa [V].")
    organizacion = SelectorField(ORGANIZACIONES, required=False, label="Organización proveedora", help_text="Si el proveedor es una organización registrada.")
    comprobante = forms.FileField(required=False, label="Foto o PDF del comprobante", help_text=comprobante.AYUDA,
                                  widget=forms.FileInput(attrs={"accept": comprobante.ACCEPT, "capture": "environment"}))
    documento = forms.ModelChoiceField(queryset=Documento.objects.none(), required=False, label="O elige un documento que ya existe",
                                       help_text="Si el comprobante ya está subido en esta tarea o su proyecto.")

    class Meta:
        model = Movimiento
        fields = ["sesion", "categoria", "monto", "fecha", "concepto", "proveedor", "organizacion", "pagado_por", "comprobante", "documento"]
        help_texts = {"concepto": "Ej.: colación para 20 personas.", "fecha": "Cuándo se pagó."}
        widgets = {"proveedor": forms.TextInput(attrs={"placeholder": "Ej.: Panadería La Esquina"})}

    secciones = [
        ("Qué se gastó", "", ["sesion", "categoria", "concepto", "monto", "fecha"]),
        ("A quién y quién pagó", "Todo opcional.", ["proveedor", "organizacion", "pagado_por"]),
        ("Comprobante", "Sin comprobante el gasto se guarda igual y queda marcado «Sin comprobante».", ["comprobante", "documento"]),
    ]

    def __init__(self, *a, actividad, usuario, **kw):
        super().__init__(*a, **kw)
        self.actividad, self.usuario = actividad, usuario
        self.fields["sesion"].queryset = actividad.sesiones.order_by("fecha", "numero")
        self.fields["sesion"].label_from_instance = lambda j: f"Jornada {j.numero}" + (f" · {j.fecha:%d-%m-%Y}" if j.fecha else "")
        self.fields["categoria"].queryset = CategoriaGasto.objects.filter(activo=True)
        self.fields["categoria"].widget.attrs["data-descripciones"] = "1"
        if self.instance.pk and self.instance.categoria_id and not self.instance.categoria.activo:
            self.fields["categoria"].queryset = CategoriaGasto.objects.filter(pk=self.instance.categoria_id) | self.fields["categoria"].queryset
        docs = Documento.objects.filter(activo=True).filter(Q(actividad=actividad) | (Q(proyecto_id=actividad.proyecto_id) if actividad.proyecto_id else Q(pk__in=[])))
        if not usuario.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        self.fields["documento"].queryset = docs.select_related("tipo")
        self.fields["documento"].label_from_instance = lambda d: f"{d.nombre} ({d.fecha:%d-%m-%Y})"
        if not self.is_bound and not self.instance.pk:
            self.fields["fecha"].initial = timezone.localdate()

    def clean_comprobante(self):
        archivo = self.cleaned_data.get("comprobante")
        return comprobante.validar_comprobante(archivo) if archivo else archivo

    def clean(self):
        datos = super().clean()
        if self.instance.pk and not self.instance.editable:
            raise forms.ValidationError("Un gasto revisado o anulado no se edita: anúlalo con un motivo y registra otro.")
        if datos.get("comprobante") and datos.get("documento"):
            self.add_error("documento", "Sube un comprobante nuevo o elige un documento, no los dos.")
        return datos

    def _post_clean(self):
        # el modelo valida con la actividad y el tipo ya puestos (la jornada debe ser de la tarea; la tarea fija el proyecto)
        self.instance.actividad, self.instance.tipo = self.actividad, "gasto"
        super()._post_clean()

    def save(self, commit=True):
        """Guarda el gasto y, si se subió, su comprobante, en una sola transacción."""
        gasto = super().save(commit=False)
        gasto.actividad, gasto.tipo = self.actividad, "gasto"
        if self.cleaned_data.get("documento"):
            gasto.documento = self.cleaned_data["documento"]
        if not gasto.pk:
            gasto.creado_por = self.usuario
        archivo = self.cleaned_data.get("comprobante")
        with transaction.atomic():
            if archivo:
                comprobante.guardar_comprobante(archivo, gasto, self.usuario)
            gasto.save()
            self.save_m2m()
        return gasto

"""Formulario para subir o pegar una planilla y elegir qué se carga (participantes de una actividad,
personas, organizaciones o lugares)."""
from django import forms
from django.urls import reverse_lazy

from apps.actividades.models import Actividad
from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import RolParticipacion

from .models import Lote, validar_listado


class LoteForm(BootstrapMixin, forms.Form):
    tipo = forms.ChoiceField(choices=Lote.TIPOS, label="¿Qué vas a cargar?")
    actividad = SelectorField(Actividad.objects.exclude(estado__codigo__in=["cancelada", "realizada"]), reverse_lazy("actividades:opciones"), required=False, label="Actividad (para listados de participantes)")
    rol = forms.ModelChoiceField(RolParticipacion.objects.filter(activo=True), required=False, label="Rol de las personas del listado")
    archivo = forms.FileField(required=False, validators=[validar_listado], help_text="CSV, TXT con tabulaciones o XLSX. La primera fila son los encabezados.")
    texto = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 6}), label="…o pega aquí las filas (copiadas desde Excel, con encabezados)")
    fuente = forms.CharField(max_length=250, required=False, label="Fuente de los datos", help_text="Ej.: planilla enviada por la institución el 10-10.")

    def clean(self):
        d = super().clean()
        if not d.get("archivo") and not (d.get("texto") or "").strip():
            raise forms.ValidationError("Sube un archivo o pega el contenido.")
        if d.get("tipo") == "listado_actividad":
            if not d.get("actividad"):
                self.add_error("actividad", "Elige la actividad a la que pertenece el listado.")
            if not d.get("rol"):
                self.add_error("rol", "Elige el rol de las personas del listado.")
        return d

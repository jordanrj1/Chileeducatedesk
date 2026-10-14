"""Formularios de organización (tipo, RUT u otro identificador, sitio web, si es la Fundación, comuna si es municipalidad)
y de carrera de una institución educativa."""
from django import forms

from apps.nucleo.formularios import BootstrapMixin
from apps.nucleo.rut import CampoRut

from .models import Carrera, Organizacion


class OrganizacionForm(BootstrapMixin, forms.ModelForm):
    rut = CampoRut(label="RUT")

    class Meta:
        model = Organizacion
        fields = [
            "nombre", "tipo", "rut", "otro_identificador", "estado_registro", "descripcion", "sitio_web", "comuna_municipal",
            "naturaleza_juridica", "domicilio_legal", "vigencia_desde", "vigencia_hasta", "es_propia",
        ]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        from apps.nucleo.models import EstadoRegistro, TipoOrganizacion

        self.fields["tipo"].queryset = TipoOrganizacion.objects.filter(activo=True)
        self.fields["estado_registro"].queryset = EstadoRegistro.objects.filter(activo=True)
        self.fields["estado_registro"].label = "Estado"
        if self.instance.pk and self.instance.rut_numero:
            self.initial["rut"] = self.instance.rut

    def clean_rut(self):
        valor = self.cleaned_data.get("rut")
        if valor and Organizacion.objects.filter(rut_numero=valor[0]).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe una organización con ese RUT.")
        return valor

    def save(self, commit=True):
        obj = super().save(commit=False)
        rut = self.cleaned_data.get("rut")
        obj.rut_numero, obj.rut_dv = (rut if rut else (None, None))
        if commit:
            obj.save()
        return obj


class CarreraForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Carrera
        fields = ["nombre", "activo"]

    def __init__(self, *args, organizacion=None, **kw):
        super().__init__(*args, **kw)
        self.organizacion = organizacion or getattr(self.instance, "organizacion", None)

    def _post_clean(self):
        self.instance.organizacion = self.organizacion
        super()._post_clean()

    def validate_unique(self):
        pass

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if Carrera.objects.filter(organizacion=self.organizacion, nombre__iexact=nombre).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa carrera ya existe en esta institución.")
        return nombre

from django import forms

from apps.nucleo.formularios import BootstrapMixin

from .models import Comuna, Direccion, Sector


class SectorForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Sector
        fields = ["nombre", "tipo", "sector_padre"]

    def __init__(self, *args, comuna=None, **kw):
        super().__init__(*args, **kw)
        self.comuna = comuna or getattr(self.instance, "comuna", None)
        self.fields["sector_padre"].queryset = Sector.objects.filter(comuna=self.comuna) if self.comuna else Sector.objects.none()
        self.fields["sector_padre"].required = False

    def _post_clean(self):
        self.instance.comuna = self.comuna
        super()._post_clean()

    def validate_unique(self):
        pass  # lo cubren las restricciones únicas condicionales; se verifica en clean()

    def clean(self):
        datos = super().clean()
        nombre, padre = datos.get("nombre"), datos.get("sector_padre")
        existe = Sector.objects.filter(comuna=self.comuna, nombre__iexact=nombre, sector_padre=padre).exclude(pk=self.instance.pk)
        if nombre and existe.exists():
            raise forms.ValidationError("Ya existe un sector con ese nombre en este nivel.")
        return datos


class DireccionForm(BootstrapMixin, forms.ModelForm):
    """Dirección reutilizable. El sector se acota a la comuna elegida (también en el servidor)."""

    class Meta:
        model = Direccion
        fields = ["calle", "numero", "block", "depto", "referencia", "comuna", "sector"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.fields["comuna"].queryset = Comuna.objects.select_related("provincia__region")
        comuna_id = self.data.get(self.add_prefix("comuna")) or (self.instance.comuna_id if self.instance.pk else None)
        qs = Sector.objects.none()
        if comuna_id:
            qs = Sector.objects.filter(comuna_id=comuna_id)
        self.fields["sector"].queryset = qs
        self.fields["comuna"].widget.attrs.update(
            {"hx-get": "/territorio/sectores", "hx-target": f"#id_{self.add_prefix('sector')}", "hx-trigger": "change", "hx-include": "this"}
        )

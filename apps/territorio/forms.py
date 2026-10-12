from django import forms

from apps.nucleo.formularios import BootstrapMixin

from .models import Comuna, Direccion, Provincia, Region, Sector, SectorAlias
from .reconocer import mismo_sector


class SectorForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Sector
        fields = ["nombre", "tipo", "sector_padre"]

    def __init__(self, *args, comuna=None, **kw):
        super().__init__(*args, **kw)
        self.comuna = comuna or getattr(self.instance, "comuna", None)
        qs = Sector.objects.filter(comuna=self.comuna) if self.comuna else Sector.objects.none()
        if self.instance.pk:
            qs = qs.exclude(pk__in=self.instance.descendientes_ids())  # no puede quedar dentro de sí mismo
        self.fields["sector_padre"].queryset = qs
        self.fields["sector_padre"].required = False
        self.fields["sector_padre"].label = "Dentro de (opcional)"

    def _post_clean(self):
        self.instance.comuna = self.comuna
        super()._post_clean()

    def validate_unique(self):
        pass  # lo cubren las restricciones únicas condicionales; se verifica en clean()

    def clean(self):
        datos = super().clean()
        nombre, padre = datos.get("nombre"), datos.get("sector_padre")
        if nombre:
            igual = mismo_sector(self.comuna, nombre, padre)
            if igual and igual.pk != self.instance.pk:
                raise forms.ValidationError(f"Ya existe «{igual}» en este nivel (mismo nombre o nombre alternativo).")
        return datos


class AliasForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = SectorAlias
        fields = ["nombre"]
        labels = {"nombre": "Nombre alternativo"}


class DireccionForm(BootstrapMixin, forms.ModelForm):
    """Dirección reutilizable con selección en cascada: región → provincia → comuna → sector (TE-01, TE-03).

    Región y provincia no se guardan: se deducen de la comuna. El sector se valida contra la comuna en el servidor.
    """

    region = forms.ModelChoiceField(Region.objects.all(), required=False, label="Región")
    provincia = forms.ModelChoiceField(Provincia.objects.all(), required=False, label="Provincia")

    class Meta:
        model = Direccion
        fields = ["region", "provincia", "comuna", "sector", "calle", "numero", "block", "depto", "referencia"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        dato = lambda n: self.data.get(self.add_prefix(n)) if self.is_bound else None
        comuna_id = dato("comuna") or (self.instance.comuna_id if self.instance.pk else None)
        comuna = Comuna.objects.select_related("provincia__region").filter(pk=comuna_id).first() if str(comuna_id or "").isdigit() else None
        if comuna and not self.is_bound:
            self.initial["region"] = comuna.provincia.region_id
            self.initial["provincia"] = comuna.provincia_id
        region_id = dato("region") or self.initial.get("region")
        provincia_id = dato("provincia") or self.initial.get("provincia")
        if region_id:
            self.fields["provincia"].queryset = Provincia.objects.filter(region_id=region_id)
        comunas = Comuna.objects.select_related("provincia__region")
        self.fields["comuna"].queryset = comunas  # validación contra todas las comunas
        if provincia_id:
            self.fields["comuna"].choices = [("", "---------")] + [(c.pk, c.nombre) for c in comunas.filter(provincia_id=provincia_id)]
        self.fields["sector"].queryset = Sector.objects.filter(comuna_id=comuna_id) if comuna_id else Sector.objects.none()
        p = self.add_prefix
        self.fields["region"].widget.attrs.update({"hx-get": "/territorio/provincias", "hx-target": f"#id_{p('provincia')}", "hx-trigger": "change"})
        self.fields["provincia"].widget.attrs.update({"hx-get": "/territorio/comunas", "hx-target": f"#id_{p('comuna')}", "hx-trigger": "change"})
        self.fields["comuna"].widget.attrs.update({"hx-get": "/territorio/sectores", "hx-target": f"#id_{p('sector')}", "hx-trigger": "change", "hx-include": "this"})

    def clean(self):
        d = super().clean()
        c = d.get("comuna")
        if c and d.get("provincia") and c.provincia_id != d["provincia"].pk:
            self.add_error("comuna", "La comuna no pertenece a la provincia elegida.")
        return d

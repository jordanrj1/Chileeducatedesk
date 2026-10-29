"""Formularios de territorio: sector (con sector padre), nombre alternativo de un sector,
y la dirección con la ubicación en cascada (región → comuna → sector; ver ubicacion.py), que exige que el sector sea de esa comuna.
Las listas solo ofrecen sectores activos; al editar, se conserva el sector desactivado que el registro ya tenía."""
from django import forms

from apps.nucleo.formularios import BootstrapMixin

from .models import Direccion, Sector, SectorAlias
from .reconocer import mismo_sector
from .ubicacion import UbicacionMixin


class SectorForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Sector
        fields = ["nombre", "tipo", "sector_padre"]

    def __init__(self, *args, comuna=None, **kw):
        super().__init__(*args, **kw)
        self.comuna = comuna or getattr(self.instance, "comuna", None)
        # el nombre de cada opción incluye el de su padre y su abuelo: se traen en la misma consulta.
        # Un sector desactivado no recibe sectores nuevos dentro; al editar se conserva el padre que ya tenía.
        if self.comuna:
            qs = Sector.para_elegir(conservar=self.instance.sector_padre_id).filter(comuna=self.comuna).select_related("sector_padre__sector_padre")
        else:
            qs = Sector.objects.none()
        if self.instance.pk:
            qs = qs.exclude(pk__in=self.instance.descendientes_ids())  # no puede quedar dentro de sí mismo
        campo = self.fields["sector_padre"]
        campo.queryset = qs
        campo.required = False
        campo.label = "Dentro de (opcional)"
        campo.label_from_instance = Sector.etiqueta
        campo.error_messages["invalid_choice"] = "Ese sector está desactivado o no es de esta comuna: elige otro."

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
            if igual and igual.pk != self.instance.pk and not igual.activo:
                raise forms.ValidationError(f"Ya existe «{igual}» en este nivel, pero está desactivado. Reactívalo desde su ficha en vez de crearlo de nuevo.")
            if igual and igual.pk != self.instance.pk:
                raise forms.ValidationError(f"Ya existe «{igual}» en este nivel (mismo nombre o nombre alternativo).")
        return datos


class AliasForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = SectorAlias
        fields = ["nombre"]
        labels = {"nombre": "Nombre alternativo"}


class DireccionForm(UbicacionMixin, BootstrapMixin, forms.ModelForm):
    """Dirección reutilizable con la ubicación en cascada: región → comuna → sector, con la provincia opcional (TE-01, TE-03).

    Región y provincia no se guardan: se deducen de la comuna. El sector se valida contra la comuna en el servidor.
    Se dibuja con territorio/_ubicacion.html (la cascada) más `campos_sin_ubicacion` (calle, número…).
    """

    class Meta:
        model = Direccion
        fields = ["comuna", "sector", "calle", "numero", "block", "depto", "referencia"]

    # F26 Ia: block, depto y referencia van plegados en «Más datos de la dirección» (territorio/_direccion_form.html)
    CAMPOS_MAS = ("block", "depto", "referencia")

    def campos_principales(self):
        return [c for c in self.campos_sin_ubicacion() if c.name not in self.CAMPOS_MAS]

    def campos_mas(self):
        return [c for c in self.campos_sin_ubicacion() if c.name in self.CAMPOS_MAS]

    def mas_abierto(self):
        """El pliegue se abre solo si alguno de sus campos trae valor o error."""
        return any(c.value() or c.errors for c in self.campos_mas())

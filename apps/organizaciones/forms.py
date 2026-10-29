"""Formularios de organización (tipo, RUT u otro identificador, sitio web, si es la Fundación, comuna si es municipalidad),
de carrera de una institución educativa y de la ventana «+ Crear organización» de los buscadores."""
from django import forms

from apps.nucleo.formularios import BloqueDeSeccion, BootstrapMixin
from apps.nucleo.models import TipoOrganizacion
from apps.nucleo.rut import CampoRut

from .models import Carrera, Organizacion


class OrganizacionForm(BootstrapMixin, forms.ModelForm):
    """Crear y editar una organización en tres secciones: Identificación, Contacto y dirección, y Datos legales (plegada).
    La naturaleza jurídica se elige del catálogo; el texto escrito antes solo aparece si tiene algo, para revisarlo."""

    rut = CampoRut(label="RUT de la organización", help_text="Opcional. Aparece en sus certificados, cartas o facturas. Ej.: 65.123.456-5.")
    secciones = [
        ("Identificación", "Solo el nombre y el tipo son obligatorios; el resto se puede completar después.",
         ["nombre", "tipo", "rut", "otro_identificador", "descripcion", "comuna_municipal", "estado_registro"]),
        ("Contacto y dirección", "Dónde funciona o se reúne la organización. La dirección es opcional.", ["sitio_web", "direccion"]),
        ("Datos legales", "Complétalos con el certificado de vigencia o los estatutos a la vista. Si no los tienes, déjalos vacíos: "
                          "el resto se guarda igual.",
         ["naturaleza", "naturaleza_juridica", "domicilio_legal", "vigencia_desde", "vigencia_hasta", "es_propia"], {"plegada": True}),  # F26 Ia: «Esta ficha es la de la Fundación» va aquí
    ]

    class Meta:
        model = Organizacion
        fields = [
            "nombre", "tipo", "rut", "otro_identificador", "estado_registro", "descripcion", "sitio_web", "comuna_municipal",
            "naturaleza", "naturaleza_juridica", "domicilio_legal", "vigencia_desde", "vigencia_hasta", "es_propia",
        ]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2}), "vigencia_desde": forms.DateInput, "vigencia_hasta": forms.DateInput}
        labels = {
            "nombre": "Nombre de la organización",
            "tipo": "Tipo de organización",
            "otro_identificador": "N.º de personalidad jurídica u otro registro",
            "estado_registro": "Estado de la ficha",
            "descripcion": "¿Qué hace?",
            "sitio_web": "Sitio web o red social",
            "comuna_municipal": "Comuna que administra",
            "naturaleza": "Naturaleza jurídica",
            "domicilio_legal": "Domicilio legal",
            "vigencia_desde": "Vigente desde",
            "vigencia_hasta": "Vigente hasta",
            "es_propia": "Esta ficha es la de la Fundación",
        }
        help_texts = {
            "nombre": "Como aparece en sus documentos. Ej.: Junta de Vecinos Villa Los Aromos.",
            "tipo": "Elige la que mejor la describe. Ej.: Junta de vecinos o comité.",
            "otro_identificador": "Si no tiene RUT, o además del RUT. Ej.: el N.º de inscripción en el Registro Civil, o el RBD si es un liceo.",
            "estado_registro": "Qué tan completa y confiable es esta información (no si la organización funciona). "
                               "Ej.: Por verificar, si vino de una planilla.",
            "descripcion": "Una o dos frases. Ej.: junta de vecinos de la Etapa 2; organiza ferias y talleres para personas mayores.",
            "sitio_web": "Ej.: https://www.ejemplo.cl",
            "comuna_municipal": "Solo para municipalidades. Ej.: Municipalidad de Hualpén → Hualpén.",
            "naturaleza": "Qué tipo de entidad es ante la ley: figura en su certificado de vigencia o en sus estatutos. "
                          "Ej.: una junta de vecinos es «Organización comunitaria territorial».",
            "domicilio_legal": "El que figura en sus estatutos o en el certificado. Solo si es distinto de la dirección donde funciona. "
                               "Ej.: comuna de Hualpén, aunque se reúna en la sede de la villa.",
            "vigencia_desde": "Desde cuándo está vigente su personalidad jurídica, según el certificado. Ej.: 15-04-2025.",
            "vigencia_hasta": "Hasta cuándo, según el certificado. El Inicio avisa 30 días antes de que venza. Ej.: 15-04-2028.",
            "es_propia": "Márcalo solo en la ficha de la propia Fundación (hay una sola).",
        }

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        from apps.nucleo.models import EstadoRegistro, NaturalezaJuridica, TipoOrganizacion

        self.fields["tipo"].queryset = TipoOrganizacion.objects.filter(activo=True)
        # «Fallecida/o» no corresponde a una organización y «Fusionada» la pone solo la fusión de fichas
        estados = EstadoRegistro.objects.filter(activo=True).exclude(codigo__in=["fallecida", "fusionada"])
        self.fields["estado_registro"].queryset = estados | EstadoRegistro.objects.filter(pk=self.instance.estado_registro_id or 0)
        self.fields["naturaleza"].queryset = NaturalezaJuridica.objects.filter(activo=True) | NaturalezaJuridica.objects.filter(
            pk=self.instance.naturaleza_id or 0)
        if self.instance.naturaleza_juridica:
            self.fields["naturaleza_juridica"].label = "Naturaleza jurídica (texto anterior)"
            self.fields["naturaleza_juridica"].help_text = ("Se escribió antes de que existiera la lista. Elige arriba la naturaleza jurídica "
                                                            "que corresponda y luego borra este texto.")
        else:
            self.fields.pop("naturaleza_juridica")
        # «Comuna que administra» solo tiene sentido en una municipalidad: se muestra solo si ese es el tipo elegido.
        muni = TipoOrganizacion.objects.filter(codigo="municipalidad").values_list("pk", flat=True).first()
        if muni and "comuna_municipal" in self.fields:
            self.fields["comuna_municipal"].widget.attrs.update({"data-mostrar-si-campo": self.add_prefix("tipo"), "data-mostrar-si-valor": str(muni)})
        if self.instance.pk and self.instance.rut_numero:
            self.initial["rut"] = self.instance.rut

    @property
    def bloques_de_seccion(self):
        """«direccion» dibuja, dentro de «Contacto y dirección», el formulario de dirección que arma la vista (form_direccion)."""
        return {"direccion": BloqueDeSeccion(self, "organizaciones/_direccion.html", ())}

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
        labels = {"nombre": "Nombre de la carrera", "activo": "Se ofrece actualmente"}
        help_texts = {"nombre": "Como la llama la institución. Ej.: Técnico en Trabajo Social.",
                      "activo": "Desmárcala si la institución dejó de ofrecerla: las personas que la estudiaron la conservan."}

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


class OrganizacionRapidaForm(BootstrapMixin, forms.Form):
    """Ventana «+ Crear organización» de los buscadores: solo nombre y tipo; el resto se completa en su ficha."""

    nombre = forms.CharField(max_length=200, label="Nombre de la organización", help_text="Ej.: Junta de Vecinos Villa Los Aromos.")
    tipo = forms.ModelChoiceField(TipoOrganizacion.objects.filter(activo=True), label="Tipo de organización")

    def __init__(self, *a, tipo_fijo="", **kw):
        super().__init__(*a, **kw)
        if tipo_fijo:  # el campo de origen solo acepta un tipo (p. ej. instituciones educativas)
            self.fields["tipo"].queryset = TipoOrganizacion.objects.filter(codigo=tipo_fijo)
            self.fields["tipo"].empty_label = None
            self.fields["tipo"].help_text = "Este campo solo acepta organizaciones de este tipo."

    def clean_nombre(self):
        return self.cleaned_data["nombre"].strip()

from django import forms

from django.urls import reverse_lazy

from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import AreaTematica, Canal, EstadoRegistro, OrigenPersona, PerfilPersona, TipoContacto
from apps.nucleo.rut import CampoRut
from apps.nucleo.utilidades import normalizar_telefono, telefono_normalizado_valido
from apps.organizaciones.models import Carrera, Organizacion
from apps.territorio.forms import DireccionForm

from .models import (
    Apoderado, Consentimiento, Contacto, ContactoEmergencia, DisponibilidadPersona, Experiencia, PerfilSensible, Persona, PersonaDireccion,
    PersonaFormacion, PersonaOrganizacion, VerificacionPersona,
)


def selector_persona(**kw):
    return SelectorField(Persona.objects.filter(activo=True), reverse_lazy("personas:opciones"), **kw)


CAMPOS_PERFIL = ["nombre_social", "fecha_nacimiento", "nacionalidad", "perfiles", "nivel_educacional", "situacion_ocupacional",
                 "areas_interes", "habilidades", "idiomas", "canal_preferido"]

SECCIONES_PERSONA = [
    ("Identificación", "Solo el nombre es obligatorio; el resto se puede completar después.",
     ["nombres", "apellido_paterno", "apellido_materno", "nombre_social", "rut", "tipo_documento", "numero_documento", "fecha_nacimiento", "nacionalidad"]),
    ("Contacto", "Un dato basta para registrarla.", ["correo", "telefono", "canal_preferido"]),
    ("Perfil y ocupación", "Qué es esta persona para la Fundación y a qué se dedica. Sirve para filtrar el banco de personas.",
     ["perfiles", "nivel_educacional", "situacion_ocupacional", "profesion", "sitio_web"]),
    ("Intereses y habilidades", "Para invitarla a las actividades que le interesan y encontrar talleristas y voluntarios.",
     ["areas_interes", "habilidades", "idiomas"]),
    ("Registro", "", ["origen", "estado_registro", "observaciones"]),
]


class PersonaForm(BootstrapMixin, forms.ModelForm):
    """Ficha completa por secciones (F22). Solo el nombre es obligatorio: se puede completar después."""

    rut = CampoRut(label="RUT")
    secciones = SECCIONES_PERSONA

    class Meta:
        model = Persona
        fields = ["nombres", "apellido_paterno", "apellido_materno", "rut", "tipo_documento", "numero_documento", *CAMPOS_PERFIL[:3],
                  "profesion", "sitio_web", *CAMPOS_PERFIL[3:], "origen", "estado_registro", "observaciones"]
        widgets = {
            "perfiles": forms.CheckboxSelectMultiple, "areas_interes": forms.CheckboxSelectMultiple,
            "fecha_nacimiento": forms.DateInput, "habilidades": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        if "origen" in self.fields:
            self.fields["origen"].queryset = OrigenPersona.objects.filter(activo=True)
        if "estado_registro" in self.fields:
            self.fields["estado_registro"].queryset = EstadoRegistro.objects.filter(activo=True)
        if "perfiles" in self.fields:
            self.fields["perfiles"].queryset = PerfilPersona.objects.filter(activo=True)
        if "areas_interes" in self.fields:
            self.fields["areas_interes"].queryset = AreaTematica.objects.filter(activo=True)
        if "canal_preferido" in self.fields:
            self.fields["canal_preferido"].queryset = Canal.objects.filter(activo=True)
        if "nacionalidad" in self.fields:
            self.fields["nacionalidad"].widget.attrs.update(list="nacionalidades", placeholder="Ej.: chilena")
        if self.instance.pk and self.instance.rut_numero:
            self.initial["rut"] = self.instance.rut

    def clean_rut(self):
        valor = self.cleaned_data.get("rut")
        if valor:
            existe = Persona.objects.filter(rut_numero=valor[0]).exclude(pk=self.instance.pk).first()
            if existe:
                raise forms.ValidationError(f"Ya existe una persona con ese RUT: {existe.nombre_completo}.")
        return valor

    def clean(self):
        d = super().clean()
        tipo, numero = d.get("tipo_documento"), (d.get("numero_documento") or "").strip().upper()
        if numero and not tipo:
            self.add_error("tipo_documento", "Indica el tipo de documento.")
        if tipo and not numero:
            self.add_error("numero_documento", "Indica el número del documento.")
        if tipo and numero:
            d["numero_documento"] = numero
            otra = Persona.objects.filter(tipo_documento=tipo, numero_documento=numero).exclude(pk=self.instance.pk).first()
            if otra:
                self.add_error("numero_documento", f"Ya existe una persona con ese documento: {otra.nombre_completo}.")
        return d

    def save(self, commit=True):
        obj = super().save(commit=False)
        rut = self.cleaned_data.get("rut")
        obj.rut_numero, obj.rut_dv = rut if rut else (None, None)
        if commit:
            obj.save()
        return obj


class PersonaNuevaForm(PersonaForm):
    """Ficha rápida: nombre y un dato de contacto; el resto después."""

    correo = forms.EmailField(required=False)
    telefono = forms.CharField(label="teléfono", required=False, max_length=40)

    class Meta(PersonaForm.Meta):
        fields = ["nombres", "apellido_paterno", "apellido_materno", "rut", "tipo_documento", "numero_documento", *CAMPOS_PERFIL[:3], "correo", "telefono",
                  "profesion", *CAMPOS_PERFIL[3:], "origen", "observaciones"]

    def clean_telefono(self):
        t = self.cleaned_data.get("telefono", "").strip()
        if t and not telefono_normalizado_valido(normalizar_telefono(t)):
            raise forms.ValidationError("No se pudo interpretar el teléfono. Usa el formato +56 9 1234 5678.")
        return t


class PersonaRapidaForm(PersonaNuevaForm):
    """Ficha rápida (IG-01): nombre y un dato de contacto, para registrar mientras se habla por teléfono."""

    rut = None  # campos de la ficha completa que aquí no se piden

    class Meta(PersonaNuevaForm.Meta):
        fields = ["nombres", "apellido_paterno", "correo", "telefono"]

    def clean(self):
        return super(PersonaForm, self).clean()  # sin documento en la ficha rápida


class ContactoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Contacto
        fields = ["tipo", "valor", "proposito", "principal", "vigente"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.fields["tipo"].queryset = TipoContacto.objects.filter(activo=True)

    def clean(self):
        d = super().clean()
        tipo, valor = d.get("tipo"), d.get("valor", "")
        if tipo and valor:
            norm = Contacto.normalizar(tipo, valor)
            if tipo.codigo in ("telefono_movil", "telefono_fijo") and not telefono_normalizado_valido(norm):
                self.add_error("valor", "Teléfono no válido. Usa el formato +56 9 1234 5678.")
            if tipo.codigo == "correo":
                try:
                    forms.EmailField().clean(valor)
                except forms.ValidationError:
                    self.add_error("valor", "Correo no válido.")
        return d


class PersonaDireccionForm(DireccionForm):
    tipo = forms.ChoiceField(choices=PersonaDireccion.TIPOS, label="Tipo de dirección")

    def __iter__(self):  # el bloque de dirección no repite «tipo»: se muestra aparte
        return (c for c in super().__iter__() if c.name != "tipo")

    def save_para(self, persona):
        direccion = super().save()
        return PersonaDireccion.objects.create(persona=persona, direccion=direccion, tipo=self.cleaned_data["tipo"])


class FormacionForm(BootstrapMixin, forms.ModelForm):
    docente = selector_persona(required=False, label="Docente o tutor a cargo")
    secciones = [
        ("Estudios", "", ["organizacion", "carrera", "estado", "sede", "jornada", "nivel_actual", "anio_inicio", "anio_termino"]),
        ("Vínculo con la Fundación", "Para coordinar con la institución y certificar las horas.", ["asignatura", "docente", "horas_comprometidas", "vigente"]),
    ]

    class Meta:
        model = PersonaFormacion
        fields = ["organizacion", "carrera", "estado", "sede", "jornada", "nivel_actual", "anio_inicio", "anio_termino", "asignatura", "docente", "horas_comprometidas", "vigente"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.fields["organizacion"].queryset = Organizacion.objects.filter(tipo__codigo="institucion_educativa", activo=True)
        self.fields["carrera"].queryset = Carrera.objects.filter(activo=True).select_related("organizacion")
        self.fields["carrera"].required = False

    def clean(self):
        d = super().clean()
        # PersonaFormacion.clean() valida carrera ↔ institución; ModelForm la llama con la instancia ya armada
        return d


class VinculoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PersonaOrganizacion
        fields = ["organizacion", "cargo", "tipo_cargo", "fecha_inicio", "fecha_termino"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.fields["organizacion"].queryset = Organizacion.objects.filter(activo=True)


class VinculoDesdeOrganizacionForm(BootstrapMixin, forms.ModelForm):
    """Agregar persona con cargo desde la ficha de la organización. Los cargos son históricos: se cierran con «hasta»."""

    persona = forms.ModelChoiceField(Persona.objects.none())

    class Meta:
        model = PersonaOrganizacion
        fields = ["persona", "cargo", "tipo_cargo", "fecha_inicio", "fecha_termino"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from django.urls import reverse_lazy

        from apps.nucleo.formularios import SelectorField, fijar_valores_selectores

        self.fields["persona"] = SelectorField(Persona.objects.filter(activo=True), reverse_lazy("personas:opciones"))
        self.fields["persona"].widget.attrs["class"] = "form-select"
        fijar_valores_selectores(self)


class ExperienciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Experiencia
        fields = ["descripcion", "lugar", "desde", "hasta", "vigente"]


class DisponibilidadForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DisponibilidadPersona
        fields = ["dia", "hora_inicio", "hora_fin", "comentario", "vigente"]


class EmergenciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ContactoEmergencia
        fields = ["nombre", "parentesco", "telefono", "vigente"]


class VerificacionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = VerificacionPersona
        fields = ["tipo", "fecha", "vigente_hasta", "observaciones", "vigente"]


class PerfilSensibleForm(BootstrapMixin, forms.ModelForm):
    """Datos sensibles. Exigen un consentimiento vigente de tipo «datos sensibles»; si no hay, se registra aquí mismo."""

    consentimiento = forms.BooleanField(required=False, label="La persona (o su apoderado) dio su consentimiento explícito para registrar estos datos")
    consentimiento_fecha = forms.DateField(required=False, label="Fecha del consentimiento", widget=forms.DateInput)
    consentimiento_medio = forms.ChoiceField(required=False, choices=Consentimiento.MEDIOS, label="Medio")
    secciones = [
        ("Género y origen", "Solo para estadísticas desagregadas. Siempre se puede responder «Prefiere no responder».", ["genero", "pueblo_originario"]),
        ("Salud y accesibilidad", "Para preparar el lugar y la actividad, y actuar en una emergencia.",
         ["discapacidad", "necesidades_apoyo", "condiciones_salud", "alergias", "prevision_salud"]),
        ("Hogar", "Para focalizar beneficios e informar a fondos.", ["jefatura_hogar", "integrantes_hogar", "tramo_rsh"]),
        ("Consentimiento", "", ["consentimiento", "consentimiento_fecha", "consentimiento_medio"]),
    ]

    class Meta:
        model = PerfilSensible
        fields = ["genero", "pueblo_originario", "discapacidad", "necesidades_apoyo", "condiciones_salud", "alergias", "prevision_salud",
                  "jefatura_hogar", "integrantes_hogar", "tramo_rsh"]
        widgets = {
            "discapacidad": forms.Select(choices=[("", "Sin información"), (True, "Sí"), (False, "No")]),
            "jefatura_hogar": forms.Select(choices=[("", "Sin información"), (True, "Sí"), (False, "No")]),
        }

    def __init__(self, *a, persona=None, **kw):
        super().__init__(*a, **kw)
        self.persona = persona
        self.consentimiento_previo = persona.consentimiento_vigente("sensibles") if persona else None
        if self.consentimiento_previo:
            for c in ("consentimiento", "consentimiento_fecha", "consentimiento_medio"):
                del self.fields[c]

    def clean(self):
        d = super().clean()
        hay_datos = any(d.get(c) not in (None, "") for c in self._meta.fields)
        if hay_datos and not self.consentimiento_previo and not d.get("consentimiento"):
            raise forms.ValidationError("Sin consentimiento explícito no se pueden registrar datos sensibles (Ley 21.719). Márcalo e indica la fecha y el medio.")
        if d.get("consentimiento") and not d.get("consentimiento_fecha"):
            self.add_error("consentimiento_fecha", "Indica la fecha del consentimiento.")
        return d


class ConsentimientoForm(BootstrapMixin, forms.ModelForm):
    otorgado_por = selector_persona(required=False, label="Otorgado por (apoderado)")

    class Meta:
        model = Consentimiento
        fields = ["tipo", "otorgado", "fecha", "medio", "otorgado_por", "documento", "revocado_en", "observaciones"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.documentos.models import Documento

        persona = self.instance.persona if self.instance.persona_id else None
        docs = Documento.objects.filter(activo=True, persona=persona) if persona else Documento.objects.none()
        if self.instance.documento_id:
            docs = docs | Documento.objects.filter(pk=self.instance.documento_id)
        self.fields["documento"].queryset = docs
        self.fields["documento"].help_text = "Documentos ya subidos a la ficha de esta persona (pestaña Documentos)."


class ApoderadoForm(BootstrapMixin, forms.ModelForm):
    apoderado = selector_persona(label="Apoderado o apoderada")

    class Meta:
        model = Apoderado
        fields = ["apoderado", "parentesco", "tutor_legal", "vigente"]

    def clean_apoderado(self):
        a = self.cleaned_data["apoderado"]
        if self.instance.persona_id and a.pk == self.instance.persona_id:
            raise forms.ValidationError("Una persona no puede ser su propio apoderado.")
        if Apoderado.objects.filter(persona_id=self.instance.persona_id, apoderado=a).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa persona ya está registrada como apoderado.")
        return a

    def validate_unique(self):
        pass

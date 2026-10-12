from django import forms

from apps.nucleo.formularios import BootstrapMixin
from apps.nucleo.models import EstadoRegistro, OrigenPersona, TipoContacto
from apps.nucleo.rut import CampoRut
from apps.nucleo.utilidades import normalizar_telefono, telefono_normalizado_valido
from apps.organizaciones.models import Carrera, Organizacion
from apps.territorio.forms import DireccionForm

from .models import (
    Contacto, ContactoEmergencia, DisponibilidadPersona, Experiencia, Persona, PersonaDireccion, PersonaFormacion,
    PersonaOrganizacion, VerificacionPersona,
)


class PersonaForm(BootstrapMixin, forms.ModelForm):
    """Edición de datos básicos. Solo el nombre es obligatorio: se puede completar después."""

    rut = CampoRut(label="RUT")

    class Meta:
        model = Persona
        fields = ["nombres", "apellido_paterno", "apellido_materno", "rut", "profesion", "sitio_web", "origen", "estado_registro", "observaciones"]

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.fields["origen"].queryset = OrigenPersona.objects.filter(activo=True)
        if "estado_registro" in self.fields:
            self.fields["estado_registro"].queryset = EstadoRegistro.objects.filter(activo=True)
        if self.instance.pk and self.instance.rut_numero:
            self.initial["rut"] = self.instance.rut

    def clean_rut(self):
        valor = self.cleaned_data.get("rut")
        if valor:
            existe = Persona.objects.filter(rut_numero=valor[0]).exclude(pk=self.instance.pk).first()
            if existe:
                raise forms.ValidationError(f"Ya existe una persona con ese RUT: {existe.nombre_completo}.")
        return valor

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
        fields = ["nombres", "apellido_paterno", "apellido_materno", "rut", "correo", "telefono", "profesion", "origen", "observaciones"]

    def clean_telefono(self):
        t = self.cleaned_data.get("telefono", "").strip()
        if t and not telefono_normalizado_valido(normalizar_telefono(t)):
            raise forms.ValidationError("No se pudo interpretar el teléfono. Usa el formato +56 9 1234 5678.")
        return t


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
    class Meta:
        model = PersonaFormacion
        fields = ["organizacion", "carrera", "estado", "anio_inicio", "anio_termino", "vigente"]

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

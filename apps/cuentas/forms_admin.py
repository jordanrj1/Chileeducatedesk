"""Formularios del Administrador: crear o editar una cuenta (ligada a una persona registrada, con su rol)
y restablecer la contraseña de otra cuenta."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password

from apps.nucleo.formularios import BootstrapMixin, SelectorField, fijar_valores_selectores
from apps.personas.selector import PERSONAS_SIN_CUENTA

from .models import PerfilCuenta

User = get_user_model()


class UsuarioForm(BootstrapMixin, forms.ModelForm):
    rol = forms.ModelChoiceField(Group.objects.all(), label="Rol")
    persona = SelectorField(PERSONAS_SIN_CUENTA, crear=False, required=False, label="Persona", help_text="Opcional. Vincula la cuenta con una ficha existente.")
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]
        labels = {"username": "Usuario", "first_name": "Nombres", "last_name": "Apellidos", "email": "Correo"}

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.crear = not self.instance.pk
        self.fields["email"].required = True
        actual = None
        if not self.crear:
            actual = getattr(getattr(self.instance, "perfil", None), "persona", None)
            self.initial["rol"] = self.instance.groups.first()
            self.initial["persona"] = actual
        fijar_valores_selectores(self)  # la persona que ya tiene esta cuenta se conserva aunque no esté «libre»
        if self.crear:
            self.fields["password1"].required = self.fields["password2"].required = True
            self.fields["persona"].required = True  # US-01: la cuenta se crea para una persona ya registrada
            self.fields["persona"].help_text = "Obligatoria. Si la persona no existe, regístrala primero en Personas."
        else:
            del self.fields["password1"], self.fields["password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya hay una cuenta con ese correo.")
        return email

    def clean(self):
        d = super().clean()
        if self.crear:
            if d.get("password1") != d.get("password2"):
                self.add_error("password2", "Las contraseñas no coinciden.")
            elif d.get("password1"):
                try:
                    validate_password(d["password1"], User(username=d.get("username", ""), email=d.get("email", "")))
                except forms.ValidationError as e:
                    self.add_error("password1", e)
        return d

    def save(self, commit=True):
        usuario = super().save(commit=False)
        persona = self.cleaned_data.get("persona")
        if persona:
            usuario.first_name = usuario.first_name or persona.nombres
            usuario.last_name = usuario.last_name or " ".join(x for x in [persona.apellido_paterno, persona.apellido_materno] if x)
        if self.crear:
            usuario.set_password(self.cleaned_data["password1"])
        usuario.save()
        usuario.groups.set([self.cleaned_data["rol"]])
        perfil, _ = PerfilCuenta.objects.get_or_create(usuario=usuario)
        perfil.persona = persona
        perfil.save()
        return usuario


class ClaveForm(BootstrapMixin, forms.Form):
    password1 = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput)

    def __init__(self, usuario, *a, **kw):
        super().__init__(*a, **kw)
        self.usuario = usuario

    def clean(self):
        d = super().clean()
        if d.get("password1") != d.get("password2"):
            self.add_error("password2", "Las contraseñas no coinciden.")
        elif d.get("password1"):
            try:
                validate_password(d["password1"], self.usuario)
            except forms.ValidationError as e:
                self.add_error("password1", e)
        return d

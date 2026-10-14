"""Formulario de la pantalla de ingreso (usuario o correo y contraseña),
con mensajes que no dicen qué dato estaba mal y que explican si la cuenta está desactivada o bloqueada."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

MENSAJE = "No fue posible iniciar sesión. Revisa tus datos."


class LoginForm(AuthenticationForm):
    """Datos incorrectos: mensaje genérico (no revela qué cuentas existen).

    Cuenta desactivada con la contraseña correcta: se explica y se indica a quién consultar (AC-02).
    Solo quien conoce la contraseña recibe ese aviso, por lo que no se filtra información a terceros.
    """

    error_messages = {"invalid_login": MENSAJE, "inactive": MENSAJE}

    def clean(self):
        from .bloqueo import bloqueado

        if bloqueado(self.cleaned_data.get("username")):
            minutos = getattr(settings, "BLOQUEO_MINUTOS", 15)
            raise ValidationError(
                f"Demasiados intentos fallidos. Espera {minutos} minutos o pide al Administrador que desbloquee el acceso.", code="bloqueado"
            )
        try:
            return super().clean()
        except ValidationError:
            usuario = self._cuenta_desactivada()
            if usuario:
                contacto = getattr(settings, "CONTACTO_ADMINISTRADOR", "") or "el Administrador del sistema"
                raise ValidationError(f"Tu cuenta está desactivada, por eso no puedes ingresar. Consulta a {contacto}.", code="inactive")
            raise

    def _cuenta_desactivada(self):
        ident = (self.cleaned_data.get("username") or "").strip()
        clave = self.cleaned_data.get("password") or ""
        if not ident or not clave:
            return None
        User = get_user_model()
        qs = User.objects.filter(username__iexact=ident)
        if not qs.exists() and "@" in ident:
            qs = User.objects.filter(email__iexact=ident)
        if qs.count() != 1:
            return None
        u = qs.get()
        return u if (not u.is_active and u.check_password(clave)) else None

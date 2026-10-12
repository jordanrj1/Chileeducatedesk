from django.contrib.auth.forms import AuthenticationForm

MENSAJE = "No fue posible iniciar sesión. Revisa tus datos."


class LoginForm(AuthenticationForm):
    """Mismo mensaje para datos incorrectos y cuenta desactivada (no revela cuál cuentas existen)."""

    error_messages = {"invalid_login": MENSAJE, "inactive": MENSAJE}

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CorreoOUsuarioBackend(ModelBackend):
    """Permite ingresar con nombre de usuario o con correo (F02)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if not username or not password:
            return None
        texto = username.strip()
        candidatos = User.objects.filter(username__iexact=texto)
        if not candidatos.exists() and "@" in texto:
            candidatos = User.objects.filter(email__iexact=texto)
        if candidatos.count() != 1:
            User().set_password(password)  # iguala el tiempo de respuesta
            return None
        user = candidatos.get()
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

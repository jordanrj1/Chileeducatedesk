from django.contrib.auth.models import Group, Permission
from django.db import models


class PermisoInicial(models.Model):
    """Permisos ya sembrados a un rol. Evita que un cambio del Administrador se revierta al migrar."""

    grupo = models.ForeignKey(Group, on_delete=models.CASCADE)
    permiso = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["grupo", "permiso"], name="permiso_inicial_unico")]


class PerfilCuenta(models.Model):
    """Vincula una cuenta con su ficha de persona. Persona y cuenta son 1 a 0..1 (la persona existe sin cuenta)."""

    from django.conf import settings as _settings

    usuario = models.OneToOneField(_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    persona = models.OneToOneField("personas.Persona", null=True, blank=True, on_delete=models.PROTECT, related_name="cuenta")

    class Meta:
        verbose_name = "perfil de cuenta"
        verbose_name_plural = "perfiles de cuenta"

    def __str__(self):
        return f"{self.usuario} ↔ {self.persona or 'sin persona'}"

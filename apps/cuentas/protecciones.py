"""Protección del último Superadministrador (F29): siempre debe quedar al menos uno activo."""
from django.contrib.auth import get_user_model

from .roles import SUPERADMIN

MENSAJE_ULTIMO = "Debe quedar al menos un Superadministrador activo. Crea o activa otro antes de hacer este cambio."


def es_superadmin_activo(usuario):
    return bool(usuario.pk) and usuario.is_active and usuario.groups.filter(name=SUPERADMIN).exists()


def es_el_ultimo(usuario):
    """True si `usuario` es hoy Superadministrador activo y no hay otro."""
    if not es_superadmin_activo(usuario):
        return False
    return not get_user_model().objects.filter(is_active=True, groups__name=SUPERADMIN).exclude(pk=usuario.pk).exists()

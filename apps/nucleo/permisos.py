from functools import wraps

from django.core.exceptions import PermissionDenied

GESTOR = "Gestor"
ADMINISTRADOR = "Administrador"


def grupo_requerido(*grupos):
    """Exige pertenecer a alguno de los grupos; si no, 403 (la sesión ya está validada)."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.groups.filter(name__in=grupos).exists():
                raise PermissionDenied
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador

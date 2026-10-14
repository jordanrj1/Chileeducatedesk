"""Función para anotar una acción importante en la auditoría (quién, qué, sobre qué y cuándo).
La usan las demás apps al exportar, descargar, crear cuentas, cambiar roles, etc."""
from .models import Auditoria


def registrar(usuario, accion, objeto="", detalle=""):
    """Anota una operación sensible. `usuario` puede ser None (p. ej. intento de ingreso fallido)."""
    autenticado = bool(usuario and getattr(usuario, "is_authenticated", False))
    return Auditoria.objects.create(
        usuario=usuario if autenticado else None,
        usuario_nombre=(usuario.get_username() if autenticado else ""),
        accion=accion,
        objeto=str(objeto)[:200],
        detalle=str(detalle),
    )

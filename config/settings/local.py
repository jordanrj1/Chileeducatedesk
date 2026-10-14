"""Ajustes para desarrollar en el propio equipo: los estilos se sirven directo desde las carpetas del código.
No se usa en el computador de la Fundación: ahí iniciar.bat usa produccion.py."""
from .base import *  # noqa: F401,F403

WHITENOISE_USE_FINDERS = True

"""Módulos de «segunda fase» (Requerimientos por módulo): existen en el código y se muestran según el ajuste.

SEGUNDA_FASE=True muestra todos. MODULOS_SEGUNDA_FASE=reuniones,tareas muestra solo esos, con el resto oculto.
"""
import re

from django.conf import settings
from django.http import Http404

MODULOS = ("reuniones", "tareas", "beneficiarios", "verificaciones", "postulaciones", "finanzas")  # «sesiones» siempre visible desde F22

RUTAS = [
    (re.compile(r"^/reuniones(/|$)"), "reuniones"),
    (re.compile(r"^/tareas(/|$)"), "tareas"),
    (re.compile(r"^/finanzas(/|$)"), "finanzas"),
    (re.compile(r"^/personas/\d+/verificaciones/"), "verificaciones"),
    (re.compile(r"^/proyectos/\d+/beneficiarios/"), "beneficiarios"),
    (re.compile(r"^/proyectos/\d+/postulaciones/"), "postulaciones"),
]


def modulo_activo(clave):
    if getattr(settings, "SEGUNDA_FASE", False):
        return True
    return clave in {m.strip() for m in getattr(settings, "MODULOS_SEGUNDA_FASE", []) if m.strip()}


def modulos_activos():
    return {m: modulo_activo(m) for m in MODULOS}


def segunda_fase_activa():
    """True solo si toda la segunda fase está visible."""
    return bool(getattr(settings, "SEGUNDA_FASE", False))


class SegundaFaseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        for patron, modulo in RUTAS:
            if patron.match(request.path) and not modulo_activo(modulo):
                raise Http404("Módulo no habilitado en esta etapa.")
        return self.get_response(request)

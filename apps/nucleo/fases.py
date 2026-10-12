"""Módulos de «segunda fase» (Requerimientos por módulo): existen en el código, pero se muestran solo con SEGUNDA_FASE=True."""
import re

from django.conf import settings
from django.http import Http404

RUTAS_SEGUNDA_FASE = [
    re.compile(p)
    for p in (
        r"^/reuniones(/|$)",
        r"^/tareas(/|$)",
        r"^/finanzas(/|$)",
        r"^/actividades/\d+/sesiones/",
        r"^/personas/\d+/verificaciones/",
        r"^/proyectos/\d+/(beneficiarios|postulaciones)/",
    )
]


def segunda_fase_activa():
    return bool(getattr(settings, "SEGUNDA_FASE", False))


class SegundaFaseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not segunda_fase_activa() and any(p.match(request.path) for p in RUTAS_SEGUNDA_FASE):
            raise Http404("Módulo no habilitado en esta etapa.")
        return self.get_response(request)

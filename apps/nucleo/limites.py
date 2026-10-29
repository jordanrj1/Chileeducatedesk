"""F26 Ra: límite de peticiones por usuario (o por IP si no hay sesión), con la caché de Django y sin dependencias.

Tres cuentas por minuto, cada una con su ajuste en `.env` (0 = sin límite):
- exportaciones e informes (`LIMITE_EXPORTACIONES_MINUTO`, 10);
- búsquedas y buscadores (`LIMITE_BUSQUEDAS_MINUTO`, 120): /buscar y las listas de los buscadores de los formularios;
- envíos (`LIMITE_ENVIOS_MINUTO`, 60): todo POST, salvo el ingreso, que tiene su propio bloqueo (apps/cuentas/bloqueo.py).

Ventana fija de un minuto: una sola lectura y escritura en la caché por petición. Al pasarse responde 429 con la pantalla
propia (o un fragmento corto si la pidió HTMX) y la cabecera Retry-After con los segundos que faltan.
"""
import math
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import render

# Listas de los buscadores (selectores con «escribe para buscar») y de la ubicación en cascada
RUTAS_BUSQUEDA = ("/buscar",)
FINALES_BUSQUEDA = ("/opciones", "/territorio/provincias", "/territorio/comunas", "/territorio/sectores")
FINALES_EXPORTACION = ("/exportar", "/informe")
RUTAS_SIN_LIMITE_DE_ENVIO = ("/login",)  # el ingreso conserva su bloqueo por intentos fallidos

CATEGORIAS = {
    "exportaciones": ("LIMITE_EXPORTACIONES_MINUTO", "exportaciones o informes"),
    "busquedas": ("LIMITE_BUSQUEDAS_MINUTO", "búsquedas"),
    "envios": ("LIMITE_ENVIOS_MINUTO", "envíos de formularios"),
}


def ahora():
    return time.time()


def categoria(request):
    ruta = request.path.rstrip("/") or "/"
    if ruta.endswith(FINALES_EXPORTACION):
        return "exportaciones"
    if request.method == "GET" and (ruta in RUTAS_BUSQUEDA or ruta.endswith(FINALES_BUSQUEDA)):
        return "busquedas"
    if request.method == "POST" and ruta not in RUTAS_SIN_LIMITE_DE_ENVIO:
        return "envios"
    return None


def quien(request):
    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated:
        return f"u{usuario.pk}"
    return "ip" + request.META.get("REMOTE_ADDR", "")


def respuesta_429(request, espera, que):
    contexto = {"espera": espera, "que": que}
    if request.headers.get("HX-Request"):
        r = HttpResponse(
            f'<div class="alert alert-warning small mb-0" role="alert">Llegaron demasiadas solicitudes seguidas ({que}). Espera {espera} segundos y vuelve a intentarlo.</div>',
            status=429,
        )
    else:
        r = render(request, "errores/429.html", contexto, status=429)
    r["Retry-After"] = str(espera)
    return r


class LimitePeticionesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cat = categoria(request)
        if cat:
            ajuste, que = CATEGORIAS[cat]
            limite = getattr(settings, ajuste, 0)
            if limite and limite > 0:
                t = ahora()
                clave = f"limite:{cat}:{quien(request)}:{int(t // 60)}"
                cache.add(clave, 0, 70)
                try:
                    n = cache.incr(clave)
                except ValueError:  # se venció justo entre las dos llamadas
                    cache.set(clave, 1, 70)
                    n = 1
                if n > limite:
                    return respuesta_429(request, max(1, math.ceil(60 - t % 60)), que)
        return self.get_response(request)

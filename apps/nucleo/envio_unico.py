"""F26 Ra: envío único en el servidor. Protege aunque no haya JavaScript (doble clic, «reenviar», red que reintenta).

Cada formulario de creación lleva una marca de un solo uso (`{% marca_envio %}`, campo oculto `_envio`). Este middleware:
- si la marca ya se usó con éxito, no deja pasar el envío: lleva a lo que se creó la primera vez con el aviso
  «Ya estaba guardado» (en HTMX responde lo mismo que la primera vez);
- si la marca está en curso (el primer envío aún no termina), espera a que termine y hace lo mismo;
- si el envío termina bien (redirección, o respuesta HTMX marcada con `envio_completado`), guarda en la sesión la marca
  con su resultado. Un envío con errores no gasta la marca: se corrige y se vuelve a enviar.

Las ediciones siguen con su control de versión (`_version`, ControlVersionMixin).
"""
import re
import time
import uuid

from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect

CAMPO = "_envio"
CLAVE_SESION = "envios_unicos"
MAXIMO_EN_SESION = 50
EN_CURSO = "en_curso"
ESPERA_MAXIMA = 10  # segundos que espera un segundo envío a que termine el primero
MENSAJE = "Ya estaba guardado."
CABECERAS_HTMX = ("HX-Trigger", "HX-Reswap", "HX-Retarget", "HX-Redirect", "HX-Location", "HX-Refresh")
_MARCA_VALIDA = re.compile(r"^[0-9a-f]{32}$")


def nueva_marca():
    return uuid.uuid4().hex


def marcar_completado(respuesta):
    """Para respuestas HTMX que no redirigen (p. ej. «Crear y elegir»): el envío se completó y la marca se gasta."""
    respuesta.envio_completado = True
    return respuesta


def _marca(request):
    if request.method != "POST":
        return None
    tipo = request.META.get("CONTENT_TYPE", "")
    if not (tipo.startswith("application/x-www-form-urlencoded") or tipo.startswith("multipart/form-data")):
        return None
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return None
    marca = request.POST.get(CAMPO, "")
    return marca if _MARCA_VALIDA.match(marca) else None


def _resultado(request, respuesta):
    if respuesta.status_code in (301, 302, 303) and respuesta.get("Location"):
        return {"tipo": "redireccion", "url": respuesta["Location"]}
    if getattr(respuesta, "envio_completado", False) and 200 <= respuesta.status_code < 300:
        return {
            "tipo": "htmx", "contenido": respuesta.content.decode(respuesta.charset or "utf-8")[:20000],
            "cabeceras": {k: respuesta[k] for k in CABECERAS_HTMX if respuesta.has_header(k)},
        }
    return None


def _repetir(request, resultado):
    if resultado["tipo"] == "redireccion":
        messages.info(request, MENSAJE)
        if request.headers.get("HX-Request"):
            r = HttpResponse("")
            r["HX-Redirect"] = resultado["url"]
            return r
        return HttpResponseRedirect(resultado["url"])
    r = HttpResponse(resultado["contenido"])
    for k, v in resultado["cabeceras"].items():
        r[k] = v
    return r


class EnvioUnicoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        marca = _marca(request)
        if not marca:
            return self.get_response(request)
        usados = request.session.get(CLAVE_SESION, {})
        if marca in usados:
            return _repetir(request, usados[marca])
        clave = f"envio:{request.user.pk}:{marca}"
        if not cache.add(clave, EN_CURSO, 300):
            return self._esperar(request, clave)
        try:
            respuesta = self.get_response(request)
        except Exception:
            cache.delete(clave)
            raise
        resultado = _resultado(request, respuesta)
        if resultado is None:
            cache.delete(clave)  # con errores: la marca sigue disponible
            return respuesta
        cache.set(clave, resultado, 300)
        usados = dict(request.session.get(CLAVE_SESION, {}))
        usados[marca] = resultado
        while len(usados) > MAXIMO_EN_SESION:
            usados.pop(next(iter(usados)))
        request.session[CLAVE_SESION] = usados
        return respuesta

    def _esperar(self, request, clave):
        """El primer envío sigue guardando: se espera su resultado en vez de crear otra vez."""
        fin = time.monotonic() + ESPERA_MAXIMA
        while time.monotonic() < fin:
            valor = cache.get(clave)
            if isinstance(valor, dict):
                return _repetir(request, valor)
            if valor is None:  # el primero terminó con errores: este envío sigue su curso normal
                return self.get_response(request)
            time.sleep(0.2)
        messages.info(request, "El formulario se está guardando. Revisa en un momento si quedó registrado.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER") or "/dashboard")

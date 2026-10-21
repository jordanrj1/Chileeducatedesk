"""Pide al navegador que no guarde las páginas de quien tiene la sesión iniciada. Así, al volver con «Atrás» o al
reabrir una pestaña, siempre se ve la versión actual (y nada queda a la vista después de cerrar sesión)."""


class SinCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        usuario = getattr(request, "user", None)
        if usuario is not None and usuario.is_authenticated and respuesta.get("Content-Type", "").startswith("text/html"):
            respuesta["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        return respuesta

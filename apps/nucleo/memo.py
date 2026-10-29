"""F26 Rb: memoria de una sola petición. Una misma consulta de opciones (un catálogo, las primeras personas de un
buscador) se lee una vez aunque la pidan varios campos o varias filas del mismo formulario. Se vacía al terminar la
petición, así nunca muestra datos de otra; fuera de una petición (pruebas de formularios, consola) no guarda nada."""
from contextvars import ContextVar

from django.core.exceptions import EmptyResultSet
from django.db.models import Prefetch

_memo = ContextVar("fche_memo_peticion", default=None)


class MemoPeticionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _memo.set({})
        try:
            return self.get_response(request)
        finally:
            _memo.reset(token)


def _clave(qs):
    """La consulta SQL (con sus valores) y lo que se precarga: dos consultas iguales dan la misma clave."""
    precargas = []
    for p in qs._prefetch_related_lookups:
        if isinstance(p, Prefetch):
            precargas.append((p.prefetch_through, p.prefetch_to, str(p.queryset.query) if p.queryset is not None else ""))
        else:
            precargas.append(str(p))
    return (qs.model._meta.label, str(qs.query), tuple(precargas))


def lista(qs):
    """Los registros de `qs` como lista, leídos una sola vez por petición."""
    memo = _memo.get()
    if memo is None:
        return list(qs)
    try:
        clave = _clave(qs)
    except EmptyResultSet:
        return []
    if clave not in memo:
        memo[clave] = list(qs)
    return memo[clave]

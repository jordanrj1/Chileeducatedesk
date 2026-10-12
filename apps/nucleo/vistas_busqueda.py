from django.core.paginator import Paginator
from django.views.generic import TemplateView

from . import busqueda
from .models import EstadoActividad, EstadoRegistro, TipoActividad
from .vistas_base import Permiso403Mixin


class Buscar(Permiso403Mixin, TemplateView):
    template_name = "nucleo/buscar.html"

    def has_permission(self):
        u = self.request.user
        return u.is_authenticated and u.groups.exists()

    def get_context_data(self, **kw):
        from apps.territorio.models import Comuna

        ctx = super().get_context_data(**kw)
        g = self.request.GET
        hay_criterio = any(g.get(k) for k in ("q", "tipo", "estado", "zona", "desde", "hasta", "tipo_actividad", "registro", "con_actividades"))
        resultados = busqueda.buscar(self.request.user, g) if hay_criterio else []
        pagina = Paginator(resultados, 50).get_page(g.get("page"))
        nombres = dict(busqueda.TIPOS)
        grupos = {}
        for r in pagina:
            grupos.setdefault(r.tipo, []).append(r)
        conteo = {}
        for r in resultados:
            conteo[r.tipo] = conteo.get(r.tipo, 0) + 1
        agrupados = [(nombres[t], conteo[t], grupos[t]) for t, _ in busqueda.TIPOS if t in grupos]
        params = g.copy()
        params.pop("page", None)
        ctx.update(
            titulo="Búsqueda", termino=g.get("q", "").strip(), pagina=pagina, agrupados=agrupados, total=len(resultados), hay_criterio=hay_criterio, querystring=params.urlencode(),
            tipos=busqueda.TIPOS, estados=EstadoActividad.objects.all(), comunas=Comuna.objects.all(), tipos_actividad=TipoActividad.objects.all(),
            registros=EstadoRegistro.objects.all(), datos=g,
        )
        return ctx

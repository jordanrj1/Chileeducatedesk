from django.views.generic import TemplateView

from .vistas_base import Permiso403Mixin


class Buscar(Permiso403Mixin, TemplateView):
    template_name = "nucleo/buscar.html"

    def has_permission(self):
        u = self.request.user
        return u.is_authenticated and u.groups.exists()

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Búsqueda", termino=self.request.GET.get("q", "").strip(), resultados=[])
        return ctx

from django.views.generic import TemplateView

from .vistas_base import Permiso403Mixin


class Dashboard(Permiso403Mixin, TemplateView):
    """Qué tengo que hacer hoy. Las tarjetas se registran en `nucleo.tablero`."""

    template_name = "nucleo/dashboard.html"

    def has_permission(self):
        u = self.request.user
        return u.is_authenticated and u.groups.exists()

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        from .tablero import tarjetas

        ctx["tarjetas"] = tarjetas(self.request.user)
        return ctx

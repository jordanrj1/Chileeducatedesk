from django.utils import timezone
from django.views.generic import TemplateView

from .vistas_base import Permiso403Mixin


def saludo(hora):
    return "Buenos días" if 5 <= hora < 12 else "Buenas tardes" if 12 <= hora < 20 else "Buenas noches"


class Dashboard(Permiso403Mixin, TemplateView):
    """Qué tengo que hacer hoy. Las tarjetas se registran en `nucleo.tablero`."""

    template_name = "nucleo/dashboard.html"

    def has_permission(self):
        u = self.request.user
        return u.is_authenticated and u.groups.exists()

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        from .tablero import proximas, tarjetas

        todas = tarjetas(self.request.user)
        ctx["sistema"] = next((t for t in todas if t["titulo"] == "Estado del sistema"), None)
        ctx["tarjetas"] = [t for t in todas if t is not ctx["sistema"]]
        ctx["proximas"] = proximas(self.request.user)
        ctx["saludo"] = saludo(timezone.localtime().hour)
        ctx["hoy"] = timezone.localdate()
        return ctx

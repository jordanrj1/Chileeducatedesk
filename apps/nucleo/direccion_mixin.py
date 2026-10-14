"""Mixin para vistas que guardan un modelo junto a su Dirección (formulario secundario con prefijo 'dir')."""
from django.db import transaction

from apps.territorio.forms import DireccionForm


class ConDireccionMixin:
    direccion_requerida = False
    campo_direccion = "direccion"

    def direccion_inicial(self):
        """Valores con que parte la dirección de un registro nuevo. Las vistas de alta lo sobrescriben (p. ej. `?comuna=`)."""
        return {}

    def _form_dir(self):
        instancia = getattr(self.object, self.campo_direccion, None) if getattr(self, "object", None) else None
        if self.request.method == "POST":
            return DireccionForm(self.request.POST, instance=instancia, prefix="dir")
        return DireccionForm(instance=instancia, prefix="dir", initial=None if instancia else self.direccion_inicial())

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.setdefault("form_direccion", self._form_dir())
        return ctx

    @staticmethod
    def _vacio(form):
        return not any(form.data.get(form.add_prefix(c)) for c in ("calle", "numero", "block", "depto", "referencia", "comuna"))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if hasattr(self, "get_object") and "pk" in kwargs else None
        form = self.get_form()
        form_dir = self._form_dir()
        omitir = (not self.direccion_requerida) and self._vacio(form_dir)
        if form.is_valid() and hasattr(self, "version_en_conflicto") and self.version_en_conflicto():
            form.add_error(None, self.MENSAJE_VERSION)
            return self.render_to_response(self.get_context_data(form=form, form_direccion=form_dir))
        if form.is_valid() and (omitir or form_dir.is_valid()):
            with transaction.atomic():
                if not omitir:
                    direccion = form_dir.save()
                    setattr(form.instance, self.campo_direccion, direccion)
                return self.form_valid(form)
        return self.render_to_response(self.get_context_data(form=form, form_direccion=form_dir))


class ComunaInicialMixin:
    """Alta «desde la comuna»: `?comuna=<id>` deja esa comuna elegida en la dirección en cascada. Un valor inválido se ignora."""

    def comuna_inicial(self):
        if not hasattr(self, "_comuna_inicial"):  # la vista vive una sola solicitud
            from apps.territorio.models import Comuna

            valor = self.request.GET.get("comuna", "")
            self._comuna_inicial = Comuna.objects.filter(pk=valor).first() if valor.isascii() and valor.isdigit() else None
        return self._comuna_inicial

    def direccion_inicial(self):
        comuna = self.comuna_inicial()
        return {"comuna": comuna.pk} if comuna else {}

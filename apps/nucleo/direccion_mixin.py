"""Mixin para vistas que guardan un modelo junto a su Dirección (formulario secundario con prefijo 'dir'), con la ubicación
en cascada. Sin JavaScript, «Actualizar listas» vuelve a dibujar la página con las listas al día, sin guardar ni marcar errores."""
from django.db import transaction

from apps.territorio.forms import DireccionForm
from apps.territorio.ubicacion import sin_errores


class ConDireccionMixin:
    direccion_requerida = False
    campo_direccion = "direccion"
    direccion_contexto = ""  # «lugar»: la ubicación muestra lo que ya hay en la comuna elegida

    def direccion_inicial(self):
        """Valores con que parte la dirección de un registro nuevo. Las vistas de alta lo sobrescriben (p. ej. `?comuna=`)."""
        return {}

    def _form_dir(self):
        instancia = getattr(self.object, self.campo_direccion, None) if getattr(self, "object", None) else None
        kw = {"instance": instancia, "prefix": "dir", "ubicacion_contexto": self.direccion_contexto}
        if self.request.method == "POST":
            return DireccionForm(self.request.POST, **kw)
        return DireccionForm(initial=None if instancia else self.direccion_inicial(), **kw)

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        if "form_direccion" not in ctx:  # se arma solo si la vista no lo pasó (cada dirección consulta sus listas)
            ctx["form_direccion"] = self._form_dir()
        return ctx

    @staticmethod
    def _vacio(form):
        return not any(form.data.get(form.add_prefix(c)) for c in ("calle", "numero", "block", "depto", "referencia", "comuna"))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if hasattr(self, "get_object") and "pk" in kwargs else None
        form = self.get_form()
        form_dir = self._form_dir()
        if form_dir.actualizando_ubicacion:  # sin JavaScript: solo se pidió ver las listas al día
            sin_errores(form)
            return self.render_to_response(self.get_context_data(form=form, form_direccion=form_dir))
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
    """Alta «desde la comuna» o «desde el sector»: `?comuna=<id>` (y `&sector=<id>`) deja esa elección en la dirección en cascada.

    Un valor inválido se ignora; un sector solo vale junto a su comuna, y uno desactivado no sirve de punto de partida.
    """

    def comuna_inicial(self):
        if not hasattr(self, "_comuna_inicial"):  # la vista vive una sola solicitud
            from apps.territorio.models import Comuna

            valor = self.request.GET.get("comuna", "")
            self._comuna_inicial = Comuna.objects.filter(pk=valor).first() if valor.isascii() and valor.isdigit() else None
        return self._comuna_inicial

    def sector_inicial(self):
        """El sector de `?sector=` si existe, está activo y pertenece a la comuna de `?comuna=`; si no, `None`."""
        if not hasattr(self, "_sector_inicial"):
            from apps.territorio.models import Sector

            comuna, valor = self.comuna_inicial(), self.request.GET.get("sector", "")
            self._sector_inicial = Sector.objects.filter(pk=valor, comuna=comuna, activo=True).first() if comuna and valor.isascii() and valor.isdigit() else None
        return self._sector_inicial

    def direccion_inicial(self):
        comuna = self.comuna_inicial()
        if not comuna:
            return {}
        sector = self.sector_inicial()
        return {"comuna": comuna.pk, **({"sector": sector.pk} if sector else {})}

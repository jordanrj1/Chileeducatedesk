"""Alta, edición y des/activación de registros hijos de una ficha (contactos, formación, etc.). Nunca se borran."""
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path
from django.views import View
from django.views.generic import CreateView, UpdateView

from .vistas_base import Permiso403Mixin


class _HijoBase:
    modelo = None
    form_class = None
    padre_modelo = None
    campo_padre = None
    tab = ""
    etiqueta = ""
    permiso_extra = None  # permiso adicional (datos sensibles)
    campo_vigente = "vigente"
    template_name = "generico/formulario.html"

    def get_permission_required(self):
        return self.permisos_requeridos()

    def _perm_modelo(self, accion):
        m = self.modelo._meta
        return [f"{m.app_label}.{accion}_{m.model_name}"] + ([self.permiso_extra] if self.permiso_extra else [])

    def url_padre(self):
        return f"{self.padre.get_absolute_url()}?tab={self.tab}"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo=self.titulo(), volver_url=self.url_padre(), breadcrumb=[(str(self.padre), self.padre.get_absolute_url())])
        return ctx


class HijoCrear(_HijoBase, Permiso403Mixin, CreateView):
    def permisos_requeridos(self):
        return self._perm_modelo("add")

    def dispatch(self, request, *a, **kw):
        self.padre = get_object_or_404(self.padre_modelo, pk=kw["pk"])
        return super().dispatch(request, *a, **kw)

    def titulo(self):
        return f"Agregar {self.etiqueta}"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["instance"] = self.modelo(**{self.campo_padre: self.padre})  # el padre ya está puesto al validar
        return kw

    def form_valid(self, form):
        setattr(form.instance, self.campo_padre, self.padre)
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error(None, "Ya existe un registro igual.")
            return self.form_invalid(form)
        messages.success(self.request, "Guardado.")
        return HttpResponseRedirect(self.url_padre())


class HijoEditar(_HijoBase, Permiso403Mixin, UpdateView):
    pk_url_kwarg = "hijo_pk"

    def permisos_requeridos(self):
        return self._perm_modelo("change")

    def get_queryset(self):
        return self.modelo._default_manager.all()

    def dispatch(self, request, *a, **kw):
        obj = get_object_or_404(self.modelo, pk=kw["hijo_pk"])
        self.padre = getattr(obj, self.campo_padre)
        if self.padre.pk != kw["pk"]:
            from django.http import Http404

            raise Http404
        return super().dispatch(request, *a, **kw)

    def titulo(self):
        return f"Editar {self.etiqueta}"

    def form_valid(self, form):
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error(None, "Ya existe un registro igual.")
            return self.form_invalid(form)
        messages.success(self.request, "Guardado.")
        return HttpResponseRedirect(self.url_padre())


class HijoAlternar(_HijoBase, Permiso403Mixin, View):
    def permisos_requeridos(self):
        return self._perm_modelo("change")

    def post(self, request, pk, hijo_pk):
        obj = get_object_or_404(self.modelo, pk=hijo_pk)
        self.padre = getattr(obj, self.campo_padre)
        if self.padre.pk != pk:
            from django.http import Http404

            raise Http404
        setattr(obj, self.campo_vigente, not getattr(obj, self.campo_vigente))
        obj.save()
        messages.success(request, "Marcado como vigente." if getattr(obj, self.campo_vigente) else "Marcado como no vigente; se conserva en el historial.")
        return HttpResponseRedirect(self.url_padre())


def urls_hijo(base, slug, nombre, **attrs):
    """Genera las tres rutas de un hijo bajo `base/<pk>/<slug>/…`."""
    crear = type(f"Crear{nombre}", (HijoCrear,), attrs)
    editar = type(f"Editar{nombre}", (HijoEditar,), attrs)
    res = [
        path(f"{base}/<int:pk>/{slug}/nuevo", crear.as_view(), name=f"{slug}_nuevo"),
        path(f"{base}/<int:pk>/{slug}/<int:hijo_pk>/editar", editar.as_view(), name=f"{slug}_editar"),
    ]
    if attrs.get("campo_vigente") is not None or hasattr(attrs["modelo"], "vigente"):
        alternar = type(f"Alternar{nombre}", (HijoAlternar,), attrs)
        res.append(path(f"{base}/<int:pk>/{slug}/<int:hijo_pk>/alternar", alternar.as_view(), name=f"{slug}_alternar"))
    return res

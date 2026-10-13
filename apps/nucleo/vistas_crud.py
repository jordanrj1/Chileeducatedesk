"""Vistas base de alta, edición y detalle simple, reutilizadas por varios módulos."""
from django import forms
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, DetailView, UpdateView

from .vistas_base import ControlVersionMixin, Permiso403Mixin


class Nuevo(Permiso403Mixin, CreateView):
    template_name = "generico/formulario.html"
    titulo = ""
    lista_url = "/dashboard"
    breadcrumb_ = ()
    prefill = ()  # nombres de parámetros GET que precargan campos

    def get_initial(self):
        ini = super().get_initial()
        for k in self.prefill:
            v = self.request.GET.get(k, "")
            if v.isdigit() and k in self.form_class.base_fields:
                ini[k] = int(v)
        if "fecha" in self.form_class.base_fields and isinstance(self.form_class.base_fields["fecha"], forms.DateTimeField):
            ini["fecha"] = timezone.localtime().strftime("%Y-%m-%dT%H:%M")
        return ini

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo=self.titulo, volver_url=self.request.META.get("HTTP_REFERER") or self.lista_url, breadcrumb=list(self.breadcrumb_))
        return ctx

    def despues(self, obj):
        return obj.get_absolute_url()

    def form_valid(self, form):
        obj = form.save(commit=False)
        if hasattr(obj, "creado_por_id"):
            obj.creado_por = self.request.user
        with transaction.atomic():
            obj.save()
            self.hook(form, obj)
        messages.success(self.request, "Guardado.")
        return HttpResponseRedirect(self.despues(obj))

    def hook(self, form, obj):
        pass


class Editar(ControlVersionMixin, Permiso403Mixin, UpdateView):
    template_name = "generico/formulario.html"
    titulo = ""

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo=self.titulo, volver_url=self.object.get_absolute_url(), breadcrumb=[])
        return ctx

    def form_valid(self, form):
        if self.version_en_conflicto():
            form.add_error(None, self.MENSAJE_VERSION)
            return self.form_invalid(form)
        with transaction.atomic():
            obj = form.save()
            self.hook(form, obj)
        messages.success(self.request, "Guardado.")
        return HttpResponseRedirect(obj.get_absolute_url())

    def hook(self, form, obj):
        pass


class Detalle(Permiso403Mixin, DetailView):
    template_name = "generico/detalle.html"
    campos = ()
    lista_url = "/dashboard"
    nombre_url_editar = None
    permiso_editar = None

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        filas = []
        for etiqueta, attr in self.campos:
            v = self.object
            for parte in attr.split("."):
                v = getattr(v, parte, None) if v is not None else None
                if callable(v):
                    v = v()
            filas.append((etiqueta, v if v not in (None, "") else "—"))
        ctx.update(
            titulo=str(self.object), filas=filas, volver_url=self.lista_url, breadcrumb=[],
            url_editar=reverse(self.nombre_url_editar, args=[self.object.pk]) if self.nombre_url_editar and self.request.user.has_perm(self.permiso_editar) else None,
            extra=self.extra(),
        )
        return ctx

    def extra(self):
        return {}



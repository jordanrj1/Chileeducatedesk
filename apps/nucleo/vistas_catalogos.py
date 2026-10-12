"""F17 — Administración de catálogos. Desactivar nunca borra; se muestran las dependencias."""
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .formularios import BootstrapMixin
from .models import CATALOGOS
from .vistas_base import Permiso403Mixin


def dependencias(obj):
    """[(etiqueta, cantidad)] de registros que usan este valor."""
    res = []
    for rel in obj._meta.get_fields(include_hidden=True):
        if not (rel.auto_created and (rel.one_to_many or rel.one_to_one)) or rel.related_model.__name__.startswith("Historical"):
            continue
        n = rel.related_model._default_manager.filter(**{rel.field.name: obj}).count()
        if n:
            res.append((str(rel.related_model._meta.verbose_name_plural), n))
    return res


def _modelo(slug):
    try:
        return CATALOGOS[slug]
    except KeyError:
        raise Http404


def _perm(request, accion, modelo):
    if not request.user.has_perm(f"nucleo.{accion}_{modelo._meta.model_name}"):
        raise PermissionDenied


def _form(modelo):
    class F(BootstrapMixin, forms.ModelForm):
        class Meta:
            model = modelo
            fields = ["nombre", "orden", "activo"]

    return F


class Indice(Permiso403Mixin, View):
    permission_required = "nucleo.view_estadoactividad"

    def get(self, request):
        items = [(slug, m._meta.verbose_name_plural.capitalize(), m.objects.count()) for slug, m in CATALOGOS.items()]
        return render(request, "administracion/catalogos.html", {"items": items, "titulo": "Catálogos", "breadcrumb": [("Administración", "/administracion/")]})


class Lista(View):
    def get(self, request, slug):
        modelo = _modelo(slug)
        _perm(request, "view", modelo)
        filas = [(o, dependencias(o)) for o in modelo.objects.all()]
        form = _form(modelo)(initial={"activo": True})
        return render(request, "administracion/catalogo.html", {
            "slug": slug, "filas": filas, "form": form, "titulo": modelo._meta.verbose_name_plural.capitalize(),
            "puede_crear": request.user.has_perm(f"nucleo.add_{modelo._meta.model_name}"),
            "puede_editar": request.user.has_perm(f"nucleo.change_{modelo._meta.model_name}"),
            "puede_desactivar": request.user.has_perm(f"nucleo.desactivar_{modelo._meta.model_name}"),
            "breadcrumb": [("Administración", "/administracion/"), ("Catálogos", "/administracion/catalogos/")],
        })

    def post(self, request, slug):
        modelo = _modelo(slug)
        _perm(request, "add", modelo)
        form = _form(modelo)(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Opción creada.")
        else:
            messages.error(request, "No se pudo crear: " + "; ".join(e for es in form.errors.values() for e in es))
        return redirect("nucleo:catalogo", slug=slug)


class Editar(View):
    def _obj(self, request, slug, pk):
        modelo = _modelo(slug)
        _perm(request, "change", modelo)
        return modelo, get_object_or_404(modelo, pk=pk)

    def get(self, request, slug, pk):
        modelo, obj = self._obj(request, slug, pk)
        return render(request, "generico/formulario.html", {
            "form": _form(modelo)(instance=obj), "titulo": f"Editar: {obj}", "volver_url": f"/administracion/catalogos/{slug}/",
            "breadcrumb": [("Administración", "/administracion/"), ("Catálogos", "/administracion/catalogos/")],
        })

    def post(self, request, slug, pk):
        modelo, obj = self._obj(request, slug, pk)
        form = _form(modelo)(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Opción actualizada.")
            return redirect("nucleo:catalogo", slug=slug)
        return render(request, "generico/formulario.html", {"form": form, "titulo": f"Editar: {obj}", "volver_url": f"/administracion/catalogos/{slug}/", "breadcrumb": []}, status=400)


class Alternar(View):
    def post(self, request, slug, pk):
        modelo = _modelo(slug)
        _perm(request, "desactivar", modelo)
        obj = get_object_or_404(modelo, pk=pk)
        obj.activo = not obj.activo
        obj.save()
        messages.success(request, "Opción activada." if obj.activo else "Opción desactivada; el historial se conserva.")
        return redirect("nucleo:catalogo", slug=slug)

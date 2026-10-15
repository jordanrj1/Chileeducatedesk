"""Pantallas de catálogos (F17): lista de catálogos, valores de cada uno, agregar, editar, desactivar y unir repetidos.
Desactivar nunca borra, y antes de hacerlo se muestra cuántos registros usan ese valor."""
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .formularios import BootstrapMixin
from .models import CATALOGOS
from .vistas_base import Permiso403Mixin  # noqa: F401


def dependencias(obj):
    """[(etiqueta, cantidad)] de registros que usan este valor."""
    res = []
    for rel in obj._meta.get_fields(include_hidden=True):
        if not (rel.auto_created and (rel.one_to_many or rel.one_to_one)) or rel.related_model.__name__.startswith("Historical"):
            continue
        n = rel.related_model._default_manager.filter(**{rel.field.name: obj}).count()
        if n:  # en una selección múltiple (tabla intermedia automática) se nombra al dueño: «3 actividades», no la tabla intermedia
            dueno = rel.related_model._meta.auto_created or rel.related_model
            res.append((str(dueno._meta.verbose_name_plural), n))
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
            fields = ["nombre", *getattr(modelo, "campos_extra", []), "orden", "activo"]

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
            "con_edades": "edad_min" in getattr(modelo, "campos_extra", []),
            "con_ficha": "ficha" in getattr(modelo, "campos_extra", []),
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


class Unir(__import__("apps.nucleo.vistas_fusion", fromlist=["FusionarBase"]).FusionarBase):
    """CO-E4: un valor mal escrito se une a otro; lo que lo usaba pasa al correcto."""

    titulo = "Unir valores del catálogo"

    def get_origen(self, **kw):
        self.modelo = _modelo(kw["slug"])
        self.slug = kw["slug"]
        return get_object_or_404(self.modelo, pk=kw["pk"])

    def permiso_requerido(self, origen):
        return f"nucleo.desactivar_{self.modelo._meta.model_name}"

    def campo_destino(self, origen):
        from django import forms as f

        return f.ModelChoiceField(self.modelo.objects.filter(activo=True).exclude(pk=origen.pk), label="Valor que se conserva")

    def volver(self):
        return f"/administracion/catalogos/{self.slug}/"

    def destino_url(self, destino):
        return self.volver()


class Alternar(View):
    def post(self, request, slug, pk):
        modelo = _modelo(slug)
        _perm(request, "desactivar", modelo)
        obj = get_object_or_404(modelo, pk=pk)
        obj.activo = not obj.activo
        obj.save()
        messages.success(request, "Opción activada." if obj.activo else "Opción desactivada; el historial se conserva.")
        return redirect("nucleo:catalogo", slug=slug)

from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html, format_html_join
from django.views import View

from apps.nucleo.vistas_base import ListaBase, Permiso403Mixin

from .forms import SectorForm
from .models import Comuna, Sector


class ComunasLista(ListaBase):
    model = Comuna
    permission_required = "territorio.view_comuna"
    titulo = "Territorio"
    campos_busqueda = ("nombre", "provincia__nombre", "provincia__region__nombre", "codigo")
    columnas = [
        ("Comuna", "nombre"),
        ("Provincia", "provincia.nombre"),
        ("Región", "provincia.region.nombre"),
        ("Sectores", lambda c: c.n_sectores),
    ]
    ordenes = {"comuna": "nombre", "provincia": "provincia__nombre"}
    orden_defecto = ("provincia__region__codigo", "nombre")
    texto_vacio = "El territorio aún no se ha cargado. Usa el comando cargar_territorio con el archivo oficial (códigos CUT)."

    def get_queryset(self):
        return super().get_queryset().select_related("provincia__region").annotate(n_sectores=Count("sectores"))


class ComunaDetalle(Permiso403Mixin, View):
    permission_required = "territorio.view_comuna"

    def contexto(self, request, comuna, form):
        raices = comuna.sectores.filter(sector_padre__isnull=True).prefetch_related("hijos__hijos")
        return {
            "comuna": comuna,
            "raices": raices,
            "form": form,
            "titulo": comuna.nombre,
            "breadcrumb": [("Territorio", "/territorio")],
            "puede_crear": request.user.has_perm("territorio.add_sector"),
        }

    def get(self, request, pk):
        comuna = get_object_or_404(Comuna.objects.select_related("provincia__region"), pk=pk)
        return render(request, "territorio/comuna.html", self.contexto(request, comuna, SectorForm(comuna=comuna)))

    def post(self, request, pk):
        if not request.user.has_perm("territorio.add_sector"):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        comuna = get_object_or_404(Comuna, pk=pk)
        form = SectorForm(request.POST, comuna=comuna)
        if form.is_valid():
            form.save()
            messages.success(request, "Sector agregado.")
            return redirect("territorio:comuna", pk=pk)
        return render(request, "territorio/comuna.html", self.contexto(request, comuna, form), status=400)


class SectoresOpciones(Permiso403Mixin, View):
    """Devuelve <option> de los sectores de una comuna (para HTMX)."""

    permission_required = "territorio.view_sector"

    def get(self, request):
        valor = next((v for v in request.GET.values() if v.isdigit()), None)
        opciones = [("", "---------")]
        if valor:
            opciones += [(s.pk, str(s)) for s in Sector.objects.filter(comuna_id=valor).select_related("sector_padre")]
        return HttpResponse(format_html_join("", '<option value="{}">{}</option>', opciones))

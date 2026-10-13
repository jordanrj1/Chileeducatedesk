from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.views import View
from django.views.generic import TemplateView

from apps.nucleo.vistas_base import FichaBase, Permiso403Mixin

from . import consultas
from .forms import AliasForm, SectorForm
from .models import Comuna, Provincia, Region, Sector
from .reconocer import mismo_sector, sectores_parecidos

RAIZ = [("Territorio", "/territorio")]


def _opciones(pares, seleccionado=None):
    filas = [("", "", "---------")] + [(pk, "selected" if seleccionado and pk == seleccionado else "", texto) for pk, texto in pares]
    return format_html_join("", '<option value="{}" {}>{}</option>', filas)


def _valor(request):
    return next((v for v in request.GET.values() if v.isdigit()), None)


class TerritorioIndice(Permiso403Mixin, TemplateView):
    """Navegación región → provincia → comuna, o búsqueda directa de una comuna."""

    permission_required = "territorio.view_comuna"
    template_name = "territorio/indice.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        q = self.request.GET.get("q", "").strip()
        ctx.update(titulo="Territorio", q=q)
        if q:
            ctx["comunas"] = Comuna.objects.filter(nombre__unaccent__icontains=q).select_related("provincia__region")[:60]
        else:
            ctx["regiones"] = Region.objects.annotate(n_provincias=Count("provincias", distinct=True), n_comunas=Count("provincias__comunas"))
        return ctx


class RegionDetalle(Permiso403Mixin, TemplateView):
    permission_required = "territorio.view_comuna"
    template_name = "territorio/region.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        region = get_object_or_404(Region, pk=self.kwargs["pk"])
        ctx.update(region=region, titulo=region.nombre, breadcrumb=RAIZ, provincias=region.provincias.prefetch_related("comunas"))
        return ctx


class _FichaTerritorio(FichaBase):
    """Pestañas con contador (TE-04)."""

    def contadores(self):
        return {}

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        n = self.contadores()
        ctx["pestanas"] = [(c, f"{e} ({n[c]})" if c in n else e) for c, e in ctx["pestanas"]]
        ctx["puede_agregar"] = self.request.user.has_perm("territorio.add_sector")
        return ctx

    def ctx_lugares(self):
        return {"lugares": self._lugares()}

    def ctx_organizaciones(self):
        return {"organizaciones": self._organizaciones()}

    def ctx_actividades(self):
        return {"actividades": self._actividades(), "comuna_ficha": getattr(self.object, "provincia_id", None) and self.object, "sectores_ficha": self._ids() if hasattr(self, "_ids") else None}


class ComunaFicha(_FichaTerritorio):
    model = Comuna
    permission_required = "territorio.view_comuna"
    pestanas = [
        ("sectores", "Sectores", "territorio/pestanas/sectores.html"),
        ("lugares", "Lugares", "territorio/pestanas/lugares.html", "lugares.view_lugar"),
        ("organizaciones", "Organizaciones", "territorio/pestanas/organizaciones.html", "organizaciones.view_organizacion"),
        ("comunidades", "Comunidades", "territorio/pestanas/comunidades.html", "comunidades.view_comunidad"),
        ("actividades", "Actividades", "territorio/pestanas/actividades.html", "actividades.view_actividad"),
    ]

    def get_queryset(self):
        return Comuna.objects.select_related("provincia__region")

    def _comunidades(self):
        return self.object.comunidades.filter(activo=True).select_related("sector", "organizacion")

    def ctx_comunidades(self):
        return {"comunidades": self._comunidades(), "url_nueva_comunidad": f"/comunidades/nueva?comuna={self.object.pk}"}

    @property
    def breadcrumb(self):
        r = self.object.provincia.region
        return RAIZ + [(r.nombre, r.get_absolute_url())]

    def _lugares(self):
        return consultas.lugares_de(comuna=self.object)

    def _organizaciones(self):
        return consultas.organizaciones_de(comuna=self.object)

    def _actividades(self):
        return consultas.actividades_de(comuna=self.object)

    def contadores(self):
        return {"sectores": self.object.sectores.count(), "lugares": self._lugares().count(), "organizaciones": self._organizaciones().count(),
                "comunidades": self._comunidades().count(), "actividades": self._actividades().count()}

    def contexto_ficha(self):
        from apps.organizaciones.models import Organizacion

        return {"url_volver": self.object.provincia.region.get_absolute_url(), "municipalidad": Organizacion.objects.filter(comuna_municipal=self.object).first()}

    def ctx_sectores(self):
        return {"raices": self.object.sectores.filter(sector_padre__isnull=True).prefetch_related("hijos__hijos", "alias"), "form": SectorForm(comuna=self.object), "url_crear": reverse("territorio:sector_nuevo", args=[self.object.pk])}


class SectorFicha(_FichaTerritorio):
    model = Sector
    permission_required = "territorio.view_sector"
    pestanas = [
        ("sectores", "Sectores dentro", "territorio/pestanas/sectores.html"),
        ("nombres", "Nombres alternativos", "territorio/pestanas/nombres.html"),
        ("lugares", "Lugares", "territorio/pestanas/lugares.html", "lugares.view_lugar"),
        ("organizaciones", "Organizaciones", "territorio/pestanas/organizaciones.html", "organizaciones.view_organizacion"),
        ("comunidades", "Comunidades", "territorio/pestanas/comunidades.html", "comunidades.view_comunidad"),
        ("actividades", "Actividades", "territorio/pestanas/actividades.html", "actividades.view_actividad"),
    ]
    permiso_editar = "territorio.change_sector"

    def _comunidades(self):
        from apps.comunidades.models import Comunidad

        return Comunidad.objects.filter(activo=True, sector_id__in=self._ids()).select_related("sector", "organizacion")

    def ctx_comunidades(self):
        return {"comunidades": self._comunidades(), "url_nueva_comunidad": f"/comunidades/nueva?comuna={self.object.comuna_id}"}

    def get_queryset(self):
        return Sector.objects.select_related("comuna__provincia__region", "sector_padre")

    @property
    def breadcrumb(self):
        return RAIZ + [(self.object.comuna.nombre, self.object.comuna.get_absolute_url())]

    def _ids(self):
        if not hasattr(self, "_ids_cache"):
            self._ids_cache = self.object.descendientes_ids()
        return self._ids_cache

    def _lugares(self):
        return consultas.lugares_de(sectores=self._ids())

    def _organizaciones(self):
        return consultas.organizaciones_de(sectores=self._ids())

    def _actividades(self):
        return consultas.actividades_de(sectores=self._ids())

    def contadores(self):
        return {"sectores": self.object.hijos.count(), "nombres": self.object.alias.count(), "lugares": self._lugares().count(), "organizaciones": self._organizaciones().count(),
                "comunidades": self._comunidades().count(), "actividades": self._actividades().count()}

    def contexto_ficha(self):
        return {"url_editar": reverse("territorio:sector_editar", args=[self.object.pk]), "url_volver": self.object.comuna.get_absolute_url()}

    def ctx_sectores(self):
        form = SectorForm(comuna=self.object.comuna, initial={"sector_padre": self.object.pk})
        return {"raices": self.object.hijos.prefetch_related("hijos", "alias"), "form": form, "url_crear": reverse("territorio:sector_nuevo", args=[self.object.comuna_id])}

    def ctx_nombres(self):
        return {"form_alias": AliasForm(), "url_alias": reverse("territorio:alias_nuevo", args=[self.object.pk])}


class SectorNuevo(Permiso403Mixin, View):
    """Crear sector desde la ficha de la comuna o de un sector."""

    permission_required = "territorio.add_sector"

    def post(self, request, pk):
        comuna = get_object_or_404(Comuna, pk=pk)
        form = SectorForm(request.POST, comuna=comuna)
        if form.is_valid():
            s = form.save()
            messages.success(request, f"Sector «{s}» agregado.")
            return redirect(s.sector_padre.get_absolute_url() if s.sector_padre_id else comuna.get_absolute_url())
        for e in form.non_field_errors() + [e for f in form.errors.values() for e in f]:
            messages.error(request, e)
        padre = form.data.get("sector_padre")
        destino = Sector.objects.filter(pk=padre).first() if str(padre).isdigit() else None
        return redirect(destino.get_absolute_url() if destino else comuna.get_absolute_url())


class SectorEditar(Permiso403Mixin, View):
    permission_required = "territorio.change_sector"

    def _ctx(self, s, form):
        return {"form": form, "titulo": f"Editar sector: {s.nombre}", "volver_url": s.get_absolute_url(), "breadcrumb": RAIZ + [(s.comuna.nombre, s.comuna.get_absolute_url())]}

    def get(self, request, pk):
        s = get_object_or_404(Sector, pk=pk)
        return render(request, "generico/formulario.html", self._ctx(s, SectorForm(instance=s)))

    def post(self, request, pk):
        s = get_object_or_404(Sector, pk=pk)
        form = SectorForm(request.POST, instance=s)
        if form.is_valid():
            form.save()
            messages.success(request, "Sector actualizado.")
            return redirect(s.get_absolute_url())
        return render(request, "generico/formulario.html", self._ctx(s, form), status=400)


class AliasNuevo(Permiso403Mixin, View):
    permission_required = "territorio.change_sector"

    def post(self, request, pk):
        s = get_object_or_404(Sector, pk=pk)
        form = AliasForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data["nombre"].strip()
            otro = mismo_sector(s.comuna, nombre, s.sector_padre)
            if otro and otro.pk != s.pk:
                messages.error(request, f"Ese nombre ya corresponde a «{otro}».")
            else:
                try:
                    with transaction.atomic():
                        s.alias.create(nombre=nombre)
                    messages.success(request, "Nombre alternativo agregado.")
                except IntegrityError:
                    messages.error(request, "Ese nombre alternativo ya estaba registrado.")
        return redirect(f"{s.get_absolute_url()}?tab=nombres")


# --- Opciones para la cascada (HTMX) -------------------------------------------------
class ProvinciasOpciones(Permiso403Mixin, View):
    permission_required = "territorio.view_comuna"

    def get(self, request):
        v = _valor(request)
        return HttpResponse(_opciones([(p.pk, p.nombre) for p in Provincia.objects.filter(region_id=v)] if v else []))


class ComunasOpciones(Permiso403Mixin, View):
    permission_required = "territorio.view_comuna"

    def get(self, request):
        v = _valor(request)
        qs = Comuna.objects.filter(provincia_id=v) if v else Comuna.objects.all()
        return HttpResponse(_opciones([(c.pk, c.nombre) for c in qs]))


class SectoresOpciones(Permiso403Mixin, View):
    """Devuelve <option> de los sectores de una comuna (para HTMX)."""

    permission_required = "territorio.view_sector"

    def get(self, request):
        v = _valor(request)
        return HttpResponse(_opciones([(s.pk, str(s)) for s in Sector.objects.filter(comuna_id=v).select_related("sector_padre")] if v else []))


class SectorCrearRapido(Permiso403Mixin, View):
    """[+ Crear sector] dentro de un formulario de dirección, sin salir (TE-06).

    Si el nombre coincide con uno existente (o con un nombre alternativo) se usa ese. Si solo se parece, avisa y pide confirmar.
    Responde las opciones del sector con el elegido seleccionado y un mensaje fuera de banda.
    """

    permission_required = "territorio.add_sector"

    def post(self, request):
        comuna_id = next((v for k, v in request.POST.items() if k.endswith("comuna") and v.isdigit()), None)
        nombre = request.POST.get("nuevo_sector_nombre", "").strip()
        tipo = request.POST.get("nuevo_sector_tipo", "sector")
        comuna = Comuna.objects.filter(pk=comuna_id).first() if comuna_id else None
        self.destino = request.headers.get("HX-Target", "")
        if not comuna or not nombre:
            return self._respuesta(comuna, None, "Elige la comuna y escribe el nombre del sector.", "danger")
        existente = mismo_sector(comuna, nombre)
        if existente:
            return self._respuesta(comuna, existente.pk, f"Ya existía «{existente}»: quedó seleccionado.", "info")
        parecidos = sectores_parecidos(comuna, nombre)
        if parecidos and request.POST.get("confirmar_sector") != "1":
            lista = ", ".join(f"«{p}»" for p in parecidos)
            return self._respuesta(comuna, None, f"Hay sectores parecidos: {lista}. Si es otro, pulsa «Crear igual».", "warning", confirmar=True)
        if tipo not in dict(Sector.TIPOS):
            tipo = "sector"
        s = Sector.objects.create(comuna=comuna, nombre=nombre, tipo=tipo)
        return self._respuesta(comuna, s.pk, f"Sector «{s}» creado y seleccionado.", "success")

    def _respuesta(self, comuna, seleccionado, mensaje, nivel, confirmar=False):
        pares = [(s.pk, str(s)) for s in Sector.objects.filter(comuna=comuna).select_related("sector_padre")] if comuna else []
        boton = format_html(
            ' <button type="button" class="btn btn-sm btn-outline-warning" hx-post="/territorio/sectores/crear" hx-include="closest .crear-sector, [name$=\'comuna\']" '
            'hx-vals=\'{{"confirmar_sector": "1"}}\' hx-target="#{}">Crear igual</button>', getattr(self, "destino", "") or "id_sector"
        ) if confirmar else ""
        aviso = format_html('<div id="aviso-sector" hx-swap-oob="true" class="small text-{}">{}{}</div>', nivel, mensaje, boton)
        return HttpResponse(_opciones(pares, seleccionado) + aviso)

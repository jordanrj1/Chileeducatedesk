from io import BytesIO
from itertools import groupby

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.text import slugify
from django.views import View
from django.views.generic import TemplateView

from apps.nucleo.auditoria import registrar
from apps.nucleo.vistas_base import FichaBase, Permiso403Mixin

from . import consultas
from .exportar import detalle_de, libro_territorial
from .forms import AliasForm, SectorForm
from .models import Comuna, Provincia, Region, Sector
from .reconocer import mismo_sector, sectores_parecidos
from .resumen import personas_residentes, presencia_por_comuna, resumen_territorio

RAIZ = [("Territorio", "/territorio")]


def _opciones(pares, seleccionado=None):
    filas = [("", "", "---------")] + [(pk, "selected" if seleccionado and pk == seleccionado else "", texto) for pk, texto in pares]
    return format_html_join("", '<option value="{}" {}>{}</option>', filas)


def _valor(request):
    return next((v for v in request.GET.values() if v.isdigit()), None)


class TerritorioIndice(Permiso403Mixin, TemplateView):
    """«Dónde trabajamos»: primero las comunas con presencia de la Fundación, luego todas las regiones; o búsqueda directa de una comuna."""

    permission_required = "territorio.view_comuna"
    template_name = "territorio/indice.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        q = self.request.GET.get("q", "").strip()
        ctx.update(titulo="Territorio", q=q)
        if q:
            ctx["comunas"] = Comuna.objects.filter(nombre__unaccent__icontains=q).select_related("provincia__region")[:60]
        else:
            ctx["regiones"] = regiones = Region.objects.annotate(n_provincias=Count("provincias", distinct=True), n_comunas=Count("provincias__comunas"))
            ctx["presencia"] = presencia_por_comuna() if regiones else []  # sin territorio cargado no hay nada que contar
        return ctx


class RegionDetalle(Permiso403Mixin, TemplateView):
    permission_required = "territorio.view_comuna"
    template_name = "territorio/region.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        region = get_object_or_404(Region, pk=self.kwargs["pk"])
        ctx.update(
            region=region, titulo=region.nombre, breadcrumb=RAIZ, provincias=region.provincias.prefetch_related("comunas"),
            presencia=presencia_por_comuna(region=region),
        )
        return ctx


LIMITE_PERSONAS = 200  # por grupo en la pestaña Personas; el resto, en el listado de Personas con el filtro de comuna
SECTOR_CON_PADRES = "sector__sector_padre__sector_padre"  # el nombre de un sector incluye el de su padre y su abuelo


class _FichaTerritorio(FichaBase):
    """Comuna o sector como contenedor del banco (F23): resumen, agrupaciones, personas y alcance; cada pestaña con su contador (TE-04).

    Cada pestaña usa un número fijo de consultas, sin importar cuántos registros tenga el territorio.
    Las subclases definen `comuna` (la comuna del contenedor) y `ambito()` (`{"comuna": ...}` o `{"sectores": [ids]}`).
    """

    template_name = "territorio/ficha.html"
    descripcion_ambito = ""  # «esta comuna», «este sector y los que contiene»
    ruta_exportar = ""  # nombre de la ruta del Excel del resumen (ComunaExportar, SectorExportar)

    # --- qué es de este territorio: las listas y los contadores traen los registros activos, igual que el resumen; los desactivados se piden aparte (`activo=False`) ---
    def _comunidades(self):
        from apps.comunidades.models import Comunidad

        sectores = self.ambito().get("sectores")
        filtro = {"sector_id__in": sectores} if sectores else {"comuna": self.comuna}
        return Comunidad.objects.filter(activo=True, **filtro).select_related(SECTOR_CON_PADRES, "organizacion")

    def _lugares(self, activo=True):
        """Lugares del territorio: los activos (lista principal y contador) o, con `activo=False`, los desactivados."""
        return consultas.lugares_de(**self.ambito()).filter(activo=activo).select_related(f"direccion__{SECTOR_CON_PADRES}")

    def _organizaciones(self, activo=True):
        """Organizaciones del territorio: las activas (lista principal y contador) o, con `activo=False`, las desactivadas."""
        return consultas.organizaciones_de(**self.ambito()).filter(activo=activo)

    def _actividades(self):
        return consultas.actividades_de(**self.ambito())

    def _residentes(self):
        return personas_residentes(**self.ambito())

    def _integrantes_no_residentes(self):
        """Integrantes vigentes de comunidades activas del territorio que no residen en él."""
        from apps.personas.models import Persona

        sectores = self.ambito().get("sectores")
        filtro = {"comunidades__comunidad__sector_id__in": sectores} if sectores else {"comunidades__comunidad__comuna": self.comuna}
        return (
            Persona.objects.filter(activo=True, comunidades__vigente=True, comunidades__comunidad__activo=True, **filtro)
            .exclude(pk__in=self._residentes().values("pk"))
            .distinct()
        )

    def _cuenta(self, clave, queryset):
        """Conteo que se usa en el contador de la pestaña y dentro de ella: se calcula una sola vez por respuesta."""
        cache = self.__dict__.setdefault("_cuentas", {})
        if clave not in cache:
            cache[clave] = queryset.count()
        return cache[clave]

    def conteos(self):
        """{pestaña: función que da su contador}; solo se calculan los de las pestañas visibles."""
        return {
            "lugares": lambda: self._lugares().count(),
            "organizaciones": lambda: self._organizaciones().count(),
            "comunidades": lambda: self._comunidades().count(),
            "actividades": lambda: self._actividades().count(),
            "personas": lambda: self._cuenta("residentes", self._residentes()) + self._cuenta("no_residentes", self._integrantes_no_residentes()),
        }

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        conteos = self.conteos()
        ctx["pestanas"] = [(c, f"{e} ({conteos[c]()})" if c in conteos else e) for c, e in ctx["pestanas"]]
        ctx["puede_agregar"] = self.request.user.has_perm("territorio.add_sector")
        return ctx

    def parametros_nuevo(self):
        """Consulta de los enlaces «+ Actividad», «+ Lugar»…: lo creado desde aquí parte en este territorio."""
        return f"comuna={self.comuna.pk}"

    def contexto_ficha(self):
        return {
            "comuna_contenedor": self.comuna, "nombre_ambito": self.object.nombre, "parametros_nuevo": self.parametros_nuevo(),
            "url_exportar_resumen": reverse(self.ruta_exportar, args=[self.object.pk]),
        }

    # --- pestañas ---
    def ctx_resumen(self):
        from apps.actividades.alcance import alcance

        r = resumen_territorio(**self.ambito())
        total_alcanzado = None
        if self.request.user.has_perm("actividades.view_participacion"):
            total_alcanzado = alcance(self._actividades())["total_alcanzado"]
        vacio = not any(r[k] for k in ("comunidades", "organizaciones", "personas", "lugares", "actividades_total"))
        return {"resumen": r, "total_alcanzado": total_alcanzado, "indicadores": self._indicadores(r, total_alcanzado), "resumen_vacio": vacio}

    def _indicadores(self, r, total_alcanzado):
        """Indicadores del resumen; cada uno enlaza a su pestaña si quien mira puede verla."""
        visibles = {p[0] for p in self.pestanas_visibles()}
        tipos = len(r["organizaciones_por_tipo"])
        filas = [
            ("comunidades", "Comunidades", r["comunidades"], "comunidades", "activas en el territorio"),
            ("organizaciones", "Organizaciones", r["organizaciones"], "organizaciones", f"de {tipos} tipo{'s' if tipos != 1 else ''}" if tipos else "aún sin registrar"),
            ("personas", "Residentes", r["personas"], "personas", "personas con residencia vigente aquí"),
            ("lugares", "Lugares", r["lugares"], "lugares", "salas, sedes y espacios"),
            ("actividades", "Actividades", r["actividades_12m"], "actividades", f"últimos 12 meses · {r['actividades_total']} en total"),
        ]
        if total_alcanzado is not None:
            filas.append(("alcance", "Total alcanzado", total_alcanzado, "usuarios_check", "asistentes registrados y sin registro"))
        return [{"clave": c, "titulo": t, "valor": v, "icono": i, "nota": n, "enlace": c in visibles} for c, t, v, i, n in filas]

    def ctx_personas(self):
        """Residentes e integrantes no residentes: solo nombre, perfiles y comunidad (sin RUT, contactos ni datos sensibles)."""
        from apps.comunidades.models import ComunidadMiembro

        membresias = ComunidadMiembro.objects.filter(vigente=True, comunidad__activo=True).select_related("comunidad").order_by("comunidad__nombre")
        sectores = self.ambito().get("sectores")
        del_territorio = membresias.filter(**({"comunidad__sector_id__in": sectores} if sectores else {"comunidad__comuna": self.comuna}))

        def listar(personas, comunidades):
            return list(personas.prefetch_related("perfiles", Prefetch("comunidades", queryset=comunidades, to_attr="membresias"))[:LIMITE_PERSONAS])

        return {
            "residentes": listar(self._residentes(), membresias),
            "integrantes_no_residentes": listar(self._integrantes_no_residentes(), del_territorio),
            "n_residentes": self._cuenta("residentes", self._residentes()),
            "n_no_residentes": self._cuenta("no_residentes", self._integrantes_no_residentes()),
            "limite_personas": LIMITE_PERSONAS,
        }

    def ctx_alcance(self):
        from apps.actividades.alcance import alcance

        return {"alcance": alcance(self._actividades()), "contexto_alcance": f"las actividades de {self.descripcion_ambito}"}

    def ctx_lugares(self):
        """Activos en la lista principal; los desactivados aparte y atenuados, para no perder su historia de vista."""
        return {"lugares": list(self._lugares()), "lugares_inactivos": list(self._lugares(activo=False).order_by("nombre", "pk"))}

    def ctx_organizaciones(self):
        """Activas agrupadas por tipo, en el orden del catálogo: [(TipoOrganizacion, total, [Organizacion])]; las desactivadas, aparte."""
        orgs = self._organizaciones().select_related(f"direccion__{SECTOR_CON_PADRES}").order_by("tipo__orden", "tipo__nombre", "nombre", "pk")
        grupos = [(tipo, list(lista)) for tipo, lista in groupby(orgs, key=lambda o: o.tipo)]
        inactivas = self._organizaciones(activo=False).select_related(f"direccion__{SECTOR_CON_PADRES}").order_by("nombre", "pk")
        return {"grupos_organizaciones": [(tipo, len(lista), lista) for tipo, lista in grupos], "organizaciones_inactivas": list(inactivas)}

    def ctx_comunidades(self):
        return {"comunidades": self._comunidades(), "url_nueva_comunidad": f"/comunidades/nueva?{self.parametros_nuevo()}"}

    def ctx_actividades(self):
        """BU-E7: distingue «realizada en» (su lugar está aquí) de «dirigida a» (solo indica el territorio), sin consultas por fila."""
        from apps.actividades.models import ActividadTerritorio, AgendaActividad

        actividades = list(self._actividades())
        ids = [a.pk for a in actividades]
        sectores = self.ambito().get("sectores")
        if sectores:
            agendas = AgendaActividad.objects.filter(lugar__direccion__sector_id__in=sectores)
            territorios = ActividadTerritorio.objects.filter(sector_id__in=sectores)
        else:
            agendas = AgendaActividad.objects.filter(lugar__direccion__comuna=self.comuna)
            territorios = ActividadTerritorio.objects.filter(Q(comuna=self.comuna) | Q(sector__comuna=self.comuna))
        realizadas = {ag.actividad_id: ag.lugar for ag in agendas.filter(vigente=True, actividad_id__in=ids).select_related("lugar")}
        dirigidas = set(territorios.filter(vigente=True, actividad_id__in=ids).values_list("actividad_id", flat=True))
        for a in actividades:
            partes = [f"Realizada en {realizadas[a.pk]}"] if a.pk in realizadas else []
            if a.pk in dirigidas:
                partes.append("Dirigida a este territorio")
            a.relacion_territorial = " · ".join(partes)
        return {"actividades": actividades}


class ComunaFicha(_FichaTerritorio):
    model = Comuna
    permission_required = "territorio.view_comuna"
    descripcion_ambito = "esta comuna"
    ruta_exportar = "territorio:comuna_exportar"
    pestanas = [
        ("resumen", "Resumen", "territorio/pestanas/resumen.html"),
        ("sectores", "Sectores", "territorio/pestanas/sectores.html"),
        ("comunidades", "Comunidades", "territorio/pestanas/comunidades.html", "comunidades.view_comunidad"),
        ("organizaciones", "Organizaciones", "territorio/pestanas/organizaciones.html", "organizaciones.view_organizacion"),
        ("personas", "Personas", "territorio/pestanas/personas.html", "personas.view_persona"),
        ("lugares", "Lugares", "territorio/pestanas/lugares.html", "lugares.view_lugar"),
        ("actividades", "Actividades", "territorio/pestanas/actividades.html", "actividades.view_actividad"),
        ("alcance", "Alcance", "actividades/pestanas/alcance.html", "actividades.view_participacion"),
    ]

    def get_queryset(self):
        return Comuna.objects.select_related("provincia__region")

    @property
    def comuna(self):
        return self.object

    def ambito(self):
        return {"comuna": self.object}

    @property
    def breadcrumb(self):
        r = self.object.provincia.region
        return RAIZ + [(r.nombre, r.get_absolute_url())]

    def conteos(self):
        return {"sectores": lambda: self.object.sectores.count(), **super().conteos()}

    def contexto_ficha(self):
        from apps.organizaciones.models import Organizacion

        municipalidad = Organizacion.objects.filter(comuna_municipal=self.object).order_by("-activo", "pk").first()
        return {**super().contexto_ficha(), "url_volver": self.object.provincia.region.get_absolute_url(), "municipalidad": municipalidad}

    def ctx_sectores(self):
        return {"raices": self.object.sectores.filter(sector_padre__isnull=True).prefetch_related("hijos__hijos", "alias"), "form": SectorForm(comuna=self.object), "url_crear": reverse("territorio:sector_nuevo", args=[self.object.pk])}


class SectorFicha(_FichaTerritorio):
    """El sector como contenedor: todo se calcula sobre el sector y los que contiene (etapas, villas…)."""

    model = Sector
    permission_required = "territorio.view_sector"
    descripcion_ambito = "este sector y los que contiene"
    ruta_exportar = "territorio:sector_exportar"
    pestanas = [
        ("resumen", "Resumen", "territorio/pestanas/resumen.html"),
        ("sectores", "Sectores dentro", "territorio/pestanas/sectores.html"),
        ("nombres", "Nombres alternativos", "territorio/pestanas/nombres.html"),
        ("comunidades", "Comunidades", "territorio/pestanas/comunidades.html", "comunidades.view_comunidad"),
        ("organizaciones", "Organizaciones", "territorio/pestanas/organizaciones.html", "organizaciones.view_organizacion"),
        ("personas", "Personas", "territorio/pestanas/personas.html", "personas.view_persona"),
        ("lugares", "Lugares", "territorio/pestanas/lugares.html", "lugares.view_lugar"),
        ("actividades", "Actividades", "territorio/pestanas/actividades.html", "actividades.view_actividad"),
        ("alcance", "Alcance", "actividades/pestanas/alcance.html", "actividades.view_participacion"),
    ]
    permiso_editar = "territorio.change_sector"

    def get_queryset(self):
        return Sector.objects.select_related("comuna__provincia__region", "sector_padre__sector_padre")

    @property
    def comuna(self):
        return self.object.comuna

    def ambito(self):
        return {"sectores": self._ids()}

    @property
    def breadcrumb(self):
        return RAIZ + [(self.object.comuna.nombre, self.object.comuna.get_absolute_url())]

    def parametros_nuevo(self):
        return f"comuna={self.object.comuna_id}&sector={self.object.pk}"

    def _ids(self):
        if not hasattr(self, "_ids_cache"):
            self._ids_cache = self.object.descendientes_ids()
        return self._ids_cache

    def conteos(self):
        return {"sectores": lambda: self.object.hijos.count(), "nombres": lambda: self.object.alias.count(), **super().conteos()}

    def contexto_ficha(self):
        return {**super().contexto_ficha(), "es_sector": True, "url_editar": reverse("territorio:sector_editar", args=[self.object.pk]), "url_volver": self.object.comuna.get_absolute_url()}

    def ctx_sectores(self):
        form = SectorForm(comuna=self.object.comuna, initial={"sector_padre": self.object.pk})
        return {"raices": self.object.hijos.prefetch_related("hijos__hijos", "alias"), "form": form, "url_crear": reverse("territorio:sector_nuevo", args=[self.object.comuna_id])}

    def ctx_nombres(self):
        return {"form_alias": AliasForm(), "url_alias": reverse("territorio:alias_nuevo", args=[self.object.pk])}


class _Exportar(Permiso403Mixin, View):
    """Excel del resumen territorial (F23) de una comuna o un sector. Queda en la auditoría; lleva el aviso de confidencialidad.

    Hace falta `territorio.exportar_territorio` y poder ver el territorio. Lo que lleva el archivo depende además de los permisos
    sobre personas, comunidades, organizaciones y actividades (ver `exportar.py`).
    """

    def get(self, request, pk):
        objeto = get_object_or_404(self.queryset(), pk=pk)
        libro = libro_territorial(request.user, **self.ambito(objeto))
        buffer = BytesIO()
        libro.save(buffer)
        registrar(request.user, "resumen_territorial_exportado", objeto, detalle_de(request.user, libro))
        r = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        r["Content-Disposition"] = f'attachment; filename="territorio_{slugify(str(objeto))}_{timezone.localdate():%Y-%m-%d}.xlsx"'
        return r


class ComunaExportar(_Exportar):
    permission_required = ("territorio.exportar_territorio", "territorio.view_comuna")

    def queryset(self):
        return Comuna.objects.all()

    def ambito(self, comuna):
        return {"comuna": comuna, "titulo": str(comuna)}


class SectorExportar(_Exportar):
    """El sector y los que contiene (etapas, villas…), igual que su ficha."""

    permission_required = ("territorio.exportar_territorio", "territorio.view_sector")

    def queryset(self):
        return Sector.objects.select_related("comuna", "sector_padre__sector_padre")

    def ambito(self, sector):
        return {"comuna": sector.comuna, "sectores": sector.descendientes_ids(), "titulo": str(sector)}


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

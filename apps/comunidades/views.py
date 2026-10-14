"""Pantallas de comunidades: listado con filtros, crear (con la comuna ya elegida si viene del territorio),
ficha con integrantes, actividades y alcance, desactivar sin borrar y exportar."""
from django.db.models import Count, Q
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html_join
from django.views import View

from apps.nucleo.direccion_mixin import ComunaInicialMixin
from apps.nucleo.vistas_base import AlternarActivoBase, CrearBase, EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, filtro_activo
from apps.territorio.models import Comuna

from .forms import ComunidadForm
from .models import Comunidad


class ComunidadLista(ListaBase):
    model = Comunidad
    permission_required = "comunidades.view_comunidad"
    titulo = "Comunidades"
    descripcion = "Grupos de personas de un sector o espacio a quienes van dirigidas las actividades: su padrón, diagnóstico y alcance."
    campos_busqueda = ("nombre", "descripcion", "comuna__nombre", "sector__nombre", "organizacion__nombre")
    columnas = [
        ("Comunidad", "nombre"), ("Tipo", "get_tipo_display"), ("Territorio", "territorio"), ("Organización", lambda c: c.organizacion or "—"),
        ("Integrantes", lambda c: c.n_miembros), ("Actividades", lambda c: c.n_actividades), ("Estado", lambda c: "Activa" if c.activo else "Inactiva"),
    ]
    orden_defecto = ("nombre",)
    filtros = [
        filtro_activo(),
        Filtro("tipo", "Tipo", "tipo", lambda: list(Comunidad.TIPOS)),
        Filtro("comuna", "Comuna", "comuna_id", lambda: [(str(c.pk), c.nombre) for c in Comuna.objects.filter(comunidades__isnull=False).distinct().order_by("nombre")]),
    ]
    url_crear = "/comunidades/nueva"
    permiso_crear = "comunidades.add_comunidad"
    etiqueta_crear = "+ Nueva comunidad"
    url_exportar = "/comunidades/exportar"
    permiso_exportar = "comunidades.exportar_comunidad"
    texto_vacio = "Aún no hay comunidades registradas."

    def get_queryset(self):
        return super().get_queryset().select_related("comuna", "sector", "organizacion").annotate(
            n_miembros=Count("miembros", filter=Q(miembros__vigente=True), distinct=True),
            n_actividades=Count("actividades_dirigidas", filter=Q(actividades_dirigidas__vigente=True), distinct=True),
        )


class ComunidadExportar(ComunidadLista):
    exportar = True
    permission_required = "comunidades.exportar_comunidad"


class ComunidadNueva(ComunaInicialMixin, CrearBase):
    model = Comunidad
    form_class = ComunidadForm
    permission_required = "comunidades.add_comunidad"
    titulo = "Nueva comunidad"
    breadcrumb = [("Comunidades", "/comunidades")]
    mensaje_ok = "Comunidad registrada. Agrega a sus integrantes desde la pestaña «Integrantes»."

    def get_initial(self):
        ini = super().get_initial()
        if self.request.GET.get("comuna", "").isdigit():
            ini["comuna"] = self.request.GET["comuna"]
        sector = self.sector_inicial()  # desde la ficha de un sector: parte con ese sector elegido
        if sector:
            ini["sector"] = sector.pk
        return ini


class ComunidadEditar(EditarBase):
    model = Comunidad
    form_class = ComunidadForm
    permission_required = "comunidades.change_comunidad"
    titulo = "Editar comunidad"
    breadcrumb = [("Comunidades", "/comunidades")]


class ComunidadAlternar(AlternarActivoBase):
    modelo = Comunidad
    permission_required = "comunidades.change_comunidad"


class ComunidadOpciones(Permiso403Mixin, View):
    permission_required = "comunidades.view_comunidad"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        qs = Comunidad.objects.filter(activo=True).select_related("comuna")
        if q:
            qs = qs.filter(Q(nombre__unaccent__icontains=q) | Q(comuna__nombre__unaccent__icontains=q))
        opciones = [("", "---------")] + [(c.pk, f"{c.nombre} · {c.territorio}") for c in qs[:25]]
        return HttpResponse(format_html_join("", '<option value="{}">{}</option>', opciones))


class ComunidadFicha(FichaBase):
    model = Comunidad
    template_name = "comunidades/ficha.html"
    permission_required = "comunidades.view_comunidad"
    breadcrumb = [("Comunidades", "/comunidades")]
    permiso_editar = "comunidades.change_comunidad"
    pestanas = [
        ("info", "Información", "comunidades/pestanas/info.html"),
        ("integrantes", "Integrantes", "generico/_hijos.html", "comunidades.view_comunidadmiembro"),
        ("actividades", "Actividades y proyectos", "comunidades/pestanas/actividades.html", "actividades.view_actividad"),
        ("alcance", "Alcance", "actividades/pestanas/alcance.html", "actividades.view_participacion"),
        ("historial", "Historial", "generico/_historial.html", "comunidades.view_historicalcomunidad"),
    ]

    def get_queryset(self):
        return super().get_queryset().select_related("comuna__provincia__region", "sector", "organizacion", "referente")

    def contexto_ficha(self):
        c = self.object
        return {
            "url_editar": reverse("comunidades:editar", args=[c.pk]),
            "url_volver": "/comunidades",
            "puede_agregar": self.request.user.has_perm("comunidades.change_comunidad"),
            "n_integrantes": c.miembros.filter(vigente=True).count(),
        }

    def ctx_integrantes(self):
        pk = self.object.pk
        hijos = [{
            "texto": str(m.persona), "badge": m.get_rol_display() if m.rol != "integrante" else "",
            "detalle": " · ".join(x for x in [f"desde {m.desde:%d-%m-%Y}" if m.desde else "", f"hasta {m.hasta:%d-%m-%Y}" if m.hasta else "", m.observaciones] if x),
            "vigente": m.vigente, "url_editar": reverse("comunidades:integrantes_editar", args=[pk, m.pk]), "url_alternar": reverse("comunidades:integrantes_alternar", args=[pk, m.pk]),
        } for m in self.object.miembros.select_related("persona")]
        return {"titulo_pestana": "Integrantes", "etiqueta_nuevo": "Integrante", "url_nuevo": reverse("comunidades:integrantes_nuevo", args=[pk]), "hijos": hijos,
                "vacio": "Aún no hay integrantes registrados. Agrega a los vecinos y vecinas que participan, o cárgalos desde una planilla.",
                "puede_agregar": self.request.user.has_perm("comunidades.add_comunidadmiembro")}

    def ctx_actividades(self):
        c = self.object
        return {
            "dirigidas": c.actividades_dirigidas.filter(vigente=True).select_related("actividad__estado", "actividad__tipo").order_by("-actividad__creado_en"),
            "proyectos": c.proyectos_dirigidos.filter(vigente=True).select_related("proyecto"),
        }

    def ctx_alcance(self):
        from apps.actividades.alcance import alcance
        from apps.actividades.models import Actividad

        actividades = Actividad.objects.filter(Q(comunidades_destino__comunidad=self.object, comunidades_destino__vigente=True) | Q(participaciones__comunidad=self.object)).distinct()
        return {"alcance": alcance(actividades), "contexto_alcance": "las actividades dirigidas a esta comunidad"}

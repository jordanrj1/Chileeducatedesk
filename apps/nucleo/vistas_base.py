"""Vistas genéricas reutilizadas por todos los módulos (listado, formulario, ficha con pestañas)."""
from dataclasses import dataclass, field
from typing import Callable, Optional

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView


class Permiso403Mixin(PermissionRequiredMixin):
    """Autenticado sin permiso -> 403 propio (no redirige al login)."""

    raise_exception = True


@dataclass
class Filtro:
    param: str
    etiqueta: str
    lookup: str
    opciones: Callable = field(default=lambda: [])  # -> [(valor, etiqueta)]
    convertir: Optional[Callable] = None
    por_defecto: str = ""
    entrada: str = "select"  # select | text | number | date
    aplicar: Optional[Callable] = None  # (qs, valor) -> qs; reemplaza al lookup simple


def opciones_activo():
    return [("1", "Activos"), ("0", "Inactivos"), ("*", "Todos")]


def filtro_activo(param="activo", lookup="activo"):
    return Filtro(param, "Estado", lookup, opciones_activo, lambda v: v == "1", por_defecto="1")


def opciones_modelo(modelo, campo="nombre", **filtros):
    return lambda: [(str(o.pk), str(getattr(o, campo))) for o in modelo.objects.filter(**filtros)]


class ListaBase(Permiso403Mixin, ListView):
    template_name = "generico/lista.html"
    paginate_by = 25
    titulo = ""
    descripcion = ""  # una frase bajo el título: para qué sirve este listado
    breadcrumb = ()  # [(etiqueta, url|None)]
    campos_busqueda = ()  # lookups con icontains
    filtros = ()
    columnas = ()  # [(etiqueta, "atributo.anidado" | callable)]
    ordenes = {}  # clave -> campo de orden
    orden_defecto = None
    url_crear = None
    permiso_crear = None
    etiqueta_crear = "Nuevo"
    texto_vacio = "Aún no hay registros."
    url_exportar = None
    permiso_exportar = None
    botones_extra = ()  # [(etiqueta, url, permiso)]

    exportar = False

    def get(self, request, *args, **kwargs):
        if self.exportar:
            return self.responder_xlsx()
        request.session[f"lista:{request.path}"] = request.get_full_path()  # «← Volver» conserva filtros y página
        return super().get(request, *args, **kwargs)

    def responder_xlsx(self):
        from .exportacion import respuesta_xlsx

        filas = []
        for obj in self.get_queryset():
            filas.append(["" if v is None else str(v) for v in (self._valor(obj, a) for _, a in self.columnas)])
        return respuesta_xlsx(self.request.user, self.titulo, [e for e, _ in self.columnas], filas)

    def valor_filtro(self, f):
        v = self.request.GET.get(f.param, f.por_defecto)
        return v

    def filtrar(self, qs):
        q = self.request.GET.get("q", "").strip()
        if q and self.campos_busqueda:
            cond = Q()
            for campo in self.campos_busqueda:
                cond |= Q(**{f"{campo}__unaccent__icontains": q})  # sin distinguir tildes (BU-E1)
            qs = qs.filter(cond)
        for f in self.filtros:
            v = self.valor_filtro(f)
            if v and v != "*":
                try:
                    valor = f.convertir(v) if f.convertir else v
                    nuevo = f.aplicar(qs, valor) if f.aplicar else qs.filter(**{f.lookup: valor})
                    list(nuevo.query.where.children)  # fuerza a validar el valor aquí
                except (ValueError, TypeError, ValidationError):
                    continue  # valor mal escrito: se ignora el filtro en vez de fallar
                qs = nuevo
        return qs

    def get_queryset(self):
        qs = self.filtrar(super().get_queryset())
        clave = self.request.GET.get("orden", "")
        desc = clave.startswith("-")
        campo = self.ordenes.get(clave.lstrip("-"))
        if campo:
            qs = qs.order_by(("-" if desc else "") + campo)
        elif self.orden_defecto:
            qs = qs.order_by(*self.orden_defecto)
        return qs

    @staticmethod
    def _valor(obj, acceso):
        if callable(acceso):
            return acceso(obj)
        for parte in acceso.split("."):
            obj = getattr(obj, parte, "") if obj is not None else ""
            if callable(obj):
                obj = obj()
        return "" if obj is None else obj

    def contexto_extra(self):
        return {}

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        filas = []
        for obj in ctx["object_list"]:
            filas.append({"obj": obj, "celdas": [self._valor(obj, a) for _, a in self.columnas]})
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx.update(
            titulo=self.titulo,
            descripcion=self.descripcion,
            breadcrumb=self.breadcrumb,
            filas=filas,
            encabezados=[e for e, _ in self.columnas],
            filtros_ui=[
                {"param": f.param, "etiqueta": f.etiqueta, "opciones": f.opciones() if f.entrada == "select" else [], "valor": self.valor_filtro(f), "entrada": f.entrada}
                for f in self.filtros
            ],
            q=self.request.GET.get("q", ""),
            buscable=bool(self.campos_busqueda),
            orden_actual=self.request.GET.get("orden", ""),
            ordenes=list(self.ordenes),
            querystring=params.urlencode(),
            url_crear=self.url_crear,
            puede_crear=bool(self.url_crear and (not self.permiso_crear or self.request.user.has_perm(self.permiso_crear))),
            etiqueta_crear=self.etiqueta_crear,
            texto_vacio=self.texto_vacio,
            hay_filtros=bool(self.request.GET.get("q")) or any(
                self.request.GET.get(f.param) not in (None, "", f.por_defecto) for f in self.filtros
            ),
            botones_extra=[(e, u) for e, u, p in self.botones_extra if not p or self.request.user.has_perm(p)],
            url_exportar=self.url_exportar
            if self.url_exportar and (not self.permiso_exportar or self.request.user.has_perm(self.permiso_exportar))
            else None,
        )
        ctx.update(self.contexto_extra())
        return ctx


class ControlVersionMixin:
    """UI-E5: si el registro cambió desde que se abrió el formulario (otra pestaña u otro usuario), no se pisa."""

    MENSAJE_VERSION = "Este registro cambió mientras lo editabas (en otra pestaña o por otra persona). Recarga la página para ver los cambios y vuelve a guardar."

    def _version_actual(self):
        obj = getattr(self, "object", None)
        if obj is None or not obj.pk or not hasattr(obj, "history"):
            return ""
        return str(obj.history.order_by("-history_id").values_list("history_id", flat=True).first() or 0)

    def version_en_conflicto(self):
        enviada = self.request.POST.get("_version")
        return bool(enviada) and enviada != self._version_actual()

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["version_registro"] = self._version_actual()
        return ctx

    def form_valid(self, form):
        if self.version_en_conflicto():
            form.add_error(None, self.MENSAJE_VERSION)
            return self.form_invalid(form)
        return super().form_valid(form)


class FormularioMixin:
    template_name = "generico/formulario.html"
    titulo = ""
    breadcrumb = ()
    mensaje_ok = "Guardado."

    def volver_url(self):
        obj = getattr(self, "object", None)
        if obj is not None and obj.pk and hasattr(obj, "get_absolute_url"):
            return obj.get_absolute_url()
        return self.request.META.get("HTTP_REFERER") or "/dashboard"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo=self.titulo, breadcrumb=self.breadcrumb, volver_url=self.volver_url())
        return ctx

    def form_valid(self, form):
        obj = form.instance
        if not obj.pk and hasattr(obj, "creado_por_id") and not obj.creado_por_id:
            obj.creado_por = self.request.user
        respuesta = super().form_valid(form)
        messages.success(self.request, self.mensaje_ok)
        return respuesta


class CrearBase(FormularioMixin, Permiso403Mixin, CreateView):
    pass


class EditarBase(ControlVersionMixin, FormularioMixin, Permiso403Mixin, UpdateView):
    pass


def cambios_historial(obj, limite=50):
    """Lista de cambios de un registro con django-simple-history."""
    registros = list(obj.history.select_related("history_user").order_by("-history_date", "-history_id")[: limite + 1])
    etiquetas = {f.name: str(f.verbose_name) for f in obj._meta.get_fields() if hasattr(f, "verbose_name")}
    salida = []
    for i, r in enumerate(registros[:limite]):
        previo = registros[i + 1] if i + 1 < len(registros) else None
        cambios = []
        if previo is not None:
            for c in r.diff_against(previo).changes:
                cambios.append((etiquetas.get(c.field, c.field), c.old, c.new))
        salida.append(
            {
                "fecha": r.history_date,
                "usuario": r.history_user.get_username() if r.history_user else "—",
                "tipo": {"+": "Creación", "~": "Modificación", "-": "Eliminación"}.get(r.history_type, r.history_type),
                "cambios": cambios,
            }
        )
    return salida


# Icono de la cabecera de cada ficha; personas y organizaciones muestran sus iniciales.
ICONOS_FICHA = {
    "actividad": "actividades", "proyecto": "proyectos", "lugar": "lugares", "documento": "documentos", "solicitud": "solicitudes",
    "region": "territorio", "comuna": "territorio", "reunion": "reuniones", "tarea": "tareas", "movimiento": "finanzas", "lote": "importaciones",
    "interaccion": "reuniones", "invitacion": "correo", "colaboracion": "usuarios_check",
}


class FichaBase(Permiso403Mixin, DetailView):
    """Ficha con pestañas internas. Cada pestaña: (clave, etiqueta, plantilla). Contexto en `ctx_<clave>()`."""

    template_name = "generico/ficha.html"
    pestanas = ()
    breadcrumb = ()
    permiso_editar = None
    url_editar = None
    permiso_historial = None

    def pestana_actual(self):
        claves = [p[0] for p in self.pestanas_visibles()]
        t = self.request.GET.get("tab", claves[0] if claves else "")
        return t if t in claves else (claves[0] if claves else "")

    pestanas_segunda_fase = {}  # pestaña -> módulo de segunda fase que la habilita

    def pestanas_visibles(self):
        from .fases import modulo_activo

        res = []
        for p in self.pestanas:
            modulo = self.pestanas_segunda_fase.get(p[0])
            if modulo and not modulo_activo(modulo):
                continue
            perm = p[3] if len(p) > 3 else None
            if not perm or self.request.user.has_perm(perm):
                res.append(p)
        return res

    def encabezado(self):
        return str(self.object)

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        actual = self.pestana_actual()
        plantilla = next((p[2] for p in self.pestanas if p[0] == actual), None)
        ctx.update(
            pestanas=[(p[0], p[1]) for p in self.pestanas_visibles()],
            pestana=actual,
            plantilla_pestana=plantilla,
            titulo=self.encabezado(),
            tipo_ficha=str(self.object._meta.verbose_name).capitalize(),
            icono_ficha=ICONOS_FICHA.get(self.object._meta.model_name),
            breadcrumb=self.breadcrumb,
            puede_editar=bool(self.permiso_editar and self.request.user.has_perm(self.permiso_editar)),
        )
        extra = getattr(self, f"ctx_{actual}", None)
        if extra:
            ctx.update(extra())
        ctx.update(self.contexto_ficha())
        volver = ctx.get("url_volver")
        if volver and "?" not in volver:
            ctx["url_volver"] = self.request.session.get(f"lista:{volver}", volver)
        ctx["acciones_extra"] = self.acciones_extra()
        return ctx

    def contexto_ficha(self):
        return {}

    def acciones_extra(self):
        """[(etiqueta, url)] que aparecen junto a «Editar» en la cabecera de la ficha."""
        return []

    def ctx_historial(self):
        ctx = {"cambios": cambios_historial(self.object)}
        etiqueta = f"{self.object._meta.app_label}.{self.object._meta.model_name}"
        from apps.documentos.origen import MODELOS_CON_ORIGEN, origenes_de

        if etiqueta in MODELOS_CON_ORIGEN and self.request.user.has_perm("documentos.view_origendato"):
            ctx["origenes_historial"] = origenes_de(self.object)  # HI-04: de qué fuente salió el dato
        return ctx


class AlternarActivoBase(Permiso403Mixin, View):
    """Desactiva o reactiva un registro. Nunca borra (docs/CONTEXTO.md §3).

    NR-06: si al desactivar hay actividades futuras afectadas, primero las muestra y pide confirmar.
    """

    modelo = None

    def afectados(self, obj):
        """[(texto, url)] de actividades futuras que dependen de este registro."""
        return []

    def post(self, request, pk):
        obj = get_object_or_404(self.modelo, pk=pk)
        if obj.activo and not request.POST.get("confirmar"):
            afectados = self.afectados(obj)
            if afectados:
                from django.shortcuts import render

                return render(request, "generico/desactivar.html", {"obj": obj, "afectados": afectados, "titulo": f"Desactivar «{obj}»", "breadcrumb": []})
        obj.activo = not obj.activo
        obj.save()
        messages.success(request, "Registro activado." if obj.activo else "Registro desactivado.")
        return HttpResponseRedirect(obj.get_absolute_url())

    def get(self, request, pk):
        raise Http404

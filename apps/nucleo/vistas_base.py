"""Vistas genéricas reutilizadas por todos los módulos (listado, formulario, ficha con pestañas)."""
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional
from urllib.parse import urlencode

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
    """Un filtro de listado. El nombre del parámetro (`param`) es parte de la dirección: no se cambia."""

    param: str
    etiqueta: str
    lookup: str
    opciones: Callable = field(default=lambda: [])  # -> [(valor, etiqueta)] o [(valor, etiqueta, grupo)] para <optgroup>
    convertir: Optional[Callable] = None
    por_defecto: str = ""
    entrada: str = "select"  # select | text | number | date | casilla (envía «1»)
    aplicar: Optional[Callable] = None  # (qs, valor) -> qs; reemplaza al lookup simple
    principal: bool = False  # se ve siempre en la barra; los demás van en «Más filtros»
    grupo: str = ""  # subtítulo dentro de «Más filtros»
    todos: str = "Todos"  # texto de la opción vacía, con su género («Todas»)
    oculto: bool = False  # funciona por la dirección (y se ve como filtro aplicado), pero no se dibuja
    texto_casilla: str = ""  # casilla: texto junto a ella, p. ej. «Solo incompletas»
    tope: int = 0  # si las opciones pasan de este número, se muestran las primeras y se avisa
    etiqueta_de: Optional[Callable] = None  # valor -> nombre, para un valor elegido que no está entre las opciones

    def texto(self, valor, opciones=()):
        """Cómo se lee el valor aplicado en su etiqueta («Comuna: Hualpén»)."""
        if self.entrada == "casilla":
            return self.texto_casilla or "Sí"
        if self.entrada == "date":
            try:
                return date.fromisoformat(valor).strftime("%d-%m-%Y")
            except (TypeError, ValueError):
                return valor
        for o in opciones:
            if o[0] == valor:
                return o[1]
        return valor


def opciones_activo(femenino=False):
    if femenino:
        return [("1", "Activas"), ("0", "Inactivas"), ("*", "Todas")]
    return [("1", "Activos"), ("0", "Inactivos"), ("*", "Todos")]


def filtro_activo(param="activo", lookup="activo", femenino=False, grupo="Registro"):
    # «Mostrar: Inactivos» se lee mejor que «Estado», que se confunde con el estado del registro
    return Filtro(param, "Mostrar", lookup, lambda: opciones_activo(femenino), lambda v: v == "1", por_defecto="1", grupo=grupo)


def opciones_modelo(modelo, campo="nombre", **filtros):
    return lambda: [(str(o.pk), str(getattr(o, campo))) for o in modelo.objects.filter(**filtros)]


def opciones_comunas(en_uso=None):
    """Comunas agrupadas por región (con <optgroup>). `en_uso`: condición (Q) con las comunas que tienen registros,
    para no ofrecer las 346 de Chile cuando solo se trabaja en unas pocas. Una sola consulta."""
    from apps.territorio.models import Comuna

    qs = Comuna.objects.select_related("provincia__region").order_by("provincia__region__codigo", "nombre")
    if en_uso is not None:
        qs = qs.filter(en_uso)
    return [(str(c.pk), c.nombre, c.provincia.region.nombre) for c in qs]


def nombre_comuna(valor):
    from apps.territorio.models import Comuna

    return Comuna.objects.filter(pk=valor).values_list("nombre", flat=True).first() if str(valor).isdigit() else None


def opciones_organizaciones(qs, tope=300):
    """Organizaciones agrupadas por tipo. Trae una más que el tope para saber si hay que avisar."""
    qs = qs.select_related("tipo").order_by("tipo__nombre", "nombre")
    return [(str(o.pk), o.nombre, o.tipo.nombre if o.tipo_id else "Sin tipo") for o in qs[: tope + 1]]


def nombre_organizacion(valor):
    from apps.organizaciones.models import Organizacion

    return Organizacion.objects.filter(pk=valor).values_list("nombre", flat=True).first() if str(valor).isdigit() else None


class ListaBase(Permiso403Mixin, ListView):
    template_name = "generico/lista.html"
    paginate_by = 25
    titulo = ""
    descripcion = ""  # una frase bajo el título: para qué sirve este listado
    breadcrumb = ()  # [(etiqueta, url|None)]
    campos_busqueda = ()  # lookups con icontains
    buscable = None  # None: hay buscador si hay campos_busqueda (Personas busca con su propio método)
    texto_busqueda = ""  # ayuda dentro del buscador; por defecto «Buscar en <título>…»
    filtros = ()
    columnas = ()  # [(etiqueta, "atributo.anidado" | callable)]
    ordenes = {}  # clave -> campo de orden
    orden_defecto = None
    url_crear = None
    permiso_crear = None
    etiqueta_crear = "Nuevo"
    texto_vacio = "Aún no hay registros."
    texto_vacio_detalle = ""  # segunda línea del estado vacío; sin ella: «Cuando se registren <título>, aparecerán aquí.»
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

        columnas = self.columnas_exportacion()
        filas = []
        for obj in self.get_queryset():
            filas.append(["" if v is None else str(v) for v in (self._valor(obj, a) for _, a in columnas)])
        return respuesta_xlsx(self.request.user, self.titulo, [e for e, _ in columnas], filas)

    def columnas_visibles(self):
        """Columnas de la tabla. Una lista puede cambiarlas según los permisos de quien mira (p. ej. el RUT)."""
        return self.columnas

    def columnas_exportacion(self):
        """Columnas del Excel: por defecto, las mismas de la tabla."""
        return self.columnas_visibles()

    def valor_filtro(self, f):
        v = self.request.GET.get(f.param, "").strip()
        return v if v != "" else f.por_defecto  # «?activo=» vacío vale lo predeterminado, no «todos» sin avisar

    def filtrar(self, qs):
        self.aplicados = {}  # param -> valor de los filtros que de verdad se aplicaron (para sus etiquetas con ×)
        q = self.request.GET.get("q", "").strip()
        if q and self.campos_busqueda:
            cond = Q()
            for campo in self.campos_busqueda:
                cond |= Q(**{f"{campo}__unaccent__icontains": q})  # sin distinguir tildes (BU-E1)
            qs = qs.filter(cond)
        for f in self.filtros:
            v = self.valor_filtro(f)
            if v == "*" and f.por_defecto:
                self.aplicados[f.param] = v  # «Todos» cuando lo normal es «Activos»: se ve como filtro aplicado
            if v and v != "*":
                try:
                    valor = f.convertir(v) if f.convertir else v
                    nuevo = f.aplicar(qs, valor) if f.aplicar else qs.filter(**{f.lookup: valor})
                    list(nuevo.query.where.children)  # fuerza a validar el valor aquí
                except (ValueError, TypeError, ValidationError):
                    continue  # valor mal escrito: se ignora el filtro en vez de fallar
                qs = nuevo
                if v != f.por_defecto:
                    self.aplicados[f.param] = v
        return qs

    def _consulta_sin(self, *quitar):
        """La consulta actual sin la página, sin los parámetros indicados y sin los vacíos."""
        params = self.request.GET.copy()
        for p in ("page",) + quitar:
            params.pop(p, None)
        for p in list(params):
            valores = [v for v in params.getlist(p) if v.strip() != ""]
            if valores:
                params.setlist(p, valores)
            else:
                params.pop(p)
        return params.urlencode()

    def _filtro_ui(self, f, valor):
        """Lo que la barra necesita de un filtro: opciones (con grupo), valor, aviso de tope."""
        opciones, aviso = [], ""
        if f.entrada == "select":
            opciones = [(str(o[0]), o[1], o[2] if len(o) > 2 else "") for o in f.opciones()]
            if f.tope and len(opciones) > f.tope:
                opciones = opciones[: f.tope]
                aviso = f"Hay más de {f.tope}: se muestran las primeras {f.tope} por orden alfabético."
            if valor and valor != "*" and f.etiqueta_de and all(o[0] != valor for o in opciones):
                nombre = f.etiqueta_de(valor)  # elegido desde otra pantalla y fuera de la lista: igual se muestra
                if nombre:
                    opciones.insert(0, (valor, nombre, ""))
        return {
            "param": f.param, "etiqueta": f.etiqueta, "opciones": opciones, "valor": valor, "entrada": f.entrada,
            "todos": f.todos, "grupo": f.grupo, "por_defecto": f.por_defecto, "texto_casilla": f.texto_casilla or f.etiqueta,
            "aviso": aviso, "principal": f.principal,
        }

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
        columnas = self.columnas_visibles()
        filas = []
        for obj in ctx["object_list"]:
            filas.append({"obj": obj, "celdas": [self._valor(obj, a) for _, a in columnas]})
        aplicados = getattr(self, "aplicados", {})
        visibles, activos = [], []
        for f in self.filtros:
            valor = self.valor_filtro(f)
            ui = None if f.oculto and f.param not in aplicados else self._filtro_ui(f, valor)
            if not f.oculto:
                visibles.append(ui)
            if f.param in aplicados:
                activos.append({
                    "param": f.param, "etiqueta": f.etiqueta, "texto": f.texto(aplicados[f.param], ui["opciones"]),
                    "url_quitar": self._consulta_sin(f.param), "en_mas": not f.principal and not f.oculto,
                })
        q = self.request.GET.get("q", "").strip()
        buscable = self.buscable if self.buscable is not None else bool(self.campos_busqueda)
        if q and buscable:
            activos.insert(0, {"param": "q", "etiqueta": "Texto", "texto": f"«{q}»", "url_quitar": self._consulta_sin("q"), "en_mas": False})
        orden = self.request.GET.get("orden", "")
        mas = [u for u in visibles if not u["principal"]]
        orden_grupos = list(dict.fromkeys(u["grupo"] for u in mas))
        mas.sort(key=lambda u: orden_grupos.index(u["grupo"]))  # un grupo, un subtítulo (aunque se declaren salteados)
        ctx.update(
            titulo=self.titulo,
            descripcion=self.descripcion,
            breadcrumb=self.breadcrumb,
            filas=filas,
            encabezados=[e for e, _ in columnas],
            filtros_ui=visibles,  # se conserva por compatibilidad: todos los filtros dibujables
            filtros_principales=[u for u in visibles if u["principal"]],
            filtros_mas=mas,
            filtros_activos=activos,
            n_mas_activos=sum(1 for a in activos if a["en_mas"]),
            url_limpiar=urlencode({"orden": orden}) if orden else "",  # «Limpiar» conserva el orden elegido
            q=self.request.GET.get("q", ""),
            buscable=buscable,
            texto_busqueda=self.texto_busqueda or f"Buscar en {self.titulo.lower()}…",
            orden_actual=orden,
            ordenes=list(self.ordenes),
            querystring=self._consulta_sin(),
            url_crear=self.url_crear,
            puede_crear=bool(self.url_crear and (not self.permiso_crear or self.request.user.has_perm(self.permiso_crear))),
            etiqueta_crear=self.etiqueta_crear,
            texto_vacio=self.texto_vacio,
            texto_vacio_detalle=self.texto_vacio_detalle,
            hay_filtros=bool(activos),
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


class AvisoDuplicadosMixin:
    """F26 Ra: antes de crear, muestra los posibles repetidos (apps/nucleo/duplicados.py) en el mismo formulario.
    «Es distinto, guardar» (confirmar_duplicado) guarda igual. Nunca bloquea ni fusiona."""

    def aviso_duplicados(self, form, buscar, titulo, **extra):
        """`buscar`: función sin argumentos que entrega [(registro, [razones])]. Devuelve la respuesta con el aviso o None."""
        if self.request.POST.get("confirmar_duplicado"):
            return None
        candidatos = buscar()
        if not candidatos:
            return None
        return self.render_to_response(self.get_context_data(form=form, duplicados=candidatos, duplicados_titulo=titulo, **extra))


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
    "region": "territorio", "comuna": "territorio", "sector": "territorio", "reunion": "reuniones", "tarea": "tareas", "movimiento": "finanzas", "lote": "importaciones",
    "interaccion": "reuniones", "invitacion": "correo", "colaboracion": "usuarios_check", "comunidad": "comunidades", "sesionactividad": "minuta",
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
        t = self.alias_de_pestanas().get(t, t)  # un enlace con el nombre antiguo de la pestaña sigue funcionando
        return t if t in claves else (claves[0] if claves else "")

    alias_pestanas = {}  # nombre antiguo -> clave actual de la pestaña

    def lista_pestanas(self):
        """Todas las pestañas posibles de este registro. Una ficha puede cambiarlas según el registro (p. ej. la tarea de un proyecto)."""
        return self.pestanas

    def alias_de_pestanas(self):
        return self.alias_pestanas

    pestanas_segunda_fase = {}  # pestaña -> módulo de segunda fase que la habilita

    def pestanas_visibles(self):
        from .fases import modulo_activo

        res = []
        for p in self.lista_pestanas():
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
        plantilla = next((p[2] for p in self.lista_pestanas() if p[0] == actual), None)
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
        if self.solo_ficha():
            ctx["marco_ficha"] = "generico/_solo_ficha.html"
        return ctx

    def solo_ficha(self):
        """F26 Rb: un cambio de pestaña por HTMX (apunta a #ficha-completa) recibe solo la ficha, sin el marco de la página.
        Al recargar la dirección, o al volver con el historial del navegador, llega la página completa."""
        htmx = getattr(self.request, "htmx", None)
        return bool(htmx) and htmx.target == "ficha-completa" and not htmx.history_restore_request

    def render_to_response(self, context, **kw):
        from django.utils.cache import patch_vary_headers

        respuesta = super().render_to_response(context, **kw)
        patch_vary_headers(respuesta, ("HX-Request", "HX-Target"))  # la misma dirección da la ficha sola o la página completa
        return respuesta

    def contexto_ficha(self):
        return {}

    def acciones_extra(self):
        """[(etiqueta, url)] que aparecen junto a «Editar» en la cabecera de la ficha."""
        return []

    origen_en_historial = False  # F26 Ia: el origen de los datos va como sección al final del Historial (sin pestaña propia)

    def ctx_historial(self):
        ctx = {"cambios": cambios_historial(self.object)}
        etiqueta = f"{self.object._meta.app_label}.{self.object._meta.model_name}"
        from apps.documentos.origen import MODELOS_CON_ORIGEN, contexto_origen, origenes_de

        if self.request.user.has_perm("documentos.view_origendato"):
            if self.origen_en_historial:
                ctx.update(contexto_origen(self.object, self.request.user), mostrar_origen=True)
            elif etiqueta in MODELOS_CON_ORIGEN:
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

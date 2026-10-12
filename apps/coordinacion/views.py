from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView

from apps.nucleo.vistas_base import FichaBase, Filtro, ListaBase, Permiso403Mixin
from apps.nucleo.vistas_crud import Detalle, Editar, Nuevo

from . import servicios
from .forms import (
    AsistenteForm, ColaboracionForm, InteraccionForm, InvitacionForm, ReunionForm, TareaForm,
)
from .models import Colaboracion, Interaccion, Invitacion, Reunion, ReunionAsistente, Tarea, TareaResponsable


_Nuevo, _Editar, _Detalle = Nuevo, Editar, Detalle


# --- Interacciones -------------------------------------------------------------
class InteraccionNueva(_Nuevo):
    model = Interaccion
    form_class = InteraccionForm
    permission_required = "coordinacion.add_interaccion"
    titulo = "Nueva interacción"
    prefill = ("persona", "organizacion", "solicitud", "actividad")

    def despues(self, obj):
        if obj.solicitud_id:
            return f"{obj.solicitud.get_absolute_url()}?tab=interacciones"
        if obj.actividad_id:
            return f"{obj.actividad.get_absolute_url()}?tab=coordinacion"
        return obj.get_absolute_url()


class InteraccionEditar(_Editar):
    model = Interaccion
    form_class = InteraccionForm
    permission_required = "coordinacion.change_interaccion"
    titulo = "Editar interacción"


class InteraccionFicha(_Detalle):
    model = Interaccion
    permission_required = "coordinacion.view_interaccion"
    nombre_url_editar = "coordinacion:interaccion_editar"
    permiso_editar = "coordinacion.change_interaccion"
    campos = [("Fecha", "fecha"), ("Canal", "canal"), ("Persona", "persona"), ("Organización", "organizacion"), ("Solicitud", "solicitud"), ("Actividad", "actividad"),
              ("Motivo", "motivo"), ("Resultado", "resultado"), ("Próxima acción", "proxima_accion"), ("Para el", "proxima_fecha"), ("Cumplida", "accion_cumplida")]

    def extra(self):
        return {"marcar_cumplida": reverse("coordinacion:interaccion_cumplida", args=[self.object.pk]) if self.object.proxima_accion and not self.object.accion_cumplida and self.request.user.has_perm("coordinacion.change_interaccion") else None}


class InteraccionCumplida(Permiso403Mixin, View):
    permission_required = "coordinacion.change_interaccion"

    def post(self, request, pk):
        i = get_object_or_404(Interaccion, pk=pk)
        i.accion_cumplida = True
        i.save(update_fields=["accion_cumplida"])
        messages.success(request, "Próxima acción marcada como cumplida.")
        return HttpResponseRedirect(i.get_absolute_url())


# --- Reuniones -----------------------------------------------------------------
class ReunionLista(ListaBase):
    model = Reunion
    permission_required = "coordinacion.view_reunion"
    titulo = "Reuniones"
    url_crear = "/reuniones/nueva"
    permiso_crear = "coordinacion.add_reunion"
    etiqueta_crear = "+ Nueva reunión"
    campos_busqueda = ("titulo", "objetivo", "temas", "acuerdos")
    columnas = [("Reunión", "titulo"), ("Fecha", lambda r: r.fecha.strftime("%d-%m-%Y")), ("Actividad", "actividad"), ("Proyecto", "proyecto"), ("Asistentes", lambda r: r.asistentes.count())]
    orden_defecto = ("-fecha",)
    filtros = [Filtro("desde", "Desde", "fecha__gte", entrada="date"), Filtro("hasta", "Hasta", "fecha__lte", entrada="date")]

    def get_queryset(self):
        return super().get_queryset().select_related("actividad", "proyecto")


class ReunionNueva(_Nuevo):
    model = Reunion
    form_class = ReunionForm
    permission_required = "coordinacion.add_reunion"
    titulo = "Nueva reunión"
    lista_url = "/reuniones"
    prefill = ("actividad", "proyecto")
    breadcrumb_ = [("Reuniones", "/reuniones")]


class ReunionEditar(_Editar):
    model = Reunion
    form_class = ReunionForm
    permission_required = "coordinacion.change_reunion"
    titulo = "Editar reunión"


class ReunionFicha(FichaBase):
    model = Reunion
    permission_required = "coordinacion.view_reunion"
    breadcrumb = [("Reuniones", "/reuniones")]
    permiso_editar = "coordinacion.change_reunion"
    pestanas = [
        ("datos", "Datos", "coordinacion/pestanas/reunion_datos.html"),
        ("asistentes", "Asistentes", "generico/_hijos.html"),
        ("compromisos", "Compromisos", "coordinacion/pestanas/compromisos.html"),
    ]

    def contexto_ficha(self):
        return {"url_editar": reverse("coordinacion:reunion_editar", args=[self.object.pk]), "url_volver": "/reuniones", "puede_agregar": self.request.user.has_perm("coordinacion.change_reunion")}

    def ctx_asistentes(self):
        pk = self.object.pk
        hijos = [{
            "texto": str(a.persona), "vigente": a.vigente, "detalle": {True: "Asistió", False: "No asistió", None: "Sin dato"}[a.asistio] + (f" · {a.observaciones}" if a.observaciones else ""),
            "url_editar": reverse("coordinacion:asistentes_editar", args=[pk, a.pk]), "url_alternar": reverse("coordinacion:asistentes_alternar", args=[pk, a.pk]),
        } for a in self.object.asistentes.select_related("persona")]
        return {"titulo_pestana": "Asistentes", "etiqueta_nuevo": "Asistente", "url_nuevo": reverse("coordinacion:asistentes_nuevo", args=[pk]), "hijos": hijos, "vacio": "Sin asistentes registrados."}

    def ctx_compromisos(self):
        return {"tareas": self.object.compromisos.all()}


# --- Tareas --------------------------------------------------------------------
class TareaLista(ListaBase):
    model = Tarea
    permission_required = "coordinacion.view_tarea"
    titulo = "Tareas"
    url_crear = "/tareas/nueva"
    permiso_crear = "coordinacion.add_tarea"
    etiqueta_crear = "+ Nueva tarea"
    campos_busqueda = ("titulo", "descripcion")
    columnas = [
        ("Tarea", "titulo"), ("Estado", "get_estado_display"), ("Vence", lambda t: t.fecha_limite.strftime("%d-%m-%Y") if t.fecha_limite else "—"),
        ("Responsables", lambda t: ", ".join(str(p) for p in t.responsables) or "Sin responsable"), ("Actividad", "actividad"), ("Proyecto", "proyecto"),
    ]
    orden_defecto = ("fecha_limite", "-creado_en")
    filtros = [
        Filtro("estado", "Estado", "estado", lambda: list(Tarea.ESTADOS)),
        Filtro("responsable", "Responsable (id)", "asignaciones__persona_id", entrada="number", convertir=int),
        Filtro("vencidas", "Vencidas", "", lambda: [("1", "Solo vencidas")], aplicar=lambda qs, v: qs.filter(estado__in=["pendiente", "en_curso"], fecha_limite__lt=timezone.localdate()) if v == "1" else qs),
    ]
    url_exportar = "/tareas/exportar"
    permiso_exportar = "coordinacion.exportar_tarea"

    def get_queryset(self):
        return super().get_queryset().select_related("actividad", "proyecto").distinct()


class TareaExportar(TareaLista):
    exportar = True
    permission_required = "coordinacion.exportar_tarea"


class TareaNueva(_Nuevo):
    model = Tarea
    form_class = TareaForm
    permission_required = "coordinacion.add_tarea"
    titulo = "Nueva tarea"
    lista_url = "/tareas"
    prefill = ("actividad", "proyecto", "reunion")
    breadcrumb_ = [("Tareas", "/tareas")]

    def hook(self, form, obj):
        if form.cleaned_data.get("responsable"):
            TareaResponsable.objects.create(tarea=obj, persona=form.cleaned_data["responsable"])

    def despues(self, obj):
        if obj.reunion_id:
            return f"{obj.reunion.get_absolute_url()}?tab=compromisos"
        return obj.get_absolute_url()


class TareaEditar(_Editar):
    model = Tarea
    form_class = TareaForm
    permission_required = "coordinacion.change_tarea"
    titulo = "Editar tarea"


class TareaFicha(FichaBase):
    model = Tarea
    permission_required = "coordinacion.view_tarea"
    breadcrumb = [("Tareas", "/tareas")]
    permiso_editar = "coordinacion.change_tarea"
    pestanas = [("datos", "Datos", "coordinacion/pestanas/tarea_datos.html"), ("responsables", "Responsables", "generico/_hijos.html")]

    def contexto_ficha(self):
        return {"url_editar": reverse("coordinacion:tarea_editar", args=[self.object.pk]), "url_volver": "/tareas", "puede_agregar": self.request.user.has_perm("coordinacion.change_tarea"), "estados": Tarea.ESTADOS}

    def ctx_responsables(self):
        pk = self.object.pk
        hijos = [{
            "texto": str(a.persona), "vigente": a.vigente, "detalle": "",
            "url_editar": None, "url_alternar": reverse("coordinacion:responsables_alternar", args=[pk, a.pk]),
        } for a in self.object.asignaciones.select_related("persona")]
        return {"titulo_pestana": "Responsables", "etiqueta_nuevo": "Responsable", "url_nuevo": reverse("coordinacion:responsables_nuevo", args=[pk]), "hijos": hijos, "vacio": "Sin responsables asignados."}


class TareaEstado(Permiso403Mixin, View):
    permission_required = "coordinacion.change_tarea"

    def post(self, request, pk):
        t = get_object_or_404(Tarea, pk=pk)
        nuevo = request.POST.get("estado")
        if nuevo not in dict(Tarea.ESTADOS):
            messages.error(request, "Estado no válido.")
        else:
            t.estado = nuevo
            t.hecha_en = timezone.now() if nuevo == "hecha" else None
            t.save()
            messages.success(request, "Tarea actualizada.")
        return HttpResponseRedirect(t.get_absolute_url())


# --- Invitaciones --------------------------------------------------------------
class InvitacionNueva(_Nuevo):
    model = Invitacion
    form_class = InvitacionForm
    permission_required = "coordinacion.add_invitacion"
    titulo = "Nueva invitación"
    prefill = ("persona", "actividad")

    def hook(self, form, obj):
        servicios.sincronizar_invitacion(obj, self.request.user)

    def despues(self, obj):
        return f"{obj.actividad.get_absolute_url()}?tab=coordinacion"


class InvitacionEditar(_Editar):
    model = Invitacion
    form_class = InvitacionForm
    permission_required = "coordinacion.change_invitacion"
    titulo = "Registrar respuesta / editar invitación"

    def hook(self, form, obj):
        servicios.sincronizar_invitacion(obj, self.request.user)


class InvitacionFicha(_Detalle):
    model = Invitacion
    permission_required = "coordinacion.view_invitacion"
    nombre_url_editar = "coordinacion:invitacion_editar"
    permiso_editar = "coordinacion.change_invitacion"
    campos = [("Persona", "persona"), ("Actividad", "actividad"), ("Rol propuesto", "rol"), ("Fecha", "fecha"), ("Estado", "get_estado_display"), ("Respuesta", "respuesta"), ("Fecha de respuesta", "fecha_respuesta")]


# --- Colaboraciones ------------------------------------------------------------
class ColaboracionNueva(_Nuevo):
    model = Colaboracion
    form_class = ColaboracionForm
    permission_required = "coordinacion.add_colaboracion"
    titulo = "Nueva colaboración"
    prefill = ("organizacion", "actividad")

    def despues(self, obj):
        return f"{obj.actividad.get_absolute_url()}?tab=coordinacion"


class ColaboracionEditar(_Editar):
    model = Colaboracion
    form_class = ColaboracionForm
    permission_required = "coordinacion.change_colaboracion"
    titulo = "Editar colaboración"


class ColaboracionFicha(_Detalle):
    model = Colaboracion
    permission_required = "coordinacion.view_colaboracion"
    nombre_url_editar = "coordinacion:colaboracion_editar"
    permiso_editar = "coordinacion.change_colaboracion"
    campos = [("Organización", "organizacion"), ("Actividad", "actividad"), ("Tipo de apoyo", "tipo_apoyo"), ("Estado", "get_estado_display"), ("Resultado", "resultado"), ("Observaciones", "observaciones")]

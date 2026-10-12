from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View
from django.views.generic import CreateView

from apps.actividades.models import Actividad
from apps.nucleo.auditoria import registrar
from apps.nucleo.models import EstadoActividad, EstadoSolicitud
from apps.nucleo.vistas_base import EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, opciones_modelo

from .forms import SolicitudForm
from .models import Solicitud


class SolicitudLista(ListaBase):
    model = Solicitud
    permission_required = "solicitudes.view_solicitud"
    titulo = "Solicitudes y oportunidades"
    url_crear = "/solicitudes/nueva"
    permiso_crear = "solicitudes.add_solicitud"
    etiqueta_crear = "+ Nueva solicitud"
    campos_busqueda = ("motivo", "descripcion", "persona__nombres", "persona__apellido_paterno", "organizacion__nombre")
    columnas = [
        ("Solicitud", lambda s: s.titulo), ("Fecha", lambda s: s.fecha.strftime("%d-%m-%Y")), ("Origen", "get_origen_display"),
        ("Contacto", lambda s: s.persona or s.organizacion or "Por identificar"), ("Canal", "canal"), ("Estado", "estado"),
    ]
    ordenes = {"fecha": "fecha"}
    orden_defecto = ("-fecha", "-id")
    filtros = [
        Filtro("estado", "Estado", "estado__codigo", lambda: [(e.codigo, e.nombre) for e in EstadoSolicitud.objects.all()]),
        Filtro("origen", "Origen", "origen", lambda: list(Solicitud.ORIGENES)),
        Filtro("desde", "Desde", "fecha__gte", entrada="date"),
        Filtro("hasta", "Hasta", "fecha__lte", entrada="date"),
    ]
    url_exportar = "/solicitudes/exportar"
    permiso_exportar = "solicitudes.exportar_solicitud"
    botones_extra = [("+ Nueva oportunidad", "/solicitudes/nueva?oportunidad=1", "solicitudes.add_solicitud")]

    def get_queryset(self):
        return super().get_queryset().select_related("estado", "canal", "persona", "organizacion")


class SolicitudExportar(SolicitudLista):
    exportar = True
    permission_required = "solicitudes.exportar_solicitud"


class SolicitudNueva(Permiso403Mixin, CreateView):
    model = Solicitud
    form_class = SolicitudForm
    permission_required = "solicitudes.add_solicitud"
    template_name = "generico/formulario.html"

    def get_initial(self):
        ini = super().get_initial()
        for k in ("persona", "organizacion"):
            if self.request.GET.get(k, "").isdigit():
                ini[k] = int(self.request.GET[k])
        if self.request.GET.get("oportunidad"):
            ini["origen"] = "busqueda_activa"
        return ini

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        titulo = "Nueva oportunidad" if self.request.GET.get("oportunidad") else "Nueva solicitud"
        ctx.update(titulo=titulo, volver_url="/solicitudes", breadcrumb=[("Solicitudes", "/solicitudes")])
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.creado_por = self.request.user
        obj.estado = EstadoSolicitud.objects.get(codigo="pendiente")
        obj.save()
        from apps.documentos.origen import registrar_origen

        registrar_origen(obj, self.request.user)
        messages.success(self.request, "Solicitud registrada y pendiente de seguimiento. Puedes completar la información después.")
        return HttpResponseRedirect(obj.get_absolute_url())


class SolicitudEditar(EditarBase):
    model = Solicitud
    form_class = SolicitudForm
    permission_required = "solicitudes.change_solicitud"
    titulo = "Editar solicitud"
    breadcrumb = [("Solicitudes", "/solicitudes")]


class SolicitudFicha(FichaBase):
    model = Solicitud
    permission_required = "solicitudes.view_solicitud"
    breadcrumb = [("Solicitudes", "/solicitudes")]
    permiso_editar = "solicitudes.change_solicitud"
    pestanas = [
        ("info", "Información", "solicitudes/pestanas/info.html"),
        ("interacciones", "Seguimiento", "solicitudes/pestanas/interacciones.html", "coordinacion.view_interaccion"),
        ("origen", "Origen", "documentos/pestanas/origen.html", "documentos.view_origendato"),
        ("historial", "Historial", "generico/_historial.html", "solicitudes.view_historicalsolicitud"),
    ]

    def get_queryset(self):
        return super().get_queryset().select_related("estado", "canal", "persona", "organizacion", "proyecto", "actividad")

    def encabezado(self):
        return self.object.titulo

    def acciones_extra(self):
        if self.request.user.has_perm("coordinacion.add_interaccion"):
            return [("Registrar interacción", f"/interacciones/nueva?solicitud={self.object.pk}")]
        return []

    def contexto_ficha(self):
        s = self.object
        u = self.request.user
        abierta = s.estado.codigo in ("pendiente", "en_seguimiento")
        return {
            "url_editar": reverse("solicitudes:editar", args=[s.pk]), "url_volver": "/solicitudes",
            "puede_agregar": u.has_perm("solicitudes.change_solicitud"),
            "puede_convertir": u.has_perm("solicitudes.change_solicitud") and abierta,
            "puede_proyecto": u.has_perm("proyectos.add_proyecto") and abierta and not s.proyecto_id,
            "puede_actividad": u.has_perm("actividades.add_actividad") and abierta and not s.actividad_id,
        }

    def ctx_interacciones(self):
        return {"interacciones": self.object.interacciones.select_related("canal", "persona", "organizacion").order_by("-fecha")}

    def ctx_origen(self):
        from apps.documentos.origen import contexto_origen

        return contexto_origen(self.object, self.request.user)


class _Accion(Permiso403Mixin, View):
    permission_required = "solicitudes.change_solicitud"

    def solicitud(self, pk):
        return get_object_or_404(Solicitud.objects.select_related("estado"), pk=pk)

    def volver(self, s):
        return HttpResponseRedirect(s.get_absolute_url())


class SolicitudEstado(_Accion):
    """Seguimiento / descartar. Convertida solo se alcanza creando proyecto o actividad."""

    def post(self, request, pk):
        s = self.solicitud(pk)
        codigo = request.POST.get("estado")
        if s.estado.codigo in ("convertida", "descartada"):
            messages.error(request, "La solicitud ya está cerrada.")
        elif codigo not in ("en_seguimiento", "descartada", "pendiente"):
            messages.error(request, "Estado no válido.")
        elif codigo == "descartada" and not request.POST.get("motivo", "").strip():
            messages.error(request, "Indica por qué se descarta.")
        else:
            s.estado = EstadoSolicitud.objects.get(codigo=codigo)
            if codigo == "descartada":
                s.observaciones = (s.observaciones + "\nDescartada: " + request.POST["motivo"].strip()).strip()
            s.save()
            registrar(request.user, f"solicitud_{codigo}", s, request.POST.get("motivo", ""))
            messages.success(request, "Estado actualizado.")
        return self.volver(s)


class SolicitudAProyecto(_Accion):
    """[Crear proyecto]: crea el proyecto con lo que ya se sabe de la solicitud y la marca como convertida."""

    permission_required = "proyectos.add_proyecto"

    def post(self, request, pk):
        from apps.proyectos.models import Proyecto

        s = self.solicitud(pk)
        if s.estado.codigo not in ("pendiente", "en_seguimiento"):
            messages.error(request, "La solicitud ya fue convertida o descartada.")
            return self.volver(s)
        if s.proyecto_id:
            messages.error(request, "Ya tiene un proyecto asociado.")
            return self.volver(s)
        proyecto = Proyecto.objects.create(
            nombre=s.titulo, descripcion=s.descripcion or s.motivo, creado_por=request.user, responsable=s.persona,
        )
        if s.organizacion_id:
            from apps.proyectos.models import ProyectoOrganizacion

            ProyectoOrganizacion.objects.create(proyecto=proyecto, organizacion=s.organizacion, contacto=s.persona)
        s.proyecto = proyecto
        s.estado = EstadoSolicitud.objects.get(codigo="convertida")
        s.save()
        registrar(request.user, "solicitud_convertida_proyecto", s, proyecto.nombre)
        messages.success(request, "Proyecto creado a partir de la solicitud. Completa su información.")
        return HttpResponseRedirect(proyecto.get_absolute_url())


class SolicitudAActividad(_Accion):
    permission_required = "actividades.add_actividad"

    def post(self, request, pk):
        s = self.solicitud(pk)
        if s.estado.codigo not in ("pendiente", "en_seguimiento"):
            messages.error(request, "La solicitud ya fue convertida o descartada.")
            return self.volver(s)
        if s.actividad_id:
            messages.error(request, "Ya tiene una actividad asociada.")
            return self.volver(s)
        actividad = Actividad.objects.create(
            nombre=s.titulo, descripcion=s.descripcion, proyecto=s.proyecto, responsable=s.persona,
            estado=EstadoActividad.objects.get(codigo="pendiente"), creado_por=request.user,
        )
        if s.organizacion_id:
            from apps.actividades.models import ActividadOrganizacion

            ActividadOrganizacion.objects.create(actividad=actividad, organizacion=s.organizacion, contacto=s.persona)
        s.actividad = actividad
        s.estado = EstadoSolicitud.objects.get(codigo="convertida")
        s.save()
        registrar(request.user, "solicitud_convertida_actividad", s, actividad.nombre)
        messages.success(request, "Actividad creada a partir de la solicitud (pendiente de programar).")
        return HttpResponseRedirect(actividad.get_absolute_url())

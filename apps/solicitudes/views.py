"""Pantallas de solicitudes: listado, crear casi sin datos, ficha con seguimiento, cambiar estado (descartar pide motivo),
reabrir, y convertir en actividad o en proyecto sin volver a escribir los datos."""
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
    descripcion = "Pedidos y oportunidades que llegan a la fundación y su seguimiento."
    url_crear = "/solicitudes/nueva"
    permiso_crear = "solicitudes.add_solicitud"
    etiqueta_crear = "+ Nueva"  # F26 P1b: un solo botón; el formulario pregunta si es solicitud u oportunidad
    campos_busqueda = ("motivo", "descripcion", "persona__nombres", "persona__apellido_paterno", "organizacion__nombre")
    columnas = [
        ("Solicitud", lambda s: s.titulo), ("Fecha", lambda s: s.fecha.strftime("%d-%m-%Y")), ("Origen", "get_origen_display"),
        ("Contacto", lambda s: s.persona or s.organizacion or "Por identificar"), ("Canal", "canal"), ("Estado", "estado"),
        ("Antigüedad", lambda s: f"{s.dias_abierta} días" if s.dias_abierta is not None else ""),
    ]
    ordenes = {"fecha": "fecha"}
    orden_defecto = ("-fecha", "-id")
    filtros = [
        Filtro("estado", "Estado", "estado__codigo", lambda: [(e.codigo, e.nombre) for e in EstadoSolicitud.objects.all()], oculto=True),  # F26 Ia: lo eligen las pestañas
        Filtro("origen", "Origen", "origen", lambda: list(Solicitud.ORIGENES), principal=True),
        Filtro("desde", "Desde", "fecha__gte", entrada="date", grupo="Fecha"),
        Filtro("hasta", "Hasta", "fecha__lte", entrada="date", grupo="Fecha"),
    ]
    url_exportar = "/solicitudes/exportar"
    permiso_exportar = "solicitudes.exportar_solicitud"
    template_name = "solicitudes/lista.html"
    PESTANAS = (("pendiente", "Pendientes"), ("en_seguimiento", "En seguimiento"), ("convertida", "Convertidas"), ("descartada", "Descartadas"))

    def get_queryset(self):
        return super().get_queryset().select_related("estado", "canal", "persona", "organizacion")

    def contexto_extra(self):
        """F26 P1b: pestañas por estado con su contador (una sola consulta). Usan el mismo «?estado=» del filtro y
        conservan la búsqueda, el origen, las fechas y el orden."""
        from django.db.models import Count

        cuenta = dict(Solicitud.objects.values_list("estado__codigo").annotate(n=Count("pk")).order_by())
        base = self._consulta_sin("estado")
        actual = self.request.GET.get("estado", "").strip()
        pestanas = [
            {"etiqueta": e, "n": cuenta.get(c, 0), "url": "?" + "&".join(x for x in (f"estado={c}", base) if x), "activa": actual == c}
            for c, e in self.PESTANAS
        ]
        pestanas.append({"etiqueta": "Todas", "n": sum(cuenta.values()), "url": "?" + base if base else "?", "activa": actual not in dict(self.PESTANAS)})
        return {"pestanas_estado": pestanas}


class SolicitudExportar(SolicitudLista):
    exportar = True
    permission_required = "solicitudes.exportar_solicitud"


class SolicitudNueva(Permiso403Mixin, CreateView):
    model = Solicitud
    form_class = SolicitudForm
    permission_required = "solicitudes.add_solicitud"
    template_name = "solicitudes/nueva.html"

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
        from apps.nucleo.duplicados import solicitudes_parecidas

        d = form.cleaned_data
        # SO-E1 y F26 Ra: ¿es la misma de antes? (abierta con ese contacto, o motivo parecido en los últimos 30 días)
        if not self.request.POST.get("confirmar_duplicado"):
            parecidas = solicitudes_parecidas(d.get("persona"), d.get("organizacion"), d.get("motivo"))
            if parecidas:
                abierta = any(r.startswith("abierta") for _, razones in parecidas for r in razones)
                return self.render_to_response(self.get_context_data(
                    form=form, duplicados=parecidas,
                    duplicados_titulo="Ya hay una solicitud abierta con ese contacto." if abierta else "Esta solicitud podría ya estar registrada.",
                    duplicados_ayuda="Si es la misma, ábrela y registra ahí una interacción. Si es otra, guárdala igual.",
                ))
        obj = form.save(commit=False)
        obj.creado_por = self.request.user
        obj.estado = EstadoSolicitud.objects.get(codigo="pendiente")
        obj.save()
        from apps.personas.vinculos import vincular_contacto

        vincular_contacto(obj.persona, obj.organizacion)  # F26 P2: la persona de contacto queda vinculada a la organización
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
    template_name = "solicitudes/ficha.html"
    permission_required = "solicitudes.view_solicitud"
    breadcrumb = [("Solicitudes", "/solicitudes")]
    permiso_editar = "solicitudes.change_solicitud"
    pestanas = [
        ("info", "Información", "solicitudes/pestanas/info.html"),
        ("interacciones", "Seguimiento", "coordinacion/_interacciones.html", "coordinacion.view_interaccion"),
        ("documentos", "Documentos", "documentos/pestanas/lista.html", "documentos.view_documento"),
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
            # F26 P1b: convertida en proyecto y aún sin actividad → su primera tarea queda ligada a la solicitud
            "puede_tarea": u.has_perm("actividades.add_actividad") and bool(s.proyecto_id) and not s.actividad_id and s.estado.codigo == "convertida",
        }

    def ctx_interacciones(self):
        puede = self.request.user.has_perm("solicitudes.change_solicitud")  # el botón exige poder editar la solicitud, como antes
        return {"interacciones": self.object.interacciones.select_related("canal", "persona", "organizacion").order_by("-fecha"),
                "titulo_interacciones": "Contactos y seguimiento", "vacio_interacciones": "Aún no se ha registrado ningún contacto.", "con_quien": True,
                "url_nueva_interaccion": f"/interacciones/nueva?solicitud={self.object.pk}" if puede else None}

    def ctx_documentos(self):
        docs = self.object.documentos.select_related("tipo")
        if not self.request.user.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        return {"documentos": docs, "url_nuevo_doc": f"/documentos/nuevo?solicitud={self.object.pk}", "url_asociar_doc": f"/documentos/asociar?solicitud={self.object.pk}"}

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


class SolicitudReabrir(_Accion):
    """SO-E4: vuelven a pedir lo mismo meses después de descartarla. Se reabre con historial."""

    def post(self, request, pk):
        s = self.solicitud(pk)
        motivo = request.POST.get("motivo", "").strip()
        if s.estado.codigo != "descartada":
            messages.error(request, "Solo se reabre una solicitud descartada.")
        elif not motivo:
            messages.error(request, "Indica por qué se reabre.")
        else:
            from django.utils import timezone

            s.estado = EstadoSolicitud.objects.get(codigo="en_seguimiento")
            s.observaciones = (s.observaciones + f"\nReabierta el {timezone.localdate():%d-%m-%Y}: {motivo}").strip()
            s.save()
            registrar(request.user, "solicitud_reabierta", s, motivo)
            messages.success(request, "Solicitud reabierta y en seguimiento.")
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

            from apps.personas.vinculos import vincular_contacto

            ProyectoOrganizacion.objects.create(proyecto=proyecto, organizacion=s.organizacion, contacto=s.persona)
            vincular_contacto(s.persona, s.organizacion)  # F26 P2
        s.proyecto = proyecto
        s.estado = EstadoSolicitud.objects.get(codigo="convertida")
        s.save()
        registrar(request.user, "solicitud_convertida_proyecto", s, proyecto.nombre)
        messages.success(request, "Proyecto creado a partir de la solicitud. Completa su información.")
        return HttpResponseRedirect(proyecto.get_absolute_url())


class SolicitudAActividad(_Accion):
    """[Crear actividad]: GET abre el formulario de nueva actividad relleno con la solicitud (con «Programar ahora»);
    al guardarlo, la solicitud queda convertida y ligada (F26 P1b). El POST directo se mantiene: crea la actividad
    pendiente de programar, como antes."""

    permission_required = "actividades.add_actividad"

    def get(self, request, pk):
        s = self.solicitud(pk)
        if s.estado.codigo not in ("pendiente", "en_seguimiento") or s.actividad_id:
            messages.error(request, "La solicitud ya tiene una actividad, o fue convertida o descartada.")
            return self.volver(s)
        return HttpResponseRedirect(f"{reverse('actividades:nueva')}?{urlencode({'solicitud': s.pk})}")

    def post(self, request, pk):
        from django.db import transaction

        from apps.actividades.views import convertir_solicitud

        s = self.solicitud(pk)
        if s.estado.codigo not in ("pendiente", "en_seguimiento"):
            messages.error(request, "La solicitud ya fue convertida o descartada.")
            return self.volver(s)
        if s.actividad_id:
            messages.error(request, "Ya tiene una actividad asociada.")
            return self.volver(s)
        with transaction.atomic():
            actividad = Actividad.objects.create(
                nombre=s.titulo, descripcion=s.descripcion, proyecto=s.proyecto, responsable=s.persona,
                estado=EstadoActividad.objects.get(codigo="pendiente"), creado_por=request.user,
            )
            convertir_solicitud(s, actividad, request.user)
            from apps.actividades.servicios import asegurar_responsable_en_equipo

            asegurar_responsable_en_equipo(actividad, request.user)  # F26 P2 [P]
        messages.success(request, "Actividad creada a partir de la solicitud (pendiente de programar).")
        return HttpResponseRedirect(actividad.get_absolute_url())

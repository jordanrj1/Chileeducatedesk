"""Pantallas de proyectos: listado, crear, editar y ficha con pestañas (resumen, equipo, organizaciones, comunidades,
actividades, alcance, documentos, historial; beneficiarios, postulación y presupuesto son de 2.ª fase)."""
from datetime import date

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView

from apps.nucleo.direccion_mixin import ComunaInicialMixin
from apps.nucleo.vistas_base import AvisoDuplicadosMixin, EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, cambios_historial
from apps.territorio.destinos import fila_inicial, texto_destino

from .forms import ProyectoForm
from .models import Proyecto, ProyectoTerritorio


class ProyectoLista(ListaBase):
    model = Proyecto
    permission_required = "proyectos.view_proyecto"
    titulo = "Proyectos"
    descripcion = "Proyectos de la fundación con su estado, zona y actividades."
    url_crear = "/proyectos/nuevo"
    permiso_crear = "proyectos.add_proyecto"
    etiqueta_crear = "+ Nuevo proyecto"
    campos_busqueda = ("nombre", "descripcion", "zona", "objetivo_general")
    columnas = [
        ("Proyecto", "nombre"), ("Estado", "get_estado_display"), ("Zona", lambda p: p.zona_resumen), ("Responsable", "responsable"),
        ("Tareas", lambda p: p.n_actividades),  # F26 Ia: en el proyecto se dicen «tareas»
        ("Inicio", lambda p: p.fecha_inicio.strftime("%d-%m-%Y") if p.fecha_inicio else "—"),
    ]
    ordenes = {"nombre": "nombre", "inicio": "fecha_inicio"}
    orden_defecto = ("-creado_en",)
    filtros = [Filtro("estado", "Estado", "estado", lambda: list(Proyecto.ESTADOS), principal=True)]
    url_exportar = "/proyectos/exportar"
    permiso_exportar = "proyectos.exportar_proyecto"

    def get_queryset(self):
        territorios = ProyectoTerritorio.objects.select_related("region", "provincia", "comuna", "sector__sector_padre").order_by("pk")
        return (
            super().get_queryset().select_related("responsable").prefetch_related(Prefetch("territorios", queryset=territorios))
            .annotate(n_actividades=Count("actividades", distinct=True))
        )


class ProyectoExportar(ProyectoLista):
    exportar = True
    permission_required = "proyectos.exportar_proyecto"


from .servicios import asegurar_responsable  # noqa: E402


class ProyectoNuevo(AvisoDuplicadosMixin, ComunaInicialMixin, Permiso403Mixin, CreateView):
    model = Proyecto
    form_class = ProyectoForm
    permission_required = "proyectos.add_proyecto"
    template_name = "generico/formulario.html"

    def get_initial(self):
        ini = super().get_initial()
        # Viene de «Crear proyecto» desde una solicitud
        for k in ("nombre", "descripcion"):
            if self.request.GET.get(k):
                ini[k] = self.request.GET[k]
        return ini

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        comuna = self.comuna_inicial()  # «¿Dónde?» parte con la comuna (y el sector) de la dirección, si viene
        kw["destinos_inicial"] = [fila_inicial(comuna=comuna, sector=self.sector_inicial())] if comuna else []
        return kw

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nuevo proyecto", volver_url="/proyectos", breadcrumb=[("Proyectos", "/proyectos")])
        return ctx

    def form_valid(self, form):
        from apps.documentos.origen import registrar_origen
        from apps.nucleo.duplicados import proyectos_parecidos

        aviso = self.aviso_duplicados(form, lambda: proyectos_parecidos(form.cleaned_data.get("nombre")), "Este proyecto podría ya estar registrado.")
        if aviso:
            return aviso
        with transaction.atomic():  # el proyecto y sus territorios («¿Dónde?») se guardan juntos o no se guardan
            obj = form.save(commit=False)
            obj.creado_por = self.request.user
            obj.save()
            form.save_m2m()
            asegurar_responsable(obj)  # F26 P2: el responsable queda en el equipo
            registrar_origen(obj, self.request.user)
        messages.success(self.request, "Proyecto creado. Puedes agregar actividades, equipo y documentos cuando quieras.")
        return HttpResponseRedirect(obj.get_absolute_url())


class ProyectoEditar(EditarBase):
    model = Proyecto
    form_class = ProyectoForm
    permission_required = "proyectos.change_proyecto"
    titulo = "Editar proyecto"
    breadcrumb = [("Proyectos", "/proyectos")]

    def form_valid(self, form):
        with transaction.atomic():  # el proyecto y sus territorios se guardan juntos o no se guardan
            respuesta = super().form_valid(form)
            if respuesta.status_code == 302:  # guardado (no hubo conflicto de versión)
                asegurar_responsable(self.object)  # F26 P2: el responsable queda en el equipo
            return respuesta


class ProyectoFicha(FichaBase):
    model = Proyecto
    template_name = "proyectos/ficha.html"
    permission_required = "proyectos.view_proyecto"
    breadcrumb = [("Proyectos", "/proyectos")]
    permiso_editar = "proyectos.change_proyecto"
    pestanas_segunda_fase = {"beneficiarios": "beneficiarios", "postulacion": "postulaciones", "presupuesto": "finanzas"}
    origen_en_historial = True  # F26 Ia
    pestanas = [
        ("resumen", "Resumen", "proyectos/pestanas/resumen.html"),
        ("equipo", "Equipo", "generico/_hijos.html"),
        ("organizaciones", "Organizaciones", "generico/_hijos.html"),
        ("comunidades", "Comunidades", "generico/_hijos.html", "comunidades.view_comunidad"),
        ("beneficiarios", "Beneficiarios", "proyectos/pestanas/beneficiarios.html"),
        ("tareas", "Tareas", "proyectos/pestanas/actividades.html", "actividades.view_actividad"),  # F25: la clave se conserva
        ("postulacion", "Postulación", "generico/_hijos.html"),
        ("alcance", "Alcance", "actividades/pestanas/alcance.html", "actividades.view_participacion"),
        ("documentos", "Documentos", "documentos/pestanas/lista.html", "documentos.view_documento"),
        ("presupuesto", "Presupuesto", "proyectos/pestanas/presupuesto.html", "finanzas.view_movimiento"),
        ("historial", "Historial", "generico/_historial.html", "proyectos.view_historicalproyecto"),
    ]

    def contexto_ficha(self):
        return {
            "url_editar": reverse("proyectos:editar", args=[self.object.pk]), "url_volver": "/proyectos",
            "puede_agregar": self.request.user.has_perm("proyectos.change_proyecto"),
        }

    def acciones_extra(self):
        """F26 P3a: «Finalizar proyecto» (con permiso de edición) y el informe en Excel (con permiso de exportar)."""
        u, pk = self.request.user, self.object.pk
        res = []
        if u.has_perm("proyectos.change_proyecto"):
            res.append(("Finalizar proyecto" if self.object.estado not in ("finalizado", "cancelado") else "Editar la conclusión",
                        reverse("proyectos:finalizar", args=[pk])))
        if u.has_perm("proyectos.exportar_proyecto"):
            res.append(("Descargar informe (Excel)", reverse("proyectos:informe", args=[pk])))
        return res

    def ctx_resumen(self):
        from apps.actividades.models import AgendaActividad

        # F25 F4: cada tarea con su fecha vigente, estado y resultado (dos consultas, sin importar cuántas tareas sean)
        acts = list(self.object.actividades.select_related("estado").prefetch_related(
            Prefetch("agendas", queryset=AgendaActividad.objects.filter(vigente=True), to_attr="agenda_v")))
        por_estado = {}
        for a in acts:
            por_estado[a.estado.nombre] = por_estado.get(a.estado.nombre, 0) + 1
        territorios = self.object.territorios.filter(vigente=True).select_related("region", "provincia", "comuna", "sector__comuna", "sector__sector_padre").order_by("pk")
        tareas = sorted(({"tarea": a, "fecha": a.agenda_v[0].fecha if a.agenda_v else None} for a in acts),
                        key=lambda t: (t["fecha"] is None, t["fecha"] or date.min, t["tarea"].nombre))
        return {"por_estado": por_estado, "total_actividades": len(acts), "tareas_resultado": tareas,
                "territorios": [{"texto": texto_destino(t), "url": getattr(t.territorio, "get_absolute_url", lambda: "")()} for t in territorios]}

    def _hijos(self, qs, slug, texto, detalle, titulo, etiqueta, vacio, url=None, ficha=None):
        pk = self.object.pk
        hijos = [{
            "texto": texto(o), "detalle": detalle(o), "vigente": o.vigente, "url": url(o) if url else "", "ficha": ficha(o) if ficha else None,
            "url_editar": reverse(f"proyectos:{slug}_editar", args=[pk, o.pk]), "url_alternar": reverse(f"proyectos:{slug}_alternar", args=[pk, o.pk]),
        } for o in qs]
        return {"titulo_pestana": titulo, "etiqueta_nuevo": etiqueta, "url_nuevo": reverse(f"proyectos:{slug}_nuevo", args=[pk]), "hijos": hijos, "vacio": vacio}

    def ctx_equipo(self):
        qs = self.object.personas.filter(tipo="equipo").select_related("persona", "rol")
        return self._hijos(qs, "equipo", lambda e: f"{e.persona}" + (" (responsable)" if e.es_responsable else ""), lambda e: str(e.rol or ""), "Equipo", "Persona", "Aún no hay personas en el equipo.",
                           url=lambda e: e.persona.get_absolute_url(),
                           ficha=lambda e: [("Persona", e.persona, e.persona.get_absolute_url()), ("Rol en el proyecto", e.rol, None),
                                            ("Responsable del proyecto", "Sí" if e.es_responsable else "No", None),
                                            ("Desde", f"{e.desde:%d-%m-%Y}" if e.desde else "", None), ("Hasta", f"{e.hasta:%d-%m-%Y}" if e.hasta else "Sigue en el proyecto", None),
                                            ("Estado", "Vigente" if e.vigente else "Dado de baja", None)])

    def ctx_organizaciones(self):
        qs = self.object.organizaciones.select_related("organizacion", "tipo_intervencion", "contacto")
        return self._hijos(qs, "organizaciones", lambda o: f"{o.organizacion}" + (f" · {o.tipo_intervencion}" if o.tipo_intervencion else ""), lambda o: o.observaciones, "Organizaciones", "Organización", "Sin organizaciones relacionadas.",
                           url=lambda o: o.organizacion.get_absolute_url(),
                           ficha=lambda o: [("Organización", o.organizacion, o.organizacion.get_absolute_url()), ("Cómo participa", o.tipo_intervencion, None),
                                            ("Persona de contacto", o.contacto or "", o.contacto.get_absolute_url() if o.contacto_id else None),
                                            ("Observaciones", o.observaciones, None), ("Estado", "Vigente" if o.vigente else "Dada de baja", None)])

    def ctx_comunidades(self):
        qs = self.object.comunidades_destino.select_related("comunidad__comuna", "comunidad__sector")
        return self._hijos(qs, "comunidades", lambda c: str(c.comunidad), lambda c: " · ".join(x for x in [c.comunidad.territorio, c.observaciones] if x),
                           "Comunidades destinatarias", "Comunidad", "Aún no se indica a qué comunidades va dirigido el proyecto.",
                           url=lambda c: c.comunidad.get_absolute_url(),
                           ficha=lambda c: [("Comunidad", c.comunidad, c.comunidad.get_absolute_url()), ("Dónde", c.comunidad.territorio, c.comunidad.comuna.get_absolute_url() if c.comunidad.comuna_id else None),
                                            ("Observaciones", c.observaciones, None), ("Estado", "Vigente" if c.vigente else "Dada de baja", None)])

    def ctx_alcance(self):
        from apps.actividades.alcance import alcance

        return {"alcance": alcance(self.object.actividades.all()), "contexto_alcance": "las actividades de este proyecto"}

    def ctx_postulacion(self):
        qs = self.object.postulaciones.all()
        return self._hijos(qs, "postulaciones", lambda p: str(p), lambda p: " · ".join(x for x in [f"{p.fecha:%d-%m-%Y}" if p.fecha else "", p.resultado] if x), "Postulaciones", "Postulación", "Sin postulaciones registradas.")

    def ctx_beneficiarios(self):
        ctx = self._hijos(self.object.personas.filter(tipo="beneficiario").select_related("persona"), "beneficiarios", lambda b: str(b.persona), lambda b: "", "Beneficiarios registrados en el proyecto", "Beneficiario", "Sin beneficiarios registrados directamente.",
                          url=lambda b: b.persona.get_absolute_url())
        from apps.actividades.models import Participacion

        ctx["desde_actividades"] = (
            Participacion.objects.filter(actividad__proyecto=self.object, rol__codigo="beneficiario").select_related("persona").order_by("persona__apellido_paterno").distinct()
        )
        ctx["poblacion"] = self.object.poblacion_objetivo
        return ctx

    alias_pestanas = {"actividades": "tareas", "origen": "historial"}  # enlaces antiguos: «actividades» abre las tareas; «origen», el historial

    def ctx_tareas(self):
        """Tareas del proyecto (actividades con proyecto) con su fecha y lugar vigentes, comunidades, participantes y asistencia.
        Cuatro consultas, sin importar cuántas tareas haya."""
        from apps.actividades.models import ActividadComunidad, AgendaActividad

        activas = ~Q(participaciones__estado__codigo="registro_erroneo")
        tareas = (
            self.object.actividades.select_related("estado", "responsable")
            .annotate(n_participantes=Count("participaciones", filter=activas, distinct=True),
                      n_asistieron=Count("participaciones", filter=activas & Q(participaciones__asistencia=True), distinct=True))
            .prefetch_related(
                Prefetch("agendas", queryset=AgendaActividad.objects.filter(vigente=True).select_related("lugar"), to_attr="agenda_v"),
                Prefetch("comunidades_destino", queryset=ActividadComunidad.objects.filter(vigente=True).select_related("comunidad"), to_attr="comunidades_v"),
            )
            .order_by("-creado_en")
        )
        return {"actividades": tareas, "url_nueva_tarea": reverse("actividades:tarea_nueva", args=[self.object.pk])}

    def ctx_documentos(self):
        docs = self.object.documentos.select_related("tipo")
        if not self.request.user.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        pk = self.object.pk
        return {"documentos": docs, "titulo_documentos": "Documentos del proyecto", "sin_contador_documentos": True,
                "url_nuevo_doc": f"/documentos/nuevo?proyecto={pk}", "url_asociar_doc": f"/documentos/asociar?proyecto={pk}"}

    def ctx_presupuesto(self):
        from apps.finanzas.resumen import resumen_proyecto

        pk = self.object.pk
        items = [{
            "texto": str(i), "detalle": i.get_categoria_display(), "vigente": i.vigente,
            "url_editar": reverse("finanzas:items_editar", args=[pk, i.pk]), "url_alternar": reverse("finanzas:items_alternar", args=[pk, i.pk]),
        } for i in self.object.items_presupuesto.all()]
        return {
            "resumen": resumen_proyecto(self.object), "hijos": items, "titulo_pestana": "Ítems del presupuesto", "etiqueta_nuevo": "Ítem",
            "url_nuevo": reverse("finanzas:items_nuevo", args=[pk]), "vacio": "Aún no hay ítems de presupuesto.",
            "puede_agregar": self.request.user.has_perm("finanzas.change_itempresupuesto"),
        }


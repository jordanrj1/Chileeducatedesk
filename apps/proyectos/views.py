from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView

from apps.nucleo.vistas_base import EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, cambios_historial

from .forms import ProyectoForm
from .models import Proyecto


class ProyectoLista(ListaBase):
    model = Proyecto
    permission_required = "proyectos.view_proyecto"
    titulo = "Proyectos"
    url_crear = "/proyectos/nuevo"
    permiso_crear = "proyectos.add_proyecto"
    etiqueta_crear = "+ Nuevo proyecto"
    campos_busqueda = ("nombre", "descripcion", "zona", "objetivo_general")
    columnas = [
        ("Proyecto", "nombre"), ("Estado", "get_estado_display"), ("Zona", "zona"), ("Responsable", "responsable"),
        ("Actividades", lambda p: p.n_actividades),
        ("Inicio", lambda p: p.fecha_inicio.strftime("%d-%m-%Y") if p.fecha_inicio else "—"),
    ]
    ordenes = {"nombre": "nombre", "inicio": "fecha_inicio"}
    orden_defecto = ("-creado_en",)
    filtros = [Filtro("estado", "Estado", "estado", lambda: list(Proyecto.ESTADOS))]
    url_exportar = "/proyectos/exportar"
    permiso_exportar = "proyectos.exportar_proyecto"

    def get_queryset(self):
        return super().get_queryset().select_related("responsable").annotate(n_actividades=Count("actividades", distinct=True))


class ProyectoExportar(ProyectoLista):
    exportar = True
    permission_required = "proyectos.exportar_proyecto"


class ProyectoNuevo(Permiso403Mixin, CreateView):
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

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nuevo proyecto", volver_url="/proyectos", breadcrumb=[("Proyectos", "/proyectos")])
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.creado_por = self.request.user
        obj.save()
        from apps.documentos.origen import registrar_origen

        registrar_origen(obj, self.request.user)
        messages.success(self.request, "Proyecto creado. Puedes agregar actividades, equipo y documentos cuando quieras.")
        return HttpResponseRedirect(obj.get_absolute_url())


class ProyectoEditar(EditarBase):
    model = Proyecto
    form_class = ProyectoForm
    permission_required = "proyectos.change_proyecto"
    titulo = "Editar proyecto"
    breadcrumb = [("Proyectos", "/proyectos")]


class ProyectoFicha(FichaBase):
    model = Proyecto
    permission_required = "proyectos.view_proyecto"
    breadcrumb = [("Proyectos", "/proyectos")]
    permiso_editar = "proyectos.change_proyecto"
    pestanas_segunda_fase = {"beneficiarios": "beneficiarios", "postulacion": "postulaciones", "presupuesto": "finanzas"}
    pestanas = [
        ("resumen", "Resumen", "proyectos/pestanas/resumen.html"),
        ("equipo", "Equipo", "generico/_hijos.html"),
        ("organizaciones", "Organizaciones", "generico/_hijos.html"),
        ("beneficiarios", "Beneficiarios", "proyectos/pestanas/beneficiarios.html"),
        ("actividades", "Actividades", "proyectos/pestanas/actividades.html", "actividades.view_actividad"),
        ("postulacion", "Postulación", "generico/_hijos.html"),
        ("documentos", "Documentos", "proyectos/pestanas/documentos.html", "documentos.view_documento"),
        ("presupuesto", "Presupuesto", "proyectos/pestanas/presupuesto.html", "finanzas.view_movimiento"),
        ("origen", "Origen", "documentos/pestanas/origen.html", "documentos.view_origendato"),
        ("historial", "Historial", "generico/_historial.html", "proyectos.view_historicalproyecto"),
    ]

    def contexto_ficha(self):
        return {
            "url_editar": reverse("proyectos:editar", args=[self.object.pk]), "url_volver": "/proyectos",
            "puede_agregar": self.request.user.has_perm("proyectos.change_proyecto"),
        }

    def ctx_resumen(self):
        acts = self.object.actividades.select_related("estado")
        por_estado = {}
        for a in acts:
            por_estado[a.estado.nombre] = por_estado.get(a.estado.nombre, 0) + 1
        return {"por_estado": por_estado, "total_actividades": len(acts)}

    def _hijos(self, qs, slug, texto, detalle, titulo, etiqueta, vacio):
        pk = self.object.pk
        hijos = [{
            "texto": texto(o), "detalle": detalle(o), "vigente": o.vigente,
            "url_editar": reverse(f"proyectos:{slug}_editar", args=[pk, o.pk]), "url_alternar": reverse(f"proyectos:{slug}_alternar", args=[pk, o.pk]),
        } for o in qs]
        return {"titulo_pestana": titulo, "etiqueta_nuevo": etiqueta, "url_nuevo": reverse(f"proyectos:{slug}_nuevo", args=[pk]), "hijos": hijos, "vacio": vacio}

    def ctx_equipo(self):
        qs = self.object.personas.filter(tipo="equipo").select_related("persona", "rol")
        return self._hijos(qs, "equipo", lambda e: f"{e.persona}" + (" (responsable)" if e.es_responsable else ""), lambda e: str(e.rol or ""), "Equipo", "Persona", "Aún no hay personas en el equipo.")

    def ctx_organizaciones(self):
        qs = self.object.organizaciones.select_related("organizacion", "tipo_intervencion", "contacto")
        return self._hijos(qs, "organizaciones", lambda o: f"{o.organizacion}" + (f" · {o.tipo_intervencion}" if o.tipo_intervencion else ""), lambda o: o.observaciones, "Organizaciones", "Organización", "Sin organizaciones relacionadas.")

    def ctx_postulacion(self):
        qs = self.object.postulaciones.all()
        return self._hijos(qs, "postulaciones", lambda p: str(p), lambda p: " · ".join(x for x in [f"{p.fecha:%d-%m-%Y}" if p.fecha else "", p.resultado] if x), "Postulaciones", "Postulación", "Sin postulaciones registradas.")

    def ctx_beneficiarios(self):
        ctx = self._hijos(self.object.personas.filter(tipo="beneficiario").select_related("persona"), "beneficiarios", lambda b: str(b.persona), lambda b: "", "Beneficiarios registrados en el proyecto", "Beneficiario", "Sin beneficiarios registrados directamente.")
        from apps.actividades.models import Participacion

        ctx["desde_actividades"] = (
            Participacion.objects.filter(actividad__proyecto=self.object, rol__codigo="beneficiario").select_related("persona").order_by("persona__apellido_paterno").distinct()
        )
        ctx["poblacion"] = self.object.poblacion_objetivo
        return ctx

    def ctx_actividades(self):
        return {"actividades": self.object.actividades.select_related("estado", "tipo", "responsable").order_by("-creado_en")}

    def ctx_documentos(self):
        docs = self.object.documentos.select_related("tipo")
        if not self.request.user.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        return {"documentos": docs}

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

    def ctx_origen(self):
        from apps.documentos.origen import contexto_origen

        return contexto_origen(self.object, self.request.user)

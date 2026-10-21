"""Pantallas de organizaciones: listado, crear con aviso de parecidas, ficha con pestañas (contactos, carreras,
personas con cargo, actividades, documentos, historial), cerrar autoridades al cambiar de administración,
unir repetidas (Administrador) y buscador para elegir una organización desde otros formularios."""
from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView

from apps.nucleo.direccion_mixin import ComunaInicialMixin, ConDireccionMixin
from apps.nucleo.models import EstadoRegistro, TipoOrganizacion
from apps.nucleo.selector import OpcionesVista, campo_seguro, respuesta_elegido
from apps.nucleo.vistas_base import (
    ControlVersionMixin, AlternarActivoBase, CrearBase, EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, filtro_activo, opciones_modelo,
)

from .duplicados import organizaciones_parecidas
from .forms import CarreraForm, OrganizacionForm
from .models import Carrera, Organizacion
from .selector import ORGANIZACIONES


class OrganizacionLista(ListaBase):
    model = Organizacion
    permission_required = "organizaciones.view_organizacion"
    titulo = "Organizaciones"
    descripcion = "Instituciones, juntas de vecinos, empresas y otras organizaciones con las que trabaja la fundación."
    url_crear = "/organizaciones/nueva"
    permiso_crear = "organizaciones.add_organizacion"
    etiqueta_crear = "+ Nueva organización"
    campos_busqueda = ("nombre", "otro_identificador", "descripcion")
    columnas = [("Nombre", "nombre"), ("Tipo", "tipo"), ("RUT", "rut"), ("Comuna", lambda o: o.direccion.comuna if o.direccion_id else ""), ("Estado", "estado_registro")]
    ordenes = {"nombre": "nombre"}
    orden_defecto = ("nombre",)
    filtros = [Filtro("tipo", "Tipo", "tipo_id", opciones_modelo(TipoOrganizacion), principal=True), filtro_activo(femenino=True)]
    url_exportar = "/organizaciones/exportar"
    permiso_exportar = "organizaciones.exportar_organizacion"

    def get_queryset(self):
        return super().get_queryset().select_related("tipo", "estado_registro", "direccion__comuna")


class OrganizacionExportar(OrganizacionLista):
    exportar = True
    permission_required = "organizaciones.exportar_organizacion"


class OrganizacionNueva(ComunaInicialMixin, ConDireccionMixin, Permiso403Mixin, CreateView):
    model = Organizacion
    form_class = OrganizacionForm
    permission_required = "organizaciones.add_organizacion"
    template_name = "organizaciones/formulario.html"

    def get_initial(self):
        """Desde la ficha de una comuna: `?comuna=<id>` prellena la dirección y `?tipo=<código>` elige el tipo. Lo inválido se ignora."""
        ini = super().get_initial()
        tipo = TipoOrganizacion.objects.filter(codigo=self.request.GET.get("tipo", ""), activo=True).first() if self.request.method == "GET" else None
        if tipo:
            ini["tipo"] = tipo.pk
            comuna = self.comuna_inicial()
            # «+ Registrar municipalidad»: queda como la municipalidad de esa comuna, si todavía no tiene una
            if tipo.codigo == "municipalidad" and comuna and not Organizacion.objects.filter(comuna_municipal=comuna).exists():
                ini["comuna_municipal"] = comuna.pk
        return ini

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nueva organización", volver_url="/organizaciones", breadcrumb=[("Organizaciones", "/organizaciones")])
        return ctx

    def form_valid(self, form):
        if not self.request.POST.get("confirmar_duplicado"):
            cands = organizaciones_parecidas(form.cleaned_data["nombre"], form.cleaned_data.get("rut"))
            if cands:
                return self.render_to_response(self.get_context_data(form=form, form_direccion=self._form_dir(), candidatos=cands))
        obj = form.save(commit=False)
        obj.creado_por = self.request.user
        if not obj.estado_registro_id:
            obj.estado_registro = EstadoRegistro.objects.filter(codigo="activo").first()
        obj.save()
        from apps.documentos.origen import registrar_origen

        registrar_origen(obj, self.request.user)
        messages.success(self.request, "Organización registrada.")
        return HttpResponseRedirect(obj.get_absolute_url())


class OrganizacionEditar(ControlVersionMixin, ConDireccionMixin, Permiso403Mixin, __import__("django.views.generic", fromlist=["UpdateView"]).UpdateView):
    model = Organizacion
    form_class = OrganizacionForm
    permission_required = "organizaciones.change_organizacion"
    template_name = "organizaciones/formulario.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Editar organización", volver_url=self.object.get_absolute_url(), breadcrumb=[("Organizaciones", "/organizaciones")])
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Guardado.")
        return HttpResponseRedirect(self.object.get_absolute_url())


class OrganizacionFusionar(__import__("apps.nucleo.vistas_fusion", fromlist=["FusionarBase"]).FusionarBase):
    modelo = Organizacion
    permiso = "organizaciones.fusionar_organizacion"
    titulo = "Fusionar organizaciones duplicadas"

    def campo_destino(self, origen):
        from apps.nucleo.formularios import SelectorField

        return SelectorField(ORGANIZACIONES, filtros={"excluir": origen.pk}, crear=False, label="Organización que se conserva")


class OrganizacionAlternar(AlternarActivoBase):
    modelo = Organizacion
    permission_required = "organizaciones.change_organizacion"

    def afectados(self, obj):
        from apps.actividades.afectacion import de_organizacion

        return de_organizacion(obj)


class OrganizacionFicha(FichaBase):
    model = Organizacion
    template_name = "organizaciones/ficha.html"
    permission_required = "organizaciones.view_organizacion"
    breadcrumb = [("Organizaciones", "/organizaciones")]
    permiso_editar = "organizaciones.change_organizacion"

    def pestanas_visibles(self):
        return [p for p in super().pestanas_visibles() if not (p[0] == "carreras" and not self.object.es_educativa)]

    pestanas = [
        ("info", "Información", "organizaciones/pestanas/info.html"),
        ("contactos", "Contactos", "generico/_hijos.html"),
        ("carreras", "Carreras", "generico/_hijos.html"),
        ("personas", "Personas relacionadas", "organizaciones/pestanas/personas.html"),
        ("actividades", "Actividades y proyectos", "organizaciones/pestanas/actividades.html", "actividades.view_actividadorganizacion"),
        ("documentos", "Documentos", "documentos/pestanas/lista.html", "documentos.view_documento"),
        ("origen", "Origen", "documentos/pestanas/origen.html", "documentos.view_origendato"),
        ("historial", "Historial", "generico/_historial.html", "organizaciones.view_historicalorganizacion"),
    ]

    def acciones_extra(self):
        res = []
        if self.request.user.has_perm("coordinacion.add_interaccion"):
            res.append(("Registrar interacción", f"/interacciones/nueva?organizacion={self.object.pk}"))
        if self.request.user.has_perm("organizaciones.fusionar_organizacion") and self.object.activo:
            res.append(("Fusionar con otra", f"/organizaciones/{self.object.pk}/fusionar"))
        return res

    def get_queryset(self):
        return super().get_queryset().select_related("direccion__comuna", "comuna_municipal")

    def contexto_ficha(self):
        o = self.object
        return {
            "url_editar": reverse("organizaciones:editar", args=[o.pk]),
            "url_volver": "/organizaciones",
            "puede_agregar": self.request.user.has_perm("organizaciones.change_organizacion"),
            # la comuna de su dirección o, si es una municipalidad sin dirección, la que representa
            "comuna_ficha": (o.direccion.comuna if o.direccion_id else None) or o.comuna_municipal,
        }

    def ctx_contactos(self):
        pk = self.object.pk
        hijos = []
        for c in self.object.contactos.select_related("tipo"):
            hijos.append({
                "texto": f"{c.tipo}: {c.valor}", "detalle": " · ".join(x for x in [c.proposito, "Principal" if c.principal else ""] if x), "vigente": c.vigente,
                "url_editar": reverse("organizaciones:contactos_editar", args=[pk, c.pk]), "url_alternar": reverse("organizaciones:contactos_alternar", args=[pk, c.pk]),
            })
        return {"titulo_pestana": "Contactos", "etiqueta_nuevo": "Contacto", "url_nuevo": reverse("organizaciones:contactos_nuevo", args=[pk]), "hijos": hijos, "vacio": "Sin contactos registrados."}

    def ctx_actividades(self):
        o = self.object
        return {
            "participaciones_org": o.actividades.select_related("actividad__estado", "tipo_intervencion").order_by("-actividad__creado_en"),
            "proyectos_org": o.proyectos.select_related("proyecto", "tipo_intervencion"),
            "interacciones": o.interacciones.select_related("canal").order_by("-fecha")[:30],
            "colaboraciones": o.colaboraciones.select_related("actividad", "tipo_apoyo"),
        }

    def ctx_documentos(self):
        docs = self.object.documentos.select_related("tipo")
        if not self.request.user.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        return {"documentos": docs, "url_nuevo_doc": f"/documentos/nuevo?organizacion={self.object.pk}", "url_asociar_doc": f"/documentos/asociar?organizacion={self.object.pk}"}

    def ctx_origen(self):
        from apps.documentos.origen import contexto_origen

        return contexto_origen(self.object, self.request.user)

    def ctx_carreras(self):
        pk = self.object.pk
        hijos = [{
            "texto": c.nombre, "vigente": c.activo, "detalle": "",
            "url_editar": reverse("organizaciones:carreras_editar", args=[pk, c.pk]),
        } for c in self.object.carreras.all()]
        return {"titulo_pestana": "Carreras", "etiqueta_nuevo": "Carrera", "url_nuevo": reverse("organizaciones:carreras_nuevo", args=[pk]), "hijos": hijos, "vacio": "Sin carreras registradas."}

    def ctx_personas(self):
        pk = self.object.pk
        hijos = [{
            "texto": f"{v.persona} · {v.cargo or 'Vínculo'}", "url": v.persona.get_absolute_url(), "vigente": v.vigente,
            "detalle": f"{v.get_tipo_cargo_display()} · {v.fecha_inicio or '?'} a {v.fecha_termino or 'actualidad'}",
            "url_editar": reverse("organizaciones:personas_editar", args=[pk, v.pk]),
        } for v in self.object.vinculos.select_related("persona")]
        return {
            "titulo_pestana": "Personas relacionadas", "hijos": hijos, "etiqueta_nuevo": "Agregar persona con cargo",
            "url_nuevo": reverse("organizaciones:personas_nuevo", args=[pk]), "vacio": "Aún no hay personas vinculadas.",
            "hay_autoridades": self.object.vinculos.filter(tipo_cargo="autoridad", fecha_termino__isnull=True).exists(),
        }


class CerrarCargosAutoridad(Permiso403Mixin, __import__("django.views", fromlist=["View"]).View):
    """OR-E6: cambio de administración. Se cierran los cargos de autoridad vigentes; los contactos de oficina siguen."""

    permission_required = "personas.change_personaorganizacion"

    def post(self, request, pk):
        from datetime import date

        from apps.nucleo.auditoria import registrar

        org = get_object_or_404(Organizacion, pk=pk)
        try:
            hasta = date.fromisoformat(request.POST.get("hasta", ""))
        except ValueError:
            messages.error(request, "Indica la fecha de término.")
            return HttpResponseRedirect(f"{org.get_absolute_url()}?tab=personas")
        n = 0
        for v in org.vinculos.filter(tipo_cargo="autoridad", fecha_termino__isnull=True):
            if v.fecha_inicio and v.fecha_inicio > hasta:
                continue
            v.fecha_termino = hasta
            v.save()
            n += 1
        registrar(request.user, "cargos_autoridad_cerrados", org, f"{n} cargos al {hasta:%d-%m-%Y}")
        messages.success(request, f"{n} cargo(s) de autoridad cerrados al {hasta:%d-%m-%Y}. Los nuevos se agregan con «Agregar persona con cargo».")
        return HttpResponseRedirect(f"{org.get_absolute_url()}?tab=personas")


class CarreraNueva(Permiso403Mixin, CreateView):
    model = Carrera
    form_class = CarreraForm
    permission_required = "organizaciones.add_carrera"
    template_name = "generico/formulario.html"

    def dispatch(self, request, *a, **kw):
        self.org = get_object_or_404(Organizacion, pk=kw["pk"])
        return super().dispatch(request, *a, **kw)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["organizacion"] = self.org
        return kw

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Agregar carrera", volver_url=f"{self.org.get_absolute_url()}?tab=carreras", breadcrumb=[(self.org.nombre, self.org.get_absolute_url())])
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Carrera guardada.")
        return HttpResponseRedirect(f"{self.org.get_absolute_url()}?tab=carreras")


class CarreraEditar(Permiso403Mixin, __import__("django.views.generic", fromlist=["UpdateView"]).UpdateView):
    model = Carrera
    form_class = CarreraForm
    permission_required = "organizaciones.change_carrera"
    template_name = "generico/formulario.html"
    pk_url_kwarg = "hijo_pk"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["organizacion"] = self.object.organizacion
        return kw

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        org = self.object.organizacion
        ctx.update(titulo="Editar carrera", volver_url=f"{org.get_absolute_url()}?tab=carreras", breadcrumb=[(org.nombre, org.get_absolute_url())])
        return ctx

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Carrera guardada.")
        return HttpResponseRedirect(f"{self.object.organizacion.get_absolute_url()}?tab=carreras")


class OrganizacionOpciones(OpcionesVista):
    """Lista de organizaciones para los buscadores de los formularios (ver apps/organizaciones/selector.py)."""

    fuente = ORGANIZACIONES


class OrganizacionCrearRapida(Permiso403Mixin, __import__("django.views", fromlist=["View"]).View):
    """Ventana «+ Crear organización» de los buscadores: nombre y tipo, aviso de parecidas («Usar esta organización»
    o «Es otra: crear») y la organización queda elegida en el formulario de origen, sin salir de él."""

    permission_required = "organizaciones.add_organizacion"
    plantilla = "generico/_crear_rapida.html"

    def _ctx(self, datos, form, **extra):
        return {
            "form": form, "campo_id": campo_seguro(datos.get("campo")), "filtros": ORGANIZACIONES.limpiar_filtros(datos),
            "accion": reverse("organizaciones:crear_rapida"), "titulo": "Crear organización", "aviso_parecido": "Esta organización podría ya existir.",
            "texto_usar": "Usar esta organización", "texto_crear_igual": "Es otra: crear", "pide_nota": False, **extra,
        }

    def _form(self, datos, data=None):
        from .forms import OrganizacionRapidaForm

        tipo = ORGANIZACIONES.limpiar_filtros(datos).get("tipo", "")
        return OrganizacionRapidaForm(data, prefix="rapida", tipo_fijo=tipo, initial={"nombre": datos.get("q", "")[:200]})

    def get(self, request):
        from django.shortcuts import render

        return render(request, self.plantilla, self._ctx(request.GET, self._form(request.GET)))

    def post(self, request):
        from django.shortcuts import render

        from apps.documentos.origen import registrar_origen

        form = self._form(request.POST, request.POST)
        if not form.is_valid():
            return render(request, self.plantilla, self._ctx(request.POST, form))
        d = form.cleaned_data
        if not request.POST.get("confirmar_duplicado"):
            cands = organizaciones_parecidas(d["nombre"])
            if cands:
                filtros = ORGANIZACIONES.limpiar_filtros(request.POST)
                elegibles = set(ORGANIZACIONES.base(**filtros).filter(pk__in=[o.pk for o, _ in cands]).values_list("pk", flat=True))
                lista = [(o, razones, o.pk in elegibles) for o, razones in cands]
                return render(request, self.plantilla, self._ctx(request.POST, form, candidatos=lista))
        org = Organizacion.objects.create(
            nombre=d["nombre"], tipo=d["tipo"], creado_por=request.user,
            estado_registro=EstadoRegistro.objects.filter(codigo="incompleto").first(),  # le falta dirección y contacto
        )
        registrar_origen(org, request.user)
        return respuesta_elegido(request.POST.get("campo"), org.pk, ORGANIZACIONES.texto(org), "Organización creada y elegida. Completa su ficha cuando puedas.")

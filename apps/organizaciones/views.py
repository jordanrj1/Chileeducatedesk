from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView

from apps.nucleo.direccion_mixin import ConDireccionMixin
from apps.nucleo.models import EstadoRegistro, TipoOrganizacion
from apps.nucleo.vistas_base import (
    AlternarActivoBase, CrearBase, EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, filtro_activo, opciones_modelo,
)
from apps.personas.duplicados import candidatos  # noqa: F401  (reutilizado por los selectores)

from .forms import CarreraForm, OrganizacionForm
from .models import Carrera, Organizacion


def organizaciones_parecidas(nombre, rut=None, excluir=None):
    """Buscar antes de crear: mismo RUT o nombre parecido (pg_trgm)."""
    from django.contrib.postgres.search import TrigramSimilarity

    encontradas = {}
    if rut:
        for o in Organizacion.objects.filter(rut_numero=rut[0]):
            encontradas[o.pk] = (o, ["mismo RUT"])
    if nombre:
        for o in Organizacion.objects.annotate(sim=TrigramSimilarity("nombre", nombre)).filter(sim__gte=0.45).order_by("-sim")[:10]:
            encontradas.setdefault(o.pk, (o, []))[1].append(f"nombre parecido ({int(o.sim * 100)}%)")
    return [v for k, v in encontradas.items() if k != excluir]


class OrganizacionLista(ListaBase):
    model = Organizacion
    permission_required = "organizaciones.view_organizacion"
    titulo = "Organizaciones"
    url_crear = "/organizaciones/nueva"
    permiso_crear = "organizaciones.add_organizacion"
    etiqueta_crear = "+ Nueva organización"
    campos_busqueda = ("nombre", "otro_identificador", "descripcion")
    columnas = [("Nombre", "nombre"), ("Tipo", "tipo"), ("RUT", "rut"), ("Comuna", lambda o: o.direccion.comuna if o.direccion_id else ""), ("Estado", "estado_registro")]
    ordenes = {"nombre": "nombre"}
    orden_defecto = ("nombre",)
    filtros = [filtro_activo(), Filtro("tipo", "Tipo", "tipo_id", opciones_modelo(TipoOrganizacion))]
    url_exportar = "/organizaciones/exportar"
    permiso_exportar = "organizaciones.exportar_organizacion"

    def get_queryset(self):
        return super().get_queryset().select_related("tipo", "estado_registro", "direccion__comuna")


class OrganizacionNueva(ConDireccionMixin, Permiso403Mixin, CreateView):
    model = Organizacion
    form_class = OrganizacionForm
    permission_required = "organizaciones.add_organizacion"
    template_name = "organizaciones/formulario.html"

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
        messages.success(self.request, "Organización registrada.")
        return HttpResponseRedirect(obj.get_absolute_url())


class OrganizacionEditar(ConDireccionMixin, Permiso403Mixin, __import__("django.views.generic", fromlist=["UpdateView"]).UpdateView):
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


class OrganizacionAlternar(AlternarActivoBase):
    modelo = Organizacion
    permission_required = "organizaciones.change_organizacion"


class OrganizacionFicha(FichaBase):
    model = Organizacion
    permission_required = "organizaciones.view_organizacion"
    breadcrumb = [("Organizaciones", "/organizaciones")]
    permiso_editar = "organizaciones.change_organizacion"

    def pestanas_visibles(self):
        return [p for p in super().pestanas_visibles() if not (p[0] == "carreras" and not self.object.es_educativa)]

    pestanas = [
        ("info", "Información", "organizaciones/pestanas/info.html"),
        ("contactos", "Contactos", "generico/_hijos.html"),
        ("carreras", "Carreras", "generico/_hijos.html"),
        ("personas", "Personas relacionadas", "generico/_hijos.html"),
        ("historial", "Historial", "generico/_historial.html", "organizaciones.view_historicalorganizacion"),
    ]

    def contexto_ficha(self):
        o = self.object
        return {
            "url_editar": reverse("organizaciones:editar", args=[o.pk]),
            "url_volver": "/organizaciones",
            "puede_agregar": self.request.user.has_perm("organizaciones.change_organizacion"),
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

    def ctx_carreras(self):
        pk = self.object.pk
        hijos = [{
            "texto": c.nombre, "vigente": c.activo, "detalle": "",
            "url_editar": reverse("organizaciones:carreras_editar", args=[pk, c.pk]),
        } for c in self.object.carreras.all()]
        return {"titulo_pestana": "Carreras", "etiqueta_nuevo": "Carrera", "url_nuevo": reverse("organizaciones:carreras_nuevo", args=[pk]), "hijos": hijos, "vacio": "Sin carreras registradas."}

    def ctx_personas(self):
        hijos = [{
            "texto": f"{v.persona} · {v.cargo or 'Vínculo'}", "vigente": v.vigente,
            "detalle": f"{v.get_tipo_cargo_display()} · {v.fecha_inicio or '?'} a {v.fecha_termino or 'actualidad'}",
        } for v in self.object.vinculos.select_related("persona")]
        return {"titulo_pestana": "Personas relacionadas", "hijos": hijos, "puede_agregar": False, "vacio": "Aún no hay personas vinculadas. Se registran desde la ficha de cada persona."}


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

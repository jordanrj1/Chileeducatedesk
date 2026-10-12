import mimetypes

from django.apps import apps as registro
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, UpdateView

from apps.nucleo.auditoria import registrar
from apps.nucleo.models import TipoDocumento
from apps.nucleo.vistas_base import FichaBase, Filtro, ListaBase, Permiso403Mixin, filtro_activo, opciones_modelo

from .forms import DocumentoForm, OrigenForm
from .models import Documento, OrigenDato
from .origen import MODELOS_CON_ORIGEN, registrar_origen


class DocumentoLista(ListaBase):
    model = Documento
    permission_required = "documentos.view_documento"
    titulo = "Documentos"
    url_crear = "/documentos/nuevo"
    permiso_crear = "documentos.add_documento"
    etiqueta_crear = "+ Nuevo documento"
    campos_busqueda = ("nombre", "descripcion", "folio", "emisor")
    columnas = [
        ("Documento", "nombre"), ("Tipo", "tipo"), ("Fecha", lambda d: d.fecha.strftime("%d-%m-%Y")),
        ("Asociado a", lambda d: d.actividad or d.proyecto or d.persona or d.organizacion or "—"), ("Restringido", lambda d: "Sí" if d.restringido else ""),
    ]
    orden_defecto = ("-fecha", "-id")
    filtros = [
        filtro_activo(),
        Filtro("tipo", "Tipo", "tipo_id", opciones_modelo(TipoDocumento)),
        Filtro("desde", "Desde", "fecha__gte", entrada="date"),
        Filtro("hasta", "Hasta", "fecha__lte", entrada="date"),
    ]

    def get_queryset(self):
        qs = super().get_queryset().select_related("tipo", "actividad", "proyecto", "persona", "organizacion")
        if not self.request.user.has_perm("documentos.ver_restringido"):
            qs = qs.filter(restringido=False)
        return qs


class DocumentoNuevo(Permiso403Mixin, CreateView):
    model = Documento
    form_class = DocumentoForm
    permission_required = "documentos.add_documento"
    template_name = "generico/formulario.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["puede_restringir"] = self.request.user.has_perm("documentos.ver_restringido")
        return kw

    def get_initial(self):
        ini = super().get_initial()
        for k in ("actividad", "proyecto", "persona", "organizacion"):
            if self.request.GET.get(k, "").isdigit():
                ini[k] = int(self.request.GET[k])
        return ini

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nuevo documento", volver_url=self.request.META.get("HTTP_REFERER") or "/documentos", breadcrumb=[("Documentos", "/documentos")])
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.subido_por = self.request.user
        obj.save()
        registrar(self.request.user, "documento_subido", obj, "restringido" if obj.restringido else "")
        for destino in (obj.actividad, obj.proyecto, obj.persona, obj.organizacion):
            if destino:
                messages.success(self.request, "Documento guardado.")
                return HttpResponseRedirect(f"{destino.get_absolute_url()}?tab=documentos")
        return HttpResponseRedirect(obj.get_absolute_url())


class DocumentoEditar(Permiso403Mixin, UpdateView):
    model = Documento
    form_class = DocumentoForm
    permission_required = "documentos.change_documento"
    template_name = "generico/formulario.html"

    def get_object(self, qs=None):
        obj = super().get_object(qs)
        if obj.restringido and not self.request.user.has_perm("documentos.ver_restringido"):
            raise PermissionDenied
        return obj

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["puede_restringir"] = self.request.user.has_perm("documentos.ver_restringido")
        return kw

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Editar documento", volver_url=self.object.get_absolute_url(), breadcrumb=[("Documentos", "/documentos")])
        return ctx

    def form_valid(self, form):
        obj = form.save()
        messages.success(self.request, "Documento actualizado.")
        return HttpResponseRedirect(obj.get_absolute_url())


class DocumentoFicha(FichaBase):
    model = Documento
    permission_required = "documentos.view_documento"
    breadcrumb = [("Documentos", "/documentos")]
    permiso_editar = "documentos.change_documento"
    pestanas = [("datos", "Datos", "documentos/pestanas/datos.html")]

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.restringido and not self.request.user.has_perm("documentos.ver_restringido"):
            raise PermissionDenied
        return obj

    def contexto_ficha(self):
        return {"url_editar": reverse("documentos:editar", args=[self.object.pk]), "url_volver": "/documentos", "puede_agregar": self.request.user.has_perm("documentos.change_documento"),
                "origenes": self.object.origenes.all()}


class DocumentoAlternar(Permiso403Mixin, View):
    """Archivar o restaurar. Nunca se borra el archivo."""

    permission_required = "documentos.change_documento"

    def post(self, request, pk):
        d = get_object_or_404(Documento, pk=pk)
        if d.restringido and not request.user.has_perm("documentos.ver_restringido"):
            raise PermissionDenied
        d.activo = not d.activo
        d.save(update_fields=["activo"])
        messages.success(request, "Documento restaurado." if d.activo else "Documento archivado; el archivo se conserva.")
        return HttpResponseRedirect(d.get_absolute_url())


class DocumentoArchivo(Permiso403Mixin, View):
    """Los archivos nunca se sirven como estáticos: siempre pasan por esta vista, que comprueba permiso."""

    permission_required = "documentos.view_documento"

    def get(self, request, pk):
        d = get_object_or_404(Documento, pk=pk)
        if d.restringido and not request.user.has_perm("documentos.ver_restringido"):
            raise PermissionDenied
        try:
            f = d.archivo.open("rb")
        except (FileNotFoundError, ValueError):
            raise Http404("El archivo no está disponible en el servidor.")
        tipo = mimetypes.guess_type(d.archivo.name)[0] or "application/octet-stream"
        registrar(request.user, "documento_descargado", d, "restringido" if d.restringido else "")
        r = FileResponse(f, content_type=tipo)
        nombre = f"{d.nombre}.{d.extension}" if d.extension and not d.nombre.lower().endswith(d.extension) else d.nombre
        r["Content-Disposition"] = f'attachment; filename*=UTF-8\'\'{__import__("urllib.parse", fromlist=["quote"]).quote(nombre)}'
        r["X-Content-Type-Options"] = "nosniff"
        return r


class OrigenNuevo(Permiso403Mixin, CreateView):
    model = OrigenDato
    form_class = OrigenForm
    permission_required = "documentos.add_origendato"
    template_name = "generico/formulario.html"

    def dispatch(self, request, *a, **kw):
        clave = f"{kw['app']}.{kw['modelo']}"
        if clave not in MODELOS_CON_ORIGEN:
            raise Http404
        self.objeto = get_object_or_404(registro.get_model(kw["app"], kw["modelo"]), pk=kw["pk"])
        return super().dispatch(request, *a, **kw)

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Registrar origen del dato", volver_url=f"{self.objeto.get_absolute_url()}?tab=origen", breadcrumb=[(str(self.objeto), self.objeto.get_absolute_url())])
        return ctx

    def form_valid(self, form):
        o = form.save(commit=False)
        o.content_type = ContentType.objects.get_for_model(self.objeto)
        o.object_id = self.objeto.pk
        o.registrado_por = self.request.user
        o.save()
        messages.success(self.request, "Origen registrado.")
        return HttpResponseRedirect(f"{self.objeto.get_absolute_url()}?tab=origen")


class OrigenVerificar(Permiso403Mixin, View):
    permission_required = "documentos.change_origendato"

    def post(self, request, pk):
        o = get_object_or_404(OrigenDato, pk=pk)
        estado = request.POST.get("estado")
        if estado in dict(OrigenDato.VERIFICACION):
            o.estado_verificacion = estado
            o.save(update_fields=["estado_verificacion"])
            registrar(request.user, "verificacion_dato", str(o.objeto), estado)
            messages.success(request, "Estado de verificación actualizado.")
        return HttpResponseRedirect(f"{o.objeto.get_absolute_url()}?tab=origen")

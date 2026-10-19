"""Pantallas de documentos: listado con filtros, subir, asociar existente, ficha, editar, reemplazar el archivo
(conserva el anterior), archivar, transcribir con el documento al lado y registrar el origen de un dato.
Los archivos nunca se sirven directo: DocumentoArchivo y DocumentoVer revisan el permiso y anotan la descarga."""
import mimetypes
from urllib.parse import quote

from django.apps import apps as registro
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.generic import CreateView, UpdateView

from apps.nucleo.auditoria import registrar
from apps.nucleo.models import TipoDocumento
from apps.nucleo.vistas_base import FichaBase, Filtro, ListaBase, Permiso403Mixin, filtro_activo, opciones_modelo

from .forms import AsociarExistenteForm, DocumentoForm, OrigenForm
from .models import Documento, OrigenDato
from .origen import MODELOS_CON_ORIGEN, registrar_origen


class DocumentoLista(ListaBase):
    model = Documento
    permission_required = "documentos.view_documento"
    titulo = "Documentos"
    descripcion = "Archivos, evidencias y respaldos asociados a actividades, proyectos, personas y organizaciones."
    url_crear = "/documentos/nuevo"
    permiso_crear = "documentos.add_documento"
    etiqueta_crear = "+ Nuevo documento"
    campos_busqueda = ("nombre", "descripcion", "folio", "emisor")
    columnas = [
        ("Documento", "nombre"), ("Tipo", "tipo"), ("Fecha", lambda d: d.fecha.strftime("%d-%m-%Y")),
        ("Asociado a", lambda d: d.actividad or d.proyecto or d.persona or d.organizacion or d.solicitud or "—"), ("Restringido", lambda d: "Sí" if d.restringido else ""),
    ]
    orden_defecto = ("-fecha", "-id")
    filtros = [
        Filtro("tipo", "Tipo", "tipo_id", opciones_modelo(TipoDocumento), principal=True),
        Filtro("vencimiento", "Vigencia", "", lambda: [("vencidos", "Vencidos"), ("por_vencer", "Vencen en 30 días")], aplicar=lambda qs, v: _vigencia(qs, v),
               principal=True, todos="Todas"),
        Filtro("desde", "Desde", "fecha__gte", entrada="date", grupo="Fecha"),
        Filtro("hasta", "Hasta", "fecha__lte", entrada="date", grupo="Fecha"),
        Filtro("persona", "Persona", "persona_id", lambda: [(str(p.pk), p.nombre_completo) for p in __import__("apps.personas.models", fromlist=["Persona"]).Persona.objects.filter(documentos__isnull=False).distinct()],
               grupo="Asociado a", todos="Todas"),
        Filtro("actividad", "Actividad", "actividad_id", lambda: [(str(a.pk), a.nombre) for a in __import__("apps.actividades.models", fromlist=["Actividad"]).Actividad.objects.filter(documentos__isnull=False).distinct()[:301]],
               grupo="Asociado a", todos="Todas", tope=300),
        filtro_activo(),
    ]

    def get_queryset(self):
        qs = super().get_queryset().select_related("tipo", "actividad", "proyecto", "persona", "organizacion")
        if not self.request.user.has_perm("documentos.ver_restringido"):
            qs = qs.filter(restringido=False)
        return qs


def _vigencia(qs, v):
    from datetime import timedelta

    from django.utils import timezone

    hoy = timezone.localdate()
    if v == "vencidos":
        return qs.filter(fecha_vencimiento__lt=hoy)
    if v == "por_vencer":
        return qs.filter(fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=hoy + timedelta(days=30))
    return qs


DESTINOS = {"actividad": ("actividades", "Actividad"), "proyecto": ("proyectos", "Proyecto"), "persona": ("personas", "Persona"), "organizacion": ("organizaciones", "Organizacion"), "solicitud": ("solicitudes", "Solicitud")}


class DocumentoAsociar(Permiso403Mixin, View):
    """[Asociar existente]: el mismo archivo queda disponible en otra ficha sin copiarlo (DO-03)."""

    permission_required = "documentos.add_documento"

    def _destino(self, request):
        for campo, (app, modelo) in DESTINOS.items():
            v = request.GET.get(campo) or request.POST.get(campo)
            if v and v.isdigit():
                return campo, get_object_or_404(registro.get_model(app, modelo), pk=v)
        raise Http404

    def _ctx(self, destino, form):
        return {"form": form, "titulo": f"Asociar documento existente a {destino}", "volver_url": f"{destino.get_absolute_url()}?tab=documentos", "breadcrumb": [(str(destino), destino.get_absolute_url())]}

    def get(self, request):
        campo, destino = self._destino(request)
        return render(request, "documentos/asociar.html", {**self._ctx(destino, AsociarExistenteForm(usuario=request.user)), "campo": campo, "destino": destino})

    def post(self, request):
        campo, destino = self._destino(request)
        form = AsociarExistenteForm(request.POST, usuario=request.user)
        if not form.is_valid():
            return render(request, "documentos/asociar.html", {**self._ctx(destino, form), "campo": campo, "destino": destino}, status=400)
        original = form.cleaned_data["documento"]
        if Documento.objects.filter(archivo=original.archivo.name, **{campo: destino}).exists():
            messages.info(request, "Ese documento ya estaba asociado aquí.")
        else:
            copia = Documento(
                nombre=original.nombre, tipo=original.tipo, fecha=original.fecha, descripcion=original.descripcion, restringido=original.restringido,
                folio=original.folio, emisor=original.emisor, fecha_emision=original.fecha_emision, fecha_vencimiento=original.fecha_vencimiento,
                subido_por=request.user, **{campo: destino},
            )
            copia.archivo.name = original.archivo.name  # mismo archivo en disco: no se duplica
            copia.save()
            registrar(request.user, "documento_asociado", copia, f"desde documento {original.pk}")
            messages.success(request, "Documento asociado. Es el mismo archivo, no una copia.")
        return HttpResponseRedirect(f"{destino.get_absolute_url()}?tab=documentos")


class DocumentoNuevo(Permiso403Mixin, CreateView):
    model = Documento
    form_class = DocumentoForm
    permission_required = "documentos.add_documento"
    template_name = "documentos/nuevo.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["puede_restringir"] = self.request.user.has_perm("documentos.ver_restringido")
        return kw

    def get_initial(self):
        ini = super().get_initial()
        for k in ("actividad", "proyecto", "persona", "organizacion", "solicitud", "sesion"):
            if self.request.GET.get(k, "").isdigit():
                ini[k] = int(self.request.GET[k])
        return ini

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nuevo documento", volver_url=self.request.META.get("HTTP_REFERER") or "/documentos", breadcrumb=[("Documentos", "/documentos")])
        return ctx

    def form_valid(self, form):
        huella = Documento.calcular_huella(form.cleaned_data["archivo"])
        if not self.request.POST.get("subir_igual"):
            iguales = Documento.objects.filter(huella=huella, activo=True)
            if not self.request.user.has_perm("documentos.ver_restringido"):
                iguales = iguales.filter(restringido=False)
            if iguales.exists():  # DO-E3: el mismo archivo ya está
                return self.render_to_response(self.get_context_data(form=form, iguales=iguales[:5]))
        obj = form.save(commit=False)
        obj.subido_por = self.request.user
        obj.huella = huella
        obj.save()
        registrar(self.request.user, "documento_subido", obj, "restringido" if obj.restringido else "")
        if obj.sesion_id:
            messages.success(self.request, "Evidencia guardada en la sesión.")
            return HttpResponseRedirect(obj.sesion.get_absolute_url())
        for destino in (obj.actividad, obj.proyecto, obj.persona, obj.organizacion, obj.solicitud):
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
        antes = Documento.objects.get(pk=self.object.pk)
        obj = form.save()
        campos = ("actividad_id", "proyecto_id", "persona_id", "organizacion_id", "solicitud_id")
        if any(getattr(antes, c) != getattr(obj, c) for c in campos):  # DO-E4: reasignación con registro
            registrar(self.request.user, "documento_reasignado", obj, f"antes: {antes.actividad or antes.proyecto or antes.persona or antes.organizacion or antes.solicitud}")
        if form.cleaned_data.get("archivo") and antes.archivo.name != obj.archivo.name:
            obj.huella = Documento.calcular_huella(obj.archivo)
            obj.save(update_fields=["huella"])
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
        d = self.object
        existe = d.archivo_existe
        if not existe:
            registrar(self.request.user, "archivo_no_encontrado", d, d.archivo.name)
        return {"url_editar": reverse("documentos:editar", args=[d.pk]), "url_volver": "/documentos", "puede_agregar": self.request.user.has_perm("documentos.change_documento"),
                "origenes": d.origenes.all(), "archivo_existe": existe, "versiones_siguientes": d.reemplazado_por.all()}


class DocumentoAlternar(Permiso403Mixin, View):
    """Archivar o restaurar. Nunca se borra el archivo."""

    permission_required = "documentos.change_documento"

    def post(self, request, pk):
        d = get_object_or_404(Documento, pk=pk)
        if d.restringido and not request.user.has_perm("documentos.ver_restringido"):
            raise PermissionDenied
        motivo = request.POST.get("motivo", "").strip()
        if d.activo and not motivo:  # DO-E9: retirar pide motivo
            messages.error(request, "Indica por qué se archiva el documento.")
            return HttpResponseRedirect(d.get_absolute_url())
        d.activo = not d.activo
        d.save(update_fields=["activo"])
        registrar(request.user, "documento_restaurado" if d.activo else "documento_archivado", d, motivo)
        messages.success(request, "Documento restaurado." if d.activo else "Documento archivado; el archivo se conserva.")
        return HttpResponseRedirect(d.get_absolute_url())


class DocumentoReemplazar(Permiso403Mixin, View):
    """DO-E6: nueva versión del archivo (p. ej. un escaneo mejor). La anterior queda archivada y enlazada."""

    permission_required = "documentos.change_documento"

    def _form(self, data=None, files=None):
        from django import forms as f

        from .models import validar_archivo

        class F(f.Form):
            archivo = f.FileField(validators=[validar_archivo], label="Archivo nuevo")
            motivo = f.CharField(max_length=200, label="Motivo")

        form = F(data, files)
        form.fields["archivo"].widget.attrs["class"] = "form-control"
        form.fields["motivo"].widget.attrs["class"] = "form-control"
        return form

    def _doc(self, request, pk):
        d = get_object_or_404(Documento, pk=pk)
        if d.restringido and not request.user.has_perm("documentos.ver_restringido"):
            raise PermissionDenied
        return d

    def get(self, request, pk):
        d = self._doc(request, pk)
        return render(request, "generico/formulario.html", {"form": self._form(), "titulo": f"Reemplazar archivo de «{d.nombre}»", "volver_url": d.get_absolute_url(), "breadcrumb": [("Documentos", "/documentos")]})

    def post(self, request, pk):
        from django.db import transaction

        d = self._doc(request, pk)
        form = self._form(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "generico/formulario.html", {"form": form, "titulo": f"Reemplazar archivo de «{d.nombre}»", "volver_url": d.get_absolute_url(), "breadcrumb": []}, status=400)
        with transaction.atomic():
            nuevo = Documento(
                nombre=d.nombre, tipo=d.tipo, fecha=d.fecha, descripcion=d.descripcion, actividad=d.actividad, proyecto=d.proyecto, persona=d.persona,
                organizacion=d.organizacion, solicitud=d.solicitud, restringido=d.restringido, folio=d.folio, emisor=d.emisor,
                fecha_emision=d.fecha_emision, fecha_vencimiento=d.fecha_vencimiento, reemplaza=d, subido_por=request.user, archivo=form.cleaned_data["archivo"],
            )
            nuevo.save()
            d.activo = False
            d.save(update_fields=["activo"])
            registrar(request.user, "documento_reemplazado", nuevo, f"versión anterior #{d.pk}: {form.cleaned_data['motivo']}")
        messages.success(request, "Archivo reemplazado. La versión anterior queda archivada y enlazada.")
        return HttpResponseRedirect(nuevo.get_absolute_url())


class DocumentoArchivo(Permiso403Mixin, View):
    """Los archivos nunca se sirven como estáticos: siempre pasan por esta vista, que comprueba permiso."""

    permission_required = "documentos.view_documento"

    def get(self, request, pk):
        d = get_object_or_404(Documento, pk=pk)
        if d.restringido and not request.user.has_perm("documentos.ver_restringido"):
            raise PermissionDenied
        try:
            f = d.archivo.open("rb")
        except (FileNotFoundError, ValueError, OSError):
            registrar(request.user, "archivo_no_encontrado", d, d.archivo.name)  # DO-E13
            raise Http404("El archivo no está disponible en el servidor.")
        tipo = mimetypes.guess_type(d.archivo.name)[0] or "application/octet-stream"
        registrar(request.user, "documento_descargado", d, "restringido" if d.restringido else "")
        r = FileResponse(f, content_type=tipo)
        nombre = f"{d.nombre}.{d.extension}" if d.extension and not d.nombre.lower().endswith(d.extension) else d.nombre
        r["Content-Disposition"] = f'attachment; filename*=UTF-8\'\'{quote(nombre)}'
        r["X-Content-Type-Options"] = "nosniff"
        return r


@method_decorator(xframe_options_sameorigin, name="dispatch")
class DocumentoVer(Permiso403Mixin, View):
    """Muestra el documento dentro del sistema (para transcribir). Mismos permisos que la descarga."""

    permission_required = "documentos.view_documento"

    def get(self, request, pk):
        d = get_object_or_404(Documento, pk=pk)
        if d.restringido and not request.user.has_perm("documentos.ver_restringido"):
            raise PermissionDenied
        if not d.visible_en_navegador:
            raise Http404("Este tipo de archivo no se puede mostrar en el navegador.")
        try:
            f = d.archivo.open("rb")
        except (FileNotFoundError, ValueError):
            raise Http404("El archivo no está disponible en el servidor.")
        r = FileResponse(f, content_type=mimetypes.guess_type(d.archivo.name)[0] or "application/octet-stream")
        r["Content-Disposition"] = "inline"
        r["X-Content-Type-Options"] = "nosniff"
        if d.extension == "txt":
            r["Content-Security-Policy"] = "sandbox"  # texto plano: nunca se interpreta como página
        return r


class Transcribir(Permiso403Mixin, View):
    """Ingesta asistida (IG-05): el documento a un lado y el formulario al otro. El dato nuevo queda con este documento como origen."""

    def has_permission(self):
        u = self.request.user
        return u.has_perm("documentos.view_documento") and (u.has_perm("personas.add_persona") or u.has_perm("organizaciones.add_organizacion"))

    def _documento(self, request, pk):
        d = get_object_or_404(Documento, pk=pk)
        if d.restringido and not request.user.has_perm("documentos.ver_restringido"):
            raise PermissionDenied
        return d

    def _form(self, tipo, data=None):
        from apps.organizaciones.forms import OrganizacionForm
        from apps.personas.forms import PersonaNuevaForm

        return (OrganizacionForm if tipo == "organizacion" else PersonaNuevaForm)(data)

    def _ctx(self, d, tipo, form, candidatos=None):
        return {"documento": d, "tipo": tipo, "form": form, "candidatos": candidatos, "titulo": f"Transcribir: {d.nombre}", "breadcrumb": [("Documentos", "/documentos"), (d.nombre, d.get_absolute_url())]}

    def get(self, request, pk):
        d = self._documento(request, pk)
        tipo = "organizacion" if request.GET.get("registro") == "organizacion" else "persona"
        return render(request, "documentos/transcribir.html", self._ctx(d, tipo, self._form(tipo)))

    def post(self, request, pk):
        from django.db import transaction

        d = self._documento(request, pk)
        tipo = "organizacion" if request.POST.get("registro") == "organizacion" else "persona"
        if not request.user.has_perm("organizaciones.add_organizacion" if tipo == "organizacion" else "personas.add_persona"):
            raise PermissionDenied
        form = self._form(tipo, request.POST)
        if not form.is_valid():
            return render(request, "documentos/transcribir.html", self._ctx(d, tipo, form), status=400)
        if tipo == "persona" and not request.POST.get("confirmar_duplicado"):
            from apps.personas.duplicados import candidatos

            c = form.cleaned_data
            rut = c.get("rut")
            cands = candidatos(c["nombres"], c.get("apellido_paterno", ""), c.get("apellido_materno", ""), rut[0] if rut else None, c.get("correo", ""), c.get("telefono", ""))
            if cands:
                return render(request, "documentos/transcribir.html", self._ctx(d, tipo, form, cands))
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.creado_por = request.user
            if tipo == "persona":
                from apps.nucleo.models import EstadoRegistro, TipoContacto
                from apps.personas.models import Contacto

                obj.estado_registro = EstadoRegistro.objects.filter(codigo="por_verificar").first()
                obj.save()
                c = form.cleaned_data
                if c.get("correo"):
                    Contacto.objects.create(persona=obj, tipo=TipoContacto.objects.get(codigo="correo"), valor=c["correo"], principal=True)
                if c.get("telefono"):
                    Contacto.objects.create(persona=obj, tipo=TipoContacto.objects.get(codigo="telefono_movil"), valor=c["telefono"])
            else:
                obj.save()
            registrar_origen(obj, request.user, fuente="documento", documento=d, detalle="Transcrito desde el documento", verificacion="por_revisar")
        messages.success(request, f"«{obj}» registrado con este documento como origen. Puedes seguir transcribiendo.")
        return HttpResponseRedirect(f"/documentos/{d.pk}/transcribir?registro={tipo}")


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

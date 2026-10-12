import os

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import FormView

from apps.nucleo.auditoria import registrar
from apps.nucleo.vistas_base import FichaBase, Filtro, ListaBase, Permiso403Mixin

from . import lectura, procesar
from .forms import LoteForm
from .models import Lote


class LoteLista(ListaBase):
    model = Lote
    permission_required = "importaciones.importar_listado"
    titulo = "Importaciones"
    url_crear = "/importaciones/nueva"
    permiso_crear = "importaciones.importar_listado"
    etiqueta_crear = "+ Nueva importación"
    columnas = [
        ("Lote", lambda l: f"#{l.pk}"), ("Tipo", "get_tipo_display"), ("Origen", "nombre_archivo"), ("Actividad", "actividad"),
        ("Estado", "get_estado_display"), ("Fecha", lambda l: l.creado_en.astimezone().strftime("%d-%m-%Y %H:%M")), ("Usuario", "usuario"),
    ]
    orden_defecto = ("-creado_en",)
    filtros = [Filtro("tipo", "Tipo", "tipo", lambda: list(Lote.TIPOS)), Filtro("estado", "Estado", "estado", lambda: list(Lote.ESTADOS))]
    texto_vacio = "Aún no se ha importado nada."

    def get_queryset(self):
        return super().get_queryset().select_related("actividad", "usuario")


class LoteNuevo(Permiso403Mixin, FormView):
    form_class = LoteForm
    permission_required = "importaciones.importar_listado"
    template_name = "generico/formulario.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nueva importación", volver_url="/importaciones", breadcrumb=[("Importaciones", "/importaciones")])
        return ctx

    def form_valid(self, form):
        d = form.cleaned_data
        try:
            if d.get("archivo"):
                crudas, ignoradas = lectura.leer(d["archivo"].read(), d["archivo"].name)
                nombre = d["archivo"].name
            else:
                crudas, ignoradas = lectura.leer(texto=d["texto"])
                nombre = "Texto pegado"
        except lectura.ErrorLectura as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
        filas, resumen = procesar.analizar(d["tipo"], crudas)
        if ignoradas:
            resumen["columnas_ignoradas"] = ignoradas
        lote = Lote.objects.create(
            tipo=d["tipo"], nombre_archivo=nombre, fuente=d.get("fuente", ""), actividad=d.get("actividad") if d["tipo"] == "listado_actividad" else None,
            rol=d.get("rol") if d["tipo"] == "listado_actividad" else None, filas=filas, resumen=resumen, usuario=self.request.user,
        )
        if d.get("archivo"):
            d["archivo"].seek(0)
            lote.archivo.save(os.path.basename(d["archivo"].name), d["archivo"], save=True)
        registrar(self.request.user, "importacion_iniciada", lote, nombre)
        return HttpResponseRedirect(f"/importaciones/{lote.pk}/revisar")


def _recolectar(post, lote):
    """Lee de la pantalla de revisión las correcciones y decisiones."""
    campos = procesar.CAMPOS[lote.tipo]
    crudas, decisiones = [], {}
    for f in lote.filas:
        i = f["fila"]
        d = {c: post.get(f"f{i}_{c}", f["datos"].get(c, "")).strip() for c in campos}
        for extra, v in f["datos"].items():
            if extra not in campos and v:
                d[extra] = v
        crudas.append(d)
        if post.get(f"d{i}"):
            decisiones[i] = post[f"d{i}"]
    return crudas, decisiones


class LoteRevisar(Permiso403Mixin, View):
    permission_required = "importaciones.importar_listado"

    def contexto(self, lote):
        return {
            "lote": lote, "titulo": f"Revisar importación #{lote.pk}", "campos": procesar.CAMPOS[lote.tipo], "filas": lote.filas,
            "breadcrumb": [("Importaciones", "/importaciones")], "volver_url": "/importaciones",
            "hay_pendientes": any(f["decision"] == "pendiente" for f in lote.filas),
            "n_pendientes": sum(1 for f in lote.filas if f["decision"] == "pendiente"),
            "a_aplicar": sum(1 for f in lote.filas if f["decision"] not in ("omitir", "pendiente")),
        }

    def _lote(self, pk):
        return get_object_or_404(Lote, pk=pk)

    def get(self, request, pk):
        lote = self._lote(pk)
        if lote.estado != "previa":
            return HttpResponseRedirect(lote.get_absolute_url())
        return render(request, "importaciones/revisar.html", self.contexto(lote))

    def post(self, request, pk):
        lote = self._lote(pk)
        if lote.estado != "previa":
            messages.error(request, "Este lote ya fue procesado.")
            return HttpResponseRedirect(lote.get_absolute_url())
        accion = request.POST.get("accion")
        if accion == "descartar":
            lote.estado = "descartado"
            lote.filas = []  # no se conservan datos personales de una carga descartada
            lote.save()
            registrar(request.user, "importacion_descartada", lote)
            messages.success(request, "Importación descartada. No se guardó ningún dato.")
            return HttpResponseRedirect("/importaciones")
        crudas, decisiones = _recolectar(request.POST, lote)
        filas, resumen = procesar.analizar(lote.tipo, crudas, decisiones)
        ign = lote.resumen.get("columnas_ignoradas")
        if ign:
            resumen["columnas_ignoradas"] = ign
        lote.filas, lote.resumen = filas, resumen
        lote.save()
        if accion == "confirmar":
            try:
                n = procesar.aplicar(lote, request.user)
            except ValueError as e:
                messages.error(request, str(e))
            else:
                messages.success(request, f"Importación confirmada: {n['creados']} creados, {n['vinculados']} vinculados, {n['omitidos']} omitidos.")
                return HttpResponseRedirect(lote.get_absolute_url())
        else:
            messages.info(request, "Se revisaron nuevamente las filas con tus correcciones.")
        return render(request, "importaciones/revisar.html", self.contexto(lote))


class LoteFicha(FichaBase):
    model = Lote
    permission_required = "importaciones.importar_listado"
    breadcrumb = [("Importaciones", "/importaciones")]
    pestanas = [("resumen", "Resumen", "importaciones/resumen.html")]

    def encabezado(self):
        return str(self.object)

    def contexto_ficha(self):
        l = self.object
        return {"url_volver": "/importaciones", "puede_revertir": l.estado == "confirmado" and self.request.user.has_perm("importaciones.revertir_lote"), "aplicado": l.resumen.get("aplicado", {}), "reversion": l.resumen.get("reversion")}


class LoteRevertir(Permiso403Mixin, View):
    permission_required = "importaciones.revertir_lote"

    def post(self, request, pk):
        lote = get_object_or_404(Lote, pk=pk)
        try:
            n = procesar.revertir(lote, request.user)
        except ValueError as e:
            messages.error(request, str(e))
        else:
            messages.success(request, f"Lote revertido: {n['eliminados']} registros eliminados, {n['conservados']} conservados porque tienen otra historia.")
        return HttpResponseRedirect(lote.get_absolute_url())

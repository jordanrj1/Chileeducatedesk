"""Pantallas de finanzas (2.ª fase, oculta): listado, nuevo, ficha, editar, anular y exportar movimientos."""
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView

from apps.nucleo.auditoria import registrar
from apps.nucleo.vistas_base import FichaBase, Filtro, ListaBase, Permiso403Mixin
from apps.nucleo.vistas_crud import Editar, Nuevo
from apps.proyectos.models import Proyecto

from .forms import MovimientoForm
from .models import Movimiento
from .resumen import resumen_proyecto


def _pesos(n):
    return "$" + f"{n:,}".replace(",", ".")


class MovimientoLista(ListaBase):
    model = Movimiento
    permission_required = "finanzas.view_movimiento"
    titulo = "Finanzas"
    descripcion = "Gastos, aportes y donaciones asociados a cada proyecto."
    url_crear = "/finanzas/nuevo"
    permiso_crear = "finanzas.add_movimiento"
    etiqueta_crear = "+ Nuevo movimiento"
    campos_busqueda = ("concepto", "persona__nombres", "persona__apellido_paterno", "organizacion__nombre")
    columnas = [
        ("Fecha", lambda m: m.fecha.strftime("%d-%m-%Y")), ("Tipo", "get_tipo_display"), ("Monto", lambda m: _pesos(m.monto)),
        ("Proyecto", "proyecto"), ("Concepto", "concepto"), ("Persona u organización", lambda m: m.persona or m.organizacion or "—"), ("Estado", lambda m: "Anulado" if m.anulado else ""),
    ]
    orden_defecto = ("-fecha", "-id")
    filtros = [
        Filtro("proyecto", "Proyecto", "proyecto_id", lambda: [(str(p.pk), p.nombre) for p in Proyecto.objects.all()], principal=True),
        Filtro("tipo", "Tipo", "tipo", lambda: list(Movimiento.TIPOS), principal=True),
        Filtro("desde", "Desde", "fecha__gte", entrada="date", grupo="Fecha"),
        Filtro("hasta", "Hasta", "fecha__lte", entrada="date", grupo="Fecha"),
    ]
    url_exportar = "/finanzas/exportar"
    permiso_exportar = "finanzas.exportar_movimiento"

    def get_queryset(self):
        return super().get_queryset().select_related("proyecto", "persona", "organizacion")

    def contexto_extra(self):
        p = self.request.GET.get("proyecto", "")
        return {"resumen": resumen_proyecto(get_object_or_404(Proyecto, pk=p)) if p.isdigit() and Proyecto.objects.filter(pk=p).exists() else None}


class MovimientoExportar(MovimientoLista):
    exportar = True
    permission_required = "finanzas.exportar_movimiento"


class MovimientoNuevo(Nuevo):
    model = Movimiento
    form_class = MovimientoForm
    permission_required = "finanzas.add_movimiento"
    titulo = "Nuevo movimiento"
    lista_url = "/finanzas"
    prefill = ("proyecto",)
    breadcrumb_ = [("Finanzas", "/finanzas")]

    def hook(self, form, obj):
        registrar(self.request.user, "movimiento_registrado", obj, f"{obj.tipo} {obj.monto}")


class MovimientoEditar(Editar):
    model = Movimiento
    form_class = MovimientoForm
    permission_required = "finanzas.change_movimiento"
    titulo = "Editar movimiento"

    def get_object(self, qs=None):
        obj = super().get_object(qs)
        return obj

    def form_valid(self, form):
        if self.object.anulado:
            messages.error(self.request, "El movimiento está anulado.")
            return self.form_invalid(form)
        return super().form_valid(form)


class MovimientoFicha(FichaBase):
    model = Movimiento
    permission_required = "finanzas.view_movimiento"
    breadcrumb = [("Finanzas", "/finanzas")]
    permiso_editar = "finanzas.change_movimiento"
    pestanas = [("datos", "Datos", "finanzas/pestanas/datos.html"), ("historial", "Historial", "generico/_historial.html", "finanzas.view_historicalmovimiento")]

    def contexto_ficha(self):
        m = self.object
        return {
            "url_editar": reverse("finanzas:editar", args=[m.pk]) if not m.anulado else None, "url_volver": "/finanzas",
            "puede_agregar": self.request.user.has_perm("finanzas.change_movimiento") and not m.anulado,
        }


class MovimientoAnular(Permiso403Mixin, View):
    permission_required = "finanzas.change_movimiento"

    def post(self, request, pk):
        m = get_object_or_404(Movimiento, pk=pk)
        motivo = request.POST.get("motivo", "").strip()
        if m.anulado:
            messages.error(request, "Ya está anulado.")
        elif not motivo:
            messages.error(request, "Indica el motivo de la anulación.")
        else:
            m.anulado, m.motivo_anulacion = True, motivo[:250]
            m.save()
            registrar(request.user, "movimiento_anulado", m, motivo)
            messages.success(request, "Movimiento anulado; queda registrado en el historial.")
        return HttpResponseRedirect(m.get_absolute_url())

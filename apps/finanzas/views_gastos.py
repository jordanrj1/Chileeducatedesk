"""F28 B · Pantallas del gasto de una actividad o tarea (specs/f28/spec.md, punto 5): registrar (con su comprobante),
editar mientras esté «registrado», revisar, anular con motivo y exportar a Excel. Visibles siempre: sus direcciones no
empiezan con /finanzas (que sigue oculto con la segunda fase). Todo es de formularios normales, sin JavaScript.

Estados: registrado -> revisado -> anulado. Un gasto revisado no se edita: el servidor lo rechaza; se anula con motivo y se
registra otro. Los permisos son los de finanzas (ver, agregar, cambiar movimiento); el Excel pide además exportar la actividad
o el proyecto."""
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from django.views import View

from apps.actividades.models import Actividad
from apps.nucleo.auditoria import registrar
from apps.nucleo.exportacion import respuesta_xlsx
from apps.nucleo.vistas_base import Permiso403Mixin
from apps.nucleo.vistas_crud import Editar, Nuevo
from apps.proyectos.models import Proyecto

from .forms import GastoForm
from .models import Movimiento


def url_gastos(actividad):
    return f"{actividad.get_absolute_url()}?tab=gastos"


def url_nuevo_gasto(actividad, jornada=None):
    """Dirección del registro de un gasto de la actividad, con la jornada ya elegida (si se indica)."""
    from django.urls import reverse

    base = reverse("finanzas:gasto_nuevo", args=[actividad.pk])
    return f"{base}?jornada={jornada.pk}" if jornada is not None and jornada.pk else base


def _actividad(pk):
    return get_object_or_404(Actividad.objects.select_related("estado", "proyecto"), pk=pk)


class _ConActividad:
    def dispatch(self, request, *a, **kw):
        self.actividad = _actividad(kw["pk"])
        return super().dispatch(request, *a, **kw)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw.update(actividad=self.actividad, usuario=self.request.user)
        return kw


class GastoNuevo(_ConActividad, Nuevo):
    model = Movimiento
    form_class = GastoForm
    permission_required = "finanzas.add_movimiento"
    titulo = "Registrar gasto"

    def get_initial(self):
        ini = super().get_initial()
        j = self.request.GET.get("jornada", "")
        if j.isdigit() and self.actividad.sesiones.filter(pk=j).exists():
            ini["sesion"] = int(j)
            fecha = self.actividad.sesiones.get(pk=j).fecha
            if fecha:
                ini["fecha"] = fecha
        return ini

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(volver_url=url_gastos(self.actividad), breadcrumb=[("Actividades", "/actividades"), (self.actividad.nombre, self.actividad.get_absolute_url())],
                   bajada="Un gasto se guarda aunque falte el comprobante: queda marcado «Sin comprobante». Los campos marcados con * son obligatorios.")
        return ctx

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["instance"] = Movimiento(actividad=self.actividad, tipo="gasto", proyecto_id=self.actividad.proyecto_id)
        return kw

    def form_valid(self, form):
        gasto = form.save()
        registrar(self.request.user, "gasto_registrado", gasto, f"${gasto.monto} · {self.actividad.nombre}" + ("" if gasto.documento_id else " · sin comprobante"))
        messages.success(self.request, "Gasto registrado" + ("." if gasto.documento_id else ": queda marcado «Sin comprobante»."))
        return HttpResponseRedirect(url_gastos(self.actividad))


class GastoEditar(_ConActividad, Editar):
    model = Movimiento
    form_class = GastoForm
    permission_required = "finanzas.change_movimiento"
    titulo = "Editar gasto"

    def get_queryset(self):
        return Movimiento.objects.filter(actividad_id=self.kwargs["pk"], tipo="gasto")

    def get_object(self, queryset=None):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["gid"])

    def rechazar_si_no_editable(self, request):
        if not self.get_object().editable:  # el servidor lo rechaza aunque alguien arme el envío a mano
            messages.error(request, "Un gasto revisado o anulado no se edita: anúlalo con un motivo y registra otro.")
            return HttpResponseRedirect(url_gastos(self.actividad))

    def post(self, request, *a, **kw):
        return self.rechazar_si_no_editable(request) or super().post(request, *a, **kw)

    def get(self, request, *a, **kw):
        return self.rechazar_si_no_editable(request) or super().get(request, *a, **kw)

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(volver_url=url_gastos(self.actividad), breadcrumb=[("Actividades", "/actividades"), (self.actividad.nombre, self.actividad.get_absolute_url())])
        return ctx

    def form_valid(self, form):
        if self.version_en_conflicto():
            form.add_error(None, self.MENSAJE_VERSION)
            return self.form_invalid(form)
        gasto = form.save()
        registrar(self.request.user, "gasto_editado", gasto, f"${gasto.monto} · {self.actividad.nombre}")
        messages.success(self.request, "Gasto actualizado; el cambio queda en el historial.")
        return HttpResponseRedirect(url_gastos(self.actividad))


class _AccionGasto(Permiso403Mixin, View):
    permission_required = "finanzas.change_movimiento"

    def dispatch(self, request, *a, **kw):
        self.actividad = _actividad(kw["pk"])
        return super().dispatch(request, *a, **kw)

    def gasto(self, gid):
        return get_object_or_404(Movimiento, pk=gid, actividad=self.actividad, tipo="gasto")

    def volver(self):
        return HttpResponseRedirect(url_gastos(self.actividad))


class GastoRevisar(_AccionGasto):
    def post(self, request, pk, gid):
        g = self.gasto(gid)
        if g.estado != Movimiento.REGISTRADO or g.anulado:
            messages.error(request, "Solo se revisa un gasto que está «registrado».")
            return self.volver()
        g.estado, g.revisado_por, g.revisado_en = Movimiento.REVISADO, request.user, timezone.now()
        g.save()
        registrar(request.user, "gasto_revisado", g, f"${g.monto} · {self.actividad.nombre}")
        messages.success(request, "Gasto revisado. Desde ahora no se edita: si hay un error, se anula con un motivo y se registra otro.")
        return self.volver()


class GastoAnular(_AccionGasto):
    def post(self, request, pk, gid):
        g = self.gasto(gid)
        motivo = request.POST.get("motivo", "").strip()
        if g.anulado:
            messages.error(request, "Ese gasto ya está anulado.")
        elif not motivo:
            messages.error(request, "Indica el motivo de la anulación.")
        else:
            g.anulado, g.estado, g.motivo_anulacion = True, Movimiento.ANULADO, motivo[:250]
            g.save()
            registrar(request.user, "gasto_anulado", g, motivo)
            messages.success(request, "Gasto anulado. Queda en el historial y no suma en los totales; registra el correcto si hace falta.")
        return self.volver()


def _filas(gastos):
    for g in gastos:
        yield [g.fecha.strftime("%d-%m-%Y"), (f"Jornada {g.sesion.numero}" if g.sesion_id else "Toda la tarea"), g.categoria or "", g.concepto,
               g.proveedor or (g.organizacion.nombre if g.organizacion_id else ""), g.pagado_por.nombre_completo if g.pagado_por_id else "",
               g.monto, g.get_estado_display(), "Sí" if g.documento_id else "No"]


ENCABEZADOS = ["Fecha", "Jornada", "Categoría", "Concepto", "Proveedor", "Pagado por", "Monto (CLP)", "Estado", "Con comprobante"]


class GastosExportar(Permiso403Mixin, View):
    """Excel de los gastos de una tarea o actividad. Pide ver finanzas y poder exportar la actividad. Sin RUT ni datos de
    contacto: solo el nombre de quien pagó."""

    permission_required = ("finanzas.view_movimiento", "actividades.exportar_actividad")

    def get(self, request, pk):
        a = _actividad(pk)
        gastos = list(Movimiento.objects.filter(actividad=a, tipo="gasto").select_related("categoria", "sesion", "pagado_por", "organizacion").order_by("fecha", "id"))
        filas = list(_filas(gastos))
        filas.append(["Total (sin anulados)", "", "", "", "", "", sum(g.monto for g in gastos if not g.anulado), "", ""])
        return respuesta_xlsx(request.user, f"Gastos {slugify(a.nombre)[:40]}", ENCABEZADOS, filas)


class GastosProyectoExportar(Permiso403Mixin, View):
    """Excel de los gastos de un proyecto (todas sus tareas). Pide ver finanzas y poder exportar proyectos."""

    permission_required = ("finanzas.view_movimiento", "proyectos.exportar_proyecto")

    def get(self, request, pk):
        p = get_object_or_404(Proyecto, pk=pk)
        gastos = list(Movimiento.objects.filter(proyecto=p, tipo="gasto").select_related("categoria", "sesion", "pagado_por", "organizacion", "actividad").order_by("fecha", "id"))
        filas = [[g.actividad.nombre if g.actividad_id else "Del proyecto", *fila] for g, fila in zip(gastos, _filas(gastos))]
        filas.append(["Total (sin anulados)", "", "", "", "", "", "", sum(g.monto for g in gastos if not g.anulado), "", ""])
        return respuesta_xlsx(request.user, f"Gastos {slugify(p.nombre)[:40]}", ["Tarea", *ENCABEZADOS], filas)

"""F26 P3a: «Finalizar proyecto» y su informe en Excel.

- La pantalla de confirmación avisa cuántas tareas siguen abiertas (sin finalizar ni cancelar), con sus enlaces, pide la
  conclusión y **sugiere** el estado del proyecto según sus tareas. No lo impone: quien finaliza elige el estado [V#7].
- El informe (hojas Tareas, Asistencia, Alcance y Aliados, más el aviso de confidencialidad) exige
  `proyectos.exportar_proyecto`. Igual que el resumen territorial (F23): sin `personas.exportar_persona` no lleva RUT y los
  menores de edad no se nombran (se cuentan al final). Nunca lleva contactos ni datos sensibles.

Número fijo de consultas, sin importar cuántas tareas o participantes tenga el proyecto.
"""
from apps.nucleo.utilidades import plural
from io import BytesIO

from django import forms
from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.text import slugify
from django.views import View
from openpyxl import Workbook

from apps.actividades.alcance import alcance
from apps.nucleo.auditoria import registrar
from apps.nucleo.exportacion import agregar_aviso
from apps.nucleo.vistas_base import Permiso403Mixin
from apps.territorio.exportar import _agregar_hoja, _ajustar_anchos, _hoja_alcance

from .models import Proyecto

CERRADAS = ("realizada", "cancelada")  # una tarea está abierta si no se ha finalizado ni cancelado
PERMISO_RUT = "personas.exportar_persona"
NOTA_MENORES = "Menores de edad que asistieron o participaron"


def tareas_de(proyecto):
    """Tareas con su fecha vigente (`agenda_v`), participantes y asistentes (sin registros erróneos). Dos consultas."""
    from apps.actividades.models import AgendaActividad

    activas = ~Q(participaciones__estado__codigo="registro_erroneo")
    return list(
        proyecto.actividades.select_related("estado")
        .annotate(n_participantes=Count("participaciones", filter=activas, distinct=True),
                  n_asistieron=Count("participaciones", filter=activas & Q(participaciones__asistencia=True), distinct=True))
        .prefetch_related(Prefetch("agendas", queryset=AgendaActividad.objects.filter(vigente=True).select_related("lugar"), to_attr="agenda_v"))
        .order_by("creado_en", "pk")
    )


def estado_sugerido(tareas):
    """(código, motivo) del estado que se sugiere para el proyecto según sus tareas. Es solo una sugerencia [V#7]."""
    abiertas = [t for t in tareas if t.estado.codigo not in CERRADAS]
    if abiertas:
        return "suspendido", ("Queda " if len(abiertas) == 1 else "Quedan ") + f"{plural(len(abiertas), 'tarea abierta', 'tareas abiertas')}: si el proyecto termina igual, elige «Finalizado»."
    if tareas and all(t.estado.codigo == "cancelada" for t in tareas):
        return "cancelado", "Todas sus tareas se cancelaron."
    if tareas:
        return "finalizado", "Todas sus tareas están realizadas o canceladas."
    return "finalizado", "El proyecto no tiene tareas."


class FinalizarForm(forms.Form):
    estado = forms.ChoiceField(label="Estado del proyecto", choices=Proyecto.ESTADOS,
                               help_text="Se sugiere uno según sus tareas; puedes elegir otro.")
    conclusion = forms.CharField(label="Conclusión", widget=forms.Textarea(attrs={"rows": 5}), required=True,
                                 help_text="Qué se logró, qué no y qué queda pendiente.")

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for nombre, campo in self.fields.items():
            campo.widget.attrs.setdefault("class", "form-select" if nombre == "estado" else "form-control")


class FinalizarProyecto(Permiso403Mixin, View):
    """GET: confirmación (tareas abiertas, conclusión y estado sugerido). POST: guarda el estado elegido y la conclusión."""

    permission_required = "proyectos.change_proyecto"
    template_name = "proyectos/finalizar.html"

    def _render(self, request, proyecto, tareas, form, sugerido):
        abiertas = [t for t in tareas if t.estado.codigo not in CERRADAS]
        return render(request, self.template_name, {
            "obj": proyecto, "titulo": f"Finalizar «{proyecto}»", "form": form, "abiertas": abiertas, "total_tareas": len(tareas),
            "sugerido": sugerido, "sugerido_nombre": dict(Proyecto.ESTADOS)[sugerido[0]],
            "puede_informe": request.user.has_perm("proyectos.exportar_proyecto"),
            "breadcrumb": [("Proyectos", "/proyectos"), (str(proyecto), proyecto.get_absolute_url())],
        })

    def get(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk)
        tareas = tareas_de(proyecto)
        sugerido = estado_sugerido(tareas)
        form = FinalizarForm(initial={"estado": sugerido[0], "conclusion": proyecto.conclusion})
        return self._render(request, proyecto, tareas, form, sugerido)

    def post(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk)
        form = FinalizarForm(request.POST)
        if not form.is_valid():
            tareas = tareas_de(proyecto)
            return self._render(request, proyecto, tareas, form, estado_sugerido(tareas))
        proyecto.estado = form.cleaned_data["estado"]
        proyecto.conclusion = form.cleaned_data["conclusion"]
        proyecto.save(update_fields=["estado", "conclusion"])
        messages.success(request, f"Proyecto guardado como «{proyecto.get_estado_display()}», con su conclusión.")
        return HttpResponseRedirect(proyecto.get_absolute_url())


def _hoja_tareas(libro, tareas):
    filas = [(t.nombre, t.agenda_v[0].fecha if t.agenda_v else None, t.estado.nombre, t.n_participantes, t.n_asistieron) for t in tareas]
    _agregar_hoja(libro, "Tareas", ["Tarea", "Fecha", "Estado", "Participantes", "Asistentes"], filas)


def _hoja_asistencia(libro, tareas, con_rut):
    from apps.actividades.models import Participacion

    partes = (Participacion.objects.filter(actividad__in=[t.pk for t in tareas]).exclude(estado__codigo="registro_erroneo")
              .select_related("persona", "actividad", "rol").order_by("actividad__creado_en", "actividad_id", "persona__apellido_paterno", "persona__nombres", "pk"))
    filas, menores = [], 0
    for p in partes:
        if p.persona.es_menor and not con_rut:  # sin exportar_persona, los menores no se nombran: solo se cuentan (V#2)
            menores += 1
            continue
        asistio = {True: "Sí", False: "No"}.get(p.asistencia, "Sin registro")
        fila = [p.persona.nombre_completo, p.actividad.nombre, str(p.rol), asistio]
        if con_rut:
            fila.append(p.persona.rut or "")
        filas.append(fila)
    if menores:
        filas.append([f"{NOTA_MENORES}: {menores} (no se listan por protección de datos; pendiente V#2)"])
    _agregar_hoja(libro, "Asistencia", ["Persona", "Tarea", "Rol", "Asistió"] + (["RUT"] if con_rut else []), filas)


def _hoja_aliados(libro, proyecto, tareas):
    from apps.actividades.models import ActividadOrganizacion

    filas = [(o.organizacion.nombre, str(o.tipo_intervencion or ""), "Proyecto", o.vigente)
             for o in proyecto.organizaciones.select_related("organizacion", "tipo_intervencion").order_by("organizacion__nombre", "pk")]
    filas += [(o.organizacion.nombre, str(o.tipo_intervencion or ""), f"Tarea «{o.actividad.nombre}»", o.vigente)
              for o in ActividadOrganizacion.objects.filter(actividad__in=[t.pk for t in tareas])
              .select_related("organizacion", "tipo_intervencion", "actividad").order_by("organizacion__nombre", "pk")]
    _agregar_hoja(libro, "Aliados", ["Organización", "Intervención", "Dónde", "Vigente"], filas)


def libro_proyecto(usuario, proyecto):
    """Libro de Excel del informe del proyecto: Tareas, Asistencia, Alcance y Aliados, y el aviso."""
    tareas = tareas_de(proyecto)
    libro = Workbook()
    libro.remove(libro.active)
    _hoja_tareas(libro, tareas)
    _hoja_asistencia(libro, tareas, usuario.has_perm(PERMISO_RUT))
    _hoja_alcance(libro, alcance(tareas))
    _hoja_aliados(libro, proyecto, tareas)
    for hoja in libro:
        _ajustar_anchos(hoja)
    agregar_aviso(libro, usuario)
    return libro


class InformeProyecto(Permiso403Mixin, View):
    """«Descargar informe (Excel)» del proyecto. Queda en la auditoría."""

    permission_required = ("proyectos.exportar_proyecto", "proyectos.view_proyecto")

    def get(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk)
        libro = libro_proyecto(request.user, proyecto)
        buffer = BytesIO()
        libro.save(buffer)
        registrar(request.user, "exportacion", proyecto, "Informe del proyecto" + ("; con RUT" if request.user.has_perm(PERMISO_RUT) else ""))
        r = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        r["Content-Disposition"] = f'attachment; filename="proyecto_{slugify(str(proyecto))}_{timezone.localdate():%Y-%m-%d}.xlsx"'
        return r

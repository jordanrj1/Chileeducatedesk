from datetime import date, timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html_join
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.nucleo.auditoria import registrar
from apps.nucleo.models import EstadoActividad, EstadoParticipacion, Modalidad, RolParticipacion, TipoActividad
from apps.nucleo.vistas_base import (
    EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, cambios_historial, opciones_modelo,
)
from apps.organizaciones.models import Organizacion
from apps.personas.duplicados import candidatos
from apps.personas.models import Contacto, Persona
from apps.proyectos.models import Proyecto
from apps.territorio.models import Comuna

from . import servicios
from .forms import (
    ActividadForm, EstadoForm, ParticipacionEditarForm, ParticipanteNuevoForm, PersonaRapidaForm, ProgramarForm, ResultadoForm,
)
from .models import Actividad, AgendaActividad, Participacion
from .reglas import TRANSICIONES, ReglaNegocio, revisar


def _avisar(request, error):
    for m in error.mensajes:
        messages.error(request, m)


def _agenda_vigente_qs():
    return AgendaActividad.objects.filter(vigente=True).select_related("lugar", "estado")


def _filtro_comuna(qs, v):
    return qs.filter(
        Q(agendas__vigente=True, agendas__lugar__direccion__comuna_id=v) | Q(territorios__vigente=True, territorios__comuna_id=v)
    ).distinct()


def _filtro_fecha(operador):
    def aplicar(qs, v):
        from datetime import date as _d

        f = _d.fromisoformat(v)
        return qs.filter(Exists(AgendaActividad.objects.filter(actividad=OuterRef("pk"), vigente=True, **{f"fecha__{operador}": f})))

    return aplicar


class ActividadLista(ListaBase):
    model = Actividad
    permission_required = "actividades.view_actividad"
    titulo = "Actividades"
    url_crear = "/actividades/nueva"
    permiso_crear = "actividades.add_actividad"
    etiqueta_crear = "+ Nueva actividad"
    campos_busqueda = ("nombre", "proyecto__nombre", "objetivo", "responsable__nombres", "responsable__apellido_paterno")
    columnas = [
        ("Actividad", "nombre"),
        ("Proyecto", "proyecto"),
        ("Tipo", "tipo"),
        ("Estado", "estado"),
        ("Fecha", lambda a: (a.agenda_v[0].fecha.strftime("%d-%m-%Y") + (a.agenda_v[0].hora_inicio.strftime(" %H:%M") if a.agenda_v[0].hora_inicio else "")) if a.agenda_v else "Sin programar"),
        ("Lugar", lambda a: (a.agenda_v[0].lugar or "") if a.agenda_v else ""),
        ("Responsable", "responsable"),
    ]
    ordenes = {"nombre": "nombre", "estado": "estado__orden", "creada": "creado_en"}
    orden_defecto = ("-creado_en",)
    filtros = [
        Filtro("estado", "Estado", "estado_id", opciones_modelo(EstadoActividad)),
        Filtro("tipo", "Tipo", "tipo_id", opciones_modelo(TipoActividad)),
        Filtro("proyecto", "Proyecto", "proyecto_id", lambda: [(str(p.pk), p.nombre) for p in Proyecto.objects.all()]),
        Filtro("comuna", "Zona (comuna)", "", opciones_modelo(Comuna), aplicar=_filtro_comuna),
        Filtro("organizacion", "Organización", "organizaciones__organizacion_id", lambda: [(str(o.pk), o.nombre) for o in Organizacion.objects.filter(activo=True)[:300]], aplicar=lambda qs, v: qs.filter(organizaciones__organizacion_id=v).distinct()),
        Filtro("responsable", "Responsable", "responsable_id", lambda: [(str(p.pk), p.nombre_completo) for p in Persona.objects.filter(actividades_a_cargo__isnull=False).distinct()]),
        Filtro("institucion", "Institución", "", lambda: [(str(o.pk), o.nombre) for o in Organizacion.objects.filter(tipo__codigo="institucion_educativa", activo=True)],
               aplicar=lambda qs, v: qs.filter(organizaciones__organizacion_id=v).distinct()),
        Filtro("desde", "Desde", "", entrada="date", aplicar=_filtro_fecha("gte")),
        Filtro("hasta", "Hasta", "", entrada="date", aplicar=_filtro_fecha("lte")),
        Filtro("incompleta", "Incompletas", "", lambda: [("1", "Solo incompletas")], aplicar=lambda qs, v: qs.filter(pk__in=Actividad.objects.incompletas().values("pk")) if v == "1" else qs),
    ]
    url_exportar = "/actividades/exportar"
    permiso_exportar = "actividades.exportar_actividad"

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related("proyecto", "tipo", "estado", "responsable")
            .prefetch_related(Prefetch("agendas", queryset=_agenda_vigente_qs(), to_attr="agenda_v"))
            .distinct()
        )


class ActividadExportar(ActividadLista):
    exportar = True
    permission_required = "actividades.exportar_actividad"


class ActividadOpciones(Permiso403Mixin, View):
    permission_required = "actividades.view_actividad"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        qs = Actividad.objects.filter(actividad_padre__isnull=True)
        if q:
            qs = qs.filter(nombre__icontains=q)
        opciones = [("", "---------")] + [(a.pk, a.nombre) for a in qs[:25]]
        from django.http import HttpResponse

        return HttpResponse(format_html_join("", '<option value="{}">{}</option>', opciones))


class ActividadNueva(Permiso403Mixin, CreateView):
    model = Actividad
    form_class = ActividadForm
    permission_required = "actividades.add_actividad"
    template_name = "generico/formulario.html"

    def get_initial(self):
        ini = super().get_initial()
        if self.request.GET.get("proyecto", "").isdigit():
            ini["proyecto"] = self.request.GET["proyecto"]
        if self.request.GET.get("padre", "").isdigit():
            ini["actividad_padre"] = int(self.request.GET["padre"])
        return ini

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nueva actividad", volver_url=self.request.META.get("HTTP_REFERER") or "/actividades", breadcrumb=[("Actividades", "/actividades")])
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.creado_por = self.request.user
        obj.estado = EstadoActividad.objects.get(codigo="pendiente")
        obj.save()
        from apps.documentos.origen import registrar_origen

        registrar_origen(obj, self.request.user)
        messages.success(self.request, "Actividad creada. Completa el resto de la información cuando puedas.")
        return HttpResponseRedirect(obj.get_absolute_url())


class ActividadEditar(EditarBase):
    model = Actividad
    form_class = ActividadForm
    permission_required = "actividades.change_actividad"
    titulo = "Editar actividad"
    breadcrumb = [("Actividades", "/actividades")]

    def form_valid(self, form):
        if self.object.estado.codigo == "realizada":
            messages.error(self.request, "La actividad ya fue finalizada. Reábrela (con permiso) para corregirla.")
            return self.form_invalid(form)
        return super().form_valid(form)


class ActividadFicha(FichaBase):
    model = Actividad
    permission_required = "actividades.view_actividad"
    template_name = "actividades/ficha.html"
    pestanas_segunda_fase = ("beneficiarios", "sesiones")
    breadcrumb = [("Actividades", "/actividades")]
    permiso_editar = "actividades.change_actividad"
    pestanas = [
        ("info", "Información", "actividades/pestanas/info.html"),
        ("participantes", "Participantes", "actividades/pestanas/participantes.html"),
        ("beneficiarios", "Beneficiarios", "actividades/pestanas/participantes.html"),
        ("organizaciones", "Organizaciones", "generico/_hijos.html"),
        ("sesiones", "Sesiones", "generico/_hijos.html"),
        ("agenda", "Agenda", "actividades/pestanas/agenda.html"),
        ("coordinacion", "Coordinación", "actividades/pestanas/coordinacion.html", "coordinacion.view_interaccion"),
        ("asistencia", "Asistencia", "actividades/pestanas/asistencia.html"),
        ("documentos", "Documentos", "actividades/pestanas/documentos.html", "documentos.view_documento"),
        ("resultados", "Resultados", "actividades/pestanas/resultados.html"),
        ("origen", "Origen", "documentos/pestanas/origen.html", "documentos.view_origendato"),
        ("historial", "Historial", "actividades/pestanas/historial.html", "actividades.view_historicalactividad"),
    ]

    def get_queryset(self):
        return super().get_queryset().select_related("proyecto", "tipo", "estado", "modalidad", "responsable", "actividad_padre")

    def acciones_extra(self):
        if self.request.user.has_perm("coordinacion.add_interaccion"):
            return [("Registrar interacción", f"/interacciones/nueva?actividad={self.object.pk}")]
        return []

    def contexto_ficha(self):
        a = self.object
        u = self.request.user
        codigo = a.estado.codigo
        siguientes = [c for c in TRANSICIONES.get(codigo, set()) if c not in ("confirmada", "realizada")]
        editable = codigo != "realizada"
        return {
            "url_editar": reverse("actividades:editar", args=[a.pk]) if editable else None,
            "url_volver": a.proyecto.get_absolute_url() if a.proyecto_id else "/actividades",
            "puede_agregar": u.has_perm("actividades.change_actividad") and editable,
            "puede_programar": u.has_perm("actividades.reprogramar_actividad") and codigo not in ("cancelada", "realizada", "suspendida"),
            "puede_confirmar": u.has_perm("actividades.change_actividad") and "confirmada" in TRANSICIONES.get(codigo, set()),
            "estados_siguientes": [(c, EstadoActividad.objects.get(codigo=c).nombre) for c in siguientes] if u.has_perm("actividades.change_actividad") else [],
            "puede_finalizar": u.has_perm("actividades.cerrar_actividad") and "realizada" in TRANSICIONES.get(codigo, set()),
            "puede_reabrir": u.has_perm("actividades.reabrir_actividad") and codigo == "realizada",
            "agenda": a.agenda_vigente,
            "faltantes": a.faltantes(),
        }

    def _participantes(self, beneficiarios):
        from apps.nucleo.fases import segunda_fase_activa

        qs = self.object.participaciones.select_related("persona", "rol", "estado")
        if not segunda_fase_activa():
            return list(qs) if not beneficiarios else []  # sin pestaña aparte: todos van en Participantes
        return [p for p in qs if p.es_beneficiario == beneficiarios]

    def ctx_participantes(self):
        return {"participaciones": self._participantes(False), "grupo": "participantes", "titulo_pestana": "Participantes", "capacidad_alerta": self._capacidad()}

    def ctx_beneficiarios(self):
        return {"participaciones": self._participantes(True), "grupo": "beneficiarios", "titulo_pestana": "Beneficiarios", "capacidad_alerta": None}

    def _capacidad(self):
        ag = self.object.agenda_vigente
        if ag and ag.lugar and ag.lugar.capacidad is not None:
            n = sum(1 for p in self.object.participaciones.select_related("estado") if p.activa)
            return {"n": n, "capacidad": ag.lugar.capacidad, "excede": n > ag.lugar.capacidad}
        return None

    def ctx_info(self):
        return {
            "territorios": [
                {"texto": f"{t.nivel.capitalize()}: {t}", "vigente": t.vigente, "url_editar": reverse("actividades:territorios_editar", args=[self.object.pk, t.pk]), "url_alternar": reverse("actividades:territorios_alternar", args=[self.object.pk, t.pk]), "detalle": ""}
                for t in self.object.territorios.select_related("region", "provincia", "comuna", "sector")
            ],
            "hijas": self.object.hijas.select_related("estado"),
        }

    def ctx_organizaciones(self):
        pk = self.object.pk
        hijos = [{
            "texto": f"{o.organizacion}" + (f" · {o.tipo_intervencion}" if o.tipo_intervencion else ""),
            "detalle": " · ".join(x for x in [f"Contacto: {o.contacto}" if o.contacto else "", o.observaciones] if x), "vigente": o.vigente,
            "url_editar": reverse("actividades:organizaciones_editar", args=[pk, o.pk]), "url_alternar": reverse("actividades:organizaciones_alternar", args=[pk, o.pk]),
        } for o in self.object.organizaciones.select_related("organizacion", "tipo_intervencion", "contacto")]
        return {"titulo_pestana": "Organizaciones", "etiqueta_nuevo": "Organización", "url_nuevo": reverse("actividades:organizaciones_nuevo", args=[pk]), "hijos": hijos, "vacio": "Sin organizaciones relacionadas."}

    def ctx_sesiones(self):
        pk = self.object.pk
        hijos = [{
            "texto": str(s), "detalle": " · ".join(x for x in [s.fecha.strftime("%d-%m-%Y") if s.fecha else "", f"{s.hora_inicio:%H:%M}" if s.hora_inicio else "", str(s.lugar) if s.lugar else "", s.observaciones] if x),
            "vigente": s.vigente, "url_editar": reverse("actividades:sesiones_editar", args=[pk, s.pk]), "url_alternar": reverse("actividades:sesiones_alternar", args=[pk, s.pk]),
        } for s in self.object.sesiones.all()]
        return {"titulo_pestana": "Sesiones", "etiqueta_nuevo": "Sesión", "url_nuevo": reverse("actividades:sesiones_nuevo", args=[pk]), "hijos": hijos, "vacio": "Esta actividad no tiene sesiones."}

    def ctx_agenda(self):
        return {"versiones": self.object.agendas.select_related("lugar", "estado", "creado_por")}

    def ctx_coordinacion(self):
        a = self.object
        return {
            "interacciones": a.interacciones.select_related("canal", "persona", "organizacion").order_by("-fecha"),
            "reuniones": a.reuniones.all(), "tareas": a.tareas.all(),
            "invitaciones": a.invitaciones.select_related("persona"), "colaboraciones": a.colaboraciones.select_related("organizacion"),
        }

    def ctx_asistencia(self):
        return {"participaciones": [p for p in self.object.participaciones.select_related("persona", "rol", "estado") if p.activa or p.asistencia is not None]}

    def ctx_documentos(self):
        u = self.request.user
        docs = self.object.documentos.select_related("tipo")
        if not u.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        return {"documentos": docs}

    def ctx_resultados(self):
        return {"form_resultado": ResultadoForm(instance=self.object), "finalizada": self.object.estado.codigo == "realizada"}

    def ctx_origen(self):
        from apps.documentos.origen import contexto_origen

        return contexto_origen(self.object, self.request.user)

    def ctx_historial(self):
        from apps.actividades.models import Participacion as P

        hist = P.history.filter(actividad_id=self.object.pk).select_related("history_user", "persona").order_by("-history_date")[:40]
        return {"cambios": cambios_historial(self.object), "cambios_participacion": hist, "agendas": self.object.agendas.select_related("lugar", "creado_por")}


# --- Acciones ---------------------------------------------------------------------
class _AccionActividad(Permiso403Mixin, View):
    def actividad(self, pk):
        return get_object_or_404(Actividad.objects.select_related("estado", "modalidad", "responsable"), pk=pk)

    def volver(self, a, tab="info"):
        return HttpResponseRedirect(f"{a.get_absolute_url()}?tab={tab}")


class ProgramarVista(_AccionActividad):
    permission_required = "actividades.reprogramar_actividad"

    def _contexto(self, a, form):
        vigente = a.agenda_vigente
        from apps.nucleo.models import TipoLugar

        return {
            "form": form, "titulo": ("Reprogramar: " if vigente else "Programar: ") + a.nombre, "volver_url": f"{a.get_absolute_url()}?tab=agenda",
            "breadcrumb": [("Actividades", "/actividades"), (a.nombre, a.get_absolute_url())], "vigente": vigente,
            "tipos_lugar": TipoLugar.objects.filter(activo=True), "comunas": Comuna.objects.all(),
        }

    def get(self, request, pk):
        a = self.actividad(pk)
        v = a.agenda_vigente
        ini = {"fecha": v.fecha, "hora_inicio": v.hora_inicio, "hora_fin": v.hora_fin, "lugar": v.lugar_id, "modalidad": v.modalidad_id or a.modalidad_id} if v else {"modalidad": a.modalidad_id}
        if request.GET.get("lugar", "").isdigit():
            ini["lugar"] = int(request.GET["lugar"])
        return render(request, "actividades/programar.html", self._contexto(a, ProgramarForm(initial=ini)))

    def post(self, request, pk):
        a = self.actividad(pk)
        form = ProgramarForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            try:
                servicios.programar(a, request.user, d["fecha"], d["hora_inicio"], d.get("hora_fin"), d.get("lugar"), d.get("modalidad"), d.get("motivo", ""))
            except ReglaNegocio as e:
                _avisar(request, e)
            else:
                messages.success(request, "Programación guardada; la anterior se conserva en el historial.")
                return self.volver(a, "agenda")
        return render(request, "actividades/programar.html", self._contexto(a, form), status=400)


class ConfirmarVista(_AccionActividad):
    """Muestra la revisión de compatibilidad y permite confirmar."""

    permission_required = "actividades.change_actividad"

    def _contexto(self, a):
        from .reglas import conflicto_critico_permitido

        problemas = revisar(a)
        niveles = {p.nivel for p in problemas}
        return {
            "actividad": a, "problemas": problemas, "titulo": f"Confirmar: {a.nombre}", "breadcrumb": [("Actividades", "/actividades"), (a.nombre, a.get_absolute_url())],
            "hay_bloqueantes": "bloqueante" in niveles, "hay_criticos": "critico" in niveles, "hay_advertencias": "advertencia" in niveles,
            "critico_permitido": conflicto_critico_permitido(), "volver_url": a.get_absolute_url(),
            "puede_confirmar": "confirmada" in TRANSICIONES.get(a.estado.codigo, set()),
        }

    def get(self, request, pk):
        return render(request, "actividades/confirmar.html", self._contexto(self.actividad(pk)))

    def post(self, request, pk):
        a = self.actividad(pk)
        try:
            servicios.confirmar(a, request.user, acepta_advertencias=request.POST.get("acepto") == "1", motivo_conflicto=request.POST.get("motivo_conflicto", ""))
        except ReglaNegocio as e:
            _avisar(request, e)
            return render(request, "actividades/confirmar.html", self._contexto(self.actividad(pk)), status=409)
        messages.success(request, "Actividad confirmada.")
        return self.volver(a)


class EstadoVista(_AccionActividad):
    permission_required = "actividades.change_actividad"

    def post(self, request, pk):
        a = self.actividad(pk)
        try:
            servicios.cambiar_estado(a, request.POST.get("estado", ""), request.user, request.POST.get("motivo", ""))
        except (ReglaNegocio, EstadoActividad.DoesNotExist) as e:
            _avisar(request, e) if isinstance(e, ReglaNegocio) else messages.error(request, "Estado no válido.")
        else:
            messages.success(request, "Estado actualizado.")
        return self.volver(a)


class ResultadosVista(_AccionActividad):
    permission_required = "actividades.change_actividad"

    def post(self, request, pk):
        a = self.actividad(pk)
        if a.estado.codigo == "realizada":
            messages.error(request, "La actividad ya fue finalizada.")
            return self.volver(a, "resultados")
        form = ResultadoForm(request.POST, instance=a)
        if form.is_valid():
            form.save()
            messages.success(request, "Resultados guardados.")
        else:
            messages.error(request, "No se pudo guardar.")
        return self.volver(a, "resultados")


class FinalizarVista(_AccionActividad):
    permission_required = "actividades.cerrar_actividad"

    def post(self, request, pk):
        a = self.actividad(pk)
        try:
            servicios.finalizar(a, request.user)
        except ReglaNegocio as e:
            _avisar(request, e)
            return self.volver(a, "resultados")
        messages.success(request, "Actividad finalizada: quedó como realizada y disponible en el historial.")
        return self.volver(a, "resultados")


class ReabrirVista(_AccionActividad):
    permission_required = "actividades.reabrir_actividad"

    def post(self, request, pk):
        a = self.actividad(pk)
        try:
            servicios.reabrir(a, request.user, request.POST.get("motivo", ""))
        except ReglaNegocio as e:
            _avisar(request, e)
        else:
            messages.success(request, "Actividad reabierta.")
        return self.volver(a, "resultados")


# --- Participantes ----------------------------------------------------------------
class ParticipanteNuevo(_AccionActividad):
    permission_required = "actividades.add_participacion"

    def _ctx(self, a, form, llego=False):
        return {
            "form": form, "titulo": "Agregar persona que llegó" if llego else "Agregar participante", "llego": llego,
            "volver_url": f"{a.get_absolute_url()}?tab={'asistencia' if llego else 'participantes'}", "breadcrumb": [(a.nombre, a.get_absolute_url())],
            "rapida_url": reverse("actividades:participante_rapido", args=[a.pk]) + ("?llego=1" if llego else ""),
        }

    def get(self, request, pk):
        a = self.actividad(pk)
        llego = request.GET.get("llego") == "1"
        form = ParticipanteNuevoForm(actividad=a, initial={"estado": EstadoParticipacion.objects.filter(codigo="asistio").first()} if llego else None)
        return render(request, "actividades/participante_form.html", self._ctx(a, form, llego))

    def post(self, request, pk):
        a = self.actividad(pk)
        if a.estado.codigo in ("realizada", "cancelada"):
            messages.error(request, "No se pueden agregar participantes a una actividad finalizada o cancelada.")
            return self.volver(a, "participantes")
        form = ParticipanteNuevoForm(request.POST, actividad=a)
        llego = request.POST.get("llego") == "1"
        if form.is_valid():
            p = form.save(commit=False)
            p.actividad = a
            p.creado_por = request.user
            if llego:  # RE-02: llegó sin estar previsto
                p.asistencia = True
                p.estado = EstadoParticipacion.objects.get(codigo="asistio")
            p.save()
            messages.success(request, f"{p.persona} agregada como {p.rol.nombre.lower()}" + (" y marcada como asistente." if llego else "."))
            from apps.nucleo.fases import segunda_fase_activa

            return self.volver(a, "asistencia" if llego else ("beneficiarios" if p.es_beneficiario and segunda_fase_activa() else "participantes"))
        return render(request, "actividades/participante_form.html", self._ctx(a, form, llego), status=400)


class ParticipanteRapido(_AccionActividad):
    """Buscar → seleccionar; si no existe, crear aquí mismo y queda agregada, sin salir de la actividad."""

    permission_required = "personas.add_persona"

    def _ctx(self, a, form, cands=None):
        llego = (self.request.GET.get("llego") or self.request.POST.get("llego")) == "1"
        return {"form": form, "titulo": "Crear persona que llegó" if llego else "Crear persona y agregarla", "volver_url": f"{a.get_absolute_url()}?tab={'asistencia' if llego else 'participantes'}", "breadcrumb": [(a.nombre, a.get_absolute_url())], "candidatos": cands, "actividad": a, "llego": llego}

    def get(self, request, pk):
        return render(request, "actividades/participante_rapido.html", self._ctx(self.actividad(pk), PersonaRapidaForm()))

    def post(self, request, pk):
        a = self.actividad(pk)
        if not request.user.has_perm("actividades.add_participacion"):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        form = PersonaRapidaForm(request.POST)
        if not form.is_valid():
            return render(request, "actividades/participante_rapido.html", self._ctx(a, form), status=400)
        d = form.cleaned_data
        if not request.POST.get("confirmar_duplicado"):
            cands = candidatos(d["nombres"], d["apellido_paterno"], d["apellido_materno"], None, d["correo"], d["telefono"])
            if cands:
                return render(request, "actividades/participante_rapido.html", self._ctx(a, form, cands))
        from apps.nucleo.models import EstadoRegistro, TipoContacto

        with transaction.atomic():
            persona = Persona.objects.create(
                nombres=d["nombres"], apellido_paterno=d["apellido_paterno"], apellido_materno=d["apellido_materno"], creado_por=request.user,
                estado_registro=EstadoRegistro.objects.filter(codigo="incompleto").first(),
            )
            if d["correo"]:
                Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="correo"), valor=d["correo"], principal=True)
            if d["telefono"]:
                Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="telefono_movil"), valor=d["telefono"])
            llego = request.POST.get("llego") == "1"
            Participacion.objects.create(
                actividad=a, persona=persona, rol=d["rol"], creado_por=request.user, asistencia=True if llego else None,
                estado=EstadoParticipacion.objects.get(codigo="asistio" if llego else "invitado"),
            )
        messages.success(request, f"{persona} creada y agregada. Completa su ficha cuando puedas.")
        return self.volver(a, "asistencia" if llego else "participantes")


class ParticipanteUsar(_AccionActividad):
    """Desde el aviso de duplicados: usar la persona existente en vez de crear otra."""

    permission_required = "actividades.add_participacion"

    def post(self, request, pk, persona_pk):
        a = self.actividad(pk)
        persona = get_object_or_404(Persona, pk=persona_pk)
        rol = get_object_or_404(RolParticipacion, pk=request.POST.get("rol"))
        llego = request.POST.get("llego") == "1"
        obj, creada = Participacion.objects.get_or_create(
            actividad=a, persona=persona, rol=rol,
            defaults={"estado": EstadoParticipacion.objects.get(codigo="asistio" if llego else "invitado"), "creado_por": request.user, "asistencia": True if llego else None},
        )
        messages.success(request, f"{persona} agregada." if creada else f"{persona} ya participaba con ese rol.")
        return self.volver(a, "participantes")


class ParticipacionEditar(Permiso403Mixin, UpdateView):
    model = Participacion
    form_class = ParticipacionEditarForm
    permission_required = "actividades.change_participacion"
    template_name = "generico/formulario.html"
    pk_url_kwarg = "part_pk"

    def get_queryset(self):
        return Participacion.objects.filter(actividad_id=self.kwargs["pk"])

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        a = self.object.actividad
        ctx.update(titulo=f"Participación de {self.object.persona}", volver_url=f"{a.get_absolute_url()}?tab=participantes", breadcrumb=[(a.nombre, a.get_absolute_url())])
        return ctx

    def form_valid(self, form):
        if self.object.actividad.estado.codigo == "realizada":
            messages.error(self.request, "La actividad ya fue finalizada.")
            return self.form_invalid(form)
        form.save()
        messages.success(self.request, "Participación actualizada.")
        return HttpResponseRedirect(f"{self.object.actividad.get_absolute_url()}?tab=participantes")


class AsistenciaVista(_AccionActividad):
    permission_required = "actividades.change_participacion"

    def post(self, request, pk):
        a = self.actividad(pk)
        if a.estado.codigo in ("realizada", "cancelada"):
            messages.error(request, "No se puede registrar asistencia en esta actividad.")
            return self.volver(a, "asistencia")
        estados = {e.codigo: e for e in EstadoParticipacion.objects.filter(codigo__in=["asistio", "no_asistio"])}
        n = 0
        with transaction.atomic():
            for p in a.participaciones.select_related("estado"):
                v = request.POST.get(f"asistencia_{p.pk}")
                if v not in ("si", "no", ""):
                    continue
                nuevo = {"si": True, "no": False, "": None}[v]
                if nuevo != p.asistencia:
                    p.asistencia = nuevo
                    if nuevo is True:
                        p.estado = estados["asistio"]
                    elif nuevo is False:
                        p.estado = estados["no_asistio"]
                    p.save()
                    n += 1
            if request.POST.get("sin_registro") is not None:
                a.asistencia_sin_registro = request.POST.get("sin_registro") == "1"
                a.save(update_fields=["asistencia_sin_registro"])
        messages.success(request, f"Asistencia guardada ({n} cambios).")
        return self.volver(a, "asistencia")


# --- Calendario -------------------------------------------------------------------
COLORES = {"planificada": "#6c757d", "confirmada": "#198754", "reprogramada": "#fd7e14", "suspendida": "#ffc107", "cancelada": "#dc3545", "realizada": "#0d6efd", "pendiente": "#adb5bd"}


class Calendario(Permiso403Mixin, TemplateView):
    permission_required = "actividades.view_agendaactividad"
    template_name = "actividades/calendario.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Calendario", estados=EstadoActividad.objects.all(), colores=COLORES)
        return ctx


class CalendarioEventos(Permiso403Mixin, View):
    permission_required = "actividades.view_agendaactividad"

    def get(self, request):
        try:
            ini = date.fromisoformat(request.GET.get("start", "")[:10])
            fin = date.fromisoformat(request.GET.get("end", "")[:10])
        except ValueError:
            ini, fin = date.today() - timedelta(days=31), date.today() + timedelta(days=62)
        qs = AgendaActividad.objects.filter(fecha__gte=ini, fecha__lte=fin).select_related("actividad__estado", "lugar", "estado")
        if request.GET.get("historicas") != "1":
            qs = qs.filter(vigente=True)
        if request.GET.get("estado"):
            qs = qs.filter(actividad__estado__codigo=request.GET["estado"])
        if request.GET.get("lugar", "").isdigit():
            qs = qs.filter(lugar_id=request.GET["lugar"])
        eventos = []
        for ag in qs[:1000]:
            codigo = ag.actividad.estado.codigo
            inicio = f"{ag.fecha.isoformat()}T{ag.hora_inicio:%H:%M:%S}" if ag.hora_inicio else ag.fecha.isoformat()
            fin_ev = f"{ag.fecha.isoformat()}T{ag.hora_fin:%H:%M:%S}" if ag.hora_inicio and ag.hora_fin else None
            ev = {
                "id": ag.pk, "title": ag.actividad.nombre + ("" if ag.vigente else f" (v{ag.version}, anterior)"), "start": inicio, "allDay": not ag.hora_inicio,
                "url": ag.actividad.get_absolute_url(), "color": COLORES.get(codigo, "#6c757d") if ag.vigente else "#ced4da", "textColor": "#fff" if ag.vigente else "#495057",
                "extendedProps": {"estado": ag.actividad.estado.nombre, "lugar": str(ag.lugar) if ag.lugar else "", "vigente": ag.vigente},
            }
            if fin_ev:
                ev["end"] = fin_ev
            eventos.append(ev)
        return JsonResponse(eventos, safe=False)


# --- Búsqueda asistida (F16) -------------------------------------------------------
class Candidatos(Permiso403Mixin, TemplateView):
    permission_required = "actividades.view_actividad"
    template_name = "actividades/candidatos.html"

    def get_context_data(self, **kw):
        from . import matching

        ctx = super().get_context_data(**kw)
        a = get_object_or_404(Actividad.objects.select_related("estado"), pk=self.kwargs["pk"])
        g = self.request.GET
        tipo = g.get("tipo", "personas")
        entero = lambda k: int(g[k]) if g.get(k, "").isdigit() else None
        resultados = []
        if g.get("buscar"):
            if tipo == "personas" and self.request.user.has_perm("personas.view_persona"):
                resultados = matching.buscar_personas(a, g.get("q", ""), g.get("area", ""), entero("institucion"), entero("carrera"), entero("comuna"), g.get("solo_disponibles") == "1")
            elif tipo == "lugares" and self.request.user.has_perm("lugares.view_lugar"):
                resultados = matching.buscar_lugares(a, entero("cantidad"), entero("comuna"), g.get("q", ""))
            elif tipo == "organizaciones" and self.request.user.has_perm("organizaciones.view_organizacion"):
                resultados = matching.buscar_organizaciones(a, entero("tipo_org"), entero("comuna"), g.get("q", ""))
        from apps.nucleo.models import TipoOrganizacion

        ctx.update(
            actividad=a, titulo=f"Buscar candidatos: {a.nombre}", tipo=tipo, resultados=resultados, buscado=bool(g.get("buscar")), agenda=a.agenda_vigente,
            roles=RolParticipacion.objects.filter(activo=True), comunas=Comuna.objects.all(), tipos_org=TipoOrganizacion.objects.filter(activo=True),
            instituciones=Organizacion.objects.filter(tipo__codigo="institucion_educativa", activo=True),
            breadcrumb=[("Actividades", "/actividades"), (a.nombre, a.get_absolute_url())], datos=g,
            puede_agregar=self.request.user.has_perm("actividades.add_participacion") and a.estado.codigo not in ("realizada", "cancelada"),
        )
        return ctx


class OrganizacionUsar(_AccionActividad):
    """El Gestor decide: agrega una organización sugerida a la actividad."""

    permission_required = "actividades.add_actividadorganizacion"

    def post(self, request, pk, org_pk):
        from .models import ActividadOrganizacion

        a = self.actividad(pk)
        org = get_object_or_404(Organizacion, pk=org_pk)
        ActividadOrganizacion.objects.get_or_create(actividad=a, organizacion=org, tipo_intervencion=None)
        messages.success(request, f"{org} agregada a la actividad.")
        return self.volver(a, "organizaciones")

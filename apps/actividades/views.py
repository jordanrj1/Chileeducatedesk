"""Pantallas de actividades: listado, ficha con pestañas, crear y editar, programar, confirmar, cambiar estado,
participantes, asistencia, resultados, finalizar, sesiones, candidatos, constancia y calendario.
Cada vista revisa el permiso en el servidor; la lógica de reglas vive en servicios.py y reglas.py."""
from datetime import date, timedelta

from django.contrib import messages
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.nucleo.auditoria import registrar
from apps.nucleo.direccion_mixin import ComunaInicialMixin
from apps.nucleo.selector import OpcionesVista, pk_seguro
from apps.nucleo.models import EstadoActividad, EstadoParticipacion, Modalidad, RolParticipacion, TipoActividad
from apps.nucleo.vistas_base import (
    EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, cambios_historial, nombre_comuna, nombre_organizacion,
    opciones_comunas, opciones_modelo, opciones_organizaciones,
)
from apps.organizaciones.models import Organizacion
from apps.personas.duplicados import candidatos
from apps.personas.models import Contacto, Persona
from apps.proyectos.models import Proyecto
from apps.territorio.consultas import actividad_en_comuna, dirigida_a_comuna
from apps.territorio.destinos import fila_inicial, texto_destino
from apps.territorio.models import Comuna

from . import servicios
from .forms import (
    SerieForm, ActividadForm, EstadoForm, ParticipacionEditarForm, ParticipanteNuevoForm, PersonaRapidaForm, ProgramarForm, ResultadoForm,
)
from .models import Actividad, ActividadComunidad, ActividadTerritorio, AgendaActividad, Participacion, SesionActividad, SesionAsistencia
from .selector import ACTIVIDADES
from .reglas import TRANSICIONES, ReglaNegocio, antes_de_la_fecha, personas_que_ocupan, revisar


def _avisar(request, error):
    for m in error.mensajes:
        messages.error(request, m)


def _agenda_vigente_qs():
    return AgendaActividad.objects.filter(vigente=True).select_related("lugar", "estado")


def _filtro_comuna(qs, v):
    """La comuna incluye las actividades dirigidas a sus sectores, igual que la ficha de la comuna."""
    return qs.filter(actividad_en_comuna(int(v))).distinct()


def _comunas_con_actividades():
    """Comunas del lugar programado o del público objetivo (también por sector): las únicas que vale la pena ofrecer."""
    territorios = ActividadTerritorio.objects.filter(vigente=True)
    return (
        Q(pk__in=AgendaActividad.objects.filter(vigente=True).values("lugar__direccion__comuna_id"))
        | Q(pk__in=territorios.values("comuna_id"))
        | Q(pk__in=territorios.values("sector__comuna_id"))
    )


PERIODOS = (("proximas", "Próximas"), ("semana", "Esta semana"), ("mes", "Este mes"), ("pasadas", "Pasadas"), ("sin", "Sin programar"))


def _filtro_periodo(qs, v):
    """«Cuándo»: según la fecha programada vigente. «Sin programar» son las que no tienen fecha."""
    hoy = timezone.localdate()
    agenda = AgendaActividad.objects.filter(actividad=OuterRef("pk"), vigente=True)
    if v == "sin":
        return qs.filter(~Exists(agenda))
    if v == "proximas":
        agenda = agenda.filter(fecha__gte=hoy)
    elif v == "semana":
        lunes = hoy - timedelta(days=hoy.weekday())
        agenda = agenda.filter(fecha__gte=lunes, fecha__lte=lunes + timedelta(days=6))
    elif v == "mes":
        agenda = agenda.filter(fecha__year=hoy.year, fecha__month=hoy.month)
    elif v == "pasadas":
        agenda = agenda.filter(fecha__lt=hoy)
    else:
        raise ValueError(v)
    return qs.filter(Exists(agenda))


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
    descripcion = "Talleres, charlas y jornadas: su estado, fecha, lugar y responsable."
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
        Filtro("estado", "Estado", "estado_id", opciones_modelo(EstadoActividad), principal=True),
        Filtro("comuna", "Comuna", "", lambda: opciones_comunas(_comunas_con_actividades()), aplicar=_filtro_comuna,
               principal=True, todos="Todas", etiqueta_de=nombre_comuna),
        Filtro("periodo", "Cuándo", "", lambda: list(PERIODOS), aplicar=_filtro_periodo, principal=True, todos="Cualquier fecha"),
        Filtro("tipo", "Tipo", "tipo_id", opciones_modelo(TipoActividad), grupo="Qué"),
        Filtro("proyecto", "Proyecto", "proyecto_id", lambda: [(str(p.pk), p.nombre) for p in Proyecto.objects.all()], grupo="Qué"),
        Filtro("incompleta", "Incompletas", "", entrada="casilla", texto_casilla="Solo incompletas", grupo="Qué",
               aplicar=lambda qs, v: qs.filter(pk__in=Actividad.objects.incompletas().values("pk")) if v == "1" else qs),
        # Organización reúne a las instituciones educativas (agrupadas por tipo); «?institucion=» sigue funcionando
        Filtro("organizacion", "Organización", "", lambda: opciones_organizaciones(Organizacion.objects.filter(actividades__isnull=False).distinct()),
               aplicar=lambda qs, v: qs.filter(organizaciones__organizacion_id=v).distinct(), grupo="Con quién", todos="Todas",
               tope=300, etiqueta_de=nombre_organizacion),
        Filtro("responsable", "Responsable", "responsable_id", lambda: [(str(p.pk), p.nombre_completo) for p in Persona.objects.filter(actividades_a_cargo__isnull=False).distinct()], grupo="Con quién"),
        Filtro("institucion", "Institución", "", aplicar=lambda qs, v: qs.filter(organizaciones__organizacion_id=v).distinct(), oculto=True,
               etiqueta_de=nombre_organizacion),
        Filtro("desde", "Desde", "", entrada="date", aplicar=_filtro_fecha("gte"), grupo="Fechas exactas"),
        Filtro("hasta", "Hasta", "", entrada="date", aplicar=_filtro_fecha("lte"), grupo="Fechas exactas"),
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


class ActividadOpciones(OpcionesVista):
    """Lista de actividades para los buscadores de los formularios (ver apps/actividades/selector.py)."""

    fuente = ACTIVIDADES


class ActividadNueva(ComunaInicialMixin, Permiso403Mixin, CreateView):
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

    def comunidad_inicial(self):
        from apps.comunidades.models import Comunidad

        valor = self.request.GET.get("comunidad") or self.request.POST.get("comunidad_destino")
        return Comunidad.objects.filter(pk=valor, activo=True).first() if str(valor or "").isdigit() else None

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["destinos_inicial"] = self.destinos_iniciales()
        return kw

    def destinos_iniciales(self):
        """«¿Dónde?» parte con la comuna o el sector de la dirección (?comuna=&sector=), el de la comunidad (?comunidad=) o
        los territorios de la jornada (?padre=). Se puede cambiar antes de guardar."""
        comuna = self.comuna_inicial()
        if comuna:
            return [fila_inicial(comuna=comuna, sector=self.sector_inicial())]
        comunidad = self.comunidad_inicial()
        if comunidad:
            sector = comunidad.sector if comunidad.sector_id and comunidad.sector.activo else None
            return [fila_inicial(comuna=comunidad.comuna, sector=sector)]
        padre = pk_seguro(self.request.GET.get("padre"))
        if padre:
            territorios = ActividadTerritorio.objects.filter(actividad_id=padre, vigente=True).select_related("sector", "provincia").order_by("pk")
            return [fila_inicial(t) for t in territorios]
        return []

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nueva actividad", volver_url=self.request.META.get("HTTP_REFERER") or "/actividades", breadcrumb=[("Actividades", "/actividades")])
        comunidad, comuna, sector = self.comunidad_inicial(), self.comuna_inicial(), self.sector_inicial()
        destinos = []
        if comunidad:
            destinos.append(f"Dirigida a la comunidad «{comunidad}» ({comunidad.territorio}).")
            ctx["comunidad_destino"] = comunidad
        if sector:
            destinos.append(f"Se dirige al sector {sector.nombre} de la comuna de {comuna.nombre}.")
        elif comuna:
            destinos.append(f"Se dirige a la comuna de {comuna.nombre}.")
        if destinos:
            ctx["bajada"] = " ".join(destinos) + " Los campos marcados con * son obligatorios."
        return ctx

    def form_valid(self, form):
        from apps.documentos.origen import registrar_origen

        with transaction.atomic():  # la actividad y lo que la ubica (comunidad, territorio, origen) se guardan juntos o no se guardan
            obj = form.save(commit=False)
            obj.creado_por = self.request.user
            obj.estado = EstadoActividad.objects.get(codigo="pendiente")
            obj.save()
            form.save_m2m()
            comunidad = self.comunidad_inicial()
            if comunidad:
                ActividadComunidad.objects.create(actividad=obj, comunidad=comunidad)
            # Sin la sección «¿Dónde?» en lo enviado, la comuna o el sector de la dirección queda como su territorio
            # (con la sección, form.save_m2m() ya guardó lo elegido en sus filas).
            comuna, sector = self.comuna_inicial(), self.sector_inicial()
            if not form.destinos_enviados and sector:
                ActividadTerritorio.objects.create(actividad=obj, sector=sector)
            elif not form.destinos_enviados and comuna:
                ActividadTerritorio.objects.create(actividad=obj, comuna=comuna)
            registrar_origen(obj, self.request.user)
        messages.success(self.request, "Actividad creada. Completa el resto de la información cuando puedas.")
        return HttpResponseRedirect(obj.get_absolute_url())


class ActividadEditar(EditarBase):
    model = Actividad
    form_class = ActividadForm
    permission_required = "actividades.change_actividad"
    titulo = "Editar actividad"
    breadcrumb = [("Actividades", "/actividades")]

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        a = self.object
        partes = [f"Estado: {a.estado.nombre}"] + ([f"Proyecto: {a.proyecto}"] if a.proyecto_id else [])
        ctx["bajada"] = (" · ".join(partes) + ". El estado, la fecha y el lugar se cambian desde la ficha de la actividad. "
                         "Los campos marcados con * son obligatorios.")
        return ctx

    def form_valid(self, form):
        if self.object.estado.codigo == "realizada":
            messages.error(self.request, "La actividad ya fue finalizada. Reábrela (con permiso) para corregirla.")
            return self.form_invalid(form)
        with transaction.atomic():  # la actividad y sus territorios («¿Dónde?») se guardan juntos o no se guardan
            return super().form_valid(form)


class ActividadFicha(FichaBase):
    model = Actividad
    permission_required = "actividades.view_actividad"
    template_name = "actividades/ficha.html"
    pestanas_segunda_fase = {"beneficiarios": "beneficiarios"}
    breadcrumb = [("Actividades", "/actividades")]
    permiso_editar = "actividades.change_actividad"
    pestanas = [
        ("info", "Información", "actividades/pestanas/info.html"),
        ("publico", "Público y comunidades", "actividades/pestanas/publico.html"),
        ("participantes", "Participantes", "actividades/pestanas/participantes.html"),
        ("beneficiarios", "Beneficiarios", "actividades/pestanas/participantes.html"),
        ("organizaciones", "Organizaciones", "generico/_hijos.html"),
        ("sesiones", "Sesiones y minutas", "actividades/pestanas/sesiones.html"),
        ("agenda", "Agenda", "actividades/pestanas/agenda.html"),
        ("coordinacion", "Coordinación", "actividades/pestanas/coordinacion.html", "coordinacion.view_interaccion"),
        ("asistencia", "Asistencia", "actividades/pestanas/asistencia.html"),
        ("documentos", "Documentos", "actividades/pestanas/documentos.html", "documentos.view_documento"),
        ("resultados", "Resultados", "actividades/pestanas/resultados.html"),
        ("alcance", "Alcance", "actividades/pestanas/alcance.html", "actividades.view_participacion"),
        ("origen", "Origen", "documentos/pestanas/origen.html", "documentos.view_origendato"),
        ("historial", "Historial", "actividades/pestanas/historial.html", "actividades.view_historicalactividad"),
    ]

    def get_queryset(self):
        return super().get_queryset().select_related("proyecto", "tipo", "estado", "modalidad", "responsable", "actividad_padre")

    def acciones_extra(self):
        res = []
        if self.request.user.has_perm("coordinacion.add_interaccion"):
            res.append(("Registrar interacción", f"/interacciones/nueva?actividad={self.object.pk}"))
        if self.request.user.has_perm("actividades.add_actividad"):
            res.append(("Duplicar", f"/actividades/{self.object.pk}/duplicar"))
        return res

    def contexto_ficha(self):
        a = self.object
        u = self.request.user
        codigo = a.estado.codigo
        siguientes = [c for c in TRANSICIONES.get(codigo, set()) if c not in ("confirmada", "realizada")]
        editable = codigo != "realizada"
        agenda = a.agenda_vigente
        return {
            "url_editar": reverse("actividades:editar", args=[a.pk]) if editable else None,
            "url_volver": a.proyecto.get_absolute_url() if a.proyecto_id else "/actividades",
            "puede_agregar": u.has_perm("actividades.change_actividad") and editable,
            "puede_programar": u.has_perm("actividades.reprogramar_actividad") and codigo not in ("cancelada", "realizada", "suspendida"),
            "puede_confirmar": u.has_perm("actividades.change_actividad") and "confirmada" in TRANSICIONES.get(codigo, set()),
            "estados_siguientes": [(c, EstadoActividad.objects.get(codigo=c).nombre) for c in siguientes] if u.has_perm("actividades.change_actividad") else [],
            "antes_de_fecha": antes_de_la_fecha(a),
            "puede_asistencia": u.has_perm("actividades.change_participacion") and codigo not in ("cancelada", "pendiente", "suspendida") and not antes_de_la_fecha(a),
            "puede_resultado": u.has_perm("actividades.change_actividad") and codigo not in ("cancelada", "pendiente", "suspendida") and not antes_de_la_fecha(a),
            "puede_finalizar": u.has_perm("actividades.cerrar_actividad") and "realizada" in TRANSICIONES.get(codigo, set()) and not antes_de_la_fecha(a),
            "puede_reabrir": u.has_perm("actividades.reabrir_actividad") and codigo == "realizada",
            "agenda": agenda,
            "faltantes": a.faltantes(),
            "comuna_ficha": self.comuna_de_la_actividad(agenda),
        }

    def comuna_de_la_actividad(self, agenda):
        """Comuna del lugar programado; si no hay, la del primer territorio vigente que sea una comuna o un sector. A lo más dos consultas."""
        if agenda and agenda.lugar_id:
            return Comuna.objects.filter(direcciones__pk=agenda.lugar.direccion_id).first()
        territorio = (
            self.object.territorios.filter(Q(comuna__isnull=False) | Q(sector__isnull=False), vigente=True)
            .select_related("comuna", "sector__comuna").order_by("pk").first()
        )
        return (territorio.comuna or territorio.sector.comuna) if territorio else None

    def _participantes(self, beneficiarios):
        from apps.nucleo.fases import modulo_activo

        qs = self.object.participaciones.select_related("persona", "rol", "estado", "institucion", "comunidad")
        if not modulo_activo("beneficiarios"):
            return list(qs) if not beneficiarios else []  # sin pestaña aparte: todos van en Participantes
        return [p for p in qs if p.es_beneficiario == beneficiarios]

    def ctx_participantes(self):
        partes = self._participantes(False)
        from apps.nucleo.models import RolParticipacion

        grupos = [(etiqueta, [p for p in partes if p.rol.grupo == clave]) for clave, etiqueta in RolParticipacion.GRUPOS]
        return {"participaciones": partes, "grupos_participacion": [(e, ps) for e, ps in grupos if ps], "grupo": "participantes",
                "titulo_pestana": "Participantes", "capacidad_alerta": self._capacidad()}

    def ctx_publico(self):
        a = self.object
        pk = a.pk
        destinos = a.comunidades_destino.select_related("comunidad__comuna", "comunidad__sector")
        return {
            "destinos": [{
                "texto": str(d.comunidad), "detalle": " · ".join(x for x in [d.comunidad.territorio, f"{d.beneficiarios_estimados} beneficiarios estimados" if d.beneficiarios_estimados else "", d.observaciones] if x),
                "vigente": d.vigente, "url_editar": reverse("actividades:comunidades_editar", args=[pk, d.pk]), "url_alternar": reverse("actividades:comunidades_alternar", args=[pk, d.pk]),
            } for d in destinos],
            "url_nueva_comunidad": reverse("actividades:comunidades_nuevo", args=[pk]),
            "territorios_publico": a.territorios.filter(vigente=True).select_related("region", "provincia", "comuna", "sector"),
        }

    def ctx_alcance(self):
        from .alcance import alcance

        return {"alcance": alcance([self.object]), "contexto_alcance": "esta actividad"}

    def ctx_beneficiarios(self):
        partes = self._participantes(True)
        return {"participaciones": partes, "grupos_participacion": [("Beneficiarios", partes)] if partes else [], "grupo": "beneficiarios",
                "titulo_pestana": "Beneficiarios", "capacidad_alerta": None}

    def _capacidad(self):
        ag = self.object.agenda_vigente
        if ag and ag.lugar and ag.lugar.capacidad is not None:
            from .reglas import personas_que_ocupan

            partes = list(self.object.participaciones.select_related("estado", "rol"))
            n = len(personas_que_ocupan(self.object, [p for p in partes if p.activa]))
            espera = sum(1 for p in partes if p.en_espera)
            return {"n": n, "capacidad": ag.lugar.capacidad, "excede": n > ag.lugar.capacidad, "lleno": n >= ag.lugar.capacidad, "espera": espera}
        return None

    def ctx_info(self):
        return {
            "territorios": [
                {"texto": texto_destino(t), "vigente": t.vigente, "url_editar": reverse("actividades:territorios_editar", args=[self.object.pk, t.pk]), "url_alternar": reverse("actividades:territorios_alternar", args=[self.object.pk, t.pk]), "detalle": ""}
                for t in self.object.territorios.select_related("region", "provincia", "comuna", "sector__comuna")
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
        sesiones = self.object.sesiones.select_related("lugar").prefetch_related("facilitadores__persona", "asistencias", "evidencias")
        return {"sesiones": sesiones, "url_nueva_sesion": reverse("actividades:sesiones_nuevo", args=[self.object.pk]),
                "puede_sesiones": self.request.user.has_perm("actividades.add_sesionactividad") and self.object.estado.codigo != "realizada"}

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
        # RE-E9: se listan todos (también quien había rechazado): manda la asistencia real
        return {"participaciones": [p for p in self.object.participaciones.select_related("persona", "rol", "estado") if p.estado.codigo != "registro_erroneo"]}

    def ctx_documentos(self):
        u = self.request.user
        docs = self.object.documentos.select_related("tipo")
        if not u.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        return {"documentos": docs}

    def ctx_resultados(self):
        a = self.object
        sin_asistencia = [p for p in a.participaciones.select_related("estado") if p.activa and p.asistencia is None]
        return {"form_resultado": ResultadoForm(instance=a), "finalizada": a.estado.codigo == "realizada", "sin_asistencia": len(sin_asistencia)}

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
        ini = {"fecha": v.fecha, "hora_inicio": v.hora_inicio, "hora_fin": v.hora_fin, "lugar": v.lugar_id, "modalidad": v.modalidad_id or a.modalidad_id, "enlace": v.enlace} if v else {"modalidad": a.modalidad_id}
        if request.GET.get("lugar", "").isdigit():
            ini["lugar"] = int(request.GET["lugar"])
        return render(request, "actividades/programar.html", self._contexto(a, ProgramarForm(initial=ini)))

    def post(self, request, pk):
        a = self.actividad(pk)
        form = ProgramarForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            try:
                servicios.programar(a, request.user, d["fecha"], d["hora_inicio"], d.get("hora_fin"), d.get("lugar"), d.get("modalidad"), d.get("motivo", ""), d.get("enlace", ""))
            except ReglaNegocio as e:
                _avisar(request, e)
            else:
                messages.success(request, "Programación guardada; la anterior se conserva en el historial.")
                return self.volver(a, "agenda")
        return render(request, "actividades/programar.html", self._contexto(a, form), status=400)


class SerieVista(_AccionActividad):
    permission_required = "actividades.reprogramar_actividad"

    def _ctx(self, a, form):
        return {"form": form, "titulo": f"Crear serie: {a.nombre}", "volver_url": f"{a.get_absolute_url()}?tab=info", "breadcrumb": [("Actividades", "/actividades"), (a.nombre, a.get_absolute_url())]}

    def get(self, request, pk):
        a = self.actividad(pk)
        v = a.agenda_vigente
        ini = {"hora_inicio": v.hora_inicio, "hora_fin": v.hora_fin, "lugar": v.lugar_id, "primera_fecha": v.fecha} if v else {}
        return render(request, "generico/formulario.html", self._ctx(a, SerieForm(initial=ini)))

    def post(self, request, pk):
        a = self.actividad(pk)
        form = SerieForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            try:
                creadas = servicios.crear_serie(a, request.user, d["primera_fecha"], d["frecuencia"], d["repeticiones"], d["hora_inicio"], d.get("hora_fin"), d.get("lugar"))
            except ReglaNegocio as e:
                _avisar(request, e)
            else:
                messages.success(request, f"Se crearon {len(creadas)} actividades programadas. Cada una se confirma y gestiona por separado.")
                return self.volver(a, "info")
        return render(request, "generico/formulario.html", self._ctx(a, form), status=400)


class ConfirmarVista(_AccionActividad):
    """Muestra la revisión de compatibilidad y permite confirmar."""

    permission_required = "actividades.change_actividad"

    def _contexto(self, a):
        from .reglas import conflicto_critico_permitido

        problemas = revisar(a)
        niveles = {p.nivel for p in problemas}
        hay_problemas = bool(niveles - {"ok", "info"})
        return {
            "actividad": a, "problemas": problemas, "titulo": f"Confirmar: {a.nombre}", "breadcrumb": [("Actividades", "/actividades"), (a.nombre, a.get_absolute_url())],
            "hay_bloqueantes": "bloqueante" in niveles, "hay_criticos": "critico" in niveles, "hay_advertencias": "advertencia" in niveles,
            "critico_permitido": conflicto_critico_permitido(), "volver_url": a.get_absolute_url(), "hay_problemas": hay_problemas,
            "puede_confirmar": "confirmada" in TRANSICIONES.get(a.estado.codigo, set()),
        }

    def get(self, request, pk):
        return render(request, "actividades/confirmar.html", self._contexto(self.actividad(pk)))

    def post(self, request, pk):
        a = self.actividad(pk)
        try:
            servicios.confirmar(
                a, request.user, acepta_advertencias=request.POST.get("acepto") == "1", motivo_conflicto=request.POST.get("motivo_conflicto", ""),
                motivo_advertencias=request.POST.get("motivo_advertencias", ""),
            )
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
        if a.estado.codigo in ("cancelada", "pendiente", "suspendida") or antes_de_la_fecha(a):
            messages.error(request, "El resultado se registra desde el día de la actividad.")
            return self.volver(a, "resultados")
        form = ResultadoForm(request.POST, instance=a)
        if form.is_valid():
            form.save()  # queda en el historial de la actividad
            if a.estado.codigo == "realizada":
                registrar(request.user, "resultado_corregido", a, "después de finalizar")
            messages.success(request, "Resultados guardados.")
        else:
            messages.error(request, "No se pudo guardar.")
        return self.volver(a, "resultados")


class FinalizarVista(_AccionActividad):
    permission_required = "actividades.cerrar_actividad"

    def post(self, request, pk):
        a = self.actividad(pk)
        sin = [p for p in a.participaciones.select_related("estado") if p.activa and p.asistencia is None]
        try:
            servicios.finalizar(a, request.user)
        except ReglaNegocio as e:
            _avisar(request, e)
            return self.volver(a, "resultados")
        messages.success(request, "Actividad finalizada: quedó como realizada y disponible en el historial.")
        if sin and not a.asistencia_sin_registro:  # RE-E5
            messages.warning(request, f"{len(sin)} participante(s) quedaron sin registro de asistencia. Puedes completarlo en la pestaña Asistencia.")
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
def _puede_sumar_participante(request, a, llego):
    """Cancelada: no. Realizada: solo «persona que llegó» (registro tardío). Resto: sí."""
    if a.estado.codigo == "cancelada" or (a.estado.codigo == "realizada" and not llego):
        messages.error(request, "En una actividad cancelada no se agregan personas; en una realizada, solo «persona que llegó».")
        return False
    return True


def _avisar_capacidad(request, a):
    """AT-E8: aviso al agregar a quien excede la capacidad del lugar."""
    ag = a.agenda_vigente
    if ag and ag.lugar and ag.lugar.capacidad is not None:
        n = len(personas_que_ocupan(a))
        if n > ag.lugar.capacidad:
            messages.warning(request, f"Ahora hay {n} personas para una capacidad de {ag.lugar.capacidad}. Considera dejar a las últimas «En lista de espera» o cambiar de lugar.")


class ParticipanteQuitar(_AccionActividad):
    """HI-E2: quitar a quien se relacionó por error. No se borra: queda «Registro erróneo» con el motivo."""

    permission_required = "actividades.change_participacion"

    def _p(self, pk, part_pk):
        return get_object_or_404(Participacion.objects.select_related("persona", "actividad"), pk=part_pk, actividad_id=pk)

    def get(self, request, pk, part_pk):
        p = self._p(pk, part_pk)
        return render(request, "actividades/quitar.html", {"p": p, "titulo": f"Quitar a {p.persona}", "breadcrumb": [(p.actividad.nombre, p.actividad.get_absolute_url())]})

    def post(self, request, pk, part_pk):
        p = self._p(pk, part_pk)
        motivo = request.POST.get("motivo", "").strip()
        if not motivo:
            messages.error(request, "Indica por qué se quita.")
            return HttpResponseRedirect(request.path)
        p.estado = EstadoParticipacion.objects.get(codigo="registro_erroneo")
        p.observaciones = f"Quitada por error: {motivo}"[:250]
        p.save()
        registrar(request.user, "participacion_quitada", p, motivo)
        messages.success(request, f"{p.persona} quitada de la actividad. Queda en el historial como registro erróneo.")
        return self.volver(p.actividad, "participantes")


class ActividadDuplicar(_AccionActividad):
    permission_required = "actividades.add_actividad"

    def get(self, request, pk):
        a = self.actividad(pk)
        return render(request, "actividades/duplicar.html", {"actividad": a, "titulo": f"Duplicar «{a.nombre}»", "breadcrumb": [(a.nombre, a.get_absolute_url())]})

    def post(self, request, pk):
        nueva = servicios.duplicar(self.actividad(pk), request.user)
        messages.success(request, "Actividad duplicada (sin participantes ni fechas). Ajusta el nombre y prográmala.")
        return HttpResponseRedirect(reverse("actividades:editar", args=[nueva.pk]))
def _perfil_del_rol(persona, rol):
    """F24: si el rol lleva un perfil (Catálogos), se agrega a la persona sin quitarle los que ya tiene."""
    if rol and rol.perfil_id:
        persona.perfiles.add(rol.perfil_id)


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
        llego = request.POST.get("llego") == "1"
        if not _puede_sumar_participante(request, a, llego):
            return self.volver(a, "participantes")
        form = ParticipanteNuevoForm(request.POST, actividad=a)
        if form.is_valid():
            p = form.save(commit=False)
            p.actividad = a
            p.creado_por = request.user
            if llego:  # RE-02: llegó sin estar previsto
                p.asistencia = True
                p.estado = EstadoParticipacion.objects.get(codigo="asistio")
            p.save()
            _perfil_del_rol(p.persona, p.rol)
            messages.success(request, f"{p.persona} agregada como {p.rol.nombre.lower()}" + (" y marcada como asistente." if llego else "."))
            _avisar_capacidad(request, a)
            if a.estado.codigo == "realizada":
                registrar(request.user, "registro_tardio", p, "persona que llegó, agregada después de finalizar")
            from apps.nucleo.fases import modulo_activo

            return self.volver(a, "asistencia" if llego else ("beneficiarios" if p.es_beneficiario and modulo_activo("beneficiarios") else "participantes"))
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
        if not _puede_sumar_participante(request, a, request.POST.get("llego") == "1"):
            return self.volver(a, "participantes")
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
            _perfil_del_rol(persona, d["rol"])
        messages.success(request, f"{persona} creada y agregada. Completa su ficha cuando puedas.")
        _avisar_capacidad(request, a)
        return self.volver(a, "asistencia" if llego else "participantes")


class ParticipanteUsar(_AccionActividad):
    """Desde el aviso de duplicados: usar la persona existente en vez de crear otra."""

    permission_required = "actividades.add_participacion"

    def post(self, request, pk, persona_pk):
        a = self.actividad(pk)
        persona = get_object_or_404(Persona, pk=persona_pk)
        rol = get_object_or_404(RolParticipacion, pk=request.POST.get("rol"))
        llego = request.POST.get("llego") == "1"
        if not _puede_sumar_participante(request, a, llego):
            return self.volver(a, "participantes")
        obj, creada = Participacion.objects.get_or_create(
            actividad=a, persona=persona, rol=rol,
            defaults={"estado": EstadoParticipacion.objects.get(codigo="asistio" if llego else "invitado"), "creado_por": request.user, "asistencia": True if llego else None},
        )
        _perfil_del_rol(persona, rol)
        messages.success(request, f"{persona} agregada." if creada else f"{persona} ya participaba con ese rol.")
        _avisar_capacidad(request, a)
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
        if a.estado.codigo in ("cancelada", "pendiente", "suspendida"):
            messages.error(request, "No se puede registrar asistencia en esta actividad.")
            return self.volver(a, "asistencia")
        if antes_de_la_fecha(a):
            messages.error(request, f"La asistencia se registra desde el día de la actividad ({a.agenda_vigente.fecha:%d-%m-%Y}).")
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
        if a.estado.codigo == "realizada" and n:
            registrar(request.user, "asistencia_tardia", a, f"{n} cambios después de finalizar")  # RE-E3
        messages.success(request, f"Asistencia guardada ({n} cambios).")
        return self.volver(a, "asistencia")


class Constancia(Permiso403Mixin, TemplateView):
    """Constancia de participación imprimible [P]. Solo para quien tiene la asistencia registrada."""

    permission_required = "actividades.view_participacion"
    template_name = "actividades/constancia.html"

    def get_context_data(self, **kw):
        from django.utils import timezone

        ctx = super().get_context_data(**kw)
        p = get_object_or_404(Participacion.objects.select_related("persona", "rol", "actividad__proyecto"), pk=self.kwargs["part_pk"], actividad_id=self.kwargs["pk"])
        if p.asistencia is not True:
            raise Http404("Solo se emite constancia a quien tiene la asistencia registrada.")
        from apps.organizaciones.models import Organizacion

        registrar(self.request.user, "constancia_emitida", p, str(p.persona))
        ctx.update(p=p, agenda=p.actividad.agenda_vigente, fundacion=Organizacion.objects.filter(es_propia=True).first(), hoy=timezone.localdate(), titulo="Constancia de participación")
        return ctx


# --- Calendario -------------------------------------------------------------------
COLORES = {"planificada": "#6c757d", "confirmada": "#198754", "reprogramada": "#fd7e14", "suspendida": "#ffc107", "cancelada": "#dc3545", "realizada": "#0d6efd", "pendiente": "#adb5bd"}


class Calendario(Permiso403Mixin, TemplateView):
    permission_required = "actividades.view_agendaactividad"
    template_name = "actividades/calendario.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(
            titulo="Calendario", estados=EstadoActividad.objects.all(), colores=COLORES, comunas=Comuna.objects.all(),
            responsables=Persona.objects.filter(actividades_a_cargo__isnull=False).distinct(),
            organizaciones=Organizacion.objects.filter(activo=True, actividades__isnull=False).distinct(),
        )
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
        if request.GET.get("zona", "").isdigit():
            z = request.GET["zona"]
            qs = qs.filter(Q(lugar__direccion__comuna_id=z) | dirigida_a_comuna(int(z), "actividad__")).distinct()  # también sus sectores
        if request.GET.get("responsable", "").isdigit():
            qs = qs.filter(actividad__responsable_id=request.GET["responsable"])
        if request.GET.get("organizacion", "").isdigit():
            qs = qs.filter(actividad__organizaciones__organizacion_id=request.GET["organizacion"]).distinct()
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


class SesionVista(Permiso403Mixin, View):
    """Minuta de una sesión: lo que se hizo, avances, asistencia por sesión y evidencias (F22)."""

    permission_required = "actividades.view_sesionactividad"

    def _sesion(self, pk, sid):
        return get_object_or_404(SesionActividad.objects.select_related("actividad__estado", "lugar", "redactada_por"), pk=sid, actividad_id=pk)

    def get(self, request, pk, sid):
        s = self._sesion(pk, sid)
        a = s.actividad
        marcadas = {x.participacion_id: x.asistio for x in s.asistencias.all()}
        partes = [p for p in a.participaciones.select_related("persona", "rol", "estado") if p.estado.codigo != "registro_erroneo"]
        filas = [(p, marcadas.get(p.pk)) for p in partes]
        docs = s.evidencias.select_related("tipo")
        if not request.user.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        return render(request, "actividades/sesion.html", {
            "sesion": s, "actividad": a, "filas": filas, "evidencias": docs, "facilitadores": [f.persona for f in s.facilitadores.select_related("persona")],
            "titulo": f"{s} · {a.nombre}", "breadcrumb": [("Actividades", "/actividades"), (a.nombre, f"{a.get_absolute_url()}?tab=sesiones")],
            "puede_editar": request.user.has_perm("actividades.change_sesionactividad") and a.estado.codigo != "realizada",
            "puede_asistencia": request.user.has_perm("actividades.change_participacion"),
            "presentes": sum(1 for _, v in filas if v is True),
        })


class SesionAsistenciaVista(Permiso403Mixin, View):
    permission_required = "actividades.change_participacion"

    def post(self, request, pk, sid):
        s = get_object_or_404(SesionActividad, pk=sid, actividad_id=pk)
        n = 0
        with transaction.atomic():
            for p in s.actividad.participaciones.all():
                v = request.POST.get(f"asistio_{p.pk}")
                if v not in ("si", "no", ""):
                    continue
                valor = {"si": True, "no": False, "": None}[v]
                fila, creada = SesionAsistencia.objects.get_or_create(sesion=s, participacion=p, defaults={"asistio": valor})
                if creada:
                    n += valor is not None
                elif fila.asistio != valor:
                    fila.asistio = valor
                    fila.save()
                    n += 1
        messages.success(request, f"Asistencia de la sesión guardada ({n} cambios).")
        return HttpResponseRedirect(s.get_absolute_url())

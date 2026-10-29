"""Pantallas de actividades: listado, ficha con pestañas, crear y editar, programar, confirmar, cambiar estado,
participantes, asistencia, resultados, finalizar, sesiones, candidatos, constancia y calendario.
Cada vista revisa el permiso en el servidor; la lógica de reglas vive en servicios.py y reglas.py."""
from apps.nucleo.templatetags.fche import tono_estado
from apps.nucleo.utilidades import plural
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
from apps.nucleo.models import EstadoActividad, EstadoParticipacion, Modalidad, RolOrganizacion, RolParticipacion, TipoActividad
from apps.nucleo.duplicados import actividades_parecidas
from apps.nucleo.vistas_base import (
    AvisoDuplicadosMixin, EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, cambios_historial, nombre_comuna, nombre_organizacion,
    opciones_comunas, opciones_modelo, opciones_organizaciones,
)
from apps.organizaciones.models import Organizacion
from apps.personas.duplicados import candidatos_ficha_rapida
from apps.personas.models import Persona
from apps.proyectos.models import Proyecto
from apps.territorio.consultas import actividad_en_comuna, dirigida_a_comuna
from apps.territorio.destinos import fila_inicial, texto_destino
from apps.territorio.models import Comuna

from . import servicios
from .forms import (
    SerieForm, ActividadDesdeSolicitudForm, ActividadForm, BeneficiarioForm, EstadoForm, ParticipacionEditarForm, ParticipanteNuevoForm, PersonaRapidaForm, ProgramarForm, ResultadoForm, TareaForm,
    aviso_otro_rol, estado_inicial, roles_en_actividad,
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
        # F25: las tareas de proyectos se gestionan en su proyecto; aquí solo aparecen con esta casilla (o al filtrar por proyecto)
        Filtro("tareas", "Qué ver", "", lambda: [("no", "Solo actividades sueltas"), ("solo", "Solo tareas de proyectos")],
               aplicar=lambda qs, v: qs.filter(proyecto__isnull=True) if v == "no" else (qs.filter(proyecto__isnull=False) if v == "solo" else qs),
               principal=True, todos="Actividades y tareas"),
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
    template_name = "actividades/lista.html"  # F26 P1b: con el selector «Lista | Calendario»

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


class ActividadNueva(AvisoDuplicadosMixin, ComunaInicialMixin, Permiso403Mixin, CreateView):
    model = Actividad
    form_class = ActividadForm
    permission_required = "actividades.add_actividad"
    template_name = "generico/formulario.html"

    def solicitud(self):
        """F26 P1b: ?solicitud= rellena el formulario con la solicitud abierta (sin actividad) y al guardar la convierte."""
        if not hasattr(self, "_solicitud"):
            from apps.solicitudes.models import Solicitud

            pk = pk_seguro(self.request.GET.get("solicitud"))
            self._solicitud = (
                Solicitud.objects.select_related("estado", "persona", "organizacion", "proyecto")
                .filter(pk=pk, actividad__isnull=True, estado__codigo__in=("pendiente", "en_seguimiento")).first() if pk else None
            )
        return self._solicitud

    def get_form_class(self):
        return ActividadDesdeSolicitudForm if self.solicitud() else ActividadForm

    def solicitud_no_disponible(self):
        """?solicitud= de una solicitud ya convertida, descartada o con actividad: se vuelve a su ficha con un aviso."""
        if self.request.GET.get("solicitud") and not self.solicitud():
            messages.error(self.request, "La solicitud ya tiene una actividad, o fue convertida o descartada.")
            pk = pk_seguro(self.request.GET.get("solicitud"))
            return HttpResponseRedirect(reverse("solicitudes:ficha", args=[pk]) if pk else "/solicitudes")
        return None

    def get(self, request, *a, **kw):
        return self.solicitud_no_disponible() or super().get(request, *a, **kw)

    def post(self, request, *a, **kw):
        return self.solicitud_no_disponible() or super().post(request, *a, **kw)

    def get_initial(self):
        ini = super().get_initial()
        if self.request.GET.get("proyecto", "").isdigit():
            ini["proyecto"] = self.request.GET["proyecto"]
        if self.request.GET.get("padre", "").isdigit():
            ini["actividad_padre"] = int(self.request.GET["padre"])
        s = self.solicitud()
        if s:
            ini.update(nombre=s.titulo, descripcion=s.descripcion)
            if s.persona_id:
                ini["responsable"] = s.persona_id
            if s.proyecto_id:
                ini["proyecto"] = s.proyecto_id
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
        s = self.solicitud()
        if s:
            con = [x for x in (s.organizacion, s.persona) if x]
            ctx.update(
                titulo="Nueva actividad desde una solicitud", volver_url=s.get_absolute_url(),
                breadcrumb=[("Solicitudes", "/solicitudes"), (s.titulo, s.get_absolute_url())],
                bajada=(f"Viene de la solicitud «{s.titulo}»" + (f", con {' y '.join(str(x) for x in con)}" if con else "")
                        + (". La organización queda agregada con su persona de contacto" if s.organizacion_id else "")
                        + ". Al guardar, la solicitud queda convertida. Los campos marcados con * son obligatorios."),
            )
        return ctx

    def form_valid(self, form):
        from apps.documentos.origen import registrar_origen

        s = self.solicitud()
        d = form.cleaned_data
        aviso = self.aviso_duplicados(form, lambda: actividades_parecidas(d.get("nombre"), d.get("fecha"), d.get("proyecto")),
                                      "Esta actividad podría ya estar registrada.")
        if aviso:
            return aviso
        try:
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
                if s:
                    if d.get("fecha") and d.get("hora_inicio"):
                        servicios.programar(obj, self.request.user, d["fecha"], d["hora_inicio"], d.get("hora_fin"), d.get("lugar"))
                    convertir_solicitud(s, obj, self.request.user)
                servicios.asegurar_responsable_en_equipo(obj, self.request.user)  # F26 P2 [P]
                registrar_origen(obj, self.request.user)
        except ReglaNegocio as e:
            for m in e.mensajes:
                form.add_error(None, m)
            return self.form_invalid(form)
        if s:
            messages.success(self.request, "Actividad creada a partir de la solicitud, que queda convertida.")
        else:
            messages.success(self.request, "Actividad creada. Completa el resto de la información cuando puedas.")
        return HttpResponseRedirect(obj.get_absolute_url())


def convertir_solicitud(solicitud, actividad, usuario):
    """Liga la solicitud con su actividad (o tarea) y la deja «convertida». Si la solicitud tiene organización,
    esta queda en la actividad con la persona de contacto. Se llama dentro de la transacción que crea la actividad;
    vuelve a leer la solicitud con bloqueo para que nunca quede con dos actividades."""
    from apps.actividades.models import ActividadOrganizacion
    from apps.nucleo.models import EstadoSolicitud
    from apps.solicitudes.models import Solicitud

    s = Solicitud.objects.select_for_update().get(pk=solicitud.pk)
    if s.actividad_id:
        raise ReglaNegocio("La solicitud ya tiene una actividad asociada.")
    if s.organizacion_id and not ActividadOrganizacion.objects.filter(actividad=actividad, organizacion_id=s.organizacion_id).exists():
        from apps.personas.vinculos import vincular_contacto

        ActividadOrganizacion.objects.create(actividad=actividad, organizacion_id=s.organizacion_id, contacto_id=s.persona_id)
        vincular_contacto(s.persona, s.organizacion)  # F26 P2: la persona de contacto queda vinculada a la organización
    s.actividad = actividad
    s.estado = EstadoSolicitud.objects.get(codigo="convertida")
    s.save()
    registrar(usuario, "solicitud_convertida_actividad", s, actividad.nombre)
    return s


class TareaNueva(AvisoDuplicadosMixin, Permiso403Mixin, CreateView):
    """F25: «+ Nueva tarea» desde el proyecto. Crea en una transacción la actividad con proyecto, su programación
    (si hay fecha y hora) y su destino (comunidad y su territorio). Si una regla impide programar, no se guarda nada."""

    model = Actividad
    form_class = TareaForm
    permission_required = "actividades.add_actividad"
    template_name = "generico/formulario.html"

    def dispatch(self, request, *a, **kw):
        self.proyecto = get_object_or_404(Proyecto, pk=kw["proyecto_pk"])
        return super().dispatch(request, *a, **kw)

    def solicitud(self):
        """F26 P1b: ?solicitud= de una solicitud convertida en este proyecto y aún sin actividad: la tarea queda ligada a ella."""
        if not hasattr(self, "_solicitud"):
            from apps.solicitudes.models import Solicitud

            pk = pk_seguro(self.request.GET.get("solicitud"))
            self._solicitud = Solicitud.objects.filter(pk=pk, proyecto=self.proyecto, actividad__isnull=True).exclude(
                estado__codigo="descartada").first() if pk else None
        return self._solicitud

    def get_initial(self):
        ini = super().get_initial()
        s = self.solicitud()
        if s:
            ini.update(nombre=s.titulo, descripcion=s.descripcion)
        return ini

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        url = self.proyecto.get_absolute_url()
        s = self.solicitud()
        ctx.update(titulo="Nueva tarea", volver_url=s.get_absolute_url() if s else f"{url}?tab=actividades",
                   breadcrumb=[("Proyectos", "/proyectos"), (str(self.proyecto), url), ("Tareas", f"{url}?tab=tareas")],
                   bajada=f"Tarea del proyecto «{self.proyecto}»"
                   + (f", a partir de la solicitud «{s.titulo}», que quedará ligada a ella" if s else "")
                   + ". Los campos marcados con * son obligatorios.")
        return ctx

    def form_valid(self, form):
        from apps.documentos.origen import registrar_origen

        d = form.cleaned_data
        aviso = self.aviso_duplicados(form, lambda: actividades_parecidas(d.get("nombre"), d.get("fecha"), self.proyecto),
                                      "Esta tarea podría ya estar registrada.")
        if aviso:
            return aviso
        try:
            with transaction.atomic():
                obj = form.save(commit=False)
                obj.proyecto = self.proyecto
                obj.creado_por = self.request.user
                obj.estado = EstadoActividad.objects.get(codigo="pendiente")
                obj.save()
                form.save_m2m()
                comunidad = d.get("comunidad")
                if comunidad:
                    ActividadComunidad.objects.create(actividad=obj, comunidad=comunidad)
                    if comunidad.sector_id:
                        ActividadTerritorio.objects.create(actividad=obj, sector=comunidad.sector)
                    elif comunidad.comuna_id:
                        ActividadTerritorio.objects.create(actividad=obj, comuna=comunidad.comuna)
                if d.get("fecha") and d.get("hora_inicio"):
                    servicios.programar(obj, self.request.user, d["fecha"], d["hora_inicio"], d.get("hora_fin"), d.get("lugar"))
                if self.solicitud():
                    convertir_solicitud(self.solicitud(), obj, self.request.user)
                servicios.asegurar_responsable_en_equipo(obj, self.request.user)  # F26 P2 [P]
                registrar_origen(obj, self.request.user)
        except ReglaNegocio as e:
            for m in e.mensajes:
                form.add_error(None, m)
            return self.form_invalid(form)
        messages.success(self.request, "Tarea creada. Agrega a sus participantes desde su ficha.")
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
            respuesta = super().form_valid(form)
            if respuesta.status_code == 302:  # F26 P2 [P]: guardado (sin conflicto de versión): el responsable, en el equipo
                servicios.asegurar_responsable_en_equipo(self.object, self.request.user)
            return respuesta


# F25 F1: una tarea (actividad con proyecto) se gestiona en un solo lugar, con ocho pestañas. Agenda, Público,
# Coordinación, Alcance y Origen no son pestañas: su contenido está en Información, Cierre o Historial, y sus
# direcciones antiguas (?tab=agenda…) abren la pestaña equivalente.
# F26 P3a: la actividad suelta (sin proyecto) usa las mismas ocho pestañas. Coordinación (interacciones, invitaciones,
# solicitudes de apoyo, reuniones) queda como sección de Información, solo en las sueltas; Alcance va en Cierre.
PESTANAS_TAREA = [
    ("info", "Información", "actividades/pestanas/info.html"),
    ("participantes", "Equipo y asistencia", "actividades/pestanas/participantes.html"),
    ("beneficiarios", "Beneficiarios", "actividades/pestanas/beneficiarios.html"),
    ("organizaciones", "Organizaciones", "generico/_hijos.html"),
    ("sesiones", "Sesiones", "actividades/pestanas/sesiones.html"),
    ("resultados", "Cierre", "actividades/pestanas/resultados.html"),
    ("documentos", "Documentos", "documentos/pestanas/lista.html", "documentos.view_documento"),
    ("historial", "Historial", "actividades/pestanas/historial.html", "actividades.view_historicalactividad"),
]
ALIAS_TAREA = {"agenda": "info", "publico": "info", "coordinacion": "info", "alcance": "resultados", "origen": "historial", "asistencia": "participantes"}
GRUPOS_EQUIPO_TAREA = [
    ("ejecutor", "Equipo ejecutor", "Quienes realizan la tarea (tallerista, voluntario, estudiante, coordinador…). Se separan por el rol."),
    ("contacto", "Invitados y contactos", "Autoridades, invitados y contactos de las organizaciones."),
]
GRUPOS_PASAR_LISTA = [("ejecutor", "Equipo ejecutor"), ("contacto", "Invitados y contactos"), ("asistente", "Beneficiarios")]  # F26 P1a


class ActividadFicha(FichaBase):
    model = Actividad
    permission_required = "actividades.view_actividad"
    template_name = "actividades/ficha.html"
    breadcrumb = [("Actividades", "/actividades")]
    permiso_editar = "actividades.change_actividad"
    pestanas = PESTANAS_TAREA  # F26 P3a: actividad suelta y tarea, las mismas ocho pestañas
    alias_pestanas = ALIAS_TAREA

    def get_queryset(self):
        return super().get_queryset().select_related("proyecto", "tipo", "estado", "modalidad", "responsable", "actividad_padre")

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.fijar_agenda_vigente()  # F26 Rb: la cabecera, las reglas y las pestañas la leían hasta nueve veces
        return obj

    @property
    def es_tarea(self):
        """Una actividad con proyecto es una tarea, se abra por /actividades/<id> o dentro de su proyecto."""
        return bool(self.object.proyecto_id)

    def pestanas_visibles(self):
        u = self.request.user  # Beneficiarios se ve siempre (no depende de la segunda fase)
        return [p for p in PESTANAS_TAREA if len(p) < 4 or u.has_perm(p[3])]

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        p = self.object.proyecto
        if p:  # F25: una actividad con proyecto es una tarea del proyecto
            url = p.get_absolute_url()
            ctx["breadcrumb"] = [("Proyectos", "/proyectos"), (str(p), url), ("Tareas", f"{url}?tab=tareas")]
            ctx["tipo_ficha"] = "Tarea"
            ctx["texto_editar"] = "Editar tarea"
        return ctx

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
            "estados_siguientes": self.estados_siguientes(siguientes) if u.has_perm("actividades.change_actividad") else [],
            "antes_de_fecha": antes_de_la_fecha(a),
            "puede_asistencia": u.has_perm("actividades.change_participacion") and codigo not in ("cancelada", "pendiente", "suspendida") and not antes_de_la_fecha(a),
            "puede_resultado": u.has_perm("actividades.change_actividad") and codigo not in ("cancelada", "pendiente", "suspendida") and not antes_de_la_fecha(a),
            "puede_finalizar": u.has_perm("actividades.cerrar_actividad") and "realizada" in TRANSICIONES.get(codigo, set()) and not antes_de_la_fecha(a),
            "puede_reabrir": u.has_perm("actividades.reabrir_actividad") and codigo == "realizada",
            "agenda": agenda,
            "faltantes": a.faltantes(),
            "comuna_ficha": self.comuna_de_la_actividad(agenda),
            "es_tarea": self.es_tarea,
        }

    @staticmethod
    def estados_siguientes(codigos):
        """[(código, nombre)] en el mismo orden, con una sola consulta (antes, una por estado)."""
        nombres = dict(EstadoActividad.objects.filter(codigo__in=codigos).values_list("codigo", "nombre"))
        return [(c, nombres[c]) for c in codigos if c in nombres]

    def comuna_de_la_actividad(self, agenda):
        """Comuna del lugar programado; si no hay, la del primer territorio vigente que sea una comuna o un sector. A lo más dos consultas."""
        if agenda and agenda.lugar_id:
            return Comuna.objects.filter(direcciones__pk=agenda.lugar.direccion_id).first()
        territorio = (
            self.object.territorios.filter(Q(comuna__isnull=False) | Q(sector__isnull=False), vigente=True)
            .select_related("comuna", "sector__comuna").order_by("pk").first()
        )
        return (territorio.comuna or territorio.sector.comuna) if territorio else None

    def _participaciones_con_procedencia(self, *prefetch_extra):
        """Participaciones con persona, rol, estado y procedencia precargados: consultas fijas, sin importar cuántas sean."""
        from apps.comunidades.models import ComunidadMiembro
        from apps.personas.models import PersonaFormacion, PersonaOrganizacion

        hoy = timezone.localdate()
        qs = self.object.participaciones.select_related("persona", "rol", "estado", "institucion", "comunidad").prefetch_related(
            Prefetch("persona__formaciones", queryset=PersonaFormacion.objects.filter(vigente=True).select_related("organizacion", "sede_institucion", "carrera")
                     .order_by("-anio_inicio", "-pk"), to_attr="formaciones_vigentes"),
            # F26 P2: todos los vínculos vigentes (con o sin cargo), para calcular la procedencia que falte
            Prefetch("persona__vinculos", queryset=PersonaOrganizacion.objects.filter(Q(fecha_termino__isnull=True) | Q(fecha_termino__gte=hoy))
                     .select_related("organizacion", "rol").order_by("-fecha_inicio", "-pk"), to_attr="cargos_vigentes"),
            Prefetch("persona__comunidades", queryset=ComunidadMiembro.objects.filter(vigente=True).select_related("comunidad").order_by("-pk"),
                     to_attr="comunidades_vigentes"),
            *prefetch_extra,
        )
        partes = list(qs)
        for p in partes:
            p.procedencia = self._procedencia(p)
        return partes

    @staticmethod
    def _procedencia(p):
        """F25 E4: organización (con su sede y carrera si estudia ahí, o su cargo si trabaja ahí) y comunidad, para la tabla.
        F26 P2: si la participación no las tiene, se calculan desde los vínculos vigentes de la persona (formación,
        organización y padrón) y se marcan como «calculada». Usa lo ya precargado: sin consultas."""
        persona = p.persona
        institucion, inst_calculada = p.institucion if p.institucion_id else None, False
        if institucion is None:
            origen = next(iter(persona.formaciones_vigentes), None) or next(iter(persona.cargos_vigentes), None)
            institucion, inst_calculada = (origen.organizacion, True) if origen else (None, False)
        comunidad, com_calculada = p.comunidad if p.comunidad_id else None, False
        if comunidad is None and persona.comunidades_vigentes:
            comunidad, com_calculada = persona.comunidades_vigentes[0].comunidad, True
        formacion, cargo = None, ""
        if institucion is not None:
            formacion = next((f for f in persona.formaciones_vigentes if f.organizacion_id == institucion.pk), None)
            cargo = next((v.cargo or (str(v.rol) if v.rol_id else "") for v in persona.cargos_vigentes
                          if v.organizacion_id == institucion.pk and (v.cargo or v.rol_id)), "")
        return {"institucion": institucion, "comunidad": comunidad, "institucion_calculada": inst_calculada,
                "comunidad_calculada": com_calculada, "formacion": formacion, "cargo": cargo}

    def _pasar_lista(self, todas):
        """F26 P1a: «Pasar lista», un solo formulario con todas las participaciones no erróneas, por grupo. Una consulta más
        (quiénes tienen la asistencia calculada desde las sesiones), sin importar cuántas sean."""
        lista = [p for p in todas if p.estado.codigo != "registro_erroneo"]
        grupos = [(etiqueta, [p for p in lista if p.rol.grupo == clave]) for clave, etiqueta in GRUPOS_PASAR_LISTA]
        return {"con_lista": True, "grupos_lista": [g for g in grupos if g[1]], "total_lista": len(lista),
                "calculadas_sesiones": servicios.participaciones_con_sesiones(self.object) if lista else set()}

    def ctx_participantes(self):
        """F25 F2 y F26 P3a: «Equipo y asistencia» (en la tarea y en la actividad suelta); los asistentes van en Beneficiarios."""
        todas = self._participaciones_con_procedencia()
        lista = self._pasar_lista(todas)
        partes = [p for p in todas if p.rol.grupo != "asistente"]
        que = "la tarea" if self.es_tarea else "la actividad"
        grupos = [(etiqueta, [p for p in partes if p.rol.grupo == clave], ayuda.replace("la tarea", que)) for clave, etiqueta, ayuda in GRUPOS_EQUIPO_TAREA]
        return {"participaciones": partes, "grupos_participacion": [g for g in grupos if g[1]], "grupo": "integrantes del equipo ni invitados",
                "titulo_pestana": "Equipo y asistencia", "capacidad_alerta": None, **lista}

    def ctx_publico(self):
        a = self.object
        pk = a.pk
        destinos = a.comunidades_destino.select_related("comunidad__comuna", "comunidad__sector")
        return {
            "destinos": [{
                "texto": str(d.comunidad), "url": d.comunidad.get_absolute_url(), "detalle": " · ".join(x for x in [d.comunidad.territorio, f"{d.beneficiarios_estimados} beneficiarios estimados" if d.beneficiarios_estimados else "", d.observaciones] if x),
                "vigente": d.vigente, "url_editar": reverse("actividades:comunidades_editar", args=[pk, d.pk]), "url_alternar": reverse("actividades:comunidades_alternar", args=[pk, d.pk]),
            } for d in destinos],
            "url_nueva_comunidad": reverse("actividades:comunidades_nuevo", args=[pk]),
        }

    def ctx_alcance(self):
        from .alcance import alcance

        return {"alcance": alcance([self.object]), "contexto_alcance": "esta actividad"}

    def ctx_beneficiarios(self):
        """F25 F2: los asistentes de la tarea (rol del grupo «Asistentes»), con su edad y, para quien puede ver datos
        sensibles, el apoderado o contacto de emergencia de los menores. Consultas fijas."""
        from apps.personas.models import ContactoEmergencia

        sensibles = self.request.user.has_perm("personas.ver_sensibles")
        extra = [Prefetch("persona__contactos_emergencia", queryset=ContactoEmergencia.objects.filter(vigente=True).order_by("pk"),
                          to_attr="emergencias")] if sensibles else []
        partes = [p for p in self._participaciones_con_procedencia(*extra) if p.rol.grupo == "asistente"]
        return {"beneficiarios": partes, "ver_sensibles": sensibles, "capacidad_alerta": self._capacidad(),
                "calculadas_sesiones": servicios.participaciones_con_sesiones(self.object) if partes else set(),
                "url_registrar_beneficiario": url_agregar_persona(self.object, rol="beneficiario", volver="beneficiarios",
                                                                  llego=BeneficiarioRegistrar._llego(self.object)),
                "puede_registrar_beneficiario": (self.request.user.has_perm("actividades.add_participacion") and self.request.user.has_perm("personas.add_persona")
                                                 and self.object.estado.codigo not in ("cancelada", "realizada"))}

    def _capacidad(self):
        ag = self.object.agenda_vigente
        if ag and ag.lugar and ag.lugar.capacidad is not None:
            from .reglas import personas_que_ocupan

            from django.conf import settings

            partes = list(self.object.participaciones.select_related("estado", "rol"))
            activas = [p for p in partes if p.activa]
            n = len(personas_que_ocupan(self.object, activas))
            fuera = set(getattr(settings, "ROLES_FUERA_DE_CAPACIDAD", []))
            participaciones = sum(1 for p in activas if p.rol.codigo not in fuera)  # F25 E10: quien tiene varios roles ocupa un cupo
            espera = sum(1 for p in partes if p.en_espera)
            return {"n": n, "capacidad": ag.lugar.capacidad, "excede": n > ag.lugar.capacidad, "lleno": n >= ag.lugar.capacidad, "espera": espera,
                    "participaciones": participaciones}
        return None

    def ctx_info(self):
        """F25 F1: Información reúne además el público, las comunidades y la fecha con sus cambios. F26 P3a: en la actividad
        suelta, también la coordinación (antes su propia pestaña), para quien puede ver las interacciones."""
        ctx = {**self._ctx_info(), **self.ctx_publico(), **self.ctx_agenda()}
        if not self.es_tarea and self.request.user.has_perm("coordinacion.view_interaccion"):
            ctx.update(self.ctx_coordinacion(), mostrar_coordinacion=True)
        return ctx

    def _ctx_info(self):
        return {
            "territorios": [
                {"texto": texto_destino(t), "vigente": t.vigente, "url_editar": reverse("actividades:territorios_editar", args=[self.object.pk, t.pk]), "url_alternar": reverse("actividades:territorios_alternar", args=[self.object.pk, t.pk]), "detalle": ""}
                for t in self.object.territorios.select_related("region", "provincia", "comuna", "sector__comuna")
            ],
            "hijas": self.object.hijas.select_related("estado"),
        }

    def ctx_organizaciones(self):
        from django.db.models import Count

        pk = self.object.pk
        trajo = dict(  # F25 E4: personas distintas que vienen de cada organización, en una consulta
            self.object.participaciones.exclude(estado__codigo="registro_erroneo").filter(institucion__isnull=False)
            .values("institucion_id").annotate(n=Count("persona_id", distinct=True)).values_list("institucion_id", "n")
        )

        def texto_trajo(org_id):
            n = trajo.get(org_id, 0)
            return f"trajo {n} persona" + ("" if n == 1 else "s") if n else ""

        # Detalle de las personas que trajo cada organización: rol, carrera, sede, estado y asistencia (consultas fijas)
        from django.db.models import Prefetch

        from apps.personas.models import PersonaFormacion

        personas_de = {}
        parts = (self.object.participaciones.exclude(estado__codigo="registro_erroneo").filter(institucion__isnull=False)
                 .select_related("persona", "rol", "estado")
                 .prefetch_related(Prefetch("persona__formaciones", queryset=PersonaFormacion.objects.filter(vigente=True)
                                            .select_related("carrera", "sede_institucion"), to_attr="formaciones_v")))
        for p in parts:
            f = next((x for x in p.persona.formaciones_v if x.organizacion_id == p.institucion_id), None)
            asistio = {True: "asistió", False: "no asistió"}.get(p.asistencia, "")
            datos = " · ".join(x for x in [p.rol_y_cargo, f.carrera.nombre if f and f.carrera_id else "", str(f.sede_institucion) if f and f.sede_institucion_id else "",
                                            str(p.estado), asistio] if x)
            personas_de.setdefault(p.institucion_id, []).append((str(p.persona), datos, p.persona.get_absolute_url()))

        hijos = [{
            "texto": f"{o.organizacion}" + (f" · {o.tipo_intervencion}" if o.tipo_intervencion else ""), "url": o.organizacion.get_absolute_url(),
            "detalle": " · ".join(x for x in [texto_trajo(o.organizacion_id), f"Contacto: {o.contacto}" if o.contacto else "", o.observaciones] if x), "vigente": o.vigente,
            "url_editar": reverse("actividades:organizaciones_editar", args=[pk, o.pk]), "url_alternar": reverse("actividades:organizaciones_alternar", args=[pk, o.pk]),
            "ficha": personas_de.get(o.organizacion_id) or None,
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

    def ctx_documentos(self):
        u = self.request.user
        docs = self.object.documentos.select_related("tipo")
        if not u.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        pk = self.object.pk
        return {"documentos": docs, "titulo_documentos": "Documentos y evidencias", "sin_contador_documentos": True,
                "url_nuevo_doc": f"/documentos/nuevo?actividad={pk}", "url_asociar_doc": f"/documentos/asociar?actividad={pk}"}

    def ctx_resultados(self):
        a = self.object
        sin_asistencia = [p for p in a.participaciones.select_related("estado") if p.activa and p.asistencia is None]
        ctx = {"form_resultado": ResultadoForm(instance=a), "finalizada": a.estado.codigo == "realizada", "sin_asistencia": len(sin_asistencia)}
        if self.request.user.has_perm("actividades.view_participacion"):  # F26 P3a: el alcance (antes su pestaña) va en Cierre
            ctx.update(self.ctx_alcance(), mostrar_alcance=True)
        return ctx

    def ctx_origen(self):
        from apps.documentos.origen import contexto_origen

        return contexto_origen(self.object, self.request.user)

    def ctx_historial(self):
        from apps.actividades.models import Participacion as P

        hist = P.history.filter(actividad_id=self.object.pk).select_related("history_user", "persona", "estado").order_by("-history_date")[:40]
        ctx = {"cambios": cambios_historial(self.object), "cambios_participacion": hist, "agendas": self.object.agendas.select_related("lugar", "creado_por")}
        if self.request.user.has_perm("documentos.view_origendato"):
            ctx.update(self.ctx_origen(), mostrar_origen=True)  # F25 F1: el origen de los datos va al final del historial
        return ctx


# --- Acciones ---------------------------------------------------------------------
class TareaFicha(ActividadFicha):
    """La ficha de una tarea vista dentro de su proyecto (/proyectos/<id>/tareas/<id>): la misma ficha de actividad,
    pero solo si la tarea pertenece a ese proyecto."""

    def get_queryset(self):
        return super().get_queryset().filter(proyecto_id=self.kwargs["proyecto_pk"])


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
            messages.warning(request, f"{plural(len(sin), 'participante quedó', 'participantes quedaron')} sin registro de asistencia. Puedes completarlo en la pestaña Participantes.")
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


def _pestana_de(a, p, defecto="participantes"):
    """F25 F2: en una tarea, quien asiste (rol del grupo «Asistentes») está en Beneficiarios; el resto, en «Equipo y asistencia»."""
    if a.proyecto_id:
        return "beneficiarios" if p.rol.grupo == "asistente" else "participantes"
    return defecto


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
        return self.volver(p.actividad, _pestana_de(p.actividad, p))


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


def _aplicar_grupo(participacion, organizacion=None, cargo="", comunidad=None, rol_organizacion=None):
    """F25: «¿De qué grupo viene?». La organización y la comunidad quedan como procedencia de la participación, y además
    (F26 P2: con `vincular()`, la única puerta) el vínculo de la persona con la organización, con su cargo y su rol (o su
    formación, si es estudiante en una institución educativa) y su lugar en el padrón de la comunidad, si no existían.
    Se llama dentro de la transacción que crea la participación; nunca duplica."""
    from apps.personas.vinculos import vincular

    if organizacion:
        participacion.institucion = organizacion
    if comunidad:
        participacion.comunidad = comunidad
    if organizacion or comunidad:
        vincular(participacion.persona, organizacion=organizacion, comunidad=comunidad, cargo=cargo,
                 rol=rol_organizacion or participacion.rol, desde=timezone.localdate())
        participacion.save(update_fields=["institucion", "comunidad"])
    servicios.asegurar_organizacion(participacion)  # F25 E4: también si la institución se completó sola con la formación


def url_agregar_persona(a, rol=None, estado=None, organizacion=None, comunidad=None, llego=False, volver=None):
    """F26 P1a: dirección del único «+ Agregar persona», con lo que se quiere dejar prellenado. `rol` acepta el id o el código."""
    from urllib.parse import urlencode

    params = {"rol": getattr(rol, "pk", rol), "estado": getattr(estado, "pk", estado), "organizacion": getattr(organizacion, "pk", organizacion),
              "comunidad": getattr(comunidad, "pk", comunidad), "llego": "1" if llego else None, "volver": volver}
    params = {k: v for k, v in params.items() if v not in (None, "")}
    url = reverse("actividades:participante_nuevo", args=[a.pk])
    return f"{url}?{urlencode(params)}" if params else url


def _registrar_apoderado(request, persona, d, motivo):
    """El apoderado o contacto de emergencia escrito en el bloque «Si es menor de edad» (dato restringido). Sin duplicar."""
    from apps.personas.models import ContactoEmergencia

    nombre = (d.get("apoderado_nombre") or "").strip()
    if not (nombre and d.get("apoderado_telefono")):
        return
    ContactoEmergencia.objects.get_or_create(persona=persona, nombre=nombre, telefono=d["apoderado_telefono"],
                                             defaults={"parentesco": (d.get("apoderado_parentesco") or "").strip()})
    registrar(request.user, "contacto_emergencia_registrado", persona, motivo)


class ParticipanteNuevo(_AccionActividad):
    """F26 P1a: el único «+ Agregar persona» de la actividad o tarea (equipo, invitados y beneficiarios). «Guardar y agregar
    otra» vuelve al formulario con el rol, el estado y el grupo prellenados. ?rol=<id o código>, ?estado, ?organizacion,
    ?comunidad, ?llego=1 y ?volver=beneficiarios prellenan el formulario."""

    permission_required = "actividades.add_participacion"

    def _ctx(self, a, form, volver):
        url = a.get_absolute_url()
        tab = "beneficiarios" if volver == "beneficiarios" else "participantes"
        return {
            "form": form, "titulo": "Agregar persona", "actividad": a, "volver": tab,
            "volver_url": f"{url}?tab={tab}", "breadcrumb": [(a.nombre, url)],
            "bajada": "Solo la persona, el rol y el estado son obligatorios. Si la persona no está en el buscador, «+ Crear persona» abre la ficha rápida.",
        }

    @staticmethod
    def _permitir_llego(a):
        return a.estado.codigo not in ("cancelada", "pendiente", "suspendida") and not antes_de_la_fecha(a)

    def _form(self, a, data=None, initial=None):
        return ParticipanteNuevoForm(data, actividad=a, initial=initial, puede_sensibles=self.request.user.has_perm("personas.ver_sensibles"),
                                     permitir_llego=self._permitir_llego(a) or bool(data and data.get("llego")) or bool(initial and initial.get("llego")))

    def _inicial(self, a):
        g = self.request.GET
        rol = g.get("rol", "")
        rol_pk = pk_seguro(rol) or (RolParticipacion.objects.filter(codigo=rol, activo=True).values_list("pk", flat=True).first() if rol else None)
        inicial = {"rol": rol_pk, "organizacion": pk_seguro(g.get("organizacion")), "comunidad": pk_seguro(g.get("comunidad"))}
        estado = pk_seguro(g.get("estado"))
        if g.get("llego") == "1":
            inicial["llego"] = True
            estado = EstadoParticipacion.objects.filter(codigo="asistio").values_list("pk", flat=True).first()
        inicial["estado"] = estado
        return {k: v for k, v in inicial.items() if v}

    def get(self, request, pk):
        a = self.actividad(pk)
        return render(request, "actividades/participante_form.html", self._ctx(a, self._form(a, initial=self._inicial(a)), request.GET.get("volver")))

    def post(self, request, pk):
        a = self.actividad(pk)
        llego = request.POST.get("llego") in ("1", "on", "true")
        volver = request.POST.get("volver")
        if not _puede_sumar_participante(request, a, llego):
            return self.volver(a, "participantes")
        form = self._form(a, request.POST)
        if form.is_valid():
            d = form.cleaned_data
            p = form.save(commit=False)
            p.actividad = a
            p.creado_por = request.user
            if llego:  # RE-02: llegó sin estar previsto
                p.asistencia = True
                p.estado = estado_inicial(llego=True)
            with transaction.atomic():
                p.save()
                _aplicar_grupo(p, d.get("organizacion"), d.get("cargo"), d.get("comunidad"), d.get("rol_organizacion"))
                _perfil_del_rol(p.persona, p.rol)
                if form.puede_sensibles:
                    _registrar_apoderado(request, p.persona, d, "apoderado o contacto de emergencia, al agregarla a una actividad")
            messages.success(request, f"{p.persona} agregada como {p.rol.nombre.lower()}" + (" y marcada como asistente." if llego else "."))
            _avisar_capacidad(request, a)
            if a.estado.codigo == "realizada":
                registrar(request.user, "registro_tardio", p, "persona que llegó, agregada después de finalizar")
            if request.POST.get("otra") == "1":  # «Guardar y agregar otra»: mismo rol, estado y grupo
                return HttpResponseRedirect(url_agregar_persona(a, rol=p.rol_id, estado=d.get("estado"), organizacion=d.get("organizacion"),
                                                                comunidad=d.get("comunidad"), llego=llego, volver=volver))
            from apps.nucleo.fases import modulo_activo

            return self.volver(a, _pestana_de(a, p, "beneficiarios" if p.es_beneficiario and modulo_activo("beneficiarios") and not llego else "participantes"))
        return render(request, "actividades/participante_form.html", self._ctx(a, form, volver), status=400)


class ParticipanteRapido(_AccionActividad):
    """Buscar → seleccionar; si no existe, crear aquí mismo y queda agregada, sin salir de la actividad."""

    permission_required = "personas.add_persona"

    def _ctx(self, a, form, cands=None):
        llego = (self.request.GET.get("llego") or self.request.POST.get("llego")) == "1"
        return {"form": form, "titulo": "Crear persona que llegó" if llego else "Crear persona y agregarla", "volver_url": f"{a.get_absolute_url()}?tab=participantes", "breadcrumb": [(a.nombre, a.get_absolute_url())], "candidatos": cands, "actividad": a, "llego": llego}

    def get(self, request, pk):
        """F26 P1a: la pantalla es ahora el único «+ Agregar persona» (su buscador crea la persona con la ficha rápida).
        Los envíos a esta ruta se siguen atendiendo."""
        a = self.actividad(pk)
        return HttpResponseRedirect(url_agregar_persona(a, llego=request.GET.get("llego") == "1"))

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
            cands = candidatos_ficha_rapida(d)
            if cands:
                return render(request, "actividades/participante_rapido.html", self._ctx(a, form, cands))
        from apps.personas.servicios import crear_persona_rapida

        llego = request.POST.get("llego") == "1"
        with transaction.atomic():
            persona = crear_persona_rapida(form, request.user)  # la ficha rápida única: queda «incompleto», con contactos y comuna
            p = Participacion.objects.create(
                actividad=a, persona=persona, rol=d["rol"], creado_por=request.user, asistencia=True if llego else None, estado=estado_inicial(llego),
                cargo=(d.get("cargo") or "").strip(),
            )
            _aplicar_grupo(p, d.get("organizacion"), d.get("cargo"), d.get("comunidad"), d.get("rol_organizacion"))
            _perfil_del_rol(persona, d["rol"])
        messages.success(request, f"{persona} creada y agregada. Completa su ficha cuando puedas.")
        _avisar_capacidad(request, a)
        return self.volver(a, _pestana_de(a, p))


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
        from apps.comunidades.models import Comunidad

        roles = roles_en_actividad(a, persona, rol)
        ya_con_ese_rol = Participacion.objects.filter(actividad=a, persona=persona, rol=rol).exists()
        if roles and not ya_con_ese_rol and not request.POST.get("otro_rol"):  # F25 E3: ya participa con otro rol: se pide confirmar
            campos = {c: request.POST.get(c, "") for c in ("rol", "llego", "organizacion", "cargo", "rol_organizacion", "comunidad")}
            return render(request, "actividades/participante_otro_rol.html", {
                "titulo": f"Agregar a {persona}", "aviso": aviso_otro_rol(persona, roles, rol), "campos": campos, "actividad": a,
                "volver_url": f"{a.get_absolute_url()}?tab=participantes", "breadcrumb": [(a.nombre, a.get_absolute_url())],
            }, status=400)
        with transaction.atomic():
            obj, creada = Participacion.objects.get_or_create(
                actividad=a, persona=persona, rol=rol,
                defaults={"estado": estado_inicial(llego), "creado_por": request.user, "asistencia": True if llego else None,
                          "cargo": request.POST.get("cargo", "").strip()[:120]},
            )
            if creada:  # lo que se alcanzó a escribir en «¿De qué grupo viene?» también vale para la persona existente
                org = Organizacion.objects.filter(pk=pk_seguro(request.POST.get("organizacion")) or 0).first()
                comunidad = Comunidad.objects.filter(pk=pk_seguro(request.POST.get("comunidad")) or 0, activo=True).first()
                rol_org = RolOrganizacion.objects.filter(pk=pk_seguro(request.POST.get("rol_organizacion")) or 0).first()
                _aplicar_grupo(obj, org, request.POST.get("cargo", "")[:120], comunidad, rol_org)
            _perfil_del_rol(persona, rol)
        messages.success(request, f"{persona} agregada." if creada else f"{persona} ya participaba con ese rol.")
        _avisar_capacidad(request, a)
        return self.volver(a, _pestana_de(a, obj))


class BeneficiarioRegistrar(_AccionActividad):
    """F25 F2: «+ Registrar beneficiario» de una tarea. La ficha rápida única, el rol (Beneficiario o Participante), su grupo
    (organización con cargo, comunidad) y, si es menor de edad, su apoderado o contacto de emergencia (dato restringido:
    solo para quien tiene personas.ver_sensibles). Primero busca si la persona ya existe: «Usar esta persona» la agrega sin
    duplicarla. Desde el día de la tarea queda «Asistió»; antes, «Inscrito». Todo se guarda junto o no se guarda."""

    permission_required = ("actividades.add_participacion", "personas.add_persona")
    CAMPOS_PARTICIPACION = {"rol", "cargo", "organizacion", "comunidad", *BeneficiarioForm.CAMPOS_MENOR}

    def _form(self, data=None):
        return BeneficiarioForm(data, puede_sensibles=self.request.user.has_perm("personas.ver_sensibles"))

    def _ctx(self, a, form, cands=None, aviso_otro_rol=None, usar=None):
        url = a.get_absolute_url()
        llega = self._llego(a)
        return {
            "form": form, "titulo": "Registrar beneficiario", "actividad": a, "candidatos": cands, "aviso_otro_rol": aviso_otro_rol, "usar": usar,
            "volver_url": f"{url}?tab=beneficiarios", "breadcrumb": [(a.nombre, url), ("Beneficiarios", f"{url}?tab=beneficiarios")],
            "bajada": ("Quedará como «Asistió», porque la tarea ya ocurrió o es hoy." if llega else "Quedará «Inscrito»; la asistencia se marca desde el día de la tarea.")
                      + " Solo el nombre es obligatorio.",
        }

    @staticmethod
    def _llego(a):
        """La regla que habilita marcar la asistencia (puede_asistencia), y además la tarea debe tener fecha: sin fecha
        no hay «día de la tarea», así que queda «Inscrito»."""
        return (a.estado.codigo not in ("cancelada", "pendiente", "suspendida") and a.agenda_vigente is not None
                and not antes_de_la_fecha(a))

    def get(self, request, pk):
        """F26 P1a: la pantalla es ahora el único «+ Agregar persona», con el rol Beneficiario elegido. Los envíos a esta
        ruta se siguen atendiendo."""
        a = self.actividad(pk)
        return HttpResponseRedirect(url_agregar_persona(a, rol="beneficiario", volver="beneficiarios", llego=self._llego(a)))

    def post(self, request, pk):
        from apps.personas.servicios import crear_persona_rapida

        a = self.actividad(pk)
        llego = self._llego(a)
        if not _puede_sumar_participante(request, a, llego):
            return self.volver(a, "beneficiarios")
        form = self._form(request.POST)
        valido = form.is_valid()
        persona = None
        usar = pk_seguro(request.POST.get("usar_persona"))
        if usar:  # «Usar esta persona»: los datos de la ficha rápida no se vuelven a crear; valen el rol, el grupo y el apoderado
            persona = get_object_or_404(Persona, pk=usar)
            if any(c in form.errors for c in self.CAMPOS_PARTICIPACION):
                return render(request, "actividades/beneficiario_form.html", self._ctx(a, form, usar=persona), status=400)
            rol = form.cleaned_data["rol"]
            if Participacion.objects.filter(actividad=a, persona=persona, rol=rol).exists():
                messages.info(request, f"{persona} ya estaba registrada como {rol.nombre.lower()}.")
                return self.volver(a, "beneficiarios")
            roles = roles_en_actividad(a, persona, rol)
            if roles and not request.POST.get("otro_rol"):  # F25 E3: ya participa con otro rol: se pide confirmar
                return render(request, "actividades/beneficiario_form.html",
                              self._ctx(a, form, aviso_otro_rol=aviso_otro_rol(persona, roles, rol), usar=persona), status=400)
        elif not valido:
            return render(request, "actividades/beneficiario_form.html", self._ctx(a, form), status=400)
        elif not request.POST.get("confirmar_duplicado"):
            cands = candidatos_ficha_rapida(form.cleaned_data)
            if cands:
                return render(request, "actividades/beneficiario_form.html", self._ctx(a, form, cands))
        d = form.cleaned_data
        with transaction.atomic():
            if persona is None:
                persona = crear_persona_rapida(form, request.user)
            p = Participacion.objects.create(
                actividad=a, persona=persona, rol=d["rol"], cargo=(d.get("cargo") or "").strip(), creado_por=request.user,
                estado=estado_inicial(llego), asistencia=True if llego else None,
            )
            _aplicar_grupo(p, d.get("organizacion"), d.get("cargo"), d.get("comunidad"), d.get("rol_organizacion"))
            _perfil_del_rol(persona, d["rol"])
            if form.puede_sensibles and (form.es_menor_de_edad() or persona.es_menor):
                _registrar_apoderado(request, persona, d, "apoderado o contacto de emergencia de un menor, al registrarlo como beneficiario")
        messages.success(request, f"{persona} registrada como {d['rol'].nombre.lower()}" + (" y marcada como asistente." if llego else "."))
        _avisar_capacidad(request, a)
        return self.volver(a, "beneficiarios")


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
        ctx.update(titulo=f"Participación de {self.object.persona}", volver_url=f"{a.get_absolute_url()}?tab={_pestana_de(a, self.object)}", breadcrumb=[(a.nombre, a.get_absolute_url())])
        return ctx

    def form_valid(self, form):
        if self.object.actividad.estado.codigo == "realizada":
            messages.error(self.request, "La actividad ya fue finalizada.")
            return self.form_invalid(form)
        cambiaron = {"institucion", "comunidad"} & set(form.changed_data)
        with transaction.atomic():
            p = form.save()
            servicios.asegurar_organizacion(p)  # F25 E4
            if form.cleaned_data.get("actualizar_vinculo") and cambiaron:  # F26 P2: la única puerta, sin duplicar
                from apps.personas.vinculos import vincular

                vincular(p.persona, organizacion=p.institucion if "institucion" in cambiaron else None,
                         comunidad=p.comunidad if "comunidad" in cambiaron else None, cargo=p.cargo, rol=p.rol, desde=timezone.localdate())
        messages.success(self.request, "Participación actualizada" + (" y también su vínculo." if form.cleaned_data.get("actualizar_vinculo") and cambiaron else "."))
        return HttpResponseRedirect(f"{self.object.actividad.get_absolute_url()}?tab={_pestana_de(self.object.actividad, self.object)}")


class AsistenciaVista(_AccionActividad):
    """Guarda la asistencia. F26 P1a «Pasar lista»: cada fila del formulario envía `en_lista=<id>` y, si su casilla está
    marcada, `asistio=<id>`: marcada → Asistió; sin marcar → No asistió (solo las filas incluidas). «Todos asistieron»
    (`todos=1`) las marca todas. Si se marca «Sin registro de asistencia» y no hay ninguna casilla marcada, las filas no se
    tocan. También acepta el formato anterior `asistencia_<id>` = si / no / vacío."""

    permission_required = "actividades.change_participacion"

    @staticmethod
    def _valores(post):
        """{id de participación: True / False / None} con lo que se envió."""
        valores = {}
        for clave, v in post.items():
            if clave.startswith("asistencia_") and v in ("si", "no", ""):
                pk = pk_seguro(clave.removeprefix("asistencia_"))
                if pk:
                    valores[pk] = {"si": True, "no": False, "": None}[v]
        en_lista = {pk for pk in map(pk_seguro, post.getlist("en_lista")) if pk}
        if en_lista:
            marcadas = en_lista if post.get("todos") == "1" else {pk for pk in map(pk_seguro, post.getlist("asistio")) if pk}
            if not marcadas and post.get("sin_registro") == "1":
                return valores  # «Sin registro de asistencia»: no se marca a nadie como ausente
            valores.update({pk: pk in marcadas for pk in en_lista})
        return valores

    def post(self, request, pk):
        a = self.actividad(pk)
        if a.estado.codigo in ("cancelada", "pendiente", "suspendida"):
            messages.error(request, "No se puede registrar asistencia en esta actividad.")
            return self.volver(a, "participantes")
        if antes_de_la_fecha(a):
            messages.error(request, f"La asistencia se registra desde el día de la actividad ({a.agenda_vigente.fecha:%d-%m-%Y}).")
            return self.volver(a, "participantes")
        estados = {e.codigo: e for e in EstadoParticipacion.objects.filter(codigo__in=["asistio", "no_asistio"])}
        n = 0
        valores = self._valores(request.POST)
        with transaction.atomic():
            for p in a.participaciones.select_related("estado"):
                if p.pk not in valores:
                    continue
                nuevo = valores[p.pk]
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
        return self.volver(a, "beneficiarios" if request.POST.get("volver") == "beneficiarios" else "participantes")


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
# F26 P: los colores salen de los mismos tonos de las insignias de estado (tono_estado en nucleo/templatetags/fche.py).


class Calendario(Permiso403Mixin, TemplateView):
    permission_required = "actividades.view_agendaactividad"
    template_name = "actividades/calendario.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        g = self.request.GET
        ctx.update(
            titulo="Calendario", estados=EstadoActividad.objects.all(), comunas=Comuna.objects.all(),
            elegido={k: g.get(k, "") for k in ("estado", "zona", "responsable", "organizacion", "historicas")},
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
        qs = AgendaActividad.objects.filter(fecha__gte=ini, fecha__lte=fin).select_related("actividad__estado", "actividad__proyecto", "lugar", "estado")
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
            act = ag.actividad
            tono = tono_estado(codigo)
            # F26 P: título corto (el nombre); el proyecto y el lugar van en el detalle al pasar el mouse
            ev = {
                "id": ag.pk, "title": act.nombre + ("" if ag.vigente else f" (v{ag.version}, anterior)"), "start": inicio, "allDay": not ag.hora_inicio,
                "url": act.get_absolute_url(),
                "classNames": ["fche-evento", f"fche-estado--{tono}"] if ag.vigente else ["fche-evento", "fche-evento--anterior"],
                "extendedProps": {"estado": act.estado.nombre, "tono": tono, "lugar": str(ag.lugar) if ag.lugar else "", "vigente": ag.vigente,
                                  "tarea": bool(act.proyecto_id), "proyecto": str(act.proyecto) if act.proyecto_id else ""},
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
        s = get_object_or_404(SesionActividad.objects.select_related("actividad__estado"), pk=sid, actividad_id=pk)
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
            # F26 P1a: la asistencia de la actividad se recalcula desde las sesiones (asistió a al menos una, o ausente en todas)
            recalculadas = servicios.asistencia_desde_sesiones(s.actividad)
        if recalculadas and s.actividad.estado.codigo == "realizada":
            registrar(request.user, "asistencia_tardia", s.actividad, f"{recalculadas} cambios calculados desde las sesiones después de finalizar")
        messages.success(request, f"Asistencia de la sesión guardada ({n} cambios)."
                         + (f" La asistencia de {recalculadas} persona{'s' if recalculadas != 1 else ''} en la actividad se actualizó desde las sesiones." if recalculadas else ""))
        return HttpResponseRedirect(s.get_absolute_url())

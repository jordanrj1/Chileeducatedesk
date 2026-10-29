"""Tarjetas del Panel de inicio: lo que Claudio tiene que hacer hoy (actividades incompletas o próximas,
solicitudes sin respuesta, personas por completar, próximas acciones, invitaciones sin respuesta) y avisos del sistema."""
from django.db import models
from django.utils import timezone


from datetime import timedelta


ICONOS_TARJETA = {
    "Actividades incompletas": "actividades", "Próximas sin participantes": "personas", "Solicitudes sin respuesta": "solicitudes",
    "Personas incompletas": "persona", "Tareas por vencer": "tareas", "Próximas acciones": "tareas", "Sin respuesta": "correo", "Estado del sistema": "administracion",
    "Datos por vencer": "reloj",
}


def proximas(user, dias=7, limite=8):
    """Agenda vigente de los próximos días, para ver de un vistazo qué viene."""
    if not user.has_perm("actividades.view_actividad"):
        return None
    from apps.actividades.models import AgendaActividad

    hoy = timezone.localdate()
    qs = (AgendaActividad.objects.filter(vigente=True, fecha__gte=hoy, fecha__lte=hoy + timedelta(days=dias), actividad__estado__codigo__in=["planificada", "confirmada", "reprogramada"])
          .select_related("actividad__estado", "lugar").order_by("fecha", "hora_inicio"))
    return {"total": qs.count(), "items": list(qs[:limite]), "hoy": hoy}


def tarjetas(user):
    hoy = timezone.localdate()
    res = []

    def agregar(titulo, items, url_todos="", vacio="Nada pendiente."):
        items = list(items)
        res.append({"titulo": titulo, "items": items[:8], "total": len(items), "url": url_todos, "vacio": vacio, "icono": ICONOS_TARJETA.get(titulo, "info")})

    try:
        if user.has_perm("actividades.view_actividad"):
            from apps.actividades.models import Actividad

            from datetime import timedelta as _td

            from django.db.models import Prefetch

            from apps.actividades.models import AgendaActividad, Participacion

            # F26 P1b: número fijo de consultas (la agenda vigente y las participaciones van precargadas)
            incompletas = Actividad.objects.incompletas().select_related("modalidad").prefetch_related(
                Prefetch("agendas", queryset=AgendaActividad.objects.filter(vigente=True), to_attr="_agenda_v"))
            agregar(
                "Actividades incompletas",
                [(a.nombre, a.get_absolute_url(), ", ".join(_faltantes(a))) for a in incompletas],
                "/actividades?incompleta=1",
            )
            vacias = []
            semana = (AgendaActividad.objects.filter(vigente=True, fecha__gte=hoy, fecha__lte=hoy + _td(days=7), actividad__estado__codigo__in=["planificada", "confirmada", "reprogramada"])
                      .select_related("actividad").prefetch_related(Prefetch("actividad__participaciones", queryset=Participacion.objects.select_related("estado")))
                      .order_by("fecha"))
            for ag in semana:
                if not any(p.activa for p in ag.actividad.participaciones.all()):
                    vacias.append((ag.actividad.nombre, ag.actividad.get_absolute_url(), f"el {ag.fecha:%d-%m-%Y}"))
            agregar("Próximas sin participantes", vacias, vacio="Todas las actividades de la semana tienen participantes.")
        if user.has_perm("solicitudes.view_solicitud"):
            from apps.solicitudes.models import Solicitud

            agregar(
                "Solicitudes sin respuesta",
                [(s.titulo, s.get_absolute_url(), f"hace {(hoy - s.fecha).days} días") for s in Solicitud.objects.sin_respuesta()],
                "/solicitudes?estado=pendiente",
            )
        if user.has_perm("personas.view_persona"):
            from apps.personas.models import Persona

            # F26 P2: cada persona dice qué le falta; con lo precargado, un número fijo de consultas
            agregar(
                "Personas incompletas",
                [(str(p), p.get_absolute_url(), _le_falta(p)) for p in Persona.objects.cola_incompletos().con_completitud()],
                "/personas?registro=incompleto",
            )
        from .fases import modulo_activo

        if modulo_activo("tareas") and user.has_perm("coordinacion.view_tarea"):
            from apps.coordinacion.models import Tarea

            agregar(
                "Tareas por vencer",
                [(t.titulo, t.get_absolute_url(), f"vence {t.fecha_limite:%d-%m-%Y}" if t.fecha_limite else "") for t in Tarea.objects.por_vencer(hoy)],
                "/tareas",
            )
        elif user.has_perm("coordinacion.view_interaccion"):
            from apps.coordinacion.models import Interaccion

            # F26 P1b: las de hoy y las vencidas están en «Para hoy y vencidas»; aquí, solo las de los próximos días
            agregar(
                "Próximas acciones",
                [(i.proxima_accion, i.get_absolute_url(), f"para el {i.proxima_fecha:%d-%m-%Y}") for i in Interaccion.objects.proximas_acciones(hoy).filter(proxima_fecha__gt=hoy)],
                vacio="Sin próximas acciones para los próximos 7 días.",
            )
        if user.has_perm("coordinacion.view_invitacion"):
            from django.conf import settings

            from apps.coordinacion.models import Colaboracion, Invitacion

            limite = hoy - timedelta(days=getattr(settings, "SIN_RESPUESTA_DIAS", 7))
            esperando = [(f"Invitación a {i.persona} · {i.actividad}", i.get_absolute_url(), f"hace {(hoy - i.fecha).days} días", i.fecha)
                         for i in Invitacion.objects.filter(estado="enviada", fecha__lte=limite).select_related("persona", "actividad")]
            esperando += [(f"Apoyo de {c.organizacion} · {c.actividad}", c.get_absolute_url(), f"hace {(hoy - timezone.localtime(c.creado_en).date()).days} días", timezone.localtime(c.creado_en).date())
                          for c in Colaboracion.objects.filter(estado="enviada", creado_en__date__lte=limite).select_related("organizacion", "actividad")]
            agregar("Sin respuesta", [(t, u, d) for t, u, d, _ in sorted(esperando, key=lambda x: x[3])], vacio="Ninguna invitación espera respuesta hace más de una semana.")
        sistema = _estado_sistema(user)
        if sistema:
            agregar("Estado del sistema", sistema)
        avisos = _por_vencer(user, hoy)
        if avisos is not None:
            agregar("Datos por vencer", avisos, vacio="Ninguna verificación ni vigencia legal vence en los próximos 30 días.")
    except (ImportError, LookupError):  # módulos que se incorporan en etapas posteriores
        pass
    return res


def _por_vencer(user, hoy, dias=30):
    """Datos que caducan: documentos con vencimiento, verificaciones de personas y vigencia legal de organizaciones."""
    from datetime import timedelta

    from .fases import modulo_activo

    limite = hoy + timedelta(days=dias)
    items, puede = [], False
    # F26 P1b: los documentos y consentimientos por vencer están en «Para hoy y vencidas» (para_hoy): no se repiten aquí.
    if modulo_activo("verificaciones") and user.has_perm("personas.ver_sensibles"):
        puede = True
        from apps.personas.models import VerificacionPersona

        for v in VerificacionPersona.objects.filter(vigente=True, vigente_hasta__isnull=False, vigente_hasta__lte=limite).select_related("persona"):
            items.append((f"Verificación de {v.persona}: {v.tipo}", f"{v.persona.get_absolute_url()}?tab=verificaciones", f"hasta {v.vigente_hasta:%d-%m-%Y}", v.vigente_hasta))
    if user.has_perm("organizaciones.view_organizacion"):
        puede = True
        from apps.organizaciones.models import Organizacion

        for o in Organizacion.objects.filter(activo=True, vigencia_hasta__isnull=False, vigencia_hasta__lte=limite):
            items.append((f"Vigencia legal de {o.nombre}", o.get_absolute_url(), f"hasta {o.vigencia_hasta:%d-%m-%Y}", o.vigencia_hasta))
    if user.has_perm("personas.view_personaorganizacion"):
        puede = True
        from apps.personas.models import PersonaOrganizacion

        hace_un_anio = hoy - timedelta(days=365)
        for v in PersonaOrganizacion.objects.filter(tipo_cargo="autoridad", fecha_termino__isnull=True, persona__activo=True).filter(
            models.Q(fecha_inicio__isnull=True) | models.Q(fecha_inicio__lt=hace_un_anio)
        ).select_related("persona", "organizacion")[:20]:
            items.append((f"Verificar si sigue vigente: {v.persona}, {v.cargo or 'autoridad'} en {v.organizacion}", f"{v.organizacion.get_absolute_url()}?tab=personas",
                          f"desde {v.fecha_inicio:%d-%m-%Y}" if v.fecha_inicio else "sin fecha de inicio", v.fecha_inicio or hoy))
    if not puede:
        return None
    return [(t, u, d) for t, u, d, _ in sorted(items, key=lambda x: x[3])]


def _le_falta(p):
    """«le falta: apellido, un contacto · en actividad próxima» (F26 P2)."""
    faltan = p.faltantes()
    return " · ".join(x for x in ["le falta: " + ", ".join(faltan) if faltan else "", "en actividad próxima" if p.prioridad else ""] if x)


def _faltantes(a):
    """Lo mismo que Actividad.faltantes(), con la agenda vigente precargada (sin una consulta por actividad)."""
    res = [] if a.responsable_id else ["responsable"]
    ag = a._agenda_v[0] if a._agenda_v else None
    if not ag or not ag.hora_inicio:
        res.append("fecha y hora")
    elif not ag.lugar_id and not (a.modalidad_id and a.modalidad.codigo == "virtual"):
        res.append("lugar")
    return res


def para_hoy(user, hoy=None, dias=30, limite=10):
    """F26 P1b: «Para hoy y vencidas». Próximas acciones de interacciones para hoy o atrasadas; actividades y tareas con
    fecha pasada que no se han finalizado ni cancelado; documentos y consentimientos que vencen en los próximos días.
    Cada ítem lleva su enlace. Número fijo de consultas (una por tipo). None si el usuario no puede ver nada de esto."""
    from datetime import timedelta

    hoy = hoy or timezone.localdate()
    items, puede = [], False
    if user.has_perm("coordinacion.view_interaccion"):
        puede = True
        from apps.coordinacion.models import Interaccion

        for i in (Interaccion.objects.filter(accion_cumplida=False, proxima_fecha__isnull=False, proxima_fecha__lte=hoy).exclude(proxima_accion="")
                  .select_related("persona", "organizacion")):
            con = i.persona or i.organizacion
            items.append((i.proxima_accion + (f" · {con}" if con else ""), i.get_absolute_url(),
                          "hoy" if i.proxima_fecha == hoy else f"atrasada desde el {i.proxima_fecha:%d-%m-%Y}", i.proxima_fecha, "Acción"))
    if user.has_perm("actividades.view_actividad"):
        puede = True
        from apps.actividades.models import AgendaActividad

        for ag in (AgendaActividad.objects.filter(vigente=True, fecha__lt=hoy).exclude(actividad__estado__codigo__in=["realizada", "cancelada"])
                   .select_related("actividad")):
            a = ag.actividad
            items.append((a.nombre, a.get_absolute_url(), f"fue el {ag.fecha:%d-%m-%Y}: falta finalizarla", ag.fecha, "Tarea" if a.proyecto_id else "Actividad"))
    venc = hoy + timedelta(days=dias)
    respaldos = set()
    if user.has_perm("personas.view_consentimiento"):
        puede = True
        from apps.personas.models import Consentimiento

        for c in (Consentimiento.objects.filter(otorgado=True, revocado_en__isnull=True, documento__activo=True, documento__fecha_vencimiento__lte=venc)
                  .select_related("persona", "documento")):
            respaldos.add(c.documento_id)
            f = c.documento.fecha_vencimiento
            items.append((f"{c.get_tipo_display()} de {c.persona}", f"{c.persona.get_absolute_url()}?tab=privacidad",
                          ("su respaldo venció el " if f < hoy else "su respaldo vence el ") + f"{f:%d-%m-%Y}", f, "Consentimiento"))
    if user.has_perm("documentos.view_documento"):
        puede = True
        from apps.documentos.models import Documento

        docs = Documento.objects.filter(activo=True, fecha_vencimiento__isnull=False, fecha_vencimiento__lte=venc).exclude(pk__in=respaldos)
        if not user.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        items += [(d.nombre, d.get_absolute_url(), ("venció el " if d.vencido else "vence el ") + f"{d.fecha_vencimiento:%d-%m-%Y}", d.fecha_vencimiento, "Documento")
                  for d in docs]
    if not puede:
        return None
    items.sort(key=lambda x: x[3])
    return {"total": len(items), "items": items[:limite], "resto": max(len(items) - limite, 0)}


def indicadores(user):
    """Cifras de la fila de indicadores que no son ya una tarjeta del Inicio (F26 P1b: sin repetir). Una consulta cada una."""
    res = []
    if user.has_perm("solicitudes.view_solicitud"):
        from apps.solicitudes.models import Solicitud

        n = Solicitud.objects.filter(estado__codigo__in=["pendiente", "en_seguimiento"]).count()
        res.append({"titulo": "Solicitudes abiertas", "valor": n, "nota": "pendientes o en seguimiento", "url": "/solicitudes", "icono": "solicitudes"})
    if user.has_perm("actividades.view_actividad"):
        from apps.actividades.models import Actividad

        n = Actividad.objects.filter(estado__codigo__in=["pendiente", "planificada", "confirmada", "reprogramada", "suspendida"]).count()
        res.append({"titulo": "Actividades y tareas en curso", "valor": n, "nota": "sin finalizar ni cancelar", "url": "/actividades", "icono": "actividades"})
    if user.has_perm("proyectos.view_proyecto"):
        from apps.proyectos.models import Proyecto

        n = Proyecto.objects.filter(estado__in=["preparacion", "postulado", "ejecucion"]).count()
        res.append({"titulo": "Proyectos activos", "valor": n, "nota": "en preparación, postulados o en ejecución", "url": "/proyectos", "icono": "proyectos"})
    return res


def _estado_sistema(user):
    """OP-E4 y OP-E2: respaldo atrasado y poco espacio en disco. Solo aparece si hay algo que atender."""
    import shutil
    from pathlib import Path

    from django.conf import settings

    from .models import Auditoria

    items = []
    max_dias = getattr(settings, "RESPALDO_MAX_DIAS", 2)
    ultimo = Auditoria.objects.filter(accion="respaldo").order_by("-fecha").values_list("fecha", flat=True).first()
    if ultimo is None:
        items.append(("No hay registro de ningún respaldo", "/administracion/auditoria?accion=respaldo" if user.has_perm("nucleo.view_auditoria") else "#", "programa respaldar.bat"))
    elif (timezone.now() - ultimo).days > max_dias:
        items.append((f"El último respaldo es del {timezone.localtime(ultimo):%d-%m-%Y}", "/administracion/auditoria?accion=respaldo" if user.has_perm("nucleo.view_auditoria") else "#", f"hace {(timezone.now() - ultimo).days} días"))
    try:
        uso = shutil.disk_usage(Path(settings.MEDIA_ROOT).parent if not Path(settings.MEDIA_ROOT).exists() else settings.MEDIA_ROOT)
        libre = uso.free / uso.total
        if libre < 0.10 or uso.free < 2 * 1024**3:
            items.append((f"Queda poco espacio en disco: {uso.free / 1024**3:.1f} GB libres", "#", f"{libre:.0%} libre"))
    except OSError:
        pass
    return items


PERIODOS_INDICADORES = [("mes", "Mes"), ("trimestre", "Trimestre"), ("anio", "Año")]


def rango_periodo(periodo, hoy=None):
    """(desde, hasta, etiqueta) del mes, trimestre o año en curso, hasta hoy. Un valor desconocido vale «mes»."""
    from datetime import date

    hoy = hoy or timezone.localdate()
    if periodo == "anio":
        return date(hoy.year, 1, 1), hoy, f"Año {hoy.year}"
    if periodo == "trimestre":
        n = (hoy.month - 1) // 3
        return date(hoy.year, 3 * n + 1, 1), hoy, f"{n + 1}.º trimestre de {hoy.year}"
    from django.utils.formats import date_format

    return hoy.replace(day=1), hoy, date_format(hoy, r"F \d\e Y").capitalize()


def indicadores_periodo(user, periodo="mes", hoy=None):
    """F26 P3a: «Indicadores del período» para la Dirección. Actividades y tareas realizadas (con fecha vigente dentro del
    período), personas distintas alcanzadas (asistentes), horas de participación, organizaciones aliadas y comunas
    atendidas. Reutiliza `alcance()` (lo mismo que la pestaña Alcance). Número fijo de consultas. None sin permiso."""
    if not (user.has_perm("actividades.view_actividad") and user.has_perm("actividades.view_participacion")):
        return None
    from django.db.models import Q

    from apps.actividades.alcance import alcance
    from apps.actividades.models import ActividadOrganizacion, ActividadTerritorio, AgendaActividad
    from apps.nucleo.models import EstadoActividad

    periodo = periodo if periodo in dict(PERIODOS_INDICADORES) else "mes"
    desde, hasta, etiqueta = rango_periodo(periodo, hoy)
    agendas = list(AgendaActividad.objects.filter(vigente=True, fecha__range=(desde, hasta), actividad__estado__codigo="realizada")
                   .select_related("actividad", "lugar__direccion"))
    actividades = [ag.actividad for ag in agendas]
    ids = [a.pk for a in actividades]
    a = alcance(actividades)
    aliadas = (ActividadOrganizacion.objects.filter(actividad_id__in=ids, vigente=True).values("organizacion_id").distinct().count()) if ids else 0
    comunas = {ag.lugar.direccion.comuna_id for ag in agendas if ag.lugar_id and ag.lugar.direccion_id}
    if ids:
        for comuna, sector_comuna in (ActividadTerritorio.objects.filter(actividad_id__in=ids, vigente=True)
                                      .filter(Q(comuna__isnull=False) | Q(sector__isnull=False)).values_list("comuna_id", "sector__comuna_id")):
            comunas.add(comuna or sector_comuna)
    comunas.discard(None)
    realizada = EstadoActividad.objects.filter(codigo="realizada").values_list("pk", flat=True).first()
    url = f"/actividades?estado={realizada or ''}&desde={desde.isoformat()}&hasta={hasta.isoformat()}"
    tareas = sum(1 for x in actividades if x.proyecto_id)
    return {
        "periodo": periodo, "opciones": PERIODOS_INDICADORES, "etiqueta": etiqueta, "desde": desde, "hasta": hasta,
        "items": [
            {"titulo": "Realizadas", "valor": len(actividades), "nota": f"{len(actividades) - tareas} actividades y {tareas} tareas", "url": url, "icono": "actividades"},
            {"titulo": "Personas alcanzadas", "valor": a["asistieron"], "nota": "personas distintas que asistieron" + (f" (+{a['sin_registro']} sin registro)" if a["sin_registro"] else ""), "url": "", "icono": "personas"},
            {"titulo": "Horas", "valor": a["horas"], "nota": "de participación de quienes asistieron", "url": "", "icono": "reloj"},
            {"titulo": "Organizaciones aliadas", "valor": aliadas, "nota": "distintas, en lo realizado", "url": "", "icono": "organizaciones"},
            {"titulo": "Comunas atendidas", "valor": len(comunas), "nota": "por el lugar o la zona", "url": "", "icono": "territorio"},
        ],
    }

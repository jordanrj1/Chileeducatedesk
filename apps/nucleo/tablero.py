"""Tarjetas del dashboard: qué tengo que hacer hoy."""
from django.db import models
from django.utils import timezone


from datetime import timedelta


def tarjetas(user):
    hoy = timezone.localdate()
    res = []

    def agregar(titulo, items, url_todos="", vacio="Nada pendiente."):
        res.append({"titulo": titulo, "items": list(items)[:8], "url": url_todos, "vacio": vacio})

    try:
        if user.has_perm("actividades.view_actividad"):
            from apps.actividades.models import Actividad

            agregar(
                "Actividades incompletas",
                [(a.nombre, a.get_absolute_url(), ", ".join(a.faltantes())) for a in Actividad.objects.incompletas()],
                "/actividades?incompleta=1",
            )
            from datetime import timedelta as _td

            from apps.actividades.models import AgendaActividad

            vacias = []
            for ag in AgendaActividad.objects.filter(vigente=True, fecha__gte=hoy, fecha__lte=hoy + _td(days=7), actividad__estado__codigo__in=["planificada", "confirmada", "reprogramada"]).select_related("actividad").order_by("fecha"):
                if not any(p.activa for p in ag.actividad.participaciones.select_related("estado")):
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

            agregar(
                "Personas incompletas",
                [(str(p), p.get_absolute_url(), "en actividad próxima" if p.prioridad else "") for p in Persona.objects.cola_incompletos()],
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

            agregar(
                "Tareas por vencer",
                [(i.proxima_accion, i.get_absolute_url(), f"para el {i.proxima_fecha:%d-%m-%Y}") for i in Interaccion.objects.proximas_acciones(hoy)],
                vacio="Sin próximas acciones pendientes.",
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
            agregar("Datos por vencer", avisos, "/documentos?vencimiento=por_vencer", vacio="Nada vence en los próximos 30 días.")
    except (ImportError, LookupError):  # módulos que se incorporan en etapas posteriores
        pass
    return res


def _por_vencer(user, hoy, dias=30):
    """Datos que caducan: documentos con vencimiento, verificaciones de personas y vigencia legal de organizaciones."""
    from datetime import timedelta

    from .fases import modulo_activo

    limite = hoy + timedelta(days=dias)
    items, puede = [], False
    if user.has_perm("documentos.view_documento"):
        puede = True
        from apps.documentos.models import Documento

        docs = Documento.objects.filter(activo=True, fecha_vencimiento__isnull=False, fecha_vencimiento__lte=limite)
        if not user.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        items += [(f"Documento: {d.nombre}", d.get_absolute_url(), ("venció " if d.vencido else "vence ") + f"{d.fecha_vencimiento:%d-%m-%Y}", d.fecha_vencimiento) for d in docs]
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

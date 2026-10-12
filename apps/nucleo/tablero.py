"""Tarjetas del dashboard: qué tengo que hacer hoy."""
from django.utils import timezone


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
        if user.has_perm("solicitudes.view_solicitud"):
            from apps.solicitudes.models import Solicitud

            agregar(
                "Solicitudes sin respuesta",
                [(s.titulo, s.get_absolute_url(), f"desde {s.fecha:%d-%m-%Y}") for s in Solicitud.objects.sin_respuesta()],
                "/solicitudes?estado=pendiente",
            )
        if user.has_perm("personas.view_persona"):
            from apps.personas.models import Persona

            agregar(
                "Personas incompletas",
                [(str(p), p.get_absolute_url(), "en actividad próxima" if p.prioridad else "") for p in Persona.objects.cola_incompletos()],
                "/personas?registro=incompleto",
            )
        from .fases import segunda_fase_activa

        if segunda_fase_activa() and user.has_perm("coordinacion.view_tarea"):
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
    except (ImportError, LookupError):  # módulos que se incorporan en etapas posteriores
        pass
    return res

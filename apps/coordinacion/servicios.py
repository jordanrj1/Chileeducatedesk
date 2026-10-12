from apps.actividades.models import Participacion
from apps.nucleo.models import EstadoParticipacion

ESTADO_PARTICIPACION = {"pendiente": "invitado", "sin_respuesta": "invitado", "aceptada": "confirmado", "rechazada": "rechazo"}


def sincronizar_invitacion(inv, usuario=None):
    """La respuesta a una invitación se refleja en la participación (nunca borra: cambia su estado)."""
    estado = EstadoParticipacion.objects.get(codigo=ESTADO_PARTICIPACION[inv.estado])
    p, creada = Participacion.objects.get_or_create(
        actividad=inv.actividad, persona=inv.persona, rol=inv.rol, defaults={"estado": estado, "creado_por": usuario}
    )
    if not creada and p.estado_id != estado.pk and not (inv.estado in ("pendiente", "sin_respuesta") and p.estado.codigo not in ("invitado",)):
        p.estado = estado
        p.save()
    return p

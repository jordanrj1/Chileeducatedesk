"""Reglas de negocio de la actividad: errores de dominio, transiciones y revisión de compatibilidad (F11)."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.conf import settings

TRANSICIONES = {
    "pendiente": {"planificada", "cancelada"},
    "planificada": {"confirmada", "suspendida", "cancelada", "realizada"},
    "confirmada": {"reprogramada", "suspendida", "cancelada", "realizada"},
    "reprogramada": {"confirmada", "suspendida", "cancelada", "realizada"},
    "suspendida": {"planificada", "cancelada"},
    "cancelada": set(),
    "realizada": {"cerrada"},
    "cerrada": set(),
}
ESTADOS_QUE_OCUPAN = ("planificada", "confirmada", "reprogramada", "realizada", "cerrada")
MOTIVO_OBLIGATORIO = {"suspendida", "cancelada"}


class ReglaNegocio(Exception):
    """Operación no permitida; `mensajes` se muestran al usuario."""

    def __init__(self, *mensajes):
        super().__init__("; ".join(mensajes))
        self.mensajes = list(mensajes)


@dataclass
class Problema:
    nivel: str  # bloqueante | critico | advertencia | info
    codigo: str
    mensaje: str


def _minutos(t):
    return t.hour * 60 + t.minute


def intervalo(hora_inicio, hora_fin):
    """(inicio, fin) en minutos; sin hora de término se asume una hora."""
    if hora_inicio is None:
        return None
    ini = _minutos(hora_inicio)
    return ini, (_minutos(hora_fin) if hora_fin else ini + 60)


def se_solapan(a, b):
    return a and b and a[0] < b[1] and b[0] < a[1]


def participaciones_activas(actividad):
    return [p for p in actividad.participaciones.select_related("persona", "rol", "estado") if p.activa]


def conflictos_de_persona(persona, agenda, excluir_actividad=None):
    """Otras actividades que ocupan a la persona (como participante activa o responsable) en el mismo horario."""
    from django.db.models import Q

    from .models import AgendaActividad

    mio = intervalo(agenda.hora_inicio, agenda.hora_fin)
    if not mio:
        return []
    candidatas = (
        AgendaActividad.objects.filter(vigente=True, fecha=agenda.fecha, actividad__estado__codigo__in=("planificada", "confirmada", "reprogramada"))
        .filter(Q(actividad__participaciones__persona=persona) | Q(actividad__responsable=persona))
        .select_related("actividad")
        .distinct()
    )
    if excluir_actividad:
        candidatas = candidatas.exclude(actividad=excluir_actividad)
    res = []
    for o in candidatas:
        ocupa = o.actividad.responsable_id == persona.pk or any(p.activa for p in o.actividad.participaciones.filter(persona=persona).select_related("estado"))
        if ocupa and se_solapan(mio, intervalo(o.hora_inicio, o.hora_fin)):
            res.append(o)
    return res


def fuera_de_disponibilidad(persona, agenda):
    """True si la persona declaró horarios y ninguno cubre esta programación."""
    bloques = list(persona.disponibilidades.filter(vigente=True))
    if not bloques or not agenda.hora_inicio:
        return False
    dia = agenda.fecha.weekday()
    ini, fin = intervalo(agenda.hora_inicio, agenda.hora_fin)
    return not any(b.dia == dia and _minutos(b.hora_inicio) <= ini and _minutos(b.hora_fin) >= fin for b in bloques)


def revisar(actividad, hoy=None):
    """Lista ordenada de problemas. `bloqueante`: falta lo mínimo. `critico`: conflicto grave. Luego advertencias e info."""
    from .models import AgendaActividad

    hoy = hoy or date.today()
    res = []
    agenda = actividad.agenda_vigente
    if not actividad.responsable_id:
        res.append(Problema("bloqueante", "sin_responsable", "Falta indicar el responsable de la actividad."))
    if not agenda or not agenda.hora_inicio:
        res.append(Problema("bloqueante", "sin_agenda", "Falta programar fecha y hora."))
    lugar = agenda.lugar if agenda else None
    if agenda and not lugar and not actividad.es_virtual:
        res.append(Problema("bloqueante", "sin_lugar", "Falta el lugar (o indicar modalidad virtual)."))
    activas = participaciones_activas(actividad)
    if not activas:
        res.append(Problema("advertencia", "sin_participantes", "No hay participantes registrados todavía."))
    if agenda and agenda.hora_inicio:
        if lugar:
            if not lugar.activo:
                res.append(Problema("critico", "lugar_inactivo", f"El lugar «{lugar}» está desactivado."))
            if lugar.capacidad is not None and len(activas) > lugar.capacidad:
                res.append(Problema("critico", "capacidad", f"Hay {len(activas)} participantes y el lugar «{lugar}» tiene capacidad para {lugar.capacidad}."))
            elif lugar.capacidad is None and activas:
                res.append(Problema("advertencia", "capacidad_desconocida", f"El lugar «{lugar}» no tiene capacidad registrada."))
            mio = intervalo(agenda.hora_inicio, agenda.hora_fin)
            ocupantes = (
                AgendaActividad.objects.filter(vigente=True, lugar=lugar, fecha=agenda.fecha)
                .exclude(actividad=actividad).exclude(actividad__estado__codigo__in=("cancelada", "suspendida", "pendiente"))
                .select_related("actividad")
            )
            for o in ocupantes:
                if se_solapan(mio, intervalo(o.hora_inicio, o.hora_fin)):
                    res.append(Problema("critico", "lugar_ocupado", f"El lugar «{lugar}» ya está ocupado por «{o.actividad}» a las {o.hora_inicio:%H:%M}."))
            if lugar.condiciones:
                res.append(Problema("info", "condiciones_lugar", f"Condiciones del lugar: {lugar.condiciones}"))
        if actividad.condiciones:
            res.append(Problema("info", "condiciones", f"Condiciones de la actividad: {actividad.condiciones}"))
        if agenda.fecha < hoy and actividad.estado.codigo not in ("realizada", "cerrada"):
            res.append(Problema("advertencia", "fecha_pasada", f"La fecha programada ({agenda.fecha:%d-%m-%Y}) ya pasó."))
        personas = {p.persona_id: p.persona for p in activas if not p.es_beneficiario}
        if actividad.responsable_id and actividad.responsable_id not in personas:
            personas[actividad.responsable_id] = actividad.responsable
        for persona in personas.values():
            for otra in conflictos_de_persona(persona, agenda, excluir_actividad=actividad):
                res.append(Problema("advertencia", "persona_ocupada", f"{persona} ya participa en «{otra.actividad}» ese día a las {otra.hora_inicio:%H:%M}."))
            if fuera_de_disponibilidad(persona, agenda):
                res.append(Problema("advertencia", "fuera_de_disponibilidad", f"{persona} declaró disponibilidad en otros horarios."))
    orden = {"bloqueante": 0, "critico": 1, "advertencia": 2, "info": 3}
    return sorted(res, key=lambda p: orden[p.nivel])


def conflicto_critico_permitido():
    return bool(getattr(settings, "CONFIRMAR_CON_CONFLICTO_CRITICO", False))

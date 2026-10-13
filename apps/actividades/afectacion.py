"""Qué actividades en curso o futuras dependen de una persona, organización o lugar (NR-06, AT-E6, LU-E2)."""
from django.db.models import Q
from django.utils import timezone

ABIERTAS = ("pendiente", "planificada", "confirmada", "reprogramada", "suspendida")


def _abiertas():
    from .models import Actividad

    hoy = timezone.localdate()
    sin_fecha_o_futura = ~Q(agendas__vigente=True) | Q(agendas__vigente=True, agendas__fecha__gte=hoy)
    return Actividad.objects.filter(estado__codigo__in=ABIERTAS).filter(sin_fecha_o_futura).distinct()


def de_persona(persona):
    qs = _abiertas().filter(Q(responsable=persona) | Q(participaciones__persona=persona)).distinct().select_related("estado")
    return [(f"{a.nombre} ({a.estado}){' · responsable' if a.responsable_id == persona.pk else ''}", a.get_absolute_url()) for a in qs]


def a_cargo_de(persona):
    return _abiertas().filter(responsable=persona).select_related("estado")


def de_organizacion(org):
    qs = _abiertas().filter(organizaciones__organizacion=org, organizaciones__vigente=True).distinct().select_related("estado")
    return [(f"{a.nombre} ({a.estado})", a.get_absolute_url()) for a in qs]


def de_lugar(lugar):
    from .models import AgendaActividad

    hoy = timezone.localdate()
    qs = AgendaActividad.objects.filter(vigente=True, lugar=lugar, fecha__gte=hoy, actividad__estado__codigo__in=ABIERTAS).select_related("actividad__estado")
    return [(f"{ag.actividad.nombre} · {ag.fecha:%d-%m-%Y} ({ag.actividad.estado})", ag.actividad.get_absolute_url()) for ag in qs]


def excedidas_por_capacidad(lugar):
    """Actividades futuras del lugar que, con su capacidad actual, quedan excedidas (LU-E2)."""
    from .models import AgendaActividad
    from .reglas import personas_que_ocupan

    hoy = timezone.localdate()
    res = []
    if lugar.capacidad is None:
        return res
    for ag in AgendaActividad.objects.filter(vigente=True, lugar=lugar, fecha__gte=hoy, actividad__estado__codigo__in=ABIERTAS).select_related("actividad"):
        n = len(personas_que_ocupan(ag.actividad))
        if n > lugar.capacidad:
            res.append((f"{ag.actividad.nombre} · {ag.fecha:%d-%m-%Y}: {n} personas", ag.actividad.get_absolute_url()))
    return res

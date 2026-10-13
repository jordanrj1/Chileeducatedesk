"""Alcance de un conjunto de actividades (F22): quién ejecutó, quién asistió, de dónde venían y cuántas horas.

Responde «con unos clics» lo que hoy se reconstruye a mano desde planillas y minutas.
"""
from collections import Counter
from decimal import Decimal

TRAMOS = [("0 a 17", 0, 17), ("18 a 29", 18, 29), ("30 a 59", 30, 59), ("60 o más", 60, 200)]


def horas_de(participacion, agenda=None):
    """Horas de una participación: las registradas o, si no hay, la duración de la programación vigente."""
    if participacion.horas is not None:
        return Decimal(participacion.horas)
    agenda = agenda if agenda is not None else participacion.actividad.agenda_vigente
    if agenda and agenda.duracion_minutos:
        return (Decimal(agenda.duracion_minutos) / 60).quantize(Decimal("0.1"))
    return Decimal(0)


def tramo(edad):
    if edad is None:
        return None
    return next((n for n, a, b in TRAMOS if a <= edad <= b), None)


def alcance(actividades):
    """`actividades`: queryset o lista de actividades. Devuelve un dict listo para mostrar."""
    from .models import AgendaActividad, Participacion, SesionActividad

    ids = [a.pk for a in actividades]
    partes = list(Participacion.objects.filter(actividad_id__in=ids).exclude(estado__codigo="registro_erroneo")
                  .select_related("rol", "institucion", "comunidad", "persona"))
    agendas = {a.actividad_id: a for a in AgendaActividad.objects.filter(actividad_id__in=ids, vigente=True)}
    ejecutores = {p.persona_id for p in partes if p.rol.grupo == "ejecutor"}
    asistentes = {p.persona_id for p in partes if p.rol.grupo == "asistente"}
    asistieron = [p for p in partes if p.asistencia is True]
    personas_asistieron = {p.persona_id: p.persona for p in asistieron}
    horas = sum((horas_de(p, agendas.get(p.actividad_id)) for p in asistieron), Decimal(0))
    horas_equipo = sum((horas_de(p, agendas.get(p.actividad_id)) for p in asistieron if p.rol.grupo == "ejecutor"), Decimal(0))
    instituciones = Counter(p.institucion for p in partes if p.institucion_id and p.rol.grupo == "ejecutor")
    comunidades = Counter(p.comunidad for p in partes if p.comunidad_id)
    roles = Counter(p.rol for p in partes)
    edades = Counter(tramo(per.edad) for per in personas_asistieron.values() if per.edad is not None)
    sesiones = list(SesionActividad.objects.filter(actividad_id__in=ids, vigente=True))
    sin_registro = sum(s.asistentes_sin_registro or 0 for s in sesiones)

    def suma(campo):
        return sum(getattr(s, campo) or 0 for s in sesiones)

    return {
        "actividades": len(ids),
        "personas": len({p.persona_id for p in partes}),
        "equipo": len(ejecutores),
        "asistentes": len(asistentes),
        "asistieron": len(personas_asistieron),
        "horas": horas,
        "horas_equipo": horas_equipo,
        "instituciones": instituciones.most_common(),
        "comunidades": comunidades.most_common(),
        "roles": roles.most_common(),
        "edades_registradas": [(n, edades.get(n, 0)) for n, _, _ in TRAMOS],
        "sesiones": len(sesiones),
        "sin_registro": sin_registro,
        "sin_registro_edades": [("0 a 17", suma("conteo_menores")), ("18 a 29", suma("conteo_jovenes")), ("30 a 59", suma("conteo_adultos")), ("60 o más", suma("conteo_mayores"))],
        "sin_registro_generos": [("Mujeres", suma("conteo_mujeres")), ("Hombres", suma("conteo_hombres")), ("Otro o no informado", suma("conteo_otros"))],
        "total_alcanzado": len(personas_asistieron) + sin_registro,
    }


def horas_persona(persona):
    """Horas acumuladas por una persona en actividades donde asistió."""
    partes = persona.participaciones.filter(asistencia=True).exclude(estado__codigo="registro_erroneo").select_related("actividad")
    return sum((horas_de(p) for p in partes), Decimal(0))

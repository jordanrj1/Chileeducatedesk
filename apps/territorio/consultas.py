"""Consultas de qué hay en un territorio: lugares, organizaciones y actividades de una comuna o sector
(incluidos sus sectores hijos). Las usan las fichas de comuna y sector y el buscador (TE-04, BU-05)."""
from django.db.models import Q


def lugares_de(comuna=None, sectores=None):
    from apps.lugares.models import Lugar

    qs = Lugar.objects.select_related("tipo", "direccion__sector")
    return qs.filter(direccion__sector_id__in=sectores) if sectores else qs.filter(direccion__comuna=comuna)


def organizaciones_de(comuna=None, sectores=None):
    from apps.organizaciones.models import Organizacion

    qs = Organizacion.objects.select_related("tipo")
    if sectores:
        return qs.filter(direccion__sector_id__in=sectores)
    return qs.filter(Q(direccion__comuna=comuna) | Q(comuna_municipal=comuna)).distinct()


def dirigida_a_comuna(comuna, prefijo=""):
    """Condición: la actividad se dirige a la comuna o a uno de sus sectores (los subsectores son de la misma comuna).
    `comuna` es la comuna o su número; `prefijo` permite preguntar desde otra tabla, p. ej. «actividad__» en la agenda."""
    p = f"{prefijo}territorios__"
    return Q(**{f"{p}vigente": True, f"{p}comuna": comuna}) | Q(**{f"{p}vigente": True, f"{p}sector__comuna": comuna})


def actividad_en_comuna(comuna):
    """Condición «la actividad es en esta comuna»: su lugar programado vigente está en ella o se dirige a ella o a sus
    sectores. La usan la ficha de la comuna, el listado de actividades y el buscador, para que cuenten lo mismo."""
    return Q(agendas__vigente=True, agendas__lugar__direccion__comuna=comuna) | dirigida_a_comuna(comuna)


def actividades_de(comuna=None, sectores=None):
    from apps.actividades.models import Actividad

    qs = Actividad.objects.select_related("estado", "tipo")
    if sectores:
        cond = Q(agendas__vigente=True, agendas__lugar__direccion__sector_id__in=sectores) | Q(territorios__vigente=True, territorios__sector_id__in=sectores)
    else:
        cond = actividad_en_comuna(comuna)
    return qs.filter(cond).distinct().order_by("-creado_en")

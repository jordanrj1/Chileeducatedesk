"""Qué hay en un territorio: lugares, organizaciones y actividades (TE-04, BU-05)."""
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


def actividades_de(comuna=None, sectores=None):
    from apps.actividades.models import Actividad

    qs = Actividad.objects.select_related("estado", "tipo")
    if sectores:
        cond = Q(agendas__vigente=True, agendas__lugar__direccion__sector_id__in=sectores) | Q(territorios__vigente=True, territorios__sector_id__in=sectores)
    else:
        cond = (
            Q(agendas__vigente=True, agendas__lugar__direccion__comuna=comuna)
            | Q(territorios__vigente=True, territorios__comuna=comuna)
            | Q(territorios__vigente=True, territorios__sector__comuna=comuna)
        )
    return qs.filter(cond).distinct().order_by("-creado_en")

from django import template

register = template.Library()


@register.simple_tag
def relacion_territorial(actividad, comuna=None, sectores=None):
    """BU-E7: distingue «realizada en» (su lugar está aquí) de «dirigida a» (solo indica el territorio)."""
    ag = actividad.agenda_vigente
    partes = []
    if ag and ag.lugar:
        d = ag.lugar.direccion
        if (sectores and d.sector_id in sectores) or (comuna and d.comuna_id == comuna.pk):
            partes.append(f"Realizada en {ag.lugar}")
    dirigida = actividad.territorios.filter(vigente=True)
    if sectores:
        dirigida = dirigida.filter(sector_id__in=sectores)
    elif comuna:
        dirigida = dirigida.filter(comuna=comuna) | actividad.territorios.filter(vigente=True, sector__comuna=comuna)
    if dirigida.exists():
        partes.append("Dirigida a este territorio")
    return " · ".join(partes)

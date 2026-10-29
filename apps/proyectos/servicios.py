"""F26 P2: una sola verdad para el responsable del proyecto. El campo `Proyecto.responsable` y la marca «responsable»
del equipo (ProyectoPersona.es_responsable) dicen siempre lo mismo."""
from django.db import transaction


def asegurar_responsable(proyecto):
    """El responsable queda en el equipo (vigente) marcado como responsable; si otro estaba marcado, se desmarca pero
    sigue en el equipo. Sin responsable, no cambia nada. A lo más cuatro consultas."""
    from .models import ProyectoPersona

    if not proyecto.responsable_id:
        return None
    with transaction.atomic():
        pp, creado = ProyectoPersona.objects.get_or_create(proyecto=proyecto, persona_id=proyecto.responsable_id, tipo="equipo",
                                                           defaults={"es_responsable": True})
        if not creado and not (pp.es_responsable and pp.vigente):
            pp.es_responsable, pp.vigente, pp.hasta = True, True, None
            pp.save(update_fields=["es_responsable", "vigente", "hasta"])
        ProyectoPersona.objects.filter(proyecto=proyecto, tipo="equipo", es_responsable=True).exclude(pk=pp.pk).update(es_responsable=False)
    return pp


def responsable_desde_equipo(pp):
    """Al marcar (o desmarcar) a alguien del equipo como responsable, el proyecto toma (o suelta) ese responsable."""
    proyecto = pp.proyecto
    if pp.tipo != "equipo":
        return
    if pp.es_responsable and proyecto.responsable_id != pp.persona_id:
        proyecto.responsable_id = pp.persona_id
        proyecto.save(update_fields=["responsable"])
        asegurar_responsable(proyecto)
    elif not pp.es_responsable and proyecto.responsable_id == pp.persona_id:
        proyecto.responsable = None
        proyecto.save(update_fields=["responsable"])

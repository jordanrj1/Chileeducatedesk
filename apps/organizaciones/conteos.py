"""F26 Ib: cuántas personas y actividades tiene una organización, iguales en la lista y en «De un vistazo».

Personas vinculadas: quienes tienen un vínculo (cargo) vigente o una formación vigente en ella, cada una una vez.
Actividades: las actividades o tareas en que participa la organización (vigentes en la actividad).
"""
from django.db.models import Count, Exists, F, Func, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone


def personas_vigentes_de(organizacion):
    """Condición sobre Persona. `organizacion`: una organización, su pk o una referencia (OuterRef) en una subconsulta."""
    from apps.personas.models import PersonaFormacion, PersonaOrganizacion

    hoy = timezone.localdate()
    vinculo = PersonaOrganizacion.objects.filter(persona=OuterRef("pk"), organizacion=organizacion).filter(
        Q(fecha_termino__isnull=True) | Q(fecha_termino__gte=hoy))
    formacion = PersonaFormacion.objects.filter(persona=OuterRef("pk"), organizacion=organizacion, vigente=True)
    return Exists(vinculo) | Exists(formacion)


def _contar(qs):
    """Subconsulta con COUNT(DISTINCT pk) de `qs`, sin GROUP BY (cada registro una vez); 0 si no hay filas."""
    cuenta = Func(F("pk"), function="COUNT", template="COUNT(DISTINCT %(expressions)s)", output_field=IntegerField())
    return Coalesce(Subquery(qs.order_by().annotate(n=cuenta).values("n")[:1], output_field=IntegerField()), 0)


def con_conteos(qs):
    """Agrega `n_personas` y `n_actividades` a un queryset de organizaciones: una sola consulta."""
    from apps.actividades.models import Actividad
    from apps.personas.models import Persona

    return qs.annotate(
        n_personas=_contar(Persona.objects.filter(personas_vigentes_de(OuterRef(OuterRef("pk"))))),
        n_actividades=_contar(Actividad.objects.filter(organizaciones__organizacion=OuterRef("pk"), organizaciones__vigente=True)),
    )


def cifras(organizacion):
    """{"act": actividades, "proy": proyectos} de una organización, en una consulta."""
    from .models import Organizacion

    return Organizacion.objects.filter(pk=organizacion.pk).aggregate(
        act=Count("actividades__actividad", filter=Q(actividades__vigente=True), distinct=True),
        proy=Count("proyectos__proyecto", filter=Q(proyectos__vigente=True), distinct=True))

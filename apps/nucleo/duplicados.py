"""F26 Ra: buscar antes de crear lugares, comunidades, proyectos, actividades (y tareas) y solicitudes.

Mismo patrón que personas y organizaciones (apps/personas/duplicados.py): solo muestra los posibles repetidos con sus
razones, antes de guardar; «Es distinto, guardar» guarda igual. Nunca bloquea ni fusiona. Cada función hace una o dos
consultas fijas (sin consultas en bucle) y compara sin distinguir mayúsculas ni tildes (unaccent).

Reglas [P]:
- lugar: mismo nombre en la misma comuna;
- comunidad: mismo nombre en la misma comuna o sector;
- proyecto: mismo nombre;
- actividad o tarea: mismo nombre y misma fecha, o mismo nombre en el mismo proyecto;
- solicitud: misma organización o persona con motivo parecido en los últimos 30 días (y, como antes, una abierta con
  ese mismo contacto).
"""
from datetime import timedelta

from django.contrib.postgres.lookups import Unaccent
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q, Value
from django.utils import timezone

TOPE = 10
DIAS_SOLICITUD = 30
UMBRAL_MOTIVO = 0.3


def _limpio(texto):
    return " ".join((texto or "").split())


def _mismo_nombre(qs, nombre, campo="nombre"):
    return qs.filter(**{f"{campo}__unaccent__iexact": nombre})


def lugares_parecidos(nombre, comuna, excluir=None):
    from apps.lugares.models import Lugar

    nombre = _limpio(nombre)
    if not (nombre and comuna):
        return []
    qs = _mismo_nombre(Lugar.objects.filter(direccion__comuna=comuna), nombre).exclude(pk=excluir or 0).select_related("direccion__comuna")
    return [(l, [f"mismo nombre en {l.direccion.comuna.nombre}"]) for l in qs[:TOPE]]


def comunidades_parecidas(nombre, comuna, sector=None, excluir=None):
    from apps.comunidades.models import Comunidad

    nombre = _limpio(nombre)
    if not (nombre and (comuna or sector)):
        return []
    donde = Q(comuna=comuna) if comuna else Q()
    if sector:
        donde |= Q(sector=sector)
    qs = _mismo_nombre(Comunidad.objects.filter(donde), nombre).exclude(pk=excluir or 0).select_related("comuna", "sector")
    salida = []
    for c in qs[:TOPE]:
        if sector and c.sector_id == sector.pk:
            salida.append((c, [f"mismo nombre en el sector {c.sector.nombre}"]))
        else:
            salida.append((c, [f"mismo nombre en {c.comuna.nombre}"]))
    return salida


def proyectos_parecidos(nombre, excluir=None):
    from apps.proyectos.models import Proyecto

    nombre = _limpio(nombre)
    if not nombre:
        return []
    qs = _mismo_nombre(Proyecto.objects.all(), nombre).exclude(pk=excluir or 0)
    return [(p, [f"mismo nombre ({p.get_estado_display().lower()})"]) for p in qs[:TOPE]]


def actividades_parecidas(nombre, fecha=None, proyecto=None, excluir=None):
    """Mismo nombre y misma fecha (programación vigente), o mismo nombre en el mismo proyecto. Dos consultas fijas."""
    from apps.actividades.models import Actividad

    nombre = _limpio(nombre)
    if not nombre or not (fecha or proyecto):
        return []
    base = _mismo_nombre(Actividad.objects.all(), nombre).exclude(pk=excluir or 0).select_related("proyecto")
    encontradas = {}
    if fecha:
        for a in base.filter(agendas__vigente=True, agendas__fecha=fecha).distinct()[:TOPE]:
            encontradas.setdefault(a.pk, (a, []))[1].append(f"mismo nombre y misma fecha ({fecha:%d-%m-%Y})")
    if proyecto:
        for a in base.filter(proyecto=proyecto)[:TOPE]:
            encontradas.setdefault(a.pk, (a, []))[1].append(f"mismo nombre en el proyecto «{proyecto}»")
    return list(encontradas.values())


def solicitudes_parecidas(persona=None, organizacion=None, motivo="", excluir=None):
    """Con la misma persona u organización: las abiertas (SO-E1) y las de los últimos 30 días con motivo parecido."""
    from apps.solicitudes.models import Solicitud

    if not (persona or organizacion):
        return []
    contacto = Q()
    if persona:
        contacto |= Q(persona=persona)
    if organizacion:
        contacto |= Q(organizacion=organizacion)
    base = Solicitud.objects.filter(contacto).exclude(pk=excluir or 0).select_related("estado")
    encontradas = {}
    for s in base.filter(estado__codigo__in=["pendiente", "en_seguimiento"]).order_by("-fecha")[:TOPE]:
        encontradas.setdefault(s.pk, (s, []))[1].append(f"abierta con el mismo contacto ({s.estado.nombre.lower()}, del {s.fecha:%d-%m-%Y})")
    motivo = _limpio(motivo)
    if motivo:
        desde = timezone.localdate() - timedelta(days=DIAS_SOLICITUD)
        recientes = (
            base.filter(fecha__gte=desde).exclude(motivo="")
            .annotate(similitud=TrigramSimilarity(Unaccent("motivo"), Unaccent(Value(motivo))))
            .filter(similitud__gte=UMBRAL_MOTIVO).order_by("-similitud")[:TOPE]
        )
        for s in recientes:
            encontradas.setdefault(s.pk, (s, []))[1].append(f"mismo contacto y motivo parecido ({int(s.similitud * 100)}%), del {s.fecha:%d-%m-%Y}")
    return list(encontradas.values())

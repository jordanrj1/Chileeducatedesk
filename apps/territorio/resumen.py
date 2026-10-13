"""Resumen de un territorio: qué hay y qué se ha hecho en una comuna o en un sector con sus hijos (F23).

Las reglas de «qué es de un territorio» son las de `consultas.py` (lugares, organizaciones y actividades). Aquí solo se cuenta:
todo con un número fijo de consultas agrupadas, sin importar cuántos registros haya.

- Comunidades, organizaciones, lugares y personas residentes: solo registros activos.
- Actividades: todas las del territorio (`actividades_total`); «últimos 12 meses» = programación vigente entre hoy − 365 días y hoy.
- Por sector se cuenta lo directo (lo que tiene exactamente ese sector); lo que no tiene sector va a la fila «Sin sector» de la comuna.
"""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, F, Q, Window
from django.db.models.functions import RowNumber
from django.utils import timezone

from apps.actividades.models import ActividadTerritorio, AgendaActividad, SesionActividad
from apps.comunidades.models import Comunidad
from apps.lugares.models import Lugar
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona, PersonaDireccion

from . import consultas
from .models import Comuna, Sector

DIAS_RECIENTES = 365
DIAS_PROXIMAS = 30
NOMBRES_POR_TIPO = 5
MINUTAS = 5
SIN_PROXIMA = ("cancelada", "suspendida")  # estados cuya agenda vigente no es una próxima actividad


def _filtro_direccion(comuna, sectores, prefijo=""):
    """Filtro de ORM para una dirección que está en los sectores pedidos o, si no hay sectores, en la comuna."""
    if sectores:
        return {f"{prefijo}sector_id__in": sectores}
    return {f"{prefijo}comuna": comuna}


def personas_residentes(comuna=None, sectores=None):
    """Personas activas con una dirección de residencia vigente en la comuna (o en los sectores indicados)."""
    filtro = _filtro_direccion(comuna, sectores, "direcciones__direccion__")
    return Persona.objects.filter(activo=True, direcciones__tipo="residencia", direcciones__vigente=True, **filtro).distinct()


def _en_orden_jerarquico(sectores):
    """Cada sector seguido de sus hijos; los de un mismo nivel, por nombre."""
    ids = {s.pk for s in sectores}
    hijos = defaultdict(list)
    for s in sorted(sectores, key=lambda s: s.nombre.casefold()):
        hijos[s.sector_padre_id if s.sector_padre_id in ids else None].append(s)
    orden, vistos = [], set()

    def bajar(padre_id):
        for s in hijos[padre_id]:
            if s.pk not in vistos:
                vistos.add(s.pk)
                orden.append(s)
                bajar(s.pk)

    bajar(None)
    return orden + [s for s in sectores if s.pk not in vistos]  # solo ocurriría con datos circulares


def _por_sector(filas, ids):
    """Suma los conteos `(sector_id, n)` por sector; lo que no cae en un sector del ámbito va a la clave None."""
    cuenta = defaultdict(int)
    for sector_id, n in filas:
        cuenta[sector_id if sector_id in ids else None] += n
    return cuenta


def _actividades_por_sector(comuna, sectores, ids):
    """`{sector_id | None: {ids de actividad}}`: agenda vigente en un lugar del ámbito o territorio vigente de la actividad."""
    por_sector = defaultdict(set)
    if sectores:
        agendas = AgendaActividad.objects.filter(vigente=True, lugar__direccion__sector_id__in=sectores)
        territorios = ActividadTerritorio.objects.filter(vigente=True, sector_id__in=sectores)
    else:
        agendas = AgendaActividad.objects.filter(vigente=True, lugar__direccion__comuna=comuna)
        territorios = ActividadTerritorio.objects.filter(Q(comuna=comuna) | Q(sector__comuna=comuna), vigente=True)
    for sector_id, actividad_id in agendas.order_by().values_list("lugar__direccion__sector_id", "actividad_id").distinct():
        por_sector[sector_id if sector_id in ids else None].add(actividad_id)
    for sector_id, actividad_id in territorios.order_by().values_list("sector_id", "actividad_id").distinct():
        por_sector[sector_id if sector_id in ids else None].add(actividad_id)
    return por_sector


def _organizaciones_por_tipo(organizaciones):
    """`[(TipoOrganizacion, total, [hasta 5 Organizacion por nombre])]`, en el orden del catálogo; solo tipos con organizaciones."""
    totales = dict(organizaciones.order_by().values_list("tipo_id").annotate(n=Count("pk")))
    fila = Window(RowNumber(), partition_by=F("tipo_id"), order_by=[F("nombre").asc(), F("pk").asc()])
    primeras = organizaciones.annotate(_fila=fila).filter(_fila__lte=NOMBRES_POR_TIPO).order_by("tipo_id", "nombre", "pk")
    grupos = {}
    for o in primeras:
        grupos.setdefault(o.tipo_id, (o.tipo, totales[o.tipo_id], []))[2].append(o)
    return sorted(grupos.values(), key=lambda g: (g[0].orden, g[0].nombre))


def resumen_territorio(comuna=None, sectores=None):
    """Indicadores, organizaciones por tipo, tabla por sector, próximas actividades y últimas minutas de un territorio.

    `sectores` es una lista de ids (el sector y sus hijos, ver `Sector.descendientes_ids`); si se omite se usa la comuna entera.
    Con comuna, `sectores` (la tabla) termina con una fila `{"sector": None}` («Sin sector»); con sectores no la lleva.
    """
    hoy = timezone.localdate()
    en_comuna = not sectores

    filas_sector = Sector.objects.filter(comuna=comuna) if en_comuna else Sector.objects.filter(pk__in=sectores)
    filas_sector = _en_orden_jerarquico(list(filas_sector.select_related("sector_padre__sector_padre")))
    ids = {s.pk for s in filas_sector}

    comunidades = Comunidad.objects.filter(activo=True, **({"comuna": comuna} if en_comuna else {"sector_id__in": sectores}))
    comunidades = _por_sector(comunidades.order_by().values_list("sector_id").annotate(n=Count("pk")), ids)
    organizaciones = consultas.organizaciones_de(comuna, sectores).filter(activo=True)
    por_sector_org = _por_sector(organizaciones.order_by().values_list("direccion__sector_id").annotate(n=Count("pk")), ids)
    lugares = consultas.lugares_de(comuna, sectores).filter(activo=True)
    por_sector_lugar = _por_sector(lugares.order_by().values_list("direccion__sector_id").annotate(n=Count("pk")), ids)
    residentes = PersonaDireccion.objects.filter(
        tipo="residencia", vigente=True, persona__activo=True, **_filtro_direccion(comuna, sectores, "direccion__")
    )
    por_sector_persona = _por_sector(residentes.order_by().values_list("direccion__sector_id").annotate(n=Count("persona_id", distinct=True)), ids)
    actividades = _actividades_por_sector(comuna, sectores, ids)

    recientes = consultas.actividades_de(comuna, sectores).order_by().filter(
        agendas__vigente=True, agendas__fecha__range=(hoy - timedelta(days=DIAS_RECIENTES), hoy)
    )
    del_territorio = consultas.actividades_de(comuna, sectores).order_by().values("pk")

    tabla = [
        {
            "sector": s, "comunidades": comunidades[s.pk], "organizaciones": por_sector_org[s.pk], "lugares": por_sector_lugar[s.pk],
            "personas": por_sector_persona[s.pk], "actividades": len(actividades[s.pk]),
        }
        for s in filas_sector
    ]
    if en_comuna:
        tabla.append({
            "sector": None, "comunidades": comunidades[None], "organizaciones": por_sector_org[None], "lugares": por_sector_lugar[None],
            "personas": por_sector_persona[None], "actividades": len(actividades[None]),
        })

    proximas = (
        AgendaActividad.objects.filter(vigente=True, fecha__range=(hoy, hoy + timedelta(days=DIAS_PROXIMAS)), actividad_id__in=del_territorio)
        .exclude(actividad__estado__codigo__in=SIN_PROXIMA)
        .select_related("actividad__estado", "lugar")
        .order_by("fecha", "hora_inicio", "pk")
    )
    minutas = (
        SesionActividad.objects.filter(vigente=True, fecha__isnull=False, actividad_id__in=del_territorio)
        .select_related("actividad")
        .order_by("-fecha", "-numero", "-pk")[:MINUTAS]
    )
    return {
        "comunidades": sum(comunidades.values()),
        "organizaciones": sum(por_sector_org.values()),
        "personas": personas_residentes(comuna, sectores).count(),
        "lugares": sum(por_sector_lugar.values()),
        "actividades_12m": recientes.distinct().count(),
        "actividades_total": len(set().union(*actividades.values())),
        "organizaciones_por_tipo": _organizaciones_por_tipo(organizaciones),
        "sectores": tabla,
        "proximas": list(proximas),
        "minutas": list(minutas),
    }


def presencia_por_comuna(region=None):
    """Comunas con presencia de la Fundación: `[{"comuna", "comunidades", "organizaciones", "personas", "actividades_12m", "total", ...}]`.

    Solo comunas con `total > 0` (suma de comunidades, organizaciones, lugares, personas y actividades de siempre), ordenadas por
    actividades de los últimos 12 meses, luego por total y luego por nombre. Con `region` solo las de esa región.
    Número fijo de consultas, sin importar cuántas comunas haya.
    """
    hoy = timezone.localdate()
    comunas = Comuna.objects.select_related("provincia__region").order_by("nombre")
    if region:
        comunas = comunas.filter(provincia__region=region)
    comunas = list(comunas)
    ids = {c.pk for c in comunas}

    def en_region(ruta):
        return {f"{ruta}provincia__region": region} if region else {}

    def conteo(qs, clave, contar="pk", distinto=False):
        return {k: n for k, n in qs.order_by().values_list(clave).annotate(n=Count(contar, distinct=distinto)) if k in ids}

    comunidades = conteo(Comunidad.objects.filter(activo=True, **en_region("comuna__")), "comuna_id")
    lugares = conteo(Lugar.objects.filter(activo=True, **en_region("direccion__comuna__")), "direccion__comuna_id")
    personas = conteo(
        PersonaDireccion.objects.filter(tipo="residencia", vigente=True, persona__activo=True, **en_region("direccion__comuna__")),
        "direccion__comuna_id", "persona_id", distinto=True,
    )
    # Una organización es de la comuna de su dirección y, si es municipalidad, de su comuna municipal (una vez si coinciden)
    organizaciones = conteo(Organizacion.objects.filter(activo=True, **en_region("direccion__comuna__")), "direccion__comuna_id")
    municipales = Organizacion.objects.filter(activo=True, comuna_municipal__isnull=False, **en_region("comuna_municipal__")).filter(
        Q(direccion__isnull=True) | ~Q(direccion__comuna_id=F("comuna_municipal_id"))
    )
    for comuna_id, n in conteo(municipales, "comuna_municipal_id").items():
        organizaciones[comuna_id] = organizaciones.get(comuna_id, 0) + n

    de_la_comuna = defaultdict(set)
    agendas = AgendaActividad.objects.filter(vigente=True, **en_region("lugar__direccion__comuna__"))
    for comuna_id, actividad_id in agendas.order_by().values_list("lugar__direccion__comuna_id", "actividad_id").distinct():
        de_la_comuna[comuna_id].add(actividad_id)
    territorios = ActividadTerritorio.objects.filter(vigente=True).filter(
        Q(comuna__isnull=False, **en_region("comuna__")) | Q(sector__isnull=False, **en_region("sector__comuna__"))
    )
    for comuna_id, de_sector, actividad_id in territorios.order_by().values_list("comuna_id", "sector__comuna_id", "actividad_id").distinct():
        de_la_comuna[comuna_id or de_sector].add(actividad_id)
    recientes = set(
        AgendaActividad.objects.filter(vigente=True, fecha__range=(hoy - timedelta(days=DIAS_RECIENTES), hoy)).values_list("actividad_id", flat=True)
    )

    filas = []
    for c in comunas:
        actividades = de_la_comuna.get(c.pk, set())
        fila = {
            "comuna": c, "comunidades": comunidades.get(c.pk, 0), "organizaciones": organizaciones.get(c.pk, 0), "lugares": lugares.get(c.pk, 0),
            "personas": personas.get(c.pk, 0), "actividades_total": len(actividades), "actividades_12m": len(actividades & recientes),
        }
        fila["total"] = fila["comunidades"] + fila["organizaciones"] + fila["lugares"] + fila["personas"] + fila["actividades_total"]
        if fila["total"]:
            filas.append(fila)
    return sorted(filas, key=lambda f: (-f["actividades_12m"], -f["total"]))  # estable: el empate queda por nombre (viene ordenado)

"""Reconocer sectores escritos de distintas formas (TE-06): «Pobl. San Pedro» = «Población San Pedro»."""
import re
import unicodedata

from django.contrib.postgres.search import TrigramSimilarity

from .models import Sector, SectorAlias

ABREVIATURAS = {"pobl": "poblacion", "pob": "poblacion", "vla": "villa", "vill": "villa", "sect": "sector", "sec": "sector", "et": "etapa", "etp": "etapa", "bo": "barrio", "bº": "barrio", "nro": "", "n": ""}
UMBRAL_PARECIDO = 0.45


def normalizar(texto):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    palabras = re.sub(r"[^a-z0-9]+", " ", t).split()
    return " ".join(p for p in (ABREVIATURAS.get(w, w) for w in palabras) if p)


def mismo_sector(comuna, nombre, padre=None):
    """Sector existente cuyo nombre o nombre alternativo coincide tras normalizar, en el mismo nivel.

    Reconoce también los desactivados, para avisar en vez de crear uno repetido."""
    clave = normalizar(nombre)
    if not clave:
        return None
    qs = Sector.objects.filter(comuna=comuna, sector_padre=padre)
    for s in qs:
        if normalizar(s.nombre) == clave:
            return s
    for a in SectorAlias.objects.filter(sector__in=qs).select_related("sector"):
        if normalizar(a.nombre) == clave:
            return a.sector
    return None


def sectores_parecidos(comuna, nombre, padre=None, excluir=None):
    """Parecidos entre los activos (para avisar, nunca para decidir solo)."""
    qs = Sector.objects.filter(comuna=comuna, sector_padre=padre, activo=True).annotate(sim=TrigramSimilarity("nombre", nombre)).filter(sim__gte=UMBRAL_PARECIDO)
    if excluir:
        qs = qs.exclude(pk=excluir)
    return list(qs.order_by("-sim")[:5])

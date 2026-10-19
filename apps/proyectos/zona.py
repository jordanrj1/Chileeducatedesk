"""Enlaza la «zona» escrita a mano en un proyecto con su comuna o sector (ProyectoTerritorio).
Solo enlaza si el texto, sin tildes ni mayúsculas, es exactamente el nombre de una sola comuna o de un solo sector activo
(o uno de sus nombres alternativos). El texto nunca se borra y un proyecto que ya tiene territorios no se toca, así que
se puede repetir sin duplicar. Recibe las clases para servir también en la migración."""
import re
import unicodedata


def _clave(texto):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", t).split())


def vincular_zonas(Proyecto, ProyectoTerritorio, Comuna, Sector, SectorAlias, simular=False):
    """Devuelve [(proyecto, nivel, territorio)] con lo enlazado (o lo que se enlazaría si `simular`). Número fijo de consultas."""
    pendientes = list(Proyecto.objects.exclude(zona="").exclude(pk__in=ProyectoTerritorio.objects.values("proyecto_id")))
    if not pendientes:
        return []
    candidatos = {}  # clave → {(nivel, id)}
    for c in Comuna.objects.only("pk", "nombre"):
        candidatos.setdefault(_clave(c.nombre), set()).add(("comuna", c.pk))
    for s in Sector.objects.filter(activo=True).only("pk", "nombre"):
        candidatos.setdefault(_clave(s.nombre), set()).add(("sector", s.pk))
    for a in SectorAlias.objects.filter(sector__activo=True).only("sector_id", "nombre"):
        candidatos.setdefault(_clave(a.nombre), set()).add(("sector", a.sector_id))
    objetos = {"comuna": Comuna, "sector": Sector}
    enlazados = []
    for p in pendientes:
        encontrados = candidatos.get(_clave(p.zona), set())
        if len(encontrados) != 1:
            continue  # sin coincidencia o ambiguo (p. ej. un sector «Centro» en varias comunas): queda el texto para revisarlo
        (nivel, pk), = encontrados
        enlazados.append((p, nivel, pk))
    if not simular:
        ProyectoTerritorio.objects.bulk_create([ProyectoTerritorio(proyecto=p, **{f"{nivel}_id": pk}) for p, nivel, pk in enlazados])
    por_nivel = {n: objetos[n].objects.in_bulk({pk for _, m, pk in enlazados if m == n}) for n in objetos}
    return [(p, nivel, por_nivel[nivel][pk]) for p, nivel, pk in enlazados]

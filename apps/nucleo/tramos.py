"""Intérprete del texto antiguo de «rango etario» (escrito a mano) a tramos de edad del catálogo.
Es conservador: solo marca tramos cuando reconoce edades («15 a 29», «60 o más», «mayores de 18») o palabras claras
(«jóvenes», «personas mayores»). Ante un texto que no entiende devuelve un conjunto vacío y el texto queda por revisar.
Lo usan las migraciones de datos de actividades y comunidades: no cambies su firma ni lo borres."""
import re
import unicodedata

INFINITO = 999

# Palabras clave → código del tramo. Se buscan después de quitar tildes y pasar a minúsculas.
PALABRAS = [
    (r"\bprimera infancia\b|\bparvul\w*|\blactantes?\b|\bjardin infantil\b", "primera_infancia"),
    (r"\bnin(?:o|a|os|as|ez)\b", "ninez"),
    (r"\badolescen\w*", "adolescencia"),
    (r"\bjoven(?:es)?\b|\bjuvenil(?:es)?\b|\bjuventud\b", "jovenes"),
    (r"\badult[oa]s?\b(?!\s+mayor)", "personas_adultas"),
    (r"\badult[oa]s?\s+mayor(?:es)?\b|\btercera edad\b|\bmayor(?:es)?\b(?!\s+de\s+(?:edad|\d))", "personas_mayores"),
]
# Rangos de edad: «15 a 29», «15-29», «entre 15 y 29». No se leen niveles escolares («1 a 4 medio»).
_NIVEL = r"(?!\s*(?:\.?\s*o\b|basic|medi|grado|curso|semestre|nivel))"
RANGO = re.compile(r"(?:\bentre\s+(\d{1,3})\s+y\s+(\d{1,3})|\b(\d{1,3})\s*(?:a|al|-|hasta)\s*(\d{1,3}))\b" + _NIVEL)
DESDE = re.compile(r"\b(?:mayores\s+de|mas\s+de|sobre(?:\s+los)?|desde(?:\s+los)?)\s+(\d{1,3})\b|\b(\d{1,3})\s*(?:anos\s+)?(?:o|y)\s+mas\b|\b(\d{1,3})\s*\+")
HASTA = re.compile(r"\b(?:menores\s+de|menos\s+de)\s+(\d{1,3})\b")
MAYORES_DE_EDAD = re.compile(r"\bmayor(?:es)?\s+de\s+edad\b")
MENORES_DE_EDAD = re.compile(r"\bmenor(?:es)?\s+de\s+edad\b")


def normalizar(texto):
    base = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(base.lower().split())


def _intervalos(texto):
    """Intervalos de edad [desde, hasta] que el texto nombra con números."""
    res = []
    for m in RANGO.finditer(texto):
        a, b = (int(x) for x in (m.group(1, 2) if m.group(1) else m.group(3, 4)))
        if a <= b <= 120:
            res.append((a, b))
    for m in DESDE.finditer(texto):
        n = int(next(g for g in m.groups() if g))
        if n <= 120:
            res.append((n, INFINITO))
    for m in HASTA.finditer(texto):
        n = int(m.group(1))
        if 0 < n <= 120:
            res.append((0, n - 1))
    if MAYORES_DE_EDAD.search(texto):
        res.append((18, INFINITO))
    if MENORES_DE_EDAD.search(texto):
        res.append((0, 17))
    return res


def interpretar(texto, tramos):
    """`tramos`: [(codigo, edad_min, edad_max)] del catálogo (None = sin límite). Devuelve el conjunto de códigos reconocidos."""
    t = normalizar(texto)
    if not t:
        return set()
    codigos = {c for c, _, _ in tramos}
    res = set()
    for a, b in _intervalos(t):
        for codigo, minimo, maximo in tramos:
            if minimo is None and maximo is None:
                continue
            lo, hi = minimo or 0, INFINITO if maximo is None else maximo
            if lo <= b and hi >= a:
                res.add(codigo)
    # «mayores de edad» y «menores de edad» ya se leyeron como edades: no cuentan como «mayores»
    sin_edad_legal = MENORES_DE_EDAD.sub(" ", MAYORES_DE_EDAD.sub(" ", t))
    for patron, codigo in PALABRAS:
        if codigo in codigos and re.search(patron, sin_edad_legal):
            res.add(codigo)
    return res


def asignar_desde_texto(Modelo, Tramo):
    """Para las migraciones: a cada registro con texto en `rango_etario` y sin tramos le marca los que se reconocen.
    No borra el texto (queda como «texto anterior» por revisar) y no toca registros que ya tienen tramos: se puede repetir."""
    filas = list(Tramo.objects.values_list("pk", "codigo", "edad_min", "edad_max"))
    pk_de = {codigo: pk for pk, codigo, _, _ in filas}
    tramos = [(codigo, minimo, maximo) for _, codigo, minimo, maximo in filas]
    for obj in Modelo.objects.exclude(rango_etario="").filter(tramos_etarios__isnull=True):
        codigos = interpretar(obj.rango_etario, tramos)
        if codigos:
            obj.tramos_etarios.add(*(pk_de[c] for c in codigos))

"""Lee y carga la lista oficial de regiones, provincias y comunas de Chile (códigos CUT) desde un CSV.
Primero revisa todo el archivo y junta los errores: si hay alguno, no carga nada. Después agrega lo nuevo y actualiza
nombre y padre por código, nivel por nivel y con un número fijo de consultas. Nunca borra (la Región Demo sigue igual).
La usa el comando `cargar_territorio`; el archivo oficial está en `datos/cut_chile.csv` (ver `datos/LEEME.md`)."""
import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

from django.db import transaction

from .models import Comuna, Provincia, Region, es_codigo_oficial

ARCHIVO_OFICIAL = Path(__file__).resolve().parent / "datos" / "cut_chile.csv"
COLUMNAS = ["region_codigo", "region_nombre", "provincia_codigo", "provincia_nombre", "comuna_codigo", "comuna_nombre"]
NIVELES = [("region", "región", 2), ("provincia", "provincia", 3), ("comuna", "comuna", 5)]  # (columna, nombre, dígitos)
TOTALES_OFICIALES = {"regiones": 16, "provincias": 56, "comunas": 346}
MAX_ERRORES = 40  # cuántos errores se muestran; el resto se cuenta
NOMBRE_PADRE = {"region": "región", "provincia": "provincia"}


class ErrorCarga(Exception):
    """El archivo no se puede cargar. Lleva todos los errores encontrados, cada uno con su fila."""

    def __init__(self, errores):
        self.errores = list(errores)
        lineas = self.errores[:MAX_ERRORES]
        if len(self.errores) > MAX_ERRORES:
            lineas.append(f"… y {len(self.errores) - MAX_ERRORES} errores más.")
        super().__init__("No se cargó nada. Corrige el archivo y vuelve a intentarlo:\n" + "\n".join(f"- {e}" for e in lineas))


@dataclass(frozen=True)
class Fila:
    numero: int  # fila de la planilla (la 1 es el encabezado)
    region_codigo: str
    region_nombre: str
    provincia_codigo: str
    provincia_nombre: str
    comuna_codigo: str
    comuna_nombre: str


def comunas_oficiales():
    """Comunas de la lista oficial (regiones 01 a 16): sin la Región Demo ni las de prueba."""
    return Comuna.objects.filter(codigo__regex=r"^(0[1-9]|1[0-6])[0-9]{3}$")


def _texto(ruta):
    try:
        datos = Path(ruta).read_bytes()
    except OSError as e:
        raise ErrorCarga([f"No se pudo abrir el archivo «{ruta}»: {e.strerror or e}."])
    try:
        return datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    try:
        return datos.decode("cp1252")  # planilla guardada con Excel en Windows
    except UnicodeDecodeError:
        raise ErrorCarga(["No se pudo leer el texto del archivo. Guárdalo como «CSV UTF-8 (delimitado por comas)»."])


def _revisar_fila(numero, valores):
    """(códigos con ceros a la izquierda, [problemas]) de una fila."""
    codigos, problemas = {}, []
    for columna, nombre, digitos in NIVELES:
        crudo = valores[f"{columna}_codigo"]
        if not crudo:
            problemas.append(f"falta el código de la {nombre}")
        elif not (crudo.isascii() and crudo.isdigit()):
            problemas.append(f"el código de la {nombre} «{crudo}» debe tener solo números")
        elif len(crudo) > digitos:
            problemas.append(f"el código de la {nombre} «{crudo}» tiene más de {digitos} dígitos")
        else:
            codigos[columna] = crudo.zfill(digitos)  # Excel borra el cero inicial: «8112» es «08112»
        if not valores[f"{columna}_nombre"]:
            problemas.append(f"falta el nombre de la {nombre}")
    if len(codigos) == len(NIVELES):
        region, provincia, comuna = codigos["region"], codigos["provincia"], codigos["comuna"]
        if not provincia.startswith(region):
            problemas.append(f"la provincia {provincia} no pertenece a la región {region} (su código debe empezar con {region})")
        if not comuna.startswith(provincia):
            problemas.append(f"la comuna {comuna} no pertenece a la provincia {provincia} (su código debe empezar con {provincia})")
    return codigos, [f"Fila {numero}: {p}." for p in problemas]


def leer(ruta=ARCHIVO_OFICIAL):
    """Lee y revisa todo el archivo. Devuelve las filas o lanza `ErrorCarga` con todos los errores juntos.

    Acepta el CSV separado por comas o por punto y coma (Excel en español) y los códigos sin ceros a la izquierda.
    Revisa: columnas, códigos numéricos, que cada comuna sea de su provincia y cada provincia de su región, comunas repetidas,
    un mismo código con dos nombres y, si el archivo trae códigos oficiales, que estén las 16 regiones, 56 provincias y 346 comunas.
    """
    texto = _texto(ruta)
    primera = texto.split("\n", 1)[0]
    lector = csv.DictReader(io.StringIO(texto), delimiter=";" if primera.count(";") > primera.count(",") else ",")
    lector.fieldnames = [(c or "").strip().lower() for c in (lector.fieldnames or [])]
    faltan = [c for c in COLUMNAS if c not in lector.fieldnames]
    if faltan:
        raise ErrorCarga([f"Faltan columnas: {', '.join(faltan)}. El archivo debe tener: {', '.join(COLUMNAS)}."])

    filas, errores = [], []
    comuna_en_fila, nombres = {}, {"región": {}, "provincia": {}}
    for numero, crudo in enumerate(lector, start=2):
        valores = {c: (crudo.get(c) or "").strip() for c in COLUMNAS}
        if not any(valores.values()):
            continue  # fila vacía (Excel suele dejarlas al final)
        codigos, problemas = _revisar_fila(numero, valores)
        if problemas:
            errores += problemas
            continue
        comuna = codigos["comuna"]
        if comuna in comuna_en_fila:
            errores.append(f"Fila {numero}: la comuna {comuna} está repetida (ya aparece en la fila {comuna_en_fila[comuna]}).")
            continue
        comuna_en_fila[comuna] = numero
        for nivel, codigo, nombre in (("región", codigos["region"], valores["region_nombre"]), ("provincia", codigos["provincia"], valores["provincia_nombre"])):
            previo = nombres[nivel].setdefault(codigo, (nombre, numero))
            if previo[0] != nombre:
                errores.append(f"Fila {numero}: la {nivel} {codigo} aparece con dos nombres: «{previo[0]}» (fila {previo[1]}) y «{nombre}».")
        filas.append(Fila(numero, codigos["region"], valores["region_nombre"], codigos["provincia"], valores["provincia_nombre"], comuna, valores["comuna_nombre"]))

    if not errores and not filas:
        errores.append("El archivo no trae ninguna comuna.")
    oficiales = [f for f in filas if es_codigo_oficial(f.region_codigo)]
    if not errores and oficiales:
        hay = {
            "regiones": len({f.region_codigo for f in oficiales}),
            "provincias": len({f.provincia_codigo for f in oficiales}),
            "comunas": len({f.comuna_codigo for f in oficiales}),
        }
        if hay != TOTALES_OFICIALES:
            errores.append(
                f"La lista oficial está incompleta o le sobran filas: trae {hay['regiones']} regiones, {hay['provincias']} provincias "
                f"y {hay['comunas']} comunas, y deben ser {TOTALES_OFICIALES['regiones']}, {TOTALES_OFICIALES['provincias']} y {TOTALES_OFICIALES['comunas']}."
            )
    if errores:
        raise ErrorCarga(errores)
    return filas


def comunas_que_faltan(filas):
    """Cuántas comunas del archivo no están en la base (una sola consulta)."""
    codigos = {f.comuna_codigo for f in filas}
    return len(codigos) - Comuna.objects.filter(codigo__in=codigos).count()


@dataclass
class Resultado:
    """Lo que cambió (o cambiaría, al simular) en un nivel: regiones, provincias o comunas."""

    titulo: str
    nuevas: list = field(default_factory=list)  # «08112 Hualpén»
    actualizadas: list = field(default_factory=list)  # «08112: «Hualpen» → «Hualpén»»
    sin_cambios: int = 0

    def linea(self):
        n, a = len(self.nuevas), len(self.actualizadas)
        return f"{self.titulo}: {n} nueva{'s' if n != 1 else ''}, {a} actualizada{'s' if a != 1 else ''}, {self.sin_cambios} sin cambios."


def _nivel(modelo, titulo, deseado, padre=None, pk_padres=None, simular=False):
    """Agrega y actualiza un nivel por código. `deseado` = {código: (nombre, código del padre)}.

    Tres consultas como máximo (leer, agregar y actualizar), sin importar cuántas filas haya. Devuelve (Resultado, {código: pk}).
    """
    existentes = modelo.objects.filter(codigo__in=deseado)
    existentes = {o.codigo: o for o in (existentes.select_related(padre) if padre else existentes)}
    resultado, nuevas, cambiadas = Resultado(titulo), [], []
    for codigo, (nombre, codigo_padre) in sorted(deseado.items()):
        obj = existentes.get(codigo)
        if obj is None:
            nuevas.append(modelo(codigo=codigo, nombre=nombre, **({f"{padre}_id": pk_padres.get(codigo_padre)} if padre else {})))
            resultado.nuevas.append(f"{codigo} {nombre}")
            continue
        cambios = []
        if obj.nombre != nombre:
            cambios.append(f"«{obj.nombre}» → «{nombre}»")
            obj.nombre = nombre
        if padre and getattr(obj, padre).codigo != codigo_padre:
            cambios.append(f"pasa de la {NOMBRE_PADRE[padre]} {getattr(obj, padre).codigo} a la {codigo_padre}")
            setattr(obj, f"{padre}_id", pk_padres.get(codigo_padre))
        if cambios:
            cambiadas.append(obj)
            resultado.actualizadas.append(f"{codigo}: {', '.join(cambios)}")
        else:
            resultado.sin_cambios += 1
    if not simular:
        modelo.objects.bulk_create(nuevas)
        if cambiadas:
            modelo.objects.bulk_update(cambiadas, ["nombre", padre] if padre else ["nombre"])
    return resultado, {o.codigo: o.pk for o in [*existentes.values(), *nuevas]}


def cargar(filas, simular=False):
    """Carga las filas ya revisadas por `leer`: regiones, luego provincias, luego comunas. Todo o nada; nunca borra.

    Con `simular` no escribe nada y devuelve lo que cambiaría. Devuelve [Resultado de regiones, provincias, comunas].
    """
    regiones = {f.region_codigo: (f.region_nombre, None) for f in filas}
    provincias = {f.provincia_codigo: (f.provincia_nombre, f.region_codigo) for f in filas}
    comunas = {f.comuna_codigo: (f.comuna_nombre, f.provincia_codigo) for f in filas}
    with transaction.atomic():
        r_regiones, pk_regiones = _nivel(Region, "Regiones", regiones, simular=simular)
        r_provincias, pk_provincias = _nivel(Provincia, "Provincias", provincias, "region", pk_regiones, simular)
        r_comunas, _ = _nivel(Comuna, "Comunas", comunas, "provincia", pk_provincias, simular)
    return [r_regiones, r_provincias, r_comunas]

"""Pruebas automáticas de la lista oficial de regiones, provincias y comunas (códigos CUT): el archivo del repositorio,
la carga con `cargar_territorio` (sin duplicar, sin borrar la Región Demo, `--si-falta` y `--simular`), el rechazo de un
archivo con errores sin cargar nada, y el aviso de /territorio cuando falta la lista oficial. Los nombres de prueba son ficticios."""
import csv
import io
import re

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.territorio.carga import ARCHIVO_OFICIAL, COLUMNAS, TOTALES_OFICIALES, ErrorCarga, comunas_oficiales, leer
from apps.territorio.models import Comuna, Provincia, Region

pytestmark = pytest.mark.django_db


def _cargar(*args):
    salida = io.StringIO()
    call_command("cargar_territorio", *args, stdout=salida)
    return salida.getvalue()


def _filas_oficiales():
    with open(ARCHIVO_OFICIAL, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _escribir(ruta, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)
    return str(ruta)


def _conteo():
    return Region.objects.count(), Provincia.objects.count(), Comuna.objects.count()


# ---------- el archivo del repositorio ----------

def test_el_archivo_oficial_es_coherente():
    filas = leer(ARCHIVO_OFICIAL)
    assert len(filas) == 346 == TOTALES_OFICIALES["comunas"]
    assert len({f.region_codigo for f in filas}) == 16 and len({f.provincia_codigo for f in filas}) == 56
    assert len({f.comuna_codigo for f in filas}) == 346  # sin repetidos
    assert all(f.comuna_codigo.startswith(f.provincia_codigo) and f.provincia_codigo.startswith(f.region_codigo) for f in filas)
    hualpen = next(f for f in filas if f.comuna_codigo == "08112")
    assert (hualpen.comuna_nombre, hualpen.provincia_codigo, hualpen.provincia_nombre, hualpen.region_codigo, hualpen.region_nombre) == (
        "Hualpén", "081", "Concepción", "08", "Región del Biobío"
    )


def test_leer_rellena_los_ceros_que_borra_excel(tmp_path):
    """Una planilla guardada desde Excel deja «8112» en vez de «08112»: se lee igual que el archivo original."""
    sin_ceros = [{**f, **{c: str(int(f[c])) for c in ("region_codigo", "provincia_codigo", "comuna_codigo")}} for f in _filas_oficiales()]
    assert sin_ceros[0]["region_codigo"] == "1"
    leidas = leer(_escribir(tmp_path / "excel.csv", sin_ceros))
    assert [(f.region_codigo, f.provincia_codigo, f.comuna_codigo) for f in leidas] == [
        (f.region_codigo, f.provincia_codigo, f.comuna_codigo) for f in leer(ARCHIVO_OFICIAL)
    ]


# ---------- carga ----------

def test_carga_oficial_con_hualpen_y_sin_duplicar(comuna):
    """Con la Región Demo ya cargada (código 99): se agregan las 16/56/346 oficiales y la Demo sigue igual."""
    salida = _cargar()
    assert comunas_oficiales().count() == 346
    assert Region.objects.filter(codigo__regex=r"^(0[1-9]|1[0-6])$").count() == 16
    assert Provincia.objects.filter(codigo__regex=r"^(0[1-9]|1[0-6])\d$").count() == 56
    hualpen = Comuna.objects.select_related("provincia__region").get(codigo="08112")
    assert hualpen.nombre == "Hualpén" and hualpen.provincia.codigo == "081" and hualpen.provincia.nombre == "Concepción"
    assert hualpen.provincia.region.codigo == "08" and hualpen.provincia.region.nombre == "Región del Biobío"
    assert "346 nuevas" in salida

    antes = _conteo()
    salida = _cargar()  # de nuevo: no duplica nada
    assert _conteo() == antes == (17, 57, 347)  # las oficiales más la de demostración
    assert "346 sin cambios" in salida and "0 nuevas" in salida
    comuna.refresh_from_db()
    assert comuna.nombre == "Comuna Ficticia" and comuna.provincia.region.codigo == "99"


def test_carga_actualiza_nombres_por_codigo(tmp_path):
    _cargar()
    hualpen = Comuna.objects.get(codigo="08112")
    Comuna.objects.filter(pk=hualpen.pk).update(nombre="Hualpen")  # escrito sin tilde por una carga antigua
    salida = _cargar()
    hualpen.refresh_from_db()
    assert hualpen.nombre == "Hualpén" and Comuna.objects.count() == 346
    assert "1 actualizada" in salida and "«Hualpen» → «Hualpén»" in salida


def test_si_falta_solo_carga_cuando_falta_alguna_comuna(comuna):
    salida = _cargar("--si-falta")  # solo está la Demo: carga
    assert comunas_oficiales().count() == 346 and "346 nuevas" in salida
    Comuna.objects.filter(codigo="08112").update(nombre="Nombre Cambiado Ficticio")
    salida = _cargar("--si-falta")  # ya están todas: no toca nada
    assert "no se cambió nada" in salida
    assert Comuna.objects.get(codigo="08112").nombre == "Nombre Cambiado Ficticio"


def test_si_falta_completa_una_lista_a_medias():
    region = Region.objects.create(codigo="08", nombre="Región del Biobío")
    provincia = Provincia.objects.create(region=region, codigo="081", nombre="Concepción")
    Comuna.objects.create(provincia=provincia, codigo="08112", nombre="Hualpén")  # una sola, creada a mano
    _cargar("--si-falta")
    assert comunas_oficiales().count() == 346 and Comuna.objects.filter(codigo="08112").count() == 1


def test_simular_no_guarda_nada(comuna):
    antes = _conteo()
    salida = _cargar("--simular")
    assert _conteo() == antes
    assert "Simulación" in salida and "346 nuevas" in salida and "no se guardó nada" in salida


def test_archivo_con_errores_se_rechaza_sin_cargar_nada(tmp_path):
    filas = _filas_oficiales()
    filas[10] = {**filas[10], "comuna_codigo": "09999"}  # una comuna que no es de su provincia
    filas[30] = {**filas[30], "provincia_codigo": "x81"}  # un código que no es número
    filas.append(dict(filas[0]))  # una comuna repetida al final
    with pytest.raises(CommandError) as error:
        _cargar(_escribir(tmp_path / "con_errores.csv", filas))
    mensaje = str(error.value)
    assert "Fila 12" in mensaje and "no pertenece a la provincia" in mensaje
    assert "Fila 32" in mensaje and "solo números" in mensaje
    assert "Fila 348" in mensaje and "repetida" in mensaje and "fila 2" in mensaje
    assert _conteo() == (0, 0, 0)  # no se cargó ni una fila de las buenas


def test_lista_oficial_incompleta_se_rechaza(tmp_path):
    """Si el archivo trae códigos oficiales, debe traer la lista completa: un archivo cortado no se carga a medias."""
    cortado = _filas_oficiales()[:-5]
    with pytest.raises(CommandError) as error:
        _cargar(_escribir(tmp_path / "cortado.csv", cortado))
    assert "341 comunas" in str(error.value) and "346" in str(error.value)
    assert _conteo() == (0, 0, 0)


def test_mismo_codigo_con_dos_nombres_se_rechaza(tmp_path):
    f = tmp_path / "dos_nombres.csv"
    f.write_text(
        "region_codigo,region_nombre,provincia_codigo,provincia_nombre,comuna_codigo,comuna_nombre\n"
        "98,Región Ficticia,981,Provincia Uno,98101,Comuna Uno\n"
        "98,Región Ficticia,981,Provincia Otra,98102,Comuna Dos\n",
        encoding="utf-8",
    )
    with pytest.raises(ErrorCarga) as error:
        leer(str(f))
    assert "981" in str(error.value) and "Provincia Otra" in str(error.value)


def test_archivo_inexistente_da_error_claro(tmp_path):
    with pytest.raises(CommandError) as error:
        _cargar(str(tmp_path / "no_existe.csv"))
    assert "No se pudo abrir" in str(error.value)


# ---------- aviso en /territorio ----------

def test_indice_avisa_que_falta_la_lista_oficial_aunque_exista_la_demo(cg, comuna):
    html = cg.get("/territorio").content.decode()
    assert "Falta la lista oficial" in html and "cargar_territorio" in html
    assert "De demostración" in html  # la región 99 se distingue de las oficiales
    assert "Falta la lista oficial" in cg.get("/territorio?q=hualp").content.decode()  # también al buscar una comuna que no está


def test_indice_sin_aviso_con_la_lista_oficial(cg, comuna, django_assert_max_num_queries):
    cg.get("/territorio")  # calienta la sesión
    with CaptureQueriesContext(connection) as solo_demo:
        cg.get("/territorio")
    _cargar()
    with django_assert_max_num_queries(len(solo_demo)):  # 346 comunas más no suman consultas
        r = cg.get("/territorio")
    html = r.content.decode()
    assert "Falta la lista oficial" not in html and "incompleta" not in html
    assert "Región del Biobío" in html and len(r.context["regiones"]) == 17
    assert html.count("De demostración") == 1  # solo la Región de Prueba
    assert "Hualpén" in cg.get("/territorio?q=hualpen").content.decode()


def test_indice_avisa_lista_oficial_incompleta(cg):
    region = Region.objects.create(codigo="08", nombre="Región del Biobío")
    provincia = Provincia.objects.create(region=region, codigo="081", nombre="Concepción")
    Comuna.objects.create(provincia=provincia, codigo="08112", nombre="Hualpén")
    texto = re.sub(r"\s+", " ", cg.get("/territorio").content.decode())
    assert "La lista oficial está incompleta" in texto and "1 de 346" in texto

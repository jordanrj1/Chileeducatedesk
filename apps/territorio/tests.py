"""Pruebas automáticas del territorio: sectores dentro de sectores, sector de la comuna correcta,
cascada de opciones, crear sector sin salir del formulario, nombres alternativos y carga oficial."""
import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.territorio.forms import DireccionForm
from apps.territorio.models import Comuna, Direccion, Region, Sector

pytestmark = pytest.mark.django_db


def test_sector_jerarquico(comuna):
    padre = Sector.objects.create(comuna=comuna, nombre="San Pedro de la Costa", tipo="sector")
    hijo = Sector.objects.create(comuna=comuna, nombre="Etapa 1", tipo="etapa", sector_padre=padre)
    assert str(hijo) == "San Pedro de la Costa › Etapa 1"


def test_sector_padre_misma_comuna(comuna):
    from apps.territorio.models import Provincia

    otra = Comuna.objects.create(provincia=comuna.provincia, codigo="99002", nombre="Otra Comuna")
    padre = Sector.objects.create(comuna=otra, nombre="X")
    with pytest.raises(ValidationError):
        Sector(comuna=comuna, nombre="Y", sector_padre=padre).full_clean()


def test_el_sector_debe_pertenecer_a_la_comuna(comuna):
    otra = Comuna.objects.create(provincia=comuna.provincia, codigo="99002", nombre="Otra Comuna")
    sector = Sector.objects.create(comuna=otra, nombre="Villa Lejana", tipo="villa")
    with pytest.raises(ValidationError):
        Direccion(calle="A", comuna=comuna, sector=sector).full_clean()
    Direccion(calle="A", comuna=otra, sector=sector).full_clean()


def test_formulario_direccion_rechaza_sector_de_otra_comuna(comuna):
    otra = Comuna.objects.create(provincia=comuna.provincia, codigo="99002", nombre="Otra Comuna")
    sector = Sector.objects.create(comuna=otra, nombre="Villa Lejana", tipo="villa")
    f = DireccionForm({"calle": "A", "comuna": comuna.pk, "sector": sector.pk})
    assert not f.is_valid() and "sector" in f.errors


def test_opciones_de_sector_por_comuna(cg, comuna):
    Sector.objects.create(comuna=comuna, nombre="Villa Uno", tipo="villa")
    html = cg.get(f"/territorio/sectores?comuna={comuna.pk}").content.decode()
    assert "Villa Uno" in html


def test_agregar_sector_desde_la_interfaz(cg, comuna):
    r = cg.post(f"/territorio/comuna/{comuna.pk}/sectores/nuevo", {"nombre": "Población Nueva", "tipo": "poblacion"})
    assert r.status_code == 302 and comuna.sectores.count() == 1
    r = cg.post(f"/territorio/comuna/{comuna.pk}/sectores/nuevo", {"nombre": "Pobl. Nueva", "tipo": "poblacion"}, follow=True)
    assert comuna.sectores.count() == 1 and "Ya existe" in r.content.decode()  # abreviatura reconocida


def test_admin_no_agrega_sectores(ca, comuna):
    assert ca.post(f"/territorio/comuna/{comuna.pk}/sectores/nuevo", {"nombre": "X", "tipo": "sector"}).status_code == 403


def test_listado_territorio(cg, comuna):
    assert "Comuna Ficticia" in cg.get("/territorio?q=ficticia").content.decode()


def test_comando_cargar_territorio(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("region_codigo,region_nombre,provincia_codigo,provincia_nombre,comuna_codigo,comuna_nombre\n98,R98,981,P981,98101,C1\n98,R98,981,P981,98102,C2\n", encoding="utf-8")
    call_command("cargar_territorio", str(f))
    call_command("cargar_territorio", str(f))  # idempotente
    assert Comuna.objects.filter(codigo__startswith="981").count() == 2 and Region.objects.filter(codigo="98").count() == 1


def test_comando_falla_con_columnas_faltantes(tmp_path):
    f = tmp_path / "mal.csv"
    f.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(CommandError):
        call_command("cargar_territorio", str(f))



# --- navegación, fichas y cascada (TE) -------------------------------------------------------------
from apps.territorio.models import Provincia, SectorAlias
from apps.territorio.reconocer import mismo_sector, normalizar


def test_navegacion_region_provincia_comuna(cg, comuna):
    html = cg.get("/territorio").content.decode()
    assert "Región de Prueba" in html and "1 comunas" in html
    html = cg.get(comuna.provincia.region.get_absolute_url()).content.decode()
    assert "Provincia de Provincia de Prueba" in html and "Comuna Ficticia" in html
    assert "Comuna Ficticia" in cg.get("/territorio?q=ficti").content.decode()
    assert "Sin resultados" in cg.get("/territorio?q=zzz").content.decode()


def test_ficha_de_comuna_con_contadores_y_lo_hecho_en_ella(cg, comuna, lugar, crear_actividad, gestor):
    from datetime import date, time, timedelta

    from apps.actividades import servicios
    from apps.actividades.models import ActividadTerritorio
    from apps.nucleo.models import TipoOrganizacion
    from apps.organizaciones.models import Organizacion

    Organizacion.objects.create(nombre="Muni Ficticia", tipo=TipoOrganizacion.objects.get(codigo="municipalidad"), comuna_municipal=comuna)
    a = crear_actividad("En el lugar")
    servicios.programar(a, gestor, date.today() + timedelta(days=3), time(10), time(11), lugar, None)
    b = crear_actividad("Solo con territorio")
    ActividadTerritorio.objects.create(actividad=b, comuna=comuna)
    crear_actividad("En otra parte")
    html = cg.get(comuna.get_absolute_url()).content.decode()
    assert "Lugares (1)" in html and "Organizaciones (1)" in html and "Actividades (2)" in html and "Sectores (0)" in html
    assert "Municipalidad:" in html
    act = cg.get(f"{comuna.get_absolute_url()}?tab=actividades").content.decode()
    assert "En el lugar" in act and "Solo con territorio" in act and "En otra parte" not in act


def test_ficha_de_sector_incluye_sus_subsectores(cg, comuna, lugar):
    padre = Sector.objects.create(comuna=comuna, nombre="San Pedro de la Costa")
    etapa = Sector.objects.create(comuna=comuna, nombre="Etapa 2", tipo="etapa", sector_padre=padre)
    lugar.direccion.sector = etapa
    lugar.direccion.save()
    html = cg.get(padre.get_absolute_url()).content.decode()
    assert "Sectores dentro (1)" in html and "Lugares (1)" in html
    assert "Sala Ficticia" in cg.get(f"{padre.get_absolute_url()}?tab=lugares").content.decode()


def test_editar_sector_no_puede_quedar_dentro_de_si_mismo(cg, comuna):
    padre = Sector.objects.create(comuna=comuna, nombre="A")
    hijo = Sector.objects.create(comuna=comuna, nombre="B", sector_padre=padre)
    r = cg.post(f"/territorio/sector/{padre.pk}/editar", {"nombre": "A", "tipo": "sector", "sector_padre": hijo.pk})
    assert r.status_code == 400
    padre.refresh_from_db()
    assert padre.sector_padre is None


def test_nombres_alternativos(cg, comuna):
    s = Sector.objects.create(comuna=comuna, nombre="San Pedro de la Costa")
    cg.post(f"/territorio/sector/{s.pk}/alias", {"nombre": "SPC"})
    assert list(s.alias.values_list("nombre", flat=True)) == ["SPC"]
    assert mismo_sector(comuna, "spc") == s
    cg.post(f"/territorio/sector/{s.pk}/alias", {"nombre": "SPC"})
    assert s.alias.count() == 1


def test_normalizar_reconoce_abreviaturas_y_tildes():
    assert normalizar("Pobl. San Pédro") == normalizar("Población san pedro") == "poblacion san pedro"
    assert normalizar("Vla. Esperanza") == "villa esperanza"
    assert normalizar("Etapa 1") != normalizar("Etapa 2")


def test_cascada_de_opciones(cg, comuna):
    otra = Provincia.objects.create(region=comuna.provincia.region, codigo="991", nombre="Otra Provincia")
    html = cg.get(f"/territorio/provincias?region={comuna.provincia.region_id}").content.decode()
    assert "Provincia de Prueba" in html and "Otra Provincia" in html
    assert "Comuna Ficticia" in cg.get(f"/territorio/comunas?provincia={comuna.provincia_id}").content.decode()
    assert "Comuna Ficticia" not in cg.get(f"/territorio/comunas?provincia={otra.pk}").content.decode()


def test_formulario_de_direccion_con_cascada(comuna):
    f = DireccionForm({"region": comuna.provincia.region_id, "provincia": comuna.provincia_id, "comuna": comuna.pk, "calle": "X"})
    assert f.is_valid(), f.errors
    otra = Provincia.objects.create(region=comuna.provincia.region, codigo="991", nombre="Otra Provincia")
    f = DireccionForm({"provincia": otra.pk, "comuna": comuna.pk})
    assert not f.is_valid() and "comuna" in f.errors
    d = Direccion.objects.create(calle="Y", comuna=comuna)
    f = DireccionForm(instance=d)
    assert f.initial["region"] == comuna.provincia.region_id and f.initial["provincia"] == comuna.provincia_id


def test_crear_sector_sin_salir_del_formulario(cg, comuna):
    r = cg.post("/territorio/sectores/crear", {"dir-comuna": comuna.pk, "nuevo_sector_nombre": "Villa Los Aromos", "nuevo_sector_tipo": "villa"}, HTTP_HX_TARGET="id_dir-sector")
    s = Sector.objects.get()
    assert f'value="{s.pk}" selected' in r.content.decode() and "creado y seleccionado" in r.content.decode()
    # escrito distinto: se reutiliza el existente
    r = cg.post("/territorio/sectores/crear", {"dir-comuna": comuna.pk, "nuevo_sector_nombre": "Vla. los aromos"})
    assert Sector.objects.count() == 1 and "Ya existía" in r.content.decode()
    # parecido pero distinto: avisa y pide confirmar
    r = cg.post("/territorio/sectores/crear", {"dir-comuna": comuna.pk, "nuevo_sector_nombre": "Villa Los Aromos Norte"})
    assert Sector.objects.count() == 1 and "Crear igual" in r.content.decode()
    cg.post("/territorio/sectores/crear", {"dir-comuna": comuna.pk, "nuevo_sector_nombre": "Villa Los Aromos Norte", "confirmar_sector": "1"})
    assert Sector.objects.count() == 2


def test_crear_sector_rapido_exige_comuna_y_permiso(cg, ca, comuna):
    assert "Elige la comuna" in cg.post("/territorio/sectores/crear", {"nuevo_sector_nombre": "X"}).content.decode()
    assert ca.post("/territorio/sectores/crear", {"dir-comuna": comuna.pk, "nuevo_sector_nombre": "X"}).status_code == 403
    assert not Sector.objects.exists()


def test_formularios_de_direccion_muestran_crear_sector(cg, persona):
    for ruta in ("/lugares/nuevo", "/organizaciones/nueva", f"/personas/{persona.pk}/direcciones/nuevo"):
        html = cg.get(ruta).content.decode()
        assert "+ Crear sector" in html and "Región" in html and "Provincia" in html, ruta

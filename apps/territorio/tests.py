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
    r = cg.post(f"/territorio/comuna/{comuna.pk}", {"nombre": "Población Nueva", "tipo": "poblacion"})
    assert r.status_code == 302 and comuna.sectores.count() == 1
    r = cg.post(f"/territorio/comuna/{comuna.pk}", {"nombre": "población nueva", "tipo": "poblacion"})
    assert r.status_code == 400 and comuna.sectores.count() == 1


def test_admin_no_agrega_sectores(ca, comuna):
    assert ca.post(f"/territorio/comuna/{comuna.pk}", {"nombre": "X", "tipo": "sector"}).status_code == 403


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

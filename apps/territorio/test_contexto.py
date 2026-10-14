"""F23: crear desde la comuna (`?comuna=`) y enlaces «en esta comuna» desde las fichas. Datos ficticios."""
import re
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.actividades.models import ActividadComunidad, ActividadTerritorio
from apps.actividades.servicios import programar
from apps.comunidades.models import Comunidad
from apps.lugares.models import Lugar
from apps.nucleo.models import TipoLugar, TipoOrganizacion
from apps.organizaciones.models import Organizacion
from apps.personas.models import PersonaDireccion
from apps.territorio.models import Comuna, Direccion, Sector

pytestmark = pytest.mark.django_db

HOY = timezone.localdate()


def _otra_comuna(comuna, codigo="99002", nombre="Otra Comuna"):
    return Comuna.objects.create(provincia=comuna.provincia, codigo=codigo, nombre=nombre)


def _dir(comuna, sector=None):
    return Direccion.objects.create(calle="Calle Inventada", numero="1", comuna=comuna, sector=sector)


def _enlaza(html, comuna):
    """La cabecera trae la comuna como enlace a su ficha."""
    return bool(re.search(rf'<a[^>]*href="{re.escape(comuna.get_absolute_url())}"[^>]*>\s*{re.escape(comuna.nombre)}\s*</a>', html))


# ---------- crear desde el contenedor ----------

def test_nueva_organizacion_con_comuna_prellenada(cg, comuna):
    muni = TipoOrganizacion.objects.get(codigo="municipalidad")
    r = cg.get(f"/organizaciones/nueva?comuna={comuna.pk}&tipo=municipalidad")
    assert r.status_code == 200
    direccion = r.context["form_direccion"]
    assert direccion.initial["comuna"] == comuna.pk
    assert direccion.initial["provincia"] == comuna.provincia_id and direccion.initial["region"] == comuna.provincia.region_id
    assert f'<option value="{comuna.pk}" selected>' in r.content.decode()
    # el tipo parte elegido y, siendo municipalidad sin otra registrada, también la comuna que representa
    assert r.context["form"].initial["tipo"] == muni.pk
    assert r.context["form"].initial["comuna_municipal"] == comuna.pk

    # lo prellenado se guarda: la organización queda con dirección en la comuna
    r = cg.post(f"/organizaciones/nueva?comuna={comuna.pk}&tipo=municipalidad", {
        "nombre": "Municipalidad Ficticia", "tipo": muni.pk, "comuna_municipal": comuna.pk, "dir-comuna": comuna.pk,
    })
    assert r.status_code == 302
    o = Organizacion.objects.get(nombre="Municipalidad Ficticia")
    assert o.direccion.comuna == comuna and comuna.municipalidad == o


def test_nueva_organizacion_ignora_parametros_invalidos(cg, comuna):
    for consulta in ("comuna=abc&tipo=no_existe", "comuna=999999&tipo=", "comuna=&tipo=empresa_o_partner%20x"):
        r = cg.get(f"/organizaciones/nueva?{consulta}")
        assert r.status_code == 200, consulta
        assert not r.context["form_direccion"].initial.get("comuna")
        assert not r.context["form"].initial.get("tipo") and not r.context["form"].initial.get("comuna_municipal")
    # un tipo que no es municipalidad no arrastra la comuna municipal; la dirección sí se prellena
    r = cg.get(f"/organizaciones/nueva?comuna={comuna.pk}&tipo=empresa_o_partner")
    assert r.context["form"].initial["tipo"] == TipoOrganizacion.objects.get(codigo="empresa_o_partner").pk
    assert not r.context["form"].initial.get("comuna_municipal")
    assert r.context["form_direccion"].initial["comuna"] == comuna.pk


def test_nueva_municipalidad_no_repite_la_comuna_si_ya_tiene_una(cg, comuna):
    Organizacion.objects.create(nombre="Municipalidad Vigente", tipo=TipoOrganizacion.objects.get(codigo="municipalidad"), comuna_municipal=comuna)
    r = cg.get(f"/organizaciones/nueva?comuna={comuna.pk}&tipo=municipalidad")
    assert r.status_code == 200 and not r.context["form"].initial.get("comuna_municipal")
    assert r.context["form_direccion"].initial["comuna"] == comuna.pk


def test_nuevo_lugar_con_comuna_prellenada(cg, comuna):
    sector = Sector.objects.create(comuna=comuna, nombre="Sector Uno")
    r = cg.get(f"/lugares/nuevo?comuna={comuna.pk}")
    assert r.status_code == 200
    direccion = r.context["form_direccion"]
    assert direccion.initial["comuna"] == comuna.pk and direccion.initial["provincia"] == comuna.provincia_id
    assert f'<option value="{comuna.pk}" selected>' in r.content.decode()
    assert list(direccion.fields["sector"].queryset) == [sector]  # los sectores ofrecidos son los de esa comuna

    r = cg.post(f"/lugares/nuevo?comuna={comuna.pk}", {
        "nombre": "Sede Ficticia", "tipo": TipoLugar.objects.get(codigo="sala").pk, "capacidad": 15, "dir-calle": "Calle Inventada", "dir-comuna": comuna.pk,
    })
    assert r.status_code == 302 and Lugar.objects.get(nombre="Sede Ficticia").direccion.comuna == comuna

    for invalido in ("abc", "999999", ""):
        r = cg.get(f"/lugares/nuevo?comuna={invalido}")
        assert r.status_code == 200 and not r.context["form_direccion"].initial.get("comuna")


def test_edicion_no_toma_la_comuna_de_la_url(cg, comuna, lugar):
    otra = _otra_comuna(comuna)
    r = cg.get(f"/lugares/{lugar.pk}/editar?comuna={otra.pk}")
    assert r.status_code == 200 and r.context["form_direccion"].initial["comuna"] == comuna.pk


def test_nueva_comunidad_con_comuna_prellenada(cg, comuna):
    r = cg.get(f"/comunidades/nueva?comuna={comuna.pk}")
    assert r.status_code == 200 and r.context["form"].initial["comuna"] == str(comuna.pk)


def test_nueva_actividad_con_comuna_crea_territorio(cg, comuna):
    r = cg.get(f"/actividades/nueva?comuna={comuna.pk}")
    assert r.status_code == 200 and "Comuna Ficticia" in r.context["bajada"]

    # el formulario publica a la misma URL (con su consulta): la comuna llega al guardar
    r = cg.post(f"/actividades/nueva?comuna={comuna.pk}", {"nombre": "Taller en la comuna"})
    assert r.status_code == 302
    t = ActividadTerritorio.objects.get()
    assert t.actividad.nombre == "Taller en la comuna" and t.comuna == comuna and t.vigente
    assert not (t.region_id or t.provincia_id or t.sector_id)

    # sin comuna, o con una inválida, no se crea territorio ni se interrumpe el alta
    assert cg.post("/actividades/nueva", {"nombre": "Sin territorio"}).status_code == 302
    for invalido in ("abc", "999999"):
        assert cg.get(f"/actividades/nueva?comuna={invalido}").status_code == 200
        assert cg.post(f"/actividades/nueva?comuna={invalido}", {"nombre": f"Valor {invalido}"}).status_code == 302
    assert ActividadTerritorio.objects.count() == 1


def test_nueva_actividad_con_comuna_y_comunidad_conserva_ambas(cg, comuna):
    comunidad = Comunidad.objects.create(nombre="Vecinos del Sector Ficticio", tipo="vecinal", comuna=comuna)
    r = cg.get(f"/actividades/nueva?comuna={comuna.pk}&comunidad={comunidad.pk}")
    assert r.status_code == 200 and "Vecinos del Sector Ficticio" in r.context["bajada"] and "Comuna Ficticia" in r.context["bajada"]
    assert cg.post(f"/actividades/nueva?comuna={comuna.pk}&comunidad={comunidad.pk}", {"nombre": "Taller doble"}).status_code == 302
    assert ActividadComunidad.objects.get().comunidad == comunidad
    assert ActividadTerritorio.objects.get().comuna == comuna


# ---------- crear desde un sector ----------

def test_nueva_actividad_desde_un_sector_crea_territorio_del_sector(cg, comuna):
    sector = Sector.objects.create(comuna=comuna, nombre="Villa Ficticia", tipo="villa")
    consulta = f"comuna={comuna.pk}&sector={sector.pk}"
    r = cg.get(f"/actividades/nueva?{consulta}")
    assert r.status_code == 200 and "sector Villa Ficticia" in r.context["bajada"] and "Comuna Ficticia" in r.context["bajada"]

    assert cg.post(f"/actividades/nueva?{consulta}", {"nombre": "Taller en la villa"}).status_code == 302
    t = ActividadTerritorio.objects.get()  # una sola fila: la del sector, no además la de la comuna
    assert t.actividad.nombre == "Taller en la villa" and t.sector == sector and t.vigente
    assert not (t.region_id or t.provincia_id or t.comuna_id)

    # y aparece donde se la busca: en el resumen y en la pestaña Actividades del sector (y también en la comuna, fuera de «Sin sector»)
    ficha = cg.get(sector.get_absolute_url())
    assert ficha.context["resumen"]["actividades_total"] == 1
    assert "Taller en la villa" in cg.get(f"{sector.get_absolute_url()}?tab=actividades").content.decode()
    en_comuna = cg.get(comuna.get_absolute_url()).context["resumen"]
    assert en_comuna["actividades_total"] == 1
    assert {(f["sector"], f["actividades"]) for f in en_comuna["sectores"]} == {(sector, 1), (None, 0)}


def test_nueva_actividad_ignora_un_sector_invalido(cg, comuna):
    otra = Comuna.objects.create(provincia=comuna.provincia, codigo="99002", nombre="Otra Comuna")
    ajeno = Sector.objects.create(comuna=otra, nombre="Sector de Otra Comuna")
    propio = Sector.objects.create(comuna=comuna, nombre="Sector Propio")
    # sin comuna el sector no vale; con un sector de otra comuna, que no existe o no es un número, cae a la comuna
    for consulta in (f"sector={propio.pk}", f"comuna={comuna.pk}&sector={ajeno.pk}", f"comuna={comuna.pk}&sector=999999",
                     f"comuna={comuna.pk}&sector=abc", f"comuna={comuna.pk}&sector=99999999999999999999", f"comuna={comuna.pk}&sector="):
        antes = ActividadTerritorio.objects.count()
        r = cg.get(f"/actividades/nueva?{consulta}")
        assert r.status_code == 200 and "sector" not in r.context.get("bajada", ""), consulta
        assert cg.post(f"/actividades/nueva?{consulta}", {"nombre": f"Valor {consulta}"}).status_code == 302, consulta
        creados = ActividadTerritorio.objects.all()[antes:]
        if consulta.startswith("sector="):
            assert not creados  # sin comuna no hay territorio
        else:
            assert [(t.comuna, t.sector) for t in creados] == [(comuna, None)], consulta


def test_nueva_organizacion_y_lugar_desde_un_sector_eligen_el_sector(cg, comuna):
    sector = Sector.objects.create(comuna=comuna, nombre="Villa Ficticia", tipo="villa")
    Sector.objects.create(comuna=comuna, nombre="Otra Villa Ficticia", tipo="villa")
    consulta = f"comuna={comuna.pk}&sector={sector.pk}"
    for url in ("/organizaciones/nueva", "/lugares/nuevo"):
        r = cg.get(f"{url}?{consulta}")
        assert r.status_code == 200, url
        direccion = r.context["form_direccion"]
        assert direccion.initial["comuna"] == comuna.pk and direccion.initial["sector"] == sector.pk, url
        assert f'<option value="{sector.pk}" selected>' in r.content.decode(), url
    # lo prellenado se guarda: el lugar queda con dirección en el sector
    r = cg.post(f"/lugares/nuevo?{consulta}", {
        "nombre": "Sede de la Villa", "tipo": TipoLugar.objects.get(codigo="sala").pk, "capacidad": 15,
        "dir-calle": "Calle Inventada", "dir-comuna": comuna.pk, "dir-sector": sector.pk,
    })
    assert r.status_code == 302 and Lugar.objects.get(nombre="Sede de la Villa").direccion.sector == sector

    # un sector inválido se ignora: la comuna sigue elegida y el sector no
    ajeno = Sector.objects.create(comuna=Comuna.objects.create(provincia=comuna.provincia, codigo="99003", nombre="Tercera Comuna"), nombre="Sector Ajeno")
    for invalido in (f"sector={ajeno.pk}", "sector=999999", "sector=abc", "sector="):
        for url in ("/organizaciones/nueva", "/lugares/nuevo"):
            r = cg.get(f"{url}?comuna={comuna.pk}&{invalido}")
            direccion = r.context["form_direccion"]
            assert r.status_code == 200 and direccion.initial["comuna"] == comuna.pk and not direccion.initial.get("sector"), (url, invalido)
    assert not cg.get(f"/lugares/nuevo?sector={sector.pk}").context["form_direccion"].initial.get("sector")  # sin comuna, el sector no vale


def test_nueva_comunidad_desde_un_sector_eligen_el_sector(cg, comuna):
    sector = Sector.objects.create(comuna=comuna, nombre="Villa Ficticia", tipo="villa")
    ajeno = Sector.objects.create(comuna=Comuna.objects.create(provincia=comuna.provincia, codigo="99002", nombre="Otra Comuna"), nombre="Sector Ajeno")
    r = cg.get(f"/comunidades/nueva?comuna={comuna.pk}&sector={sector.pk}")
    assert r.status_code == 200 and r.context["form"].initial["sector"] == sector.pk and r.context["form"].initial["comuna"] == str(comuna.pk)
    for invalido in (f"sector={ajeno.pk}", "sector=999999", "sector=abc"):
        r = cg.get(f"/comunidades/nueva?comuna={comuna.pk}&{invalido}")
        assert r.status_code == 200 and not r.context["form"].initial.get("sector"), invalido


def test_crear_actividad_es_atomico(cg, comuna, monkeypatch):
    """Si algo falla después de guardar la actividad (el territorio, el origen), no queda una actividad a medias."""
    from apps.actividades.models import Actividad

    def falla(*a, **kw):
        raise RuntimeError("falla simulada al registrar el origen")

    monkeypatch.setattr("apps.documentos.origen.registrar_origen", falla)
    with pytest.raises(RuntimeError):
        cg.post(f"/actividades/nueva?comuna={comuna.pk}", {"nombre": "Actividad a medias"})
    assert not Actividad.objects.filter(nombre="Actividad a medias").exists() and not ActividadTerritorio.objects.exists()


# ---------- enlaces hacia arriba ----------

def test_fichas_enlazan_a_su_comuna(cg, comuna, lugar, crear_persona, crear_actividad, gestor):
    otra = _otra_comuna(comuna)
    otra_mas = _otra_comuna(comuna, "99003", "Tercera Comuna")

    # persona: comuna de su residencia vigente; si hay varias, la primera
    ana = crear_persona("Ana")
    PersonaDireccion.objects.create(persona=ana, direccion=_dir(otra), tipo="procedencia", vigente=True)
    PersonaDireccion.objects.create(persona=ana, direccion=_dir(otra), tipo="residencia", vigente=False)
    assert _enlaza(cg.get(ana.get_absolute_url()).content.decode(), otra) is False  # nada vigente de residencia aún
    PersonaDireccion.objects.create(persona=ana, direccion=_dir(comuna), tipo="residencia", vigente=True)
    PersonaDireccion.objects.create(persona=ana, direccion=_dir(otra_mas), tipo="residencia", vigente=True)
    r = cg.get(ana.get_absolute_url())
    assert r.context["comuna_residencia"] == comuna
    assert _enlaza(r.content.decode(), comuna) and not _enlaza(r.content.decode(), otra_mas)
    sin_direccion = cg.get(crear_persona("Sin dirección").get_absolute_url())
    assert sin_direccion.status_code == 200 and sin_direccion.context["comuna_residencia"] is None

    # organización: comuna de su dirección, o la comuna que representa si es municipalidad sin dirección
    empresa = Organizacion.objects.create(nombre="Empresa Ficticia", tipo=TipoOrganizacion.objects.get(codigo="empresa_o_partner"), direccion=_dir(otra))
    assert _enlaza(cg.get(empresa.get_absolute_url()).content.decode(), otra)
    muni = Organizacion.objects.create(nombre="Municipalidad Ficticia", tipo=TipoOrganizacion.objects.get(codigo="municipalidad"), comuna_municipal=otra_mas)
    assert _enlaza(cg.get(muni.get_absolute_url()).content.decode(), otra_mas)
    sin_comuna = Organizacion.objects.create(nombre="Club Ficticio", tipo=TipoOrganizacion.objects.get(codigo="empresa_o_partner"))
    assert cg.get(sin_comuna.get_absolute_url()).status_code == 200

    # lugar
    assert _enlaza(cg.get(lugar.get_absolute_url()).content.decode(), comuna)

    # actividad: comuna del lugar programado
    programada = crear_actividad("Programada")
    programar(programada, gestor, HOY + timedelta(days=3), None, None, lugar, None)
    assert _enlaza(cg.get(programada.get_absolute_url()).content.decode(), comuna)

    # actividad: sin lugar, la del territorio indicado (comuna o comuna del sector); los niveles mayores no cuentan
    por_comuna = crear_actividad("Por comuna")
    ActividadTerritorio.objects.create(actividad=por_comuna, region=comuna.provincia.region)
    ActividadTerritorio.objects.create(actividad=por_comuna, comuna=otra, vigente=False)
    assert not _enlaza(cg.get(por_comuna.get_absolute_url()).content.decode(), otra)  # un territorio no vigente no cuenta
    ActividadTerritorio.objects.create(actividad=por_comuna, comuna=otra)
    assert _enlaza(cg.get(por_comuna.get_absolute_url()).content.decode(), otra)
    por_sector = crear_actividad("Por sector")
    ActividadTerritorio.objects.create(actividad=por_sector, sector=Sector.objects.create(comuna=otra_mas, nombre="Sector Dos"))
    assert _enlaza(cg.get(por_sector.get_absolute_url()).content.decode(), otra_mas)
    sin_nada = crear_actividad("Sin nada")
    r = cg.get(sin_nada.get_absolute_url())
    assert r.status_code == 200 and r.context["comuna_ficha"] is None

    # comunidad: ya enlazaba
    comunidad = Comunidad.objects.create(nombre="Vecinos", tipo="vecinal", comuna=comuna)
    assert _enlaza(cg.get(comunidad.get_absolute_url()).content.decode(), comuna)


def test_la_comuna_del_lugar_prevalece_sobre_el_territorio(cg, comuna, lugar, crear_actividad, gestor):
    otra = _otra_comuna(comuna)
    a = crear_actividad("Con lugar y territorio")
    ActividadTerritorio.objects.create(actividad=a, comuna=otra)
    programar(a, gestor, HOY + timedelta(days=3), None, None, lugar, None)
    html = cg.get(a.get_absolute_url()).content.decode()
    assert _enlaza(html, comuna) and not _enlaza(html, otra)


def test_enlace_de_comuna_cuesta_consultas_fijas(cg, comuna, crear_persona, crear_actividad):
    """Una persona con una o con varias direcciones, y una actividad con uno o con varios territorios, cuestan lo mismo."""
    def consultas(url):
        cg.get(url)  # calienta cachés (permisos, sesión)
        with CaptureQueriesContext(connection) as c:
            assert cg.get(url).status_code == 200
        return len(c)

    una = crear_persona("Una")
    PersonaDireccion.objects.create(persona=una, direccion=_dir(comuna), tipo="residencia", vigente=True)
    varias = crear_persona("Varias")
    for i in range(4):
        PersonaDireccion.objects.create(persona=varias, direccion=_dir(_otra_comuna(comuna, f"9910{i}", f"Comuna {i}")), tipo="residencia", vigente=True)
    assert consultas(varias.get_absolute_url()) == consultas(una.get_absolute_url())

    a1, a4 = crear_actividad("Un territorio"), crear_actividad("Cuatro territorios")
    ActividadTerritorio.objects.create(actividad=a1, comuna=comuna)
    for i in range(4):
        ActividadTerritorio.objects.create(actividad=a4, comuna=_otra_comuna(comuna, f"9920{i}", f"Territorio {i}"))
    assert consultas(a4.get_absolute_url()) == consultas(a1.get_absolute_url())

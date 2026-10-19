"""Pruebas de la barra de filtros de los listados: buscador y 3 filtros a la vista en Personas, «Más filtros»,
etiquetas de filtros aplicados que se quitan de a una, «Limpiar» que conserva el orden y los mismos nombres de
parámetros. También el filtro por comuna que incluye las actividades dirigidas a sus sectores. Datos ficticios."""
import re
from html import unescape

import pytest

from apps.actividades.models import ActividadTerritorio
from apps.territorio.models import Sector

pytestmark = pytest.mark.django_db


def _barra(html):
    return re.search(r'<form class="fche-filtros".*?</form>', html, re.S).group(0)


def _nombres(trozo):
    return set(re.findall(r'name="([a-z_]+)"', trozo))


def test_personas_buscador_tres_principales_y_mas_filtros(cg):
    barra = _barra(cg.get("/personas").content.decode())
    afuera, _, adentro = barra.partition('<details class="fche-filtros__mas">')
    assert 'name="q"' in afuera and "Nombre, RUT, correo o teléfono" in afuera
    assert _nombres(afuera) == {"q", "perfil", "comuna", "comunidad"}
    # los demás siguen existiendo con el mismo nombre de parámetro, dentro de «Más filtros»
    assert _nombres(adentro) == {"rol", "organizacion", "interes", "edad", "registro", "origen", "activo"}
    activo = re.search(r'<select[^>]*name="activo".*?</select>', barra, re.S).group(0)
    assert activo.count("Todos") == 1 and 'value=""' not in activo  # «todos» una sola vez: sin opción vacía repetida


def test_etiquetas_quitan_solo_su_filtro_y_limpiar_conserva_el_orden(cg, comuna, crear_persona):
    html = cg.get(f"/personas?q=ana&comuna={comuna.pk}&registro=incompleto&activo=&orden=nombre&page=1").content.decode()
    barra = unescape(_barra(html))
    assert "Comuna: <strong>Comuna Ficticia</strong>" in barra and "Texto: <strong>«ana»</strong>" in barra
    quitar_comuna = re.search(r'href="\?([^"]*)"[^>]*data-quitar="comuna"', barra).group(1)
    assert quitar_comuna == "q=ana&registro=incompleto&orden=nombre"  # sin página, sin vacíos y sin la comuna
    assert 'class="fche-contador fche-contador--activo">1<' in barra  # «registro» va en «Más filtros»
    assert 'class="fche-filtros__limpiar" href="?orden=nombre"' in barra
    assert '<input type="hidden" name="orden" value="nombre">' in barra
    # «activo=» vacío vale lo predeterminado (activos): no es un filtro aplicado
    assert 'data-quitar="activo"' not in barra


def test_activo_vacio_no_muestra_desactivados(cg, crear_persona):
    crear_persona(nombres="Inactiva", activo=False)
    assert "Inactiva" not in cg.get("/personas?activo=").content.decode()
    html = cg.get("/personas?activo=*").content.decode()
    assert "Inactiva" in html and 'data-quitar="activo"' in html


def test_comuna_incluye_actividades_dirigidas_a_sus_sectores(cg, comuna, crear_actividad):
    etapa = Sector.objects.create(comuna=comuna, nombre="Villa Inventada")
    sub = Sector.objects.create(comuna=comuna, nombre="Etapa 1", tipo="etapa", sector_padre=etapa)
    a = crear_actividad("Taller en la villa")
    ActividadTerritorio.objects.create(actividad=a, sector=sub)
    crear_actividad("Charla en otra parte")
    listado = cg.get(f"/actividades?comuna={comuna.pk}").content.decode()
    assert "Taller en la villa" in listado and "Charla en otra parte" not in listado
    buscar = cg.get(f"/buscar?tipo=actividad&zona={comuna.pk}").content.decode()
    assert "Taller en la villa" in buscar and "Charla en otra parte" not in buscar


def test_calendario_por_comuna_incluye_sectores(cg, comuna, crear_actividad, gestor):
    from django.utils import timezone

    from apps.actividades.servicios import programar
    from apps.lugares.models import Lugar
    from apps.nucleo.models import TipoLugar
    from apps.territorio.models import Comuna, Direccion

    otra = Comuna.objects.create(provincia=comuna.provincia, codigo="99002", nombre="Otra Comuna")
    lejos = Lugar.objects.create(nombre="Sala Lejana", tipo=TipoLugar.objects.get(codigo="sala"), direccion=Direccion.objects.create(calle="Otra", numero="1", comuna=otra))
    a = crear_actividad("Taller dirigido al sector")
    ActividadTerritorio.objects.create(actividad=a, sector=Sector.objects.create(comuna=comuna, nombre="Sector Inventado"))
    hoy = timezone.localdate()
    programar(a, gestor, hoy, lugar=lejos)  # se hace lejos, pero se dirige a un sector de la comuna
    programar(crear_actividad("Charla lejana"), gestor, hoy, lugar=lejos)
    eventos = cg.get(f"/calendario/eventos?start={hoy}&end={hoy}&zona={comuna.pk}").json()
    assert [e["title"] for e in eventos] == ["Taller dirigido al sector"]


def test_actividades_mismos_parametros_casilla_e_institucion(cg, crear_actividad, universidad):
    from apps.actividades.models import ActividadOrganizacion

    ActividadOrganizacion.objects.create(actividad=crear_actividad("Con la universidad"), organizacion=universidad)
    barra = unescape(_barra(cg.get(f"/actividades?institucion={universidad.pk}").content.decode()))
    # los parámetros de siempre siguen ahí («periodo» es nuevo); «institucion» funciona por la dirección sin dibujarse
    assert _nombres(barra) >= {"q", "estado", "comuna", "tipo", "proyecto", "incompleta", "organizacion", "responsable", "desde", "hasta"}
    assert 'name="institucion"' not in barra and f"Institución: <strong>{universidad.nombre}</strong>" in barra
    assert re.search(r'type="checkbox" name="incompleta" value="1"', barra)  # casilla en vez de lista de una opción


def test_tareas_responsable_por_nombre(cg, crear_persona):
    from apps.coordinacion.models import Tarea, TareaResponsable

    p = crear_persona("Responsable Inventada")
    TareaResponsable.objects.create(tarea=Tarea.objects.create(titulo="Tarea ficticia"), persona=p)
    barra = _barra(cg.get("/tareas").content.decode())
    responsable = re.search(r'<select[^>]*name="responsable".*?</select>', barra, re.S).group(0)
    assert f'value="{p.pk}"' in responsable and "Responsable Inventada" in responsable
    assert 'type="checkbox" name="vencidas" value="1"' in barra

"""F26 P: pulido de Calendario, Buscar y Catálogos. Todos los datos son ficticios."""
from datetime import date, time, timedelta

import pytest
from django.template import Context, Template

from apps.actividades import servicios
from apps.nucleo.templatetags.fche import badge_estado, tono_estado
from apps.nucleo.utilidades import plural

FUTURO = date.today() + timedelta(days=10)


@pytest.fixture
def tarea_programada(db, crear_actividad, gestor, lugar):
    from apps.proyectos.models import Proyecto

    pr = Proyecto.objects.create(nombre="Huertos Ficticios")
    a = crear_actividad("Visita ficticia", estado="planificada", proyecto=pr)
    servicios.programar(a, gestor, FUTURO, time(10, 0), time(12, 0), lugar, None, "")
    a.refresh_from_db()
    return a


def _eventos(cg):
    return cg.get(f"/calendario/eventos?start={FUTURO - timedelta(days=1)}&end={FUTURO + timedelta(days=1)}").json()


def test_color_del_evento_igual_al_de_la_insignia(cg, tarea_programada):
    ev = _eventos(cg)[0]
    tono = tono_estado(tarea_programada.estado.codigo)
    assert f"fche-estado--{tono}" in ev["classNames"] and "color" not in ev
    assert f"fche-estado--{tono}" in badge_estado(tarea_programada.estado.codigo, "x")
    assert tono_estado("planificada") == "azul"  # antes, gris en el calendario y azul en las listas
    html = cg.get("/calendario").content.decode()
    assert "fche-estado--azul" in html and "+ Nueva actividad" in html  # leyenda con las mismas insignias


def test_titulo_corto_del_evento_con_detalle(cg, tarea_programada):
    ev = _eventos(cg)[0]
    assert ev["title"] == "Visita ficticia"
    assert ev["extendedProps"]["proyecto"] == "Huertos Ficticios" and ev["extendedProps"]["lugar"]


def test_buscar_desde_hasta_y_ver_todos(cg, crear_persona):
    for i in range(7):
        crear_persona(f"Zorbalina{i}")
    html = cg.get("/buscar?q=zorbalina").content.decode()
    assert 'for="filtro-desde">Desde</label>' in html and 'for="filtro-hasta">Hasta</label>' in html
    assert "Ver todos (7)" in html and 'href="/personas?q=zorbalina"' in html
    assert html.count('class="fche-resultado"') == 5
    todos = cg.get("/buscar?q=zorbalina&tipo=persona").content.decode()
    assert todos.count('class="fche-resultado"') == 7 and "Ver todos" not in todos


@pytest.mark.parametrize("n, esperado", [(1, "1 actividad"), (2, "2 actividades")])
def test_plural_correcto(n, esperado):
    assert plural(n, "actividad", "actividades") == esperado
    html = Template('{{ n }} actividad{{ n|pluralize:"es" }}').render(Context({"n": n}))
    assert html == esperado


def test_catalogos_agrupados_por_area(cg):
    html = cg.get("/administracion/catalogos/").content.decode()
    titulos = ["Actividades", "Personas", "Organizaciones", "Lugares y territorio", "Documentos"]
    pos = [html.index(f">{t}</h2>") for t in titulos]
    assert pos == sorted(pos) and "data-filtrar-tarjetas" in html and ">Otros</h2>" not in html
    assert html.index("/administracion/catalogos/tipo-documento/") > pos[-1]

"""F26 Rb: rendimiento. Número fijo de consultas (con 1 registro y con varios), pestañas por HTMX que reciben solo
la ficha y memoria de una petición para las opciones. Todos los datos son ficticios."""
import re
from datetime import date, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.actividades.models import AgendaActividad, Participacion
from apps.nucleo.models import EstadoActividad, TipoContacto
from apps.personas.models import Consentimiento, Contacto
from apps.proyectos.models import Proyecto

HX = {"HTTP_HX_REQUEST": "true", "HTTP_HX_TARGET": "ficha-completa"}


def _consultas(cliente, url, **extra):
    cliente.get(url, **extra)  # calienta (sesión, permisos)
    with CaptureQueriesContext(connection) as q:
        r = cliente.get(url, **extra)
    assert r.status_code == 200, url
    return [x["sql"] for x in q.captured_queries]


def _repetidas(sql):
    """Consultas iguales salvo los números (la marca de una consulta en bucle)."""
    return len(sql) - len({re.sub(r"\b\d+\b", "N", s) for s in sql})


def _agenda(a, dias=10):
    return AgendaActividad.objects.create(actividad=a, fecha=date.today() + timedelta(days=dias), estado=a.estado)


# --- Consultas fijas ----------------------------------------------------------------------------------
def test_nueva_persona_lee_cada_lista_una_vez(cg, crear_actividad, crear_persona):
    """Antes: 55 consultas, 19 repetidas (cada buscador y cada fila leía su lista). Ahora la misma consulta se lee una vez."""
    crear_actividad("Charla uno", proyecto=Proyecto.objects.create(nombre="Proyecto Ficticio Uno"))  # también una tarea
    crear_persona()
    pocos = _consultas(cg, "/personas/nueva?modo=completa")
    for i in range(6):
        a = crear_actividad(f"Taller {i}", proyecto=Proyecto.objects.create(nombre=f"Proyecto Ficticio {i}"))
        _agenda(a)
        crear_persona()
    muchos = _consultas(cg, "/personas/nueva?modo=completa")
    assert len(muchos) == len(pocos)
    assert _repetidas(muchos) <= 2  # solo las dos listas distintas de actividades (todas y solo tareas) con su agenda


def test_buscar_sin_consulta_por_resultado(cg, crear_actividad, crear_persona, rol, estado_part):
    a = crear_actividad("Actividad alfa")
    _agenda(a)
    p = crear_persona("Alfa")
    Participacion.objects.create(actividad=a, persona=p, rol=rol("voluntario"), estado=estado_part("confirmado"))
    pocos = _consultas(cg, "/buscar?q=a")
    for i in range(6):
        b = crear_actividad(f"Actividad alfa {i}")
        _agenda(b)
        q = crear_persona(f"Alfa{i}")
        Participacion.objects.create(actividad=b, persona=q, rol=rol("voluntario"), estado=estado_part("confirmado"))
    muchos = _consultas(cg, "/buscar?q=a")
    assert len(muchos) == len(pocos)
    assert _repetidas(muchos) == 0


def test_buscar_cuenta_participaciones_igual_que_antes(cg, actividad, crear_persona, rol, estado_part):
    p = crear_persona("Zuleika")
    for codigo in ("voluntario", "tallerista"):
        Participacion.objects.create(actividad=actividad, persona=p, rol=rol(codigo), estado=estado_part("confirmado"))
    html = cg.get("/buscar?q=Zuleika").content.decode()
    assert "2 participaciones"  # F26 P: plural correcto in html


@pytest.mark.parametrize("tab", ["resumen", "contacto", "privacidad"])
def test_ficha_de_persona_consultas_fijas(cg, crear_persona, tab):
    p = crear_persona()
    correo = TipoContacto.objects.get(codigo="correo")
    Contacto.objects.create(persona=p, tipo=correo, valor="uno@ejemplo.cl")
    Consentimiento.objects.create(persona=p, tipo="datos")
    pocos = _consultas(cg, f"/personas/{p.pk}?tab={tab}")
    movil = TipoContacto.objects.get(codigo="telefono_movil")
    for i in range(4):
        Contacto.objects.create(persona=p, tipo=movil if i % 2 else correo, valor=f"+5691234567{i}" if i % 2 else f"otro{i}@ejemplo.cl")
        Consentimiento.objects.create(persona=p, tipo="sensibles", fecha=date.today() - timedelta(days=i))
    muchos = _consultas(cg, f"/personas/{p.pk}?tab={tab}")
    assert len(muchos) == len(pocos)
    assert _repetidas(muchos) == 0


def test_consentimiento_vigente_igual_con_y_sin_precarga(cg, crear_persona):
    """El último consentimiento de cada tipo sale igual leído de la base o de lo precargado por la ficha."""
    p = crear_persona()
    Consentimiento.objects.create(persona=p, tipo="datos", fecha=date.today() - timedelta(days=5))
    revocado = Consentimiento.objects.create(persona=p, tipo="datos", fecha=date.today(), revocado_en=date.today())
    assert p.ultimo_consentimiento("datos") == revocado and p.consentimiento_vigente("datos") is None
    from apps.personas.views import PersonaFicha

    precargada = PersonaFicha().get_queryset().get(pk=p.pk)
    with CaptureQueriesContext(connection) as q:
        assert precargada.ultimo_consentimiento("datos") == revocado and precargada.consentimiento_vigente("datos") is None
        assert precargada.ultimo_consentimiento("sensibles") is None
    assert len(q.captured_queries) == 0


@pytest.mark.parametrize("tab", ["info", "participantes", "beneficiarios", "resultados", "historial"])
def test_pestanas_de_la_tarea_consultas_fijas(cg, crear_actividad, crear_persona, rol, estado_part, lugar, tab):
    proyecto = Proyecto.objects.create(nombre="Huertos Ficticios")
    t = crear_actividad("Tarea ficticia", estado="planificada", proyecto=proyecto)
    AgendaActividad.objects.create(actividad=t, fecha=date.today() + timedelta(days=5), estado=t.estado, lugar=lugar)
    Participacion.objects.create(actividad=t, persona=crear_persona(), rol=rol("beneficiario"), estado=estado_part("confirmado"))
    url = f"/proyectos/{proyecto.pk}/tareas/{t.pk}?tab={tab}"
    pocos = _consultas(cg, url)
    for i in range(6):
        part = Participacion.objects.create(actividad=t, persona=crear_persona(), rol=rol("beneficiario" if i % 2 else "voluntario"),
                                            estado=estado_part("confirmado"))
        part.estado = estado_part("invitado")
        part.save()  # otra versión en el historial de participantes
    muchos = _consultas(cg, url)
    assert len(muchos) == len(pocos)
    assert _repetidas(muchos) == 0


def test_estados_siguientes_en_el_mismo_orden(db):
    from apps.actividades.views import ActividadFicha

    codigos = ["cancelada", "suspendida", "no_existe"]
    nombres = {c: n for c, n in EstadoActividad.objects.filter(codigo__in=codigos).values_list("codigo", "nombre")}
    assert ActividadFicha.estados_siguientes(codigos) == [(c, nombres[c]) for c in codigos if c in nombres]


# --- Pestañas por HTMX -----------------------------------------------------------------------------
def test_pestana_por_htmx_recibe_solo_la_ficha(cg, persona):
    url = f"/personas/{persona.pk}?tab=contacto"
    completa = cg.get(url)
    parcial = cg.get(url, **HX)
    html = parcial.content.decode()
    assert 'id="ficha-completa"' in html and "Contacto" in html
    assert "<html" not in html and "Menú principal" not in html and "buscador-global" not in html
    assert len(parcial.content) < len(completa.content) / 2
    assert "HX-Target" in parcial["Vary"]


def test_pestana_recargada_o_restaurada_es_la_pagina_completa(cg, persona):
    url = f"/personas/{persona.pk}?tab=contacto"
    assert "<html" in cg.get(url).content.decode()  # recargar la dirección
    assert "<html" in cg.get(url, HTTP_HX_REQUEST="true").content.decode()  # HTMX con otro destino
    assert "<html" in cg.get(url, HTTP_HX_HISTORY_RESTORE_REQUEST="true", **HX).content.decode()  # «Atrás» sin caché de htmx


def test_pestanas_son_enlaces_normales_y_un_clic_nuevo_reemplaza_al_anterior(cg, persona):
    html = cg.get(f"/personas/{persona.pk}").content.decode()
    enlaces = re.findall(r'<a class="nav-link[^"]*" href="\?tab=(\w+)"[^>]*>', html)
    assert "contacto" in enlaces  # sin JavaScript, cada pestaña es un enlace que abre la página completa
    assert 'hx-sync="#ficha-completa:replace"' in html and 'hx-push-url="true"' in html


# --- Memoria de una petición -------------------------------------------------------------------------
def test_memoria_solo_dentro_de_una_peticion(db):
    from apps.nucleo import memo
    from apps.nucleo.models import EstadoParticipacion

    def qs():
        return EstadoParticipacion.objects.order_by("pk")

    with CaptureQueriesContext(connection) as q:
        memo.lista(qs())
        memo.lista(qs())
    assert len(q.captured_queries) == 2  # fuera de una petición no guarda nada
    token = memo._memo.set({})
    try:
        with CaptureQueriesContext(connection) as q:
            assert memo.lista(qs()) == memo.lista(qs())
            memo.lista(qs().filter(activo=True))  # otra consulta, otra entrada
            assert memo.lista(EstadoParticipacion.objects.none()) == []
        assert len(q.captured_queries) == 2
    finally:
        memo._memo.reset(token)


def test_listas_del_formulario_siguen_validando_y_marcando_lo_elegido(cg):
    """El catálogo compartido entre filas sigue marcando lo elegido en cada una."""
    from apps.personas.relaciones import RelacionesFormSet

    from apps.nucleo.models import RolParticipacion

    vol = RolParticipacion.objects.get(codigo="voluntario")
    fs = RelacionesFormSet(initial=[{"rol": vol.pk}, {}], prefix="relaciones")
    html = str(fs.forms[0]["rol"]) + str(fs.forms[1]["rol"])
    assert html.count("selected") == 2  # la opción elegida en la 1.ª fila y la vacía en la 2.ª
    assert f'value="{vol.pk}" selected' in str(fs.forms[0]["rol"])

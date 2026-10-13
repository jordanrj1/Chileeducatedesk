from datetime import date, timedelta

import pytest

from apps.coordinacion.models import Interaccion, Tarea
from apps.nucleo.models import Canal

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("ruta", ["/reuniones", "/reuniones/nueva", "/tareas", "/tareas/nueva", "/finanzas", "/finanzas/nuevo"])
def test_rutas_de_segunda_fase_ocultas(cg, sin_segunda_fase, ruta):
    assert cg.get(ruta).status_code == 404


def test_menu_sin_segunda_fase(cg, sin_segunda_fase):
    html = cg.get("/dashboard").content.decode()
    assert 'href="/reuniones"' not in html and 'href="/tareas"' not in html and 'href="/finanzas"' not in html
    assert 'href="/actividades"' in html


def test_pestanas_ocultas(cg, sin_segunda_fase, actividad, persona):
    from apps.proyectos.models import Proyecto

    a = cg.get(f"/actividades/{actividad.pk}").content.decode().split("nav-tabs")[1].split("</ul>")[0]
    assert "Sesiones" not in a and "Beneficiarios" not in a and "Participantes" in a
    p = cg.get(f"/personas/{persona.pk}").content.decode().split("nav-tabs")[1].split("</ul>")[0]
    assert "Verificaciones" not in p
    pr = Proyecto.objects.create(nombre="P")
    t = cg.get(f"/proyectos/{pr.pk}").content.decode().split("nav-tabs")[1].split("</ul>")[0]
    assert "Presupuesto" not in t and "Postulación" not in t and "Equipo" in t
    assert cg.get(f"/actividades/{actividad.pk}/sesiones/nuevo").status_code == 404
    assert cg.get(f"/personas/{persona.pk}/verificaciones/nuevo").status_code == 404


def test_beneficiarios_aparecen_como_participantes(cg, sin_segunda_fase, actividad, persona, rol, estado_part):
    from apps.actividades.models import Participacion

    Participacion.objects.create(actividad=actividad, persona=persona, rol=rol("beneficiario"), estado=estado_part("invitado"))
    assert "Ana María" in cg.get(f"/actividades/{actividad.pk}?tab=participantes").content.decode()


def test_panel_muestra_proximas_acciones_de_interacciones(cg, sin_segunda_fase, persona):
    hoy = date.today()
    canal = Canal.objects.get(codigo="llamado")
    Interaccion.objects.create(canal=canal, persona=persona, proxima_accion="Volver a llamar a la junta", proxima_fecha=hoy + timedelta(days=2))
    Interaccion.objects.create(canal=canal, persona=persona, proxima_accion="Ya hecha", proxima_fecha=hoy, accion_cumplida=True)
    Interaccion.objects.create(canal=canal, persona=persona, proxima_accion="Lejana", proxima_fecha=hoy + timedelta(days=40))
    Tarea.objects.create(titulo="Tarea de segunda fase", fecha_limite=hoy)
    html = cg.get("/dashboard").content.decode()
    assert "Tareas por vencer" in html and "Volver a llamar a la junta" in html
    assert "Ya hecha" not in html and "Lejana" not in html and "Tarea de segunda fase" not in html


def test_con_segunda_fase_todo_visible(cg, actividad):
    assert cg.get("/reuniones").status_code == 200
    assert "Sesiones" in cg.get(f"/actividades/{actividad.pk}").content.decode()


def test_los_datos_no_se_borran_al_ocultar(cg, sin_segunda_fase):
    Tarea.objects.create(titulo="Sigue existiendo")
    assert Tarea.objects.filter(titulo="Sigue existiendo").exists()


def test_habilitar_solo_reuniones_y_tareas(cg, settings, actividad, persona):
    settings.SEGUNDA_FASE = False
    settings.MODULOS_SEGUNDA_FASE = ["reuniones", "tareas"]
    assert cg.get("/reuniones").status_code == 200 and cg.get("/tareas").status_code == 200
    assert cg.get("/finanzas").status_code == 404
    html = cg.get("/dashboard").content.decode()
    assert 'href="/reuniones"' in html and 'href="/tareas"' in html and 'href="/finanzas"' not in html
    tabs = cg.get(f"/actividades/{actividad.pk}").content.decode().split("nav-tabs")[1].split("</ul>")[0]
    assert "Sesiones" not in tabs
    coord = cg.get(f"/actividades/{actividad.pk}?tab=coordinacion").content.decode()
    assert "+ Nueva reunión" in coord and "+ Nueva tarea" in coord
    assert cg.get(f"/personas/{persona.pk}/verificaciones/nuevo").status_code == 404


def test_modulos_sueltos_para_proyecto(cg, settings):
    from apps.proyectos.models import Proyecto

    settings.SEGUNDA_FASE = False
    settings.MODULOS_SEGUNDA_FASE = ["finanzas"]
    pr = Proyecto.objects.create(nombre="P")
    tabs = cg.get(f"/proyectos/{pr.pk}").content.decode().split("nav-tabs")[1].split("</ul>")[0]
    assert "Presupuesto" in tabs and "Postulación" not in tabs and "Beneficiarios" not in tabs

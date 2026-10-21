"""Pruebas de F25 E (E4, E5, E7, E8, E9 y E10): procedencia completa y organización que se agrega sola, panel lateral
de la persona, asistencia en la tabla de Participantes, pestañas visibles, ayuda de los grupos y texto de cupos.
Todos los datos son ficticios."""
from datetime import date, time, timedelta
from pathlib import Path

import pytest
from django.conf import settings

from apps.actividades import servicios
from apps.actividades.models import ActividadOrganizacion, Participacion

pytestmark = pytest.mark.django_db
HOY = date.today()
FUTURO = HOY + timedelta(days=7)


def _participar(actividad, persona, rol, estado, **kw):
    return Participacion.objects.create(actividad=actividad, persona=persona, rol=rol, estado=estado, **kw)


# --- E4: organización del participante ------------------------------------------------------
def test_E4_la_organizacion_queda_en_la_actividad_y_la_procedencia_se_ve_completa(cg, actividad, universidad, lugar, crear_persona, rol, estado_part):
    from apps.organizaciones.models import Carrera
    from apps.personas.models import PersonaFormacion, PersonaOrganizacion

    ana, beto = crear_persona("Anita"), crear_persona("Beto")
    datos = {"rol": rol("estudiante").pk, "estado": estado_part("confirmado").pk, "organizacion": universidad.pk}
    assert cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", {**datos, "persona": ana.pk}).status_code == 302
    assert cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", {**datos, "persona": beto.pk}).status_code == 302
    org = ActividadOrganizacion.objects.get(actividad=actividad, organizacion=universidad)  # una sola, aunque llegaron dos
    assert org.vigente and org.tipo_intervencion.codigo == "aporta_personas"
    assert "trajo 2 personas" in cg.get(f"/actividades/{actividad.pk}?tab=organizaciones").content.decode()
    # dada de baja, no se reactiva sola al editar una participación
    org.vigente = False
    org.save()
    p = actividad.participaciones.get(persona=ana)
    cg.post(f"/actividades/{actividad.pk}/participantes/{p.pk}/editar", {"rol": p.rol_id, "estado": p.estado_id, "institucion": universidad.pk})
    assert ActividadOrganizacion.objects.filter(actividad=actividad).count() == 1 and not ActividadOrganizacion.objects.get(pk=org.pk).vigente
    # procedencia: institución, sede, carrera y cargo, con enlaces
    carrera = Carrera.objects.create(organizacion=universidad, nombre="Pedagogía Ficticia")
    PersonaFormacion.objects.create(persona=ana, organizacion=universidad, sede_institucion=lugar, carrera=carrera)
    PersonaOrganizacion.objects.filter(persona=beto, organizacion=universidad).update(cargo="Ayudante de laboratorio")
    html = cg.get(f"/actividades/{actividad.pk}?tab=participantes").content.decode()
    assert f'href="{universidad.get_absolute_url()}"' in html and f'href="{lugar.get_absolute_url()}"' in html
    assert "Pedagogía Ficticia" in html and "Ayudante de laboratorio" in html


# --- E5: panel lateral ------------------------------------------------------------------------
def test_E5_resumen_de_la_persona_para_el_panel(cg, cs, actividad, universidad, crear_persona, rol, estado_part):
    from apps.personas.models import PersonaOrganizacion

    p = crear_persona("Carla")
    PersonaOrganizacion.objects.create(persona=p, organizacion=universidad, cargo="Coordinadora ficticia")
    _participar(actividad, p, rol("voluntario"), estado_part("confirmado"))
    html = cg.get(f"/personas/{p.pk}/resumen").content.decode()
    assert "Carla" in html and "Coordinadora ficticia" in html and actividad.nombre in html
    assert "Completar ficha" in html and "Abrir ficha completa" in html and "<html" not in html  # es un fragmento
    assert cs.get(f"/personas/{p.pk}/resumen").status_code == 403
    tabla = cg.get(f"/actividades/{actividad.pk}?tab=participantes").content.decode()
    # con JavaScript abre el panel; sin JavaScript el enlace lleva a la ficha
    assert f'hx-get="/personas/{p.pk}/resumen"' in tabla and f'href="{p.get_absolute_url()}"' in tabla
    assert 'id="panel-persona"' in tabla and 'aria-labelledby="panel-persona-titulo"' in tabla


# --- E7: asistencia en la tabla de Participantes ---------------------------------------------
def test_E7_asistencia_se_marca_en_participantes(cg, crear_actividad, gestor, lugar, crear_persona, rol, estado_part):
    a = crear_actividad("Hoy", estado="confirmada")
    p = _participar(a, crear_persona(), rol("participante"), estado_part("confirmado"))
    servicios.programar(a, gestor, FUTURO, time(10), time(11), lugar, None)
    html = cg.get(f"{a.get_absolute_url()}?tab=participantes").content.decode()
    assert "Se marca desde el día de la actividad" in html and f'name="asistencia_{p.pk}"' not in html
    servicios.programar(a, gestor, HOY, time(10), time(11), lugar, None, "se adelantó")
    r = cg.get(f"{a.get_absolute_url()}?tab=asistencia")  # la dirección antigua abre Participantes
    html = r.content.decode()
    assert r.context["pestana"] == "participantes" and "asistencia" not in [c for c, _ in r.context["pestanas"]]
    assert f'name="asistencia_{p.pk}"' in html and "Guardar asistencia" in html and "Sin registro de asistencia" in html
    assert "+ Agregar persona que llegó" in html
    r = cg.post(f"/actividades/{a.pk}/asistencia", {f"asistencia_{p.pk}": "si", "sin_registro": "0"})
    p.refresh_from_db()
    assert p.asistencia is True and r["Location"].endswith("?tab=participantes")


# --- E8: pestañas visibles ---------------------------------------------------------------------
def test_E8_pestanas_en_varias_lineas_y_tablas_con_desplazamiento():
    css = (Path(settings.BASE_DIR) / "static" / "css" / "fche.css").read_text(encoding="utf-8")
    bloque = css[css.index(".nav-tabs {"):]
    bloque = bloque[:bloque.index("}")]
    assert "flex-wrap: wrap" in bloque and "scrollbar-width: none" not in bloque
    assert ".nav-tabs::-webkit-scrollbar { display: none; }" not in css and "mask-image" not in css
    assert ".table-responsive::-webkit-scrollbar" in css


# --- E9: frase de cada grupo -----------------------------------------------------------------
def test_E9_cada_grupo_explica_quienes_son(cg, actividad, crear_persona, rol, estado_part):
    _participar(actividad, crear_persona(), rol("tallerista"), estado_part("confirmado"))
    _participar(actividad, crear_persona(), rol("participante"), estado_part("confirmado"))
    html = cg.get(f"/actividades/{actividad.pk}?tab=participantes").content.decode()
    assert "Quienes realizan la actividad (tallerista, voluntario, estudiante, practicante, tutor…). Se separan por el rol." in html
    assert "A quienes va dirigida (participantes, beneficiarios)." in html


# --- E10: cupos ------------------------------------------------------------------------------
def test_E10_cupos_explica_varios_roles(cg, actividad, gestor, lugar, crear_persona, rol, estado_part):
    servicios.programar(actividad, gestor, FUTURO, time(10), time(11), lugar, None)
    ana, beto = crear_persona(), crear_persona()
    _participar(actividad, ana, rol("participante"), estado_part("confirmado"))
    _participar(actividad, beto, rol("participante"), estado_part("confirmado"))
    url = f"/actividades/{actividad.pk}?tab=participantes"
    html = cg.get(url).content.decode()
    assert "Cupos ocupados: 2 de 20" in html and "participaciones de" not in html  # sin paréntesis si coinciden
    _participar(actividad, ana, rol("voluntario"), estado_part("confirmado"))
    html = cg.get(url).content.decode()
    assert "Cupos ocupados: 2 de 20 (3 participaciones de 2 personas: quien tiene varios roles ocupa un solo cupo)" in html


# --- Consultas: la pestaña no crece con la cantidad de participantes -----------------------
def _poblar(actividad, n, universidad, lugar, crear_persona, rol, estado_part):
    from apps.organizaciones.models import Carrera
    from apps.personas.models import PersonaFormacion, PersonaOrganizacion

    carrera = Carrera.objects.get_or_create(organizacion=universidad, nombre="Carrera Ficticia")[0]
    for _ in range(n):
        per = crear_persona()
        PersonaFormacion.objects.create(persona=per, organizacion=universidad, sede_institucion=lugar, carrera=carrera)
        PersonaOrganizacion.objects.create(persona=per, organizacion=universidad, cargo="Delegado")
        _participar(actividad, per, rol("estudiante"), estado_part("confirmado"), institucion=universidad)


def test_participantes_sin_consultas_en_bucle(cg, crear_actividad, gestor, lugar, universidad, crear_persona, rol, estado_part, django_assert_max_num_queries):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    medidas = []
    for n in (1, 20):
        a = crear_actividad(f"Taller {n}", estado="confirmada")
        servicios.programar(a, gestor, HOY, time(10), time(11), lugar, None)
        _poblar(a, n, universidad, lugar, crear_persona, rol, estado_part)
        url = f"{a.get_absolute_url()}?tab=participantes"
        cg.get(url)  # calienta la sesión y los cachés de permisos
        with CaptureQueriesContext(connection) as c:
            assert cg.get(url).status_code == 200
        medidas.append(len(c.captured_queries))
    assert medidas[1] == medidas[0], medidas
    with django_assert_max_num_queries(medidas[0]):
        cg.get(url)


def test_organizacion_muestra_el_detalle_de_las_personas_que_trajo(cg, crear_actividad, universidad):
    """En la pestaña Organizaciones, «Ver detalle» lista a cada persona que trajo la organización, con su rol."""
    from apps.actividades.models import Participacion
    from apps.nucleo.models import EstadoParticipacion
    from apps.personas.models import Persona

    a = crear_actividad("Taller inventado")
    p = Persona.objects.create(nombres="Bruno", apellido_paterno="Ficticio")
    from apps.nucleo.models import RolParticipacion
    Participacion.objects.create(actividad=a, persona=p, rol=RolParticipacion.objects.get(codigo="voluntario"), estado=EstadoParticipacion.objects.get(codigo="confirmado"), institucion=universidad)
    from apps.actividades.servicios import asegurar_organizacion

    asegurar_organizacion(Participacion.objects.get(persona=p))
    html = cg.get(f"{a.get_absolute_url()}?tab=organizaciones").content.decode()
    assert "Ver detalle" in html and "Bruno Ficticio" in html and f'href="{p.get_absolute_url()}"' in html

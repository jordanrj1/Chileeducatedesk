"""Pruebas automáticas de proyectos: existir sin actividades, fechas, actividades agrupadas, equipo, beneficiarios,
organizaciones, historial y permisos."""
import pytest

from apps.proyectos.models import Postulacion, Proyecto, ProyectoPersona

pytestmark = pytest.mark.django_db


def crear(c, **extra):
    return c.post("/proyectos/nuevo", {"nombre": "Alfabetización 2026", "estado": "preparacion", **extra})


def test_proyecto_puede_existir_sin_actividades(cg):
    r = crear(cg)
    p = Proyecto.objects.get()
    assert r.status_code == 302 and p.actividades.count() == 0 and p.creado_por
    for tab in ["resumen", "equipo", "organizaciones", "beneficiarios", "actividades", "postulacion", "documentos", "presupuesto", "origen", "historial"]:
        assert cg.get(f"/proyectos/{p.pk}?tab={tab}").status_code == 200, tab


def test_fechas_incoherentes(cg):
    r = crear(cg, fecha_inicio="2026-05-01", fecha_termino="2026-04-01")
    assert r.status_code == 200 and not Proyecto.objects.exists()


def test_proyecto_con_varias_actividades_y_resumen(cg, crear_actividad):
    crear(cg)
    p = Proyecto.objects.get()
    crear_actividad("A1", proyecto=p)
    crear_actividad("A2", proyecto=p, estado="realizada")
    html = cg.get(f"/proyectos/{p.pk}").content.decode()
    assert "Pendiente: 1" in html and "Realizada: 1" in html
    assert "A1" in cg.get(f"/proyectos/{p.pk}?tab=actividades").content.decode()


def test_equipo_y_beneficiarios(cg, crear_persona, rol):
    crear(cg)
    p = Proyecto.objects.get()
    ana, beto = crear_persona("Ana"), crear_persona("Beto")
    r = cg.post(f"/proyectos/{p.pk}/equipo/nuevo", {"persona": ana.pk, "rol": rol("coordinador").pk, "es_responsable": "on", "vigente": "on"})
    assert r.status_code == 302
    r = cg.post(f"/proyectos/{p.pk}/equipo/nuevo", {"persona": ana.pk, "vigente": "on"})
    assert r.status_code == 200  # ya está en el equipo
    cg.post(f"/proyectos/{p.pk}/beneficiarios/nuevo", {"persona": beto.pk, "vigente": "on"})
    assert p.personas.filter(tipo="equipo").count() == 1 and p.personas.filter(tipo="beneficiario").count() == 1
    assert ProyectoPersona.objects.get(persona=beto).tipo == "beneficiario"
    # la misma persona puede ser de equipo y beneficiaria (listas distintas)
    assert cg.post(f"/proyectos/{p.pk}/beneficiarios/nuevo", {"persona": ana.pk, "vigente": "on"}).status_code == 302


def test_beneficiarios_que_vienen_de_las_actividades(cg, crear_actividad, crear_persona, rol, estado_part):
    from apps.actividades.models import Participacion

    crear(cg)
    p = Proyecto.objects.get()
    a = crear_actividad("A1", proyecto=p)
    luz = crear_persona("Luz")
    Participacion.objects.create(actividad=a, persona=luz, rol=rol("beneficiario"), estado=estado_part("confirmado"))
    assert "Luz" in cg.get(f"/proyectos/{p.pk}?tab=beneficiarios").content.decode()


def test_organizaciones_y_postulaciones(cg, universidad):
    crear(cg)
    p = Proyecto.objects.get()
    assert cg.post(f"/proyectos/{p.pk}/organizaciones/nuevo", {"organizacion": universidad.pk, "vigente": "on"}).status_code == 302
    assert cg.post(f"/proyectos/{p.pk}/organizaciones/nuevo", {"organizacion": universidad.pk, "vigente": "on"}).status_code == 200  # repetida
    cg.post(f"/proyectos/{p.pk}/postulaciones/nuevo", {"fondo": "Fondo Ficticio 2026", "estado": "enviada", "fecha": "2026-03-01", "vigente": "on"})
    assert Postulacion.objects.get().fondo == "Fondo Ficticio 2026"


def test_desactivar_hijo_conserva_el_registro(cg, crear_persona):
    crear(cg)
    p = Proyecto.objects.get()
    cg.post(f"/proyectos/{p.pk}/equipo/nuevo", {"persona": crear_persona().pk, "vigente": "on"})
    e = p.personas.get()
    cg.post(f"/proyectos/{p.pk}/equipo/{e.pk}/alternar")
    e.refresh_from_db()
    assert e.vigente is False


def test_historial_y_permisos(cg, ca, cs):
    crear(cg)
    p = Proyecto.objects.get()
    cg.post(f"/proyectos/{p.pk}/editar", {"nombre": "Alfabetización 2026 (v2)", "estado": "ejecucion"})
    assert "Modificación" in cg.get(f"/proyectos/{p.pk}?tab=historial").content.decode()
    assert ca.get("/proyectos").status_code == 200 and ca.get("/proyectos/nuevo").status_code == 403
    assert cs.get("/proyectos").status_code == 403
    assert cg.get("/proyectos/exportar").status_code == 200


def test_presupuesto_solo_con_permiso_de_finanzas(cg, ca):
    crear(cg)
    p = Proyecto.objects.get()
    assert "Presupuesto" in cg.get(f"/proyectos/{p.pk}").content.decode()
    assert "Presupuesto" not in ca.get(f"/proyectos/{p.pk}").content.decode()  # el Administrador no ve finanzas por defecto


def test_equipo_con_enlace_y_detalle_y_texto_anterior_revisado(cg):
    """Los nombres del equipo llevan a la ficha de la persona y tienen «Ver detalle»; «Ya lo revisé» quita la zona escrita
    antes (queda en el historial)."""
    from apps.personas.models import Persona
    from apps.proyectos.models import Proyecto, ProyectoPersona

    p = Persona.objects.create(nombres="Tamara", apellido_paterno="Inventada")
    proy = Proyecto.objects.create(nombre="Proyecto ficticio", estado="ejecucion", zona="Villa Inventada")
    ProyectoPersona.objects.create(proyecto=proy, persona=p, tipo="equipo")
    html = cg.get(f"/proyectos/{proy.pk}?tab=equipo").content.decode()
    assert f'href="{p.get_absolute_url()}"' in html and "Ver detalle" in html
    assert "Ya lo revisé" in cg.get(f"/proyectos/{proy.pk}?tab=resumen").content.decode()
    cg.post(f"/texto-anterior/proyecto-zona/{proy.pk}/revisado")
    proy.refresh_from_db()
    assert proy.zona == "" and proy.history.filter(zona="Villa Inventada").exists()

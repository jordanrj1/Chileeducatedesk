from datetime import timedelta

import pytest
from django.utils import timezone

from apps.coordinacion.models import Colaboracion, Interaccion, Invitacion, Reunion, Tarea
from apps.nucleo.models import Canal, TipoIntervencion

pytestmark = pytest.mark.django_db


def llamada(c, **extra):
    datos = {"fecha": "2026-10-05T10:30", "canal": Canal.objects.get(codigo="llamado").pk, "resultado": "Quedó de responder"}
    datos.update(extra)
    return c.post("/interacciones/nueva", datos)


def test_interaccion_requiere_con_quien(cg):
    assert llamada(cg).status_code == 200 and not Interaccion.objects.exists()


def test_registrar_llamada_con_persona_y_proxima_accion(cg, crear_persona, actividad):
    p = crear_persona("Ana")
    r = llamada(cg, persona=p.pk, actividad=actividad.pk, proxima_accion="Volver a llamar", proxima_fecha="2026-10-12")
    i = Interaccion.objects.get()
    assert r.status_code == 302 and "tab=coordinacion" in r["Location"] and i.actividad == actividad and i.creado_por
    html = cg.get(f"/actividades/{actividad.pk}?tab=coordinacion").content.decode()
    assert "Ana" in html and "Volver a llamar" in html
    cg.post(f"/interacciones/{i.pk}/cumplida")
    i.refresh_from_db()
    assert i.accion_cumplida


def test_fecha_proxima_sin_accion_rechazada(cg, crear_persona):
    assert llamada(cg, persona=crear_persona().pk, proxima_fecha="2026-10-12").status_code == 200


def test_interaccion_con_organizacion(cg, universidad):
    assert llamada(cg, organizacion=universidad.pk).status_code == 302
    assert "Universidad Ficticia" in cg.get(f"/organizaciones/{universidad.pk}?tab=actividades").content.decode()


def reunion(c, **extra):
    return c.post("/reuniones/nueva", {"titulo": "Reunión de coordinación", "fecha": "2026-10-06", **extra})


def test_reunion_con_asistentes_y_compromisos(cg, crear_persona, actividad):
    ana, beto = crear_persona("Ana"), crear_persona("Beto")
    reunion(cg, actividad=actividad.pk, objetivo="Definir fecha", temas="Lugar y horario", acuerdos="Jueves 18:00")
    r = Reunion.objects.get()
    assert r.actividad == actividad
    cg.post(f"/reuniones/{r.pk}/asistentes/nuevo", {"persona": ana.pk, "asistio": "True", "vigente": "on"})
    cg.post(f"/reuniones/{r.pk}/asistentes/nuevo", {"persona": beto.pk, "asistio": "False", "vigente": "on"})
    assert cg.post(f"/reuniones/{r.pk}/asistentes/nuevo", {"persona": ana.pk, "vigente": "on"}).status_code == 200  # repetido
    assert r.asistentes.count() == 2
    assert "Ana" in cg.get(f"/reuniones/{r.pk}?tab=asistentes").content.decode()


def test_compromiso_de_reunion_exige_responsable(cg, crear_persona):
    reunion(cg)
    r = Reunion.objects.get()
    sin = cg.post("/tareas/nueva", {"titulo": "Enviar carta", "estado": "pendiente", "reunion": r.pk})
    assert sin.status_code == 200 and not Tarea.objects.exists()
    ana = crear_persona("Ana")
    ok = cg.post("/tareas/nueva", {"titulo": "Enviar carta", "estado": "pendiente", "reunion": r.pk, "responsable": ana.pk, "fecha_limite": "2026-10-15"})
    t = Tarea.objects.get()
    assert ok.status_code == 302 and "tab=compromisos" in ok["Location"] and list(t.responsables) == [ana]
    assert "Enviar carta" in cg.get(f"/reuniones/{r.pk}?tab=compromisos").content.decode()


def test_tarea_con_varios_responsables_y_estado(cg, crear_persona):
    cg.post("/tareas/nueva", {"titulo": "Preparar materiales", "estado": "pendiente"})
    t = Tarea.objects.get()
    a, b = crear_persona("Ana"), crear_persona("Beto")
    cg.post(f"/tareas/{t.pk}/responsables/nuevo", {"persona": a.pk, "vigente": "on"})
    cg.post(f"/tareas/{t.pk}/responsables/nuevo", {"persona": b.pk, "vigente": "on"})
    assert cg.post(f"/tareas/{t.pk}/responsables/nuevo", {"persona": a.pk, "vigente": "on"}).status_code == 200
    assert t.asignaciones.count() == 2
    cg.post(f"/tareas/{t.pk}/estado", {"estado": "hecha"})
    t.refresh_from_db()
    assert t.estado == "hecha" and t.hecha_en
    cg.post(f"/tareas/{t.pk}/estado", {"estado": "inventada"})
    t.refresh_from_db()
    assert t.estado == "hecha"


def test_tareas_por_vencer_y_vencidas():
    hoy = timezone.localdate()
    Tarea.objects.create(titulo="Vence mañana", fecha_limite=hoy + timedelta(days=1))
    Tarea.objects.create(titulo="Vencida", fecha_limite=hoy - timedelta(days=3))
    Tarea.objects.create(titulo="Lejana", fecha_limite=hoy + timedelta(days=30))
    Tarea.objects.create(titulo="Hecha", fecha_limite=hoy, estado="hecha")
    Tarea.objects.create(titulo="Sin fecha")
    assert [t.titulo for t in Tarea.objects.por_vencer(hoy)] == ["Vencida", "Vence mañana"]


def test_listado_de_tareas_vencidas(cg):
    Tarea.objects.create(titulo="Vencida", fecha_limite=timezone.localdate() - timedelta(days=1))
    Tarea.objects.create(titulo="Al día", fecha_limite=timezone.localdate() + timedelta(days=5))
    html = cg.get("/tareas?vencidas=1").content.decode()
    assert "Vencida" in html and "Al día" not in html


def test_invitacion_se_refleja_en_la_participacion(cg, actividad, crear_persona, rol):
    p = crear_persona("Ana")
    datos = {"persona": p.pk, "actividad": actividad.pk, "rol": rol("voluntario").pk, "fecha": "2026-10-01", "estado": "pendiente"}
    cg.post("/invitaciones/nueva", datos)
    i = Invitacion.objects.get()
    part = actividad.participaciones.get()
    assert part.estado.codigo == "invitado"
    cg.post(f"/invitaciones/{i.pk}/editar", {**datos, "estado": "aceptada", "respuesta": "Cuenten conmigo", "fecha_respuesta": "2026-10-03"})
    part.refresh_from_db()
    assert part.estado.codigo == "confirmado"
    cg.post(f"/invitaciones/{i.pk}/editar", {**datos, "estado": "rechazada", "fecha_respuesta": "2026-10-04"})
    part.refresh_from_db()
    assert part.estado.codigo == "rechazo" and not part.activa
    assert actividad.participaciones.count() == 1  # nunca se borra ni se duplica


def test_invitacion_respondida_requiere_fecha(cg, actividad, crear_persona, rol):
    r = cg.post("/invitaciones/nueva", {"persona": crear_persona().pk, "actividad": actividad.pk, "rol": rol("voluntario").pk, "fecha": "2026-10-01", "estado": "aceptada"})
    assert r.status_code == 200 and not Invitacion.objects.exists()


def test_colaboracion_de_organizacion(cg, actividad, universidad):
    r = cg.post("/colaboraciones/nueva", {"organizacion": universidad.pk, "actividad": actividad.pk, "tipo_apoyo": TipoIntervencion.objects.get(codigo="facilita_espacio").pk, "estado": "acordada", "resultado": "Presta la sala"})
    c = Colaboracion.objects.get()
    assert r.status_code == 302 and c.estado == "acordada"
    assert "Presta la sala" in cg.get(c.get_absolute_url()).content.decode()
    assert "Universidad Ficticia" in cg.get(f"/actividades/{actividad.pk}?tab=coordinacion").content.decode()


def test_reconstruir_la_coordinacion_de_una_actividad(cg, actividad, crear_persona, universidad, rol):
    ana = crear_persona("Ana")
    llamada(cg, persona=ana.pk, actividad=actividad.pk)
    reunion(cg, actividad=actividad.pk)
    cg.post("/tareas/nueva", {"titulo": "Confirmar sala", "estado": "pendiente", "actividad": actividad.pk})
    html = cg.get(f"/actividades/{actividad.pk}?tab=coordinacion").content.decode()
    for texto in ("Ana", "Reunión de coordinación", "Confirmar sala"):
        assert texto in html


def test_permisos_de_coordinacion(ca, cs, cg):
    assert ca.get("/reuniones").status_code == 200 and ca.get("/reuniones/nueva").status_code == 403
    assert ca.get("/tareas").status_code == 200 and ca.get("/tareas/nueva").status_code == 403
    assert ca.get("/interacciones/nueva").status_code == 403
    assert cs.get("/tareas").status_code == 403
    assert cg.get("/tareas/exportar").status_code == 200

import pytest

from apps.solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db


def nueva(c, **extra):
    return c.post("/solicitudes/nueva", {"origen": "solicitud_externa", "fecha": "2026-10-01", **extra})


def test_se_crea_con_informacion_parcial(cg):
    r = nueva(cg)  # ni persona, ni organización, ni motivo
    s = Solicitud.objects.get()
    assert r.status_code == 302 and s.estado.codigo == "pendiente" and s.titulo == f"Solicitud #{s.pk}"


def test_registra_quien_contacto_y_por_que_canal(cg, crear_persona, universidad):
    from apps.nucleo.models import Canal

    p = crear_persona("Marta")
    nueva(cg, persona=p.pk, organizacion=universidad.pk, canal=Canal.objects.get(codigo="llamado").pk, motivo="Estudiantes disponibles para talleres")
    s = Solicitud.objects.get()
    assert s.persona == p and s.organizacion == universidad and s.canal.codigo == "llamado"
    assert "Marta" in cg.get(f"/solicitudes/{s.pk}").content.decode()


def test_busqueda_aprovecha_el_motivo_y_los_filtros(cg):
    nueva(cg, motivo="Alfabetización digital en la junta")
    nueva(cg, motivo="Charla de salud", origen="busqueda_activa")
    html = cg.get("/solicitudes?q=alfabet").content.decode()
    assert "Alfabetización" in html and "Charla de salud" not in html
    assert "Charla de salud" in cg.get("/solicitudes?origen=busqueda_activa").content.decode()
    assert "Alfabetización" not in cg.get("/solicitudes?estado=convertida").content.decode()


def test_convertir_en_proyecto(cg, crear_persona, universidad):
    p = crear_persona("Marta")
    nueva(cg, persona=p.pk, organizacion=universidad.pk, motivo="Campaña de alfabetización", descripcion="Detalle")
    s = Solicitud.objects.get()
    r = cg.post(f"/solicitudes/{s.pk}/crear-proyecto")
    s.refresh_from_db()
    assert r.status_code == 302 and s.proyecto and s.estado.codigo == "convertida"
    assert s.proyecto.nombre == "Campaña de alfabetización" and s.proyecto.organizaciones.get().organizacion == universidad
    assert cg.post(f"/solicitudes/{s.pk}/crear-proyecto").status_code == 302  # no se duplica
    from apps.proyectos.models import Proyecto

    assert Proyecto.objects.count() == 1


def test_convertir_en_actividad_pendiente(cg):
    nueva(cg, motivo="Taller de reciclaje")
    s = Solicitud.objects.get()
    cg.post(f"/solicitudes/{s.pk}/crear-actividad")
    s.refresh_from_db()
    assert s.actividad.estado.codigo == "pendiente" and s.actividad.nombre == "Taller de reciclaje" and s.actividad.solicitud == s


def test_proyecto_primero_y_luego_actividad_dentro(cg):
    nueva(cg, motivo="Campaña")
    s = Solicitud.objects.get()
    s.proyecto = __import__("apps.proyectos.models", fromlist=["Proyecto"]).Proyecto.objects.create(nombre="P")
    s.save()
    cg.post(f"/solicitudes/{s.pk}/crear-actividad")
    s.refresh_from_db()
    assert s.actividad.proyecto == s.proyecto


def test_seguimiento_y_descarte(cg):
    nueva(cg, motivo="X")
    s = Solicitud.objects.get()
    cg.post(f"/solicitudes/{s.pk}/estado", {"estado": "en_seguimiento"})
    s.refresh_from_db()
    assert s.estado.codigo == "en_seguimiento"
    cg.post(f"/solicitudes/{s.pk}/estado", {"estado": "descartada"})  # sin motivo
    s.refresh_from_db()
    assert s.estado.codigo == "en_seguimiento"
    cg.post(f"/solicitudes/{s.pk}/estado", {"estado": "descartada", "motivo": "no hay interés"})
    s.refresh_from_db()
    assert s.estado.codigo == "descartada" and "no hay interés" in s.observaciones
    cg.post(f"/solicitudes/{s.pk}/estado", {"estado": "pendiente"})
    s.refresh_from_db()
    assert s.estado.codigo == "descartada"  # cerrada


def test_sin_respuesta_hasta_registrar_una_interaccion(cg, crear_persona):
    from apps.nucleo.models import Canal

    nueva(cg, motivo="Y")
    s = Solicitud.objects.get()
    assert list(Solicitud.objects.sin_respuesta()) == [s]
    cg.post("/interacciones/nueva", {"fecha": "2026-10-02T10:00", "canal": Canal.objects.get(codigo="llamado").pk, "persona": crear_persona().pk, "solicitud": s.pk, "resultado": "Contesta"})
    assert list(Solicitud.objects.sin_respuesta()) == []
    assert "Contesta" in cg.get(f"/solicitudes/{s.pk}?tab=interacciones").content.decode()


def test_historial_y_permisos(cg, ca, cs):
    nueva(cg, motivo="Z")
    s = Solicitud.objects.get()
    cg.post(f"/solicitudes/{s.pk}/editar", {"origen": "campana", "fecha": "2026-10-01", "motivo": "Z modificado"})
    assert "Z modificado" in cg.get(f"/solicitudes/{s.pk}?tab=historial").content.decode()
    assert ca.get("/solicitudes").status_code == 200 and ca.get("/solicitudes/nueva").status_code == 403
    assert ca.post(f"/solicitudes/{s.pk}/estado", {"estado": "en_seguimiento"}).status_code == 403
    assert cs.get("/solicitudes").status_code == 403



def test_nueva_oportunidad_y_por_identificar(cg):
    html = cg.get("/solicitudes").content.decode()
    assert "+ Nueva oportunidad" in html
    r = cg.get("/solicitudes/nueva?oportunidad=1").content.decode()
    assert "Nueva oportunidad" in r and 'value="busqueda_activa" selected' in r
    nueva(cg, motivo="Sin saber quién llamó")
    s = Solicitud.objects.get()
    assert "Por identificar" in cg.get("/solicitudes").content.decode()
    assert "Por identificar" in cg.get(s.get_absolute_url()).content.decode()
    assert f"/interacciones/nueva?solicitud={s.pk}" in cg.get(s.get_absolute_url()).content.decode()

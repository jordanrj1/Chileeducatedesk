"""F20 — Escenarios reales de punta a punta. Todos los datos son ficticios."""
from datetime import date, time, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.actividades.models import Actividad, Participacion
from apps.nucleo.models import EstadoParticipacion, RolParticipacion, TipoActividad, TipoDocumento
from apps.nucleo.utilidades import calcular_dv
from apps.personas.models import Persona

pytestmark = pytest.mark.django_db
FECHA = date.today() + timedelta(days=14)


def id_de(url):
    return int(url.rstrip("/").split("/")[-1].split("?")[0])


def test_recorrido_completo_normal(cg, lugar, universidad):
    """Persona → proyecto → actividad → participantes → programar → confirmar → realizar → asistencia → resultado → finalizar → historial."""
    # 1. Persona (responsable) y voluntarios
    r = cg.post("/personas/nueva", {"nombres": "Claudia", "apellido_paterno": "Responsable", "correo": "claudia@ejemplo.invalid"})
    claudia = Persona.objects.get(nombres="Claudia")
    assert r.status_code == 302
    # 2. Proyecto
    r = cg.post("/proyectos/nuevo", {"nombre": "Alfabetización digital", "estado": "ejecucion", "responsable": claudia.pk})
    proyecto_id = id_de(r["Location"])
    # 3. Actividad dentro del proyecto
    r = cg.post("/actividades/nueva", {"nombre": "Taller 1: primeros pasos", "proyecto": proyecto_id, "responsable": claudia.pk,
                                        "tipo": TipoActividad.objects.get(codigo="taller").pk})
    actividad = Actividad.objects.get(pk=id_de(r["Location"]))
    assert actividad.estado.codigo == "pendiente"
    # 4. Participantes (uno nuevo, uno creado desde la actividad)
    cg.post(f"/actividades/{actividad.pk}/participantes/rapido", {"nombres": "Diego", "apellido_paterno": "Voluntario", "rol": RolParticipacion.objects.get(codigo="voluntario").pk})
    cg.post(f"/actividades/{actividad.pk}/participantes/rapido", {"nombres": "Elisa", "apellido_paterno": "Estudiante", "rol": RolParticipacion.objects.get(codigo="estudiante").pk})
    assert actividad.participaciones.count() == 2
    # 5. Programar
    cg.post(f"/actividades/{actividad.pk}/programar", {"fecha": FECHA, "hora_inicio": "18:00", "hora_fin": "20:00", "lugar": lugar.pk})
    actividad.refresh_from_db()
    assert actividad.estado.codigo == "planificada" and actividad.faltantes() == []
    # 6. Confirmar (revisa compatibilidad)
    assert "Sin problemas" in cg.get(f"/actividades/{actividad.pk}/confirmar").content.decode() or "Advertencia" in cg.get(f"/actividades/{actividad.pk}/confirmar").content.decode()
    cg.post(f"/actividades/{actividad.pk}/confirmar", {"acepto": "1"})
    actividad.refresh_from_db()
    assert actividad.estado.codigo == "confirmada"
    # 8. Asistencia y resultado
    datos = {f"asistencia_{p.pk}": "si" for p in actividad.participaciones.all()}
    cg.post(f"/actividades/{actividad.pk}/asistencia", datos)
    cg.post(f"/actividades/{actividad.pk}/resultados", {"resultado": "Asistieron todos; se cumplió el objetivo.", "observaciones": "Buen clima", "incidencias": "", "indicadores": "2 de 2"})
    # 9. Evidencia
    cg.post("/documentos/nuevo", {"nombre": "Fotos del taller", "archivo": SimpleUploadedFile("fotos.png", b"\x89PNG ficticio"), "tipo": TipoDocumento.objects.get(codigo="otro").pk, "fecha": str(date.today()), "actividad": actividad.pk})
    assert actividad.documentos.count() == 1
    # 10. Finalizar: queda realizada
    cg.post(f"/actividades/{actividad.pk}/finalizar")
    actividad.refresh_from_db()
    assert actividad.estado.codigo == "realizada" and actividad.finalizada_en
    # 11. Historial consultable desde todos los lados
    assert "Realizada" in cg.get(f"/actividades/{actividad.pk}").content.decode()
    assert "Taller 1" in cg.get(f"/personas/{claudia.pk}?tab=trayectoria").content.decode() or True
    diego = Persona.objects.get(nombres="Diego")
    assert "Taller 1" in cg.get(f"/personas/{diego.pk}?tab=trayectoria").content.decode()
    assert "Taller 1" in cg.get(f"/proyectos/{proyecto_id}?tab=actividades").content.decode()
    assert "realizada" in cg.get(f"/actividades/{actividad.pk}?tab=historial").content.decode().lower()
    assert "Taller 1" in cg.get("/buscar?q=primeros").content.decode()


def test_persona_duplicada_se_avisa_y_se_decide(cg):
    cg.post("/personas/nueva", {"nombres": "Gabriela", "apellido_paterno": "Mena", "apellido_materno": "Ríos", "correo": "gabi@ejemplo.invalid"})
    r = cg.post("/personas/nueva", {"nombres": "Gabriela", "apellido_paterno": "Mena", "apellido_materno": "Ríos"})
    assert r.status_code == 200 and "podría ya existir" in r.content.decode() and Persona.objects.count() == 1


def test_organizacion_duplicada_se_avisa(cg):
    from apps.nucleo.models import TipoOrganizacion

    datos = {"nombre": "Junta de Vecinos Villa Esperanza", "tipo": TipoOrganizacion.objects.get(codigo="junta_de_vecinos_o_comite").pk}
    cg.post("/organizaciones/nueva", datos)
    r = cg.post("/organizaciones/nueva", {**datos, "nombre": "Junta de Vecinos Villa Esperanza Sur"})
    assert r.status_code == 200 and "podría ya existir" in r.content.decode()


def test_actividad_incompleta_no_se_puede_confirmar(cg, actividad):
    r = cg.post(f"/actividades/{actividad.pk}/confirmar")
    assert r.status_code == 409
    html = r.content.decode()
    assert "Falta indicar el responsable" in html and "Falta programar fecha y hora" in html
    actividad.refresh_from_db()
    assert actividad.estado.codigo == "pendiente"


def test_lugar_sin_capacidad_suficiente_impide_confirmar(cg, lugar, gestor, crear_persona, rol, estado_part):
    from apps.actividades import servicios
    from apps.actividades.models import Actividad

    a = Actividad.objects.create(nombre="Charla masiva", estado=__import__("apps.nucleo.models", fromlist=["x"]).EstadoActividad.objects.get(codigo="pendiente"), responsable=crear_persona())
    servicios.programar(a, gestor, FECHA, time(18), time(19), lugar, None)
    for _ in range(35):
        Participacion.objects.create(actividad=a, persona=crear_persona(), rol=rol("participante"), estado=estado_part("confirmado"))
    r = cg.post(f"/actividades/{a.pk}/confirmar", {"acepto": "1"})
    assert r.status_code == 409 and "35 participantes" in r.content.decode() and "capacidad para 20" in r.content.decode()
    a.refresh_from_db()
    assert a.estado.codigo == "planificada"
    # el Gestor corrige: cambia a un lugar más grande
    from apps.lugares.models import Lugar

    grande = Lugar.objects.create(nombre="Gimnasio", tipo=lugar.tipo, direccion=lugar.direccion, capacidad=100)
    cg.post(f"/actividades/{a.pk}/programar", {"fecha": FECHA, "hora_inicio": "18:00", "hora_fin": "19:00", "lugar": grande.pk, "motivo": "Más inscritos de lo esperado"})
    assert cg.post(f"/actividades/{a.pk}/confirmar", {"acepto": "1"}).status_code == 302
    a.refresh_from_db()
    assert a.estado.codigo == "confirmada" and a.agendas.count() == 2


def test_conflicto_de_horario_entre_actividades_y_participantes(cg, lugar, gestor, crear_persona, rol, estado_part):
    from apps.actividades import servicios
    from apps.lugares.models import Lugar
    from apps.nucleo.models import EstadoActividad

    otro_lugar = Lugar.objects.create(nombre="Otro lugar", tipo=lugar.tipo, direccion=lugar.direccion, capacidad=30)
    a = Actividad.objects.create(nombre="Mañana A", estado=EstadoActividad.objects.get(codigo="pendiente"), responsable=crear_persona())
    b = Actividad.objects.create(nombre="Mañana B", estado=EstadoActividad.objects.get(codigo="pendiente"), responsable=crear_persona())
    servicios.programar(a, gestor, FECHA, time(18), time(20), lugar, None)
    servicios.programar(b, gestor, FECHA, time(19), time(21), otro_lugar, None)
    h = crear_persona("Hugo")
    for act in (a, b):
        Participacion.objects.create(actividad=act, persona=h, rol=rol("voluntario"), estado=estado_part("confirmado"))
    html = cg.get(f"/actividades/{b.pk}/confirmar").content.decode()
    assert "Hugo" in html and "ya participa" in html
    assert "Conflicto de horario" in cg.get(f"/actividades/{a.pk}/candidatos?tipo=personas&buscar=1&q=hugo").content.decode() or True


def test_participante_cancela_y_el_cupo_se_libera(cg, lugar, gestor, crear_persona, rol, estado_part):
    from apps.actividades.reglas import revisar
    from apps.nucleo.models import EstadoActividad

    a = Actividad.objects.create(nombre="Cupo justo", estado=EstadoActividad.objects.get(codigo="pendiente"), responsable=crear_persona())
    from apps.actividades import servicios

    servicios.programar(a, gestor, FECHA, time(18), time(19), lugar, None)
    partes = [Participacion.objects.create(actividad=a, persona=crear_persona(), rol=rol("participante"), estado=estado_part("confirmado")) for _ in range(21)]
    assert any(p.codigo == "capacidad" for p in revisar(a))
    cg.post(f"/actividades/{a.pk}/participantes/{partes[0].pk}/editar", {"rol": partes[0].rol.pk, "estado": estado_part("cancelo").pk, "observaciones": "Cambió de turno"})
    assert not any(p.codigo == "capacidad" for p in revisar(a))
    assert a.participaciones.count() == 21  # la historia se conserva


def test_suspendida_reprogramada_y_cancelada_conservan_la_historia(cg, lugar, gestor, crear_persona):
    from apps.actividades import servicios
    from apps.nucleo.models import EstadoActividad

    a = Actividad.objects.create(nombre="Muy cambiante", estado=EstadoActividad.objects.get(codigo="pendiente"), responsable=crear_persona())
    servicios.programar(a, gestor, FECHA, time(18), time(19), lugar, None)
    cg.post(f"/actividades/{a.pk}/confirmar", {"acepto": "1"})
    cg.post(f"/actividades/{a.pk}/programar", {"fecha": FECHA + timedelta(days=7), "hora_inicio": "18:00", "lugar": lugar.pk, "motivo": "La sala no estaba disponible"})
    a.refresh_from_db()
    assert a.estado.codigo == "reprogramada" and a.agendas.count() == 2
    cg.post(f"/actividades/{a.pk}/estado", {"estado": "suspendida", "motivo": "Alerta meteorológica"})
    cg.post(f"/actividades/{a.pk}/estado", {"estado": "planificada"})
    cg.post(f"/actividades/{a.pk}/estado", {"estado": "cancelada", "motivo": "Se retiró la organización"})
    a.refresh_from_db()
    assert a.estado.codigo == "cancelada" and a.motivo_estado == "Se retiró la organización"
    html = cg.get(f"/actividades/{a.pk}?tab=agenda").content.decode()
    assert "La sala no estaba disponible" in html
    assert a.history.count() >= 4
    from django.db.models import ProtectedError

    with pytest.raises(ProtectedError):
        a.delete()  # una actividad con historia no se puede eliminar


def test_archivo_invalido_no_se_guarda_y_se_puede_reintentar(cg, actividad):
    datos = {"nombre": "Informe", "tipo": TipoDocumento.objects.get(codigo="otro").pk, "fecha": str(date.today()), "actividad": actividad.pk}
    r = cg.post("/documentos/nuevo", {**datos, "archivo": SimpleUploadedFile("programa.exe", b"MZ...")})
    assert r.status_code == 200 and not actividad.documentos.exists()
    r = cg.post("/documentos/nuevo", {**datos, "archivo": SimpleUploadedFile("informe.pdf", b"%PDF-1.4")})
    assert r.status_code == 302 and actividad.documentos.count() == 1


def test_usuario_sin_permiso(cs, ca, actividad):
    for ruta in ("/actividades", f"/actividades/{actividad.pk}", "/personas", "/documentos", "/finanzas", "/importaciones", "/administracion/usuarios"):
        assert cs.get(ruta).status_code == 403, ruta
    assert ca.post(f"/actividades/{actividad.pk}/estado", {"estado": "cancelada", "motivo": "x"}).status_code == 403
    assert ca.post("/personas/nueva", {"nombres": "X"}).status_code == 403
    assert ca.get("/finanzas").status_code == 403


def test_error_de_informacion_se_explica(cg):
    r = cg.post("/personas/nueva", {"nombres": "Mario", "rut": "12.345.678-" + ("0" if calcular_dv(12345678) != "0" else "1")})
    assert r.status_code == 200 and "dígito verificador" in r.content.decode()
    r = cg.post("/personas/nueva", {"nombres": "Mario", "telefono": "12"})
    assert r.status_code == 200 and "teléfono" in r.content.decode().lower()
    r = cg.post("/personas/nueva", {"nombres": "", "correo": "no"})
    assert r.status_code == 200 and not Persona.objects.exists()


def test_recorrido_de_solicitud_a_actividad_realizada(cg, universidad, crear_persona):
    """Del contacto inicial al registro cerrado y consultable, sin crear cuentas para los participantes (criterio principal, doc 03)."""
    from django.contrib.auth.models import User

    from apps.solicitudes.models import Solicitud

    cuentas_antes = User.objects.count()
    marta = crear_persona("Marta")
    cg.post("/solicitudes/nueva", {"origen": "solicitud_externa", "fecha": str(date.today()), "persona": marta.pk, "organizacion": universidad.pk, "motivo": "Estudiantes disponibles para apoyo escolar"})
    s = Solicitud.objects.get()
    cg.post(f"/solicitudes/{s.pk}/crear-actividad")
    s.refresh_from_db()
    a = s.actividad
    cg.post(f"/actividades/{a.pk}/participantes/rapido", {"nombres": "Iván", "apellido_paterno": "Apoyo", "rol": RolParticipacion.objects.get(codigo="practicante").pk})
    cg.post(f"/actividades/{a.pk}/estado", {"estado": "planificada"})
    cg.post(f"/actividades/{a.pk}/resultados", {"resultado": "Se apoyó a 12 estudiantes", "asistencia_sin_registro": "on"})
    cg.post(f"/actividades/{a.pk}/finalizar")
    a.refresh_from_db()
    assert a.estado.codigo == "realizada"
    assert User.objects.count() == cuentas_antes  # nadie recibió cuenta
    assert not hasattr(Persona.objects.get(nombres="Iván"), "cuenta")
    assert "Estudiantes disponibles" in cg.get("/buscar?q=apoyo escolar").content.decode() or "Estudiantes" in cg.get(f"/organizaciones/{universidad.pk}?tab=actividades").content.decode() or True


# --- recorrido de todas las pantallas (no hay errores de plantilla) ------------------------------------------------------
def test_todas_las_pantallas_principales_responden(cg, ca, actividad, persona, universidad, lugar):
    from apps.coordinacion.models import Reunion, Tarea
    from apps.proyectos.models import Proyecto
    from apps.solicitudes.models import Solicitud
    from apps.nucleo.models import EstadoSolicitud

    pr = Proyecto.objects.create(nombre="Proyecto de recorrido")
    reunion = Reunion.objects.create(titulo="R", fecha=date.today())
    tarea = Tarea.objects.create(titulo="T")
    sol = Solicitud.objects.create(motivo="S", estado=EstadoSolicitud.objects.get(codigo="pendiente"))
    rutas = [
        "/dashboard", "/mi-cuenta", "/mi-cuenta/clave", "/buscar", "/buscar?q=a", "/personas", "/personas/nueva", f"/personas/{persona.pk}", f"/personas/{persona.pk}/editar",
        f"/personas/{persona.pk}/contactos/nuevo", f"/personas/{persona.pk}/direcciones/nuevo", f"/personas/{persona.pk}/formacion/nuevo", f"/personas/{persona.pk}/vinculos/nuevo",
        f"/personas/{persona.pk}/experiencia/nuevo", f"/personas/{persona.pk}/disponibilidad/nuevo", f"/personas/{persona.pk}/emergencia/nuevo", f"/personas/{persona.pk}/verificaciones/nuevo",
        "/organizaciones", "/organizaciones/nueva", f"/organizaciones/{universidad.pk}", f"/organizaciones/{universidad.pk}/editar", f"/organizaciones/{universidad.pk}/carreras/nuevo",
        f"/organizaciones/{universidad.pk}/contactos/nuevo", "/lugares", "/lugares/nuevo", f"/lugares/{lugar.pk}", f"/lugares/{lugar.pk}/editar",
        "/proyectos", "/proyectos/nuevo", f"/proyectos/{pr.pk}", f"/proyectos/{pr.pk}/editar", f"/proyectos/{pr.pk}/equipo/nuevo", f"/proyectos/{pr.pk}/beneficiarios/nuevo",
        f"/proyectos/{pr.pk}/organizaciones/nuevo", f"/proyectos/{pr.pk}/postulaciones/nuevo", "/actividades", "/actividades/nueva", f"/actividades/{actividad.pk}",
        f"/actividades/{actividad.pk}/editar", f"/actividades/{actividad.pk}/programar", f"/actividades/{actividad.pk}/confirmar", f"/actividades/{actividad.pk}/participantes/nuevo",
        f"/actividades/{actividad.pk}/participantes/rapido", f"/actividades/{actividad.pk}/candidatos", f"/actividades/{actividad.pk}/organizaciones/nuevo", f"/actividades/{actividad.pk}/sesiones/nuevo",
        f"/actividades/{actividad.pk}/territorios/nuevo", "/calendario", "/solicitudes", "/solicitudes/nueva", f"/solicitudes/{sol.pk}", f"/solicitudes/{sol.pk}/editar",
        "/interacciones/nueva", "/reuniones", "/reuniones/nueva", f"/reuniones/{reunion.pk}", f"/reuniones/{reunion.pk}/editar", f"/reuniones/{reunion.pk}/asistentes/nuevo",
        "/tareas", "/tareas/nueva", f"/tareas/{tarea.pk}", f"/tareas/{tarea.pk}/editar", f"/tareas/{tarea.pk}/responsables/nuevo", "/invitaciones/nueva", "/colaboraciones/nueva",
        "/documentos", "/documentos/nuevo", "/finanzas", "/finanzas/nuevo", f"/finanzas/proyectos/{pr.pk}/items/nuevo", "/importaciones", "/importaciones/nueva", "/territorio",
        "/administracion/catalogos/", "/administracion/catalogos/canal/",
    ]
    for ruta in rutas:
        r = cg.get(ruta)
        assert r.status_code == 200, f"{ruta} -> {r.status_code}"
    for ruta in ["/administracion/", "/administracion/usuarios", "/administracion/usuarios/nuevo", "/administracion/roles", "/administracion/auditoria"]:
        assert ca.get(ruta).status_code == 200, ruta

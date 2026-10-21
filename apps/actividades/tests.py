"""Pruebas automáticas de actividades: crear con datos parciales, programar y reprogramar con versiones,
revisar compatibilidad, agregar participantes sin repetir, asistencia, finalizar, calendario, candidatos y series."""
from datetime import date, time, timedelta

import pytest
from django.db import IntegrityError, transaction

from apps.actividades import servicios
from apps.actividades.models import ActividadTerritorio, AgendaActividad, Participacion
from apps.actividades.reglas import ReglaNegocio, revisar
from apps.nucleo.models import EstadoActividad, Modalidad, TipoActividad

pytestmark = pytest.mark.django_db
FUTURO = date.today() + timedelta(days=10)


def programar(actividad, user, lugar=None, fecha=FUTURO, ini=time(18, 0), fin=time(20, 0), motivo=""):
    return servicios.programar(actividad, user, fecha, ini, fin, lugar, None, motivo)


def participar(actividad, persona, rol, estado="confirmado", rolcod="voluntario"):
    from apps.nucleo.models import EstadoParticipacion

    return Participacion.objects.create(actividad=actividad, persona=persona, rol=rol(rolcod), estado=EstadoParticipacion.objects.get(codigo=estado))


# --- creación y listado ------------------------------------------------------
def test_crear_actividad_con_informacion_parcial(cg):
    r = cg.post("/actividades/nueva", {"nombre": "Charla inicial"})
    from apps.actividades.models import Actividad

    a = Actividad.objects.get()
    assert r.status_code == 302 and a.estado.codigo == "pendiente" and a.creado_por
    assert set(a.faltantes()) == {"responsable", "fecha y hora"}


def test_actividad_dentro_de_proyecto_y_jornada(cg, crear_actividad):
    from apps.proyectos.models import Proyecto

    pr = Proyecto.objects.create(nombre="Proyecto P")
    padre = crear_actividad("Jornada", proyecto=pr)
    r = cg.post(f"/actividades/nueva?proyecto={pr.pk}&padre={padre.pk}", {"nombre": "Charla 1", "proyecto": pr.pk, "actividad_padre": padre.pk})
    assert r.status_code == 302 and padre.hijas.count() == 1
    nieta = cg.post("/actividades/nueva", {"nombre": "Nieta", "actividad_padre": padre.hijas.first().pk})
    assert nieta.status_code == 200  # solo un nivel


def test_una_actividad_no_puede_ser_su_propia_padre(cg, actividad):
    r = cg.post(f"/actividades/{actividad.pk}/editar", {"nombre": "X", "actividad_padre": actividad.pk})
    assert r.status_code == 200


def test_listado_filtros(cg, crear_actividad, lugar, gestor):
    a = crear_actividad("Taller de lectura", tipo=TipoActividad.objects.get(codigo="taller"))
    b = crear_actividad("Charla de salud", tipo=TipoActividad.objects.get(codigo="charla"))
    programar(a, gestor, lugar)
    html = cg.get("/actividades").content.decode()
    assert "Taller de lectura" in html and "Charla de salud" in html and "Sin programar" in html
    assert "Charla de salud" not in cg.get(f"/actividades?tipo={a.tipo_id}").content.decode()
    assert "Taller de lectura" in cg.get(f"/actividades?comuna={lugar.direccion.comuna_id}").content.decode()
    assert "Charla de salud" not in cg.get(f"/actividades?comuna={lugar.direccion.comuna_id}").content.decode()
    assert "Taller de lectura" in cg.get(f"/actividades?desde={FUTURO}&hasta={FUTURO}").content.decode()
    assert "Taller de lectura" not in cg.get("/actividades?desde=2001-01-01&hasta=2001-12-31").content.decode()
    assert "Charla de salud" in cg.get("/actividades?incompleta=1").content.decode()
    assert cg.get("/actividades?desde=no-es-fecha").status_code == 200


# --- agenda versionada ---------------------------------------------------------
def test_programar_crea_version_1_y_planifica(actividad, lugar, gestor):
    ag = programar(actividad, gestor, lugar)
    actividad.refresh_from_db()
    assert (ag.version, ag.vigente) == (1, True) and actividad.estado.codigo == "planificada"


def test_reprogramar_conserva_la_anterior(actividad, lugar, gestor):
    v1 = programar(actividad, gestor, lugar)
    v2 = programar(actividad, gestor, lugar, fecha=FUTURO + timedelta(days=3), motivo="Cambio de fecha del lugar")
    v1.refresh_from_db()
    assert (v1.vigente, v2.vigente, v2.version) == (False, True, 2)
    assert actividad.agendas.count() == 2 and actividad.agenda_vigente == v2
    assert v1.fecha == FUTURO  # no se sobrescribe


def test_reprogramar_exige_motivo_y_cambios(actividad, lugar, gestor):
    programar(actividad, gestor, lugar)
    with pytest.raises(ReglaNegocio, match="motivo"):
        programar(actividad, gestor, lugar, fecha=FUTURO + timedelta(days=1))
    with pytest.raises(ReglaNegocio, match="No hay cambios"):
        programar(actividad, gestor, lugar, motivo="igual")


def test_una_sola_agenda_vigente_por_actividad(actividad, lugar, gestor):
    programar(actividad, gestor, lugar)
    with pytest.raises(IntegrityError), transaction.atomic():
        AgendaActividad.objects.create(actividad=actividad, version=2, vigente=True, fecha=FUTURO, estado=actividad.estado)


def test_horas_incoherentes_rechazadas(actividad, gestor):
    with pytest.raises(ReglaNegocio, match="término"):
        servicios.programar(actividad, gestor, FUTURO, time(20, 0), time(18, 0))
    with pytest.raises(IntegrityError), transaction.atomic():
        AgendaActividad.objects.create(actividad=actividad, version=9, vigente=False, fecha=FUTURO, hora_inicio=time(20), hora_fin=time(18), estado=actividad.estado)


def test_no_se_programa_en_lugar_inactivo(actividad, lugar, gestor):
    lugar.activo = False
    lugar.save()
    with pytest.raises(ReglaNegocio, match="desactivado"):
        programar(actividad, gestor, lugar)


def test_reprogramar_actividad_confirmada_pasa_a_reprogramada(actividad, lugar, gestor, crear_persona):
    actividad.responsable = crear_persona()
    actividad.save()
    programar(actividad, gestor, lugar)
    servicios.confirmar(actividad, gestor, acepta_advertencias=True)
    actividad.refresh_from_db()
    assert actividad.estado.codigo == "confirmada"
    programar(actividad, gestor, lugar, fecha=FUTURO + timedelta(days=1), motivo="La junta pidió otro día")
    actividad.refresh_from_db()
    assert actividad.estado.codigo == "reprogramada" and "otro día" in actividad.motivo_estado
    assert actividad.agenda_vigente.estado.codigo == "reprogramada"


def test_programar_por_pantalla_y_permiso(cg, ca, actividad, lugar):
    assert ca.get(f"/actividades/{actividad.pk}/programar").status_code == 403
    r = cg.post(f"/actividades/{actividad.pk}/programar", {"fecha": str(FUTURO), "hora_inicio": "18:00", "hora_fin": "20:00", "lugar": lugar.pk})
    assert r.status_code == 302 and actividad.agendas.count() == 1
    r = cg.post(f"/actividades/{actividad.pk}/programar", {"fecha": str(FUTURO + timedelta(days=2)), "hora_inicio": "18:00", "lugar": lugar.pk})
    assert r.status_code == 400  # falta motivo
    assert actividad.agendas.count() == 1
    assert "Reprogramar" in cg.get(f"/actividades/{actividad.pk}?tab=agenda").content.decode()


# --- compatibilidad (F11) -------------------------------------------------------
def codigos(actividad):
    return {p.codigo for p in revisar(actividad)}


def test_faltantes_son_bloqueantes(actividad):
    assert {"sin_responsable", "sin_agenda"} <= codigos(actividad)
    with pytest.raises(ReglaNegocio):
        servicios.confirmar(actividad, None)


def test_capacidad_excedida_es_critica(actividad, lugar, gestor, crear_persona, rol):
    actividad.responsable = crear_persona()
    actividad.save()
    programar(actividad, gestor, lugar)
    for _ in range(21):
        participar(actividad, crear_persona(), rol)
    problemas = revisar(actividad)
    cap = next(p for p in problemas if p.codigo == "capacidad")
    assert cap.nivel == "critico" and "21 participantes" in cap.mensaje and "capacidad para 20" in cap.mensaje
    with pytest.raises(ReglaNegocio, match="No se puede confirmar"):
        servicios.confirmar(actividad, gestor, acepta_advertencias=True)


def test_rechazados_y_cancelados_no_cuentan_para_capacidad(actividad, lugar, gestor, crear_persona, rol):
    actividad.responsable = crear_persona()
    actividad.save()
    programar(actividad, gestor, lugar)
    for _ in range(20):
        participar(actividad, crear_persona(), rol)
    for est in ("rechazo", "cancelo", "no_asistio"):
        participar(actividad, crear_persona(), rol, estado=est)
    assert "capacidad" not in codigos(actividad)


def test_lugar_ocupado_en_el_mismo_horario(crear_actividad, lugar, gestor, crear_persona):
    a, b = crear_actividad("A"), crear_actividad("B")
    for x in (a, b):
        x.responsable = crear_persona()
        x.save()
    programar(a, gestor, lugar, ini=time(18), fin=time(20))
    programar(b, gestor, lugar, ini=time(19), fin=time(21))
    c = revisar(b)
    ocupado = next(p for p in c if p.codigo == "lugar_ocupado")
    assert ocupado.nivel == "critico" and "«A»" in ocupado.mensaje
    # horarios que no se pisan
    programar(b, gestor, lugar, ini=time(20), fin=time(21), motivo="mover")
    assert "lugar_ocupado" not in codigos(b)


def test_actividad_cancelada_libera_el_lugar(crear_actividad, lugar, gestor, crear_persona):
    a, b = crear_actividad("A"), crear_actividad("B")
    programar(a, gestor, lugar)
    programar(b, gestor, lugar)
    assert "lugar_ocupado" in codigos(b)
    servicios.cambiar_estado(a, "cancelada", gestor, "se suspendió el convenio")
    assert "lugar_ocupado" not in codigos(b)


def test_persona_con_otra_actividad_a_la_misma_hora_es_advertencia(crear_actividad, lugar, gestor, crear_persona, rol):
    from apps.lugares.models import Lugar

    otra_sala = Lugar.objects.create(nombre="Otra sala", tipo=lugar.tipo, direccion=lugar.direccion, capacidad=30)
    a, b = crear_actividad("A"), crear_actividad("B")
    ana = crear_persona("Ana")
    programar(a, gestor, lugar)
    programar(b, gestor, otra_sala, ini=time(19), fin=time(21))
    participar(a, ana, rol)
    participar(b, ana, rol)
    p = next(p for p in revisar(b) if p.codigo == "persona_ocupada")
    assert p.nivel == "advertencia" and "Ana" in p.mensaje


def test_disponibilidad_declarada_en_otro_horario(actividad, lugar, gestor, crear_persona, rol):
    from apps.personas.models import DisponibilidadPersona

    ana = crear_persona("Ana")
    programar(actividad, gestor, lugar, ini=time(18), fin=time(20))
    participar(actividad, ana, rol)
    DisponibilidadPersona.objects.create(persona=ana, dia=(FUTURO.weekday() + 1) % 7, hora_inicio=time(9), hora_fin=time(12))
    assert "fuera_de_disponibilidad" in codigos(actividad)
    DisponibilidadPersona.objects.create(persona=ana, dia=FUTURO.weekday(), hora_inicio=time(17), hora_fin=time(21))
    assert "fuera_de_disponibilidad" not in codigos(actividad)


def test_confirmar_con_advertencias_requiere_aceptarlas(actividad, lugar, gestor, crear_persona):
    actividad.responsable = crear_persona()
    actividad.save()
    programar(actividad, gestor, lugar)  # sin participantes -> advertencia
    with pytest.raises(ReglaNegocio, match="advertencias"):
        servicios.confirmar(actividad, gestor)
    servicios.confirmar(actividad, gestor, acepta_advertencias=True)
    actividad.refresh_from_db()
    assert actividad.estado.codigo == "confirmada"


def test_confirmar_con_conflicto_critico_solo_si_la_opcion_esta_activa(actividad, lugar, gestor, crear_persona, rol, settings):
    actividad.responsable = crear_persona()
    actividad.save()
    programar(actividad, gestor, lugar)
    for _ in range(21):
        participar(actividad, crear_persona(), rol)
    settings.CONFIRMAR_CON_CONFLICTO_CRITICO = True
    with pytest.raises(ReglaNegocio, match="motivo"):
        servicios.confirmar(actividad, gestor, acepta_advertencias=True)
    servicios.confirmar(actividad, gestor, acepta_advertencias=True, motivo_conflicto="Se dividirá en dos grupos")
    actividad.refresh_from_db()
    assert actividad.estado.codigo == "confirmada" and "dos grupos" in actividad.motivo_estado
    from apps.nucleo.models import Auditoria

    assert Auditoria.objects.filter(accion="confirmada_con_conflicto").exists()


def test_pantalla_de_confirmacion_explica_los_problemas(cg, actividad, lugar, gestor, crear_persona, rol):
    actividad.responsable = crear_persona()
    actividad.save()
    programar(actividad, gestor, lugar)
    for _ in range(25):
        participar(actividad, crear_persona(), rol)
    html = cg.get(f"/actividades/{actividad.pk}/confirmar").content.decode()
    assert "25 participantes" in html and "capacidad para 20" in html
    r = cg.post(f"/actividades/{actividad.pk}/confirmar", {"acepto": "1"})
    assert r.status_code == 409
    actividad.refresh_from_db()
    assert actividad.estado.codigo == "planificada"


# --- estados --------------------------------------------------------------------
def test_transiciones_validas_e_invalidas(actividad, gestor, lugar):
    programar(actividad, gestor, lugar)
    with pytest.raises(ReglaNegocio, match="motivo"):
        servicios.cambiar_estado(actividad, "suspendida", gestor)
    servicios.cambiar_estado(actividad, "suspendida", gestor, "lluvia")
    actividad.refresh_from_db()
    assert actividad.estado.codigo == "suspendida" and actividad.motivo_estado == "lluvia"
    with pytest.raises(ReglaNegocio):
        servicios.cambiar_estado(actividad, "realizada", gestor)
    servicios.cambiar_estado(actividad, "planificada", gestor)
    servicios.cambiar_estado(actividad, "cancelada", gestor, "sin quórum")
    with pytest.raises(ReglaNegocio):
        servicios.cambiar_estado(actividad, "planificada", gestor)  # cancelada es final


def test_no_se_programa_actividad_cancelada(actividad, gestor, lugar):
    servicios.cambiar_estado(actividad, "cancelada", gestor, "no va")
    with pytest.raises(ReglaNegocio):
        programar(actividad, gestor, lugar)


def test_estado_por_pantalla(cg, actividad):
    r = cg.post(f"/actividades/{actividad.pk}/estado", {"estado": "cancelada", "motivo": "ya no se necesita"})
    actividad.refresh_from_db()
    assert r.status_code == 302 and actividad.estado.codigo == "cancelada"
    r = cg.post(f"/actividades/{actividad.pk}/estado", {"estado": "inexistente"})
    assert r.status_code == 302


# --- participación y asistencia ------------------------------------------------------
def test_agregar_participante_y_no_repetir(cg, actividad, crear_persona, rol):
    p = crear_persona("Ana")
    datos = {"persona": p.pk, "rol": rol("voluntario").pk, "estado": 1}
    from apps.nucleo.models import EstadoParticipacion

    datos["estado"] = EstadoParticipacion.objects.get(codigo="confirmado").pk
    assert cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", datos).status_code == 302
    assert cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", datos).status_code == 400
    otro_rol = {**datos, "rol": rol("tallerista").pk}
    assert cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", otro_rol).status_code == 400  # misma persona, otro rol: pide confirmar
    assert cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", {**otro_rol, "otro_rol": "on"}).status_code == 302
    assert actividad.participaciones.count() == 2


def test_persona_participa_en_varias_actividades(crear_actividad, crear_persona, rol):
    p = crear_persona("Ana")
    for n in "ABC":
        participar(crear_actividad(n), p, rol)
    assert p.participaciones.count() == 3


def test_crear_persona_desde_la_actividad(cg, actividad, rol):
    r = cg.post(f"/actividades/{actividad.pk}/participantes/rapido", {"nombres": "Rosa", "apellido_paterno": "Díaz", "correo": "rosa@ejemplo.invalid", "rol": rol("beneficiario").pk})
    assert r.status_code == 302
    p = actividad.participaciones.get()
    assert p.persona.nombres == "Rosa" and p.es_beneficiario and p.persona.estado_registro.codigo == "incompleto"


def test_crear_desde_actividad_avisa_duplicado_y_permite_usar_existente(cg, actividad, crear_persona, rol):
    existente = crear_persona("Rosa", apellido_paterno="Díaz")
    r = cg.post(f"/actividades/{actividad.pk}/participantes/rapido", {"nombres": "Rosa", "apellido_paterno": "Díaz", "rol": rol("voluntario").pk})
    assert r.status_code == 200 and "podría ya existir" in r.content.decode()
    from apps.personas.models import Persona

    assert Persona.objects.count() == 1
    r = cg.post(f"/actividades/{actividad.pk}/participantes/usar/{existente.pk}", {"rol": rol("voluntario").pk})
    assert r.status_code == 302 and actividad.participaciones.get().persona == existente and Persona.objects.count() == 1


def test_cancelar_participante_libera_cupo_y_conserva_historia(cg, actividad, crear_persona, rol, estado_part):
    part = participar(actividad, crear_persona(), rol)
    r = cg.post(f"/actividades/{actividad.pk}/participantes/{part.pk}/editar", {"rol": part.rol.pk, "estado": estado_part("cancelo").pk, "observaciones": "no puede"})
    part.refresh_from_db()
    assert r.status_code == 302 and not part.activa and Participacion.objects.filter(pk=part.pk).exists()
    assert part.history.count() == 2


def test_asistencia(cg, crear_actividad, crear_persona, rol, estado_part):
    actividad = crear_actividad("Confirmada", estado="confirmada")
    a, b, c = (participar(actividad, crear_persona(), rol) for _ in range(3))
    cg.post(f"/actividades/{actividad.pk}/asistencia", {f"asistencia_{a.pk}": "si", f"asistencia_{b.pk}": "no", f"asistencia_{c.pk}": ""})
    for p in (a, b, c):
        p.refresh_from_db()
    assert (a.asistencia, b.asistencia, c.asistencia) == (True, False, None)
    assert a.estado.codigo == "asistio" and b.estado.codigo == "no_asistio" and c.estado.codigo == "confirmado"


# --- finalizar (queda «realizada») ----------------------------------------------------------
def confirmada(crear_actividad, **kw):
    return crear_actividad("Por finalizar", estado="confirmada", **kw)


def test_finalizar_exige_asistencia_y_resultado(crear_actividad, gestor):
    a = confirmada(crear_actividad)
    with pytest.raises(ReglaNegocio) as e:
        servicios.finalizar(a, gestor)
    assert len(e.value.mensajes) == 2
    a.asistencia_sin_registro = True
    a.resultado = "Se realizó con 12 asistentes"
    a.save()
    servicios.finalizar(a, gestor)
    a.refresh_from_db()
    assert a.estado.codigo == "realizada" and a.finalizada_en and a.finalizada_por == gestor


def test_finalizar_con_asistencia_registrada(crear_actividad, gestor, crear_persona, rol):
    a = confirmada(crear_actividad, resultado="ok")
    p = participar(a, crear_persona(), rol)
    p.asistencia = True
    p.save()
    servicios.finalizar(a, gestor)


def test_no_existe_el_estado_cerrada():
    assert not EstadoActividad.objects.filter(codigo="cerrada").exists()


@pytest.mark.parametrize("estado", ["pendiente", "suspendida", "cancelada", "realizada"])
def test_solo_se_finaliza_una_actividad_en_curso(crear_actividad, gestor, estado):
    a = crear_actividad(estado=estado, resultado="x", asistencia_sin_registro=True)
    with pytest.raises(ReglaNegocio, match="No se puede finalizar"):
        servicios.finalizar(a, gestor)


def test_realizada_solo_se_alcanza_finalizando(actividad, gestor, lugar):
    programar(actividad, gestor, lugar)
    with pytest.raises(ReglaNegocio, match="Finalizar"):
        servicios.cambiar_estado(actividad, "realizada", gestor)


def test_finalizar_por_pantalla_y_bloqueo_posterior(cg, crear_actividad, crear_persona, rol):
    a = confirmada(crear_actividad)
    cg.post(f"/actividades/{a.pk}/resultados", {"resultado": "Fue bien", "observaciones": "", "incidencias": "", "indicadores": "", "asistencia_sin_registro": "on"})
    cg.post(f"/actividades/{a.pk}/finalizar")
    a.refresh_from_db()
    assert a.estado.codigo == "realizada"
    # Catálogo §3: después de finalizar, el resultado se puede corregir y queda registrado
    cg.post(f"/actividades/{a.pk}/resultados", {"resultado": "Fue bien (corregido)", "asistencia_sin_registro": "on"})
    a.refresh_from_db()
    assert a.resultado == "Fue bien (corregido)"
    from apps.nucleo.models import Auditoria

    assert Auditoria.objects.filter(accion="resultado_corregido").exists()
    cg.post(f"/actividades/{a.pk}/editar", {"nombre": "Otro nombre"})
    a.refresh_from_db()
    assert a.nombre == "Por finalizar"
    assert cg.post(f"/actividades/{a.pk}/participantes/nuevo", {}).status_code == 302  # rechazado con aviso
    assert "Finalizar actividad" not in cg.get(f"/actividades/{a.pk}?tab=resultados").content.decode()


def test_reabrir_requiere_permiso_especial(cg, crear_actividad, gestor):
    a = confirmada(crear_actividad, resultado="x", asistencia_sin_registro=True)
    servicios.finalizar(a, gestor)
    assert cg.post(f"/actividades/{a.pk}/reabrir", {"motivo": "error de digitación"}).status_code == 403
    from django.contrib.auth.models import Permission

    gestor.user_permissions.add(Permission.objects.get(codename="reabrir_actividad"))
    c = type(cg)()
    c.force_login(type(gestor).objects.get(pk=gestor.pk))
    assert c.post(f"/actividades/{a.pk}/reabrir", {"motivo": ""}).status_code == 302
    a.refresh_from_db()
    assert a.estado.codigo == "realizada"  # sin motivo no reabre
    c.post(f"/actividades/{a.pk}/reabrir", {"motivo": "error de digitación"})
    a.refresh_from_db()
    assert a.estado.codigo == "confirmada" and a.finalizada_en is None


# --- otros --------------------------------------------------------------------------------------
def test_territorio_de_la_actividad_un_solo_nivel(cg, actividad, comuna):
    r = cg.post(f"/actividades/{actividad.pk}/territorios/nuevo", {"comuna": comuna.pk, "region": comuna.provincia.region_id, "vigente": "on"})
    assert r.status_code == 200 and not actividad.territorios.exists()
    r = cg.post(f"/actividades/{actividad.pk}/territorios/nuevo", {"comuna": comuna.pk, "vigente": "on"})
    assert r.status_code == 302 and actividad.territorios.count() == 1
    with pytest.raises(IntegrityError), transaction.atomic():
        ActividadTerritorio.objects.create(actividad=actividad)


def test_organizaciones_y_sesiones_de_la_actividad(cg, actividad, universidad):
    r = cg.post(f"/actividades/{actividad.pk}/organizaciones/nuevo", {"organizacion": universidad.pk, "observaciones": "aporta estudiantes", "vigente": "on"})
    assert r.status_code == 302 and actividad.organizaciones.count() == 1
    cg.post(f"/actividades/{actividad.pk}/sesiones/nuevo", {"numero": 1, "nombre": "Primera", "vigente": "on"})
    cg.post(f"/actividades/{actividad.pk}/sesiones/nuevo", {"numero": 2, "nombre": "Segunda", "vigente": "on"})
    assert actividad.sesiones.count() == 2
    r = cg.post(f"/actividades/{actividad.pk}/sesiones/nuevo", {"numero": 2, "nombre": "Repetida", "vigente": "on"})
    assert actividad.sesiones.count() == 2  # número repetido no se guarda


def test_todas_las_pestanas_responden(cg, actividad):
    for tab in ["info", "participantes", "beneficiarios", "organizaciones", "sesiones", "agenda", "coordinacion", "documentos", "resultados", "origen", "historial"]:
        assert cg.get(f"/actividades/{actividad.pk}?tab={tab}").status_code == 200, tab
    # F25 E7: la pestaña Asistencia ya no existe; su dirección antigua abre Participantes
    r = cg.get(f"/actividades/{actividad.pk}?tab=asistencia")
    assert r.status_code == 200 and r.context["pestana"] == "participantes"


def test_calendario_muestra_la_programacion_vigente(cg, actividad, lugar, gestor):
    programar(actividad, gestor, lugar)
    programar(actividad, gestor, lugar, fecha=FUTURO + timedelta(days=2), motivo="otro día")
    assert cg.get("/calendario").status_code == 200
    rango = f"start={FUTURO - timedelta(days=5)}&end={FUTURO + timedelta(days=10)}"
    eventos = cg.get(f"/calendario/eventos?{rango}").json()
    assert len(eventos) == 1 and eventos[0]["start"].startswith(str(FUTURO + timedelta(days=2)))
    con_historicas = cg.get(f"/calendario/eventos?{rango}&historicas=1").json()
    assert len(con_historicas) == 2 and any("anterior" in e["title"] for e in con_historicas)
    assert cg.get(f"/calendario/eventos?{rango}&estado=cancelada").json() == []
    assert cg.get("/calendario/eventos?start=basura").status_code == 200


def test_permisos_de_actividades(cs, ca, actividad):
    assert cs.get("/actividades").status_code == 403
    assert ca.get("/actividades").status_code == 200
    assert ca.get("/actividades/nueva").status_code == 403
    assert ca.post(f"/actividades/{actividad.pk}/estado", {"estado": "cancelada", "motivo": "x"}).status_code == 403
    assert ca.get("/calendario").status_code == 200


def test_exportar_actividades(cg, ca, actividad):
    r = cg.get("/actividades/exportar")
    assert r.status_code == 200 and r["Content-Type"].endswith("spreadsheetml.sheet")
    assert ca.get("/actividades/exportar").status_code == 200
    from apps.nucleo.models import Auditoria

    assert Auditoria.objects.filter(accion="exportacion").count() == 2


# --- búsqueda asistida (F16) -----------------------------------------------------------------------
def test_matching_personas_con_razones(cg, actividad, lugar, gestor, crear_persona, rol):
    from apps.actividades import matching
    from apps.personas.models import DisponibilidadPersona

    libre, ocupada, otra_hora = crear_persona("Libre"), crear_persona("Ocupada"), crear_persona("OtraHora")
    programar(actividad, gestor, lugar, ini=time(18), fin=time(20))
    DisponibilidadPersona.objects.create(persona=libre, dia=FUTURO.weekday(), hora_inicio=time(17), hora_fin=time(21))
    DisponibilidadPersona.objects.create(persona=otra_hora, dia=FUTURO.weekday(), hora_inicio=time(8), hora_fin=time(10))
    otra = actividad.__class__.objects.create(nombre="Otra", estado=EstadoActividad.objects.get(codigo="planificada"))
    programar(otra, gestor, None, ini=time(19), fin=time(20))
    participar(otra, ocupada, rol)
    res = {c.objeto.nombres: c for c in matching.buscar_personas(actividad)}
    assert res["Libre"].estado == "ok" and "Disponible" in res["Libre"].razones[0]
    assert res["Ocupada"].estado == "conflicto" and "Conflicto de horario" in res["Ocupada"].razones[0]
    assert res["OtraHora"].estado == "conflicto"
    orden = [c.objeto.nombres for c in matching.buscar_personas(actividad)]
    assert orden[0] == "Libre"
    assert "Ocupada" not in [c.objeto.nombres for c in matching.buscar_personas(actividad, solo_disponibles=True)]


def test_matching_no_asigna_solo_y_excluye_a_los_que_ya_participan(cg, actividad, crear_persona, rol):
    from apps.actividades import matching

    ana = crear_persona("Ana")
    participar(actividad, ana, rol)
    assert ana not in [c.objeto for c in matching.buscar_personas(actividad)]
    cg.get(f"/actividades/{actividad.pk}/candidatos?tipo=personas&buscar=1")
    assert actividad.participaciones.count() == 1  # buscar no agrega a nadie


def test_matching_lugares_por_capacidad_y_ocupacion(actividad, lugar, gestor, crear_persona, rol):
    from apps.actividades import matching
    from apps.lugares.models import Lugar

    chico = Lugar.objects.create(nombre="Chico", tipo=lugar.tipo, direccion=lugar.direccion, capacidad=5)
    programar(actividad, gestor, None)
    for _ in range(10):
        participar(actividad, crear_persona(), rol)
    res = {c.objeto.nombre: c for c in matching.buscar_lugares(actividad)}
    assert res["Sala Ficticia"].estado == "ok" and res["Chico"].estado == "conflicto" and "Capacidad 5 para 10" in res["Chico"].razones[0]


def test_matching_por_pantalla(cg, actividad, crear_persona, universidad):
    from apps.personas.models import PersonaFormacion

    p = crear_persona("Marta", profesion="Profesora de lenguaje")
    PersonaFormacion.objects.create(persona=p, organizacion=universidad)
    html = cg.get(f"/actividades/{actividad.pk}/candidatos?tipo=personas&buscar=1&area=lenguaje").content.decode()
    assert "Marta" in html and "Agregar a la actividad" in html  # F25: el botón agrega como inscrito, no invita
    assert "Marta" not in cg.get(f"/actividades/{actividad.pk}/candidatos?tipo=personas&buscar=1&area=astronomía").content.decode()
    assert cg.get(f"/actividades/{actividad.pk}/candidatos?tipo=lugares&buscar=1").status_code == 200
    assert cg.get(f"/actividades/{actividad.pk}/candidatos?tipo=organizaciones&buscar=1").status_code == 200


def test_crear_lugar_desde_la_agenda(cg, actividad, comuna, lugar):
    from apps.lugares.models import Lugar
    from apps.nucleo.models import TipoLugar

    assert "+ Crear lugar sin salir de la actividad" in cg.get(f"/actividades/{actividad.pk}/programar").content.decode()
    datos = {"nuevo_lugar_nombre": "Biblioteca Ficticia", "nuevo_lugar_tipo": TipoLugar.objects.get(codigo="sala").pk, "nuevo_lugar_comuna": comuna.pk, "nuevo_lugar_capacidad": "40"}
    r = cg.post("/lugares/crear-rapido", datos)
    nuevo = Lugar.objects.get(nombre="Biblioteca Ficticia")
    assert f'value="{nuevo.pk}" selected' in r.content.decode() and nuevo.capacidad == 40
    r = cg.post("/lugares/crear-rapido", {**datos, "nuevo_lugar_nombre": "biblioteca ficticia"})
    assert Lugar.objects.filter(nombre__iexact="biblioteca ficticia").count() == 1 and "Ya existía" in r.content.decode()
    assert "indica nombre, tipo y comuna" in cg.post("/lugares/crear-rapido", {"nuevo_lugar_nombre": "X"}).content.decode()
    assert "entero positivo" in cg.post("/lugares/crear-rapido", {**datos, "nuevo_lugar_nombre": "Otra", "nuevo_lugar_capacidad": "-3"}).content.decode()


def test_crear_lugar_rapido_requiere_permiso(ca, comuna):
    assert ca.post("/lugares/crear-rapido", {"nuevo_lugar_nombre": "X"}).status_code == 403



def test_cargar_listado_desde_la_actividad(cg, actividad):
    assert f"/importaciones/nueva?actividad={actividad.pk}" in cg.get(f"/actividades/{actividad.pk}?tab=participantes").content.decode()
    html = cg.get(f"/importaciones/nueva?actividad={actividad.pk}").content.decode()
    assert 'value="listado_actividad" selected' in html and f'value="{actividad.pk}" selected' in html


def test_agregar_persona_que_llego(cg, crear_actividad, crear_persona, rol, estado_part):
    actividad = crear_actividad("En curso", estado="confirmada")
    assert "+ Agregar persona que llegó" in cg.get(f"/actividades/{actividad.pk}?tab=participantes").content.decode()  # F25 E7
    p = crear_persona("Llegó")
    r = cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", {"persona": p.pk, "rol": rol("participante").pk, "estado": estado_part("confirmado").pk, "llego": "1"})
    part = actividad.participaciones.get(persona=p)
    assert r.status_code == 302 and "tab=participantes" in r["Location"] and part.asistencia is True and part.estado.codigo == "asistio"
    cg.post(f"/actividades/{actividad.pk}/participantes/rapido", {"nombres": "Nueva", "apellido_paterno": "Llegada", "rol": rol("participante").pk, "llego": "1"})
    nueva = actividad.participaciones.get(persona__nombres="Nueva")
    assert nueva.asistencia is True


def test_filtros_por_responsable_e_institucion(cg, crear_actividad, crear_persona, universidad):
    from apps.actividades.models import ActividadOrganizacion

    resp = crear_persona("Responsable")
    a = crear_actividad("Con responsable", responsable=resp)
    b = crear_actividad("Con institución")
    ActividadOrganizacion.objects.create(actividad=b, organizacion=universidad)
    html = cg.get(f"/actividades?responsable={resp.pk}").content.decode()
    assert "Con responsable" in html and "Con institución" not in html
    html = cg.get(f"/actividades?institucion={universidad.pk}").content.decode()
    assert "Con institución" in html and "Con responsable" not in html


# --- Requerimientos por módulo (AG, VA) ---------------------------------------------------------------------
def test_programar_con_duracion(cg, actividad, lugar):
    r = cg.post(f"/actividades/{actividad.pk}/programar", {"fecha": str(FUTURO), "hora_inicio": "18:00", "duracion": "90", "lugar": lugar.pk})
    ag = actividad.agenda_vigente
    assert r.status_code == 302 and ag.hora_fin == time(19, 30) and ag.duracion_minutos == 90
    r = cg.post(f"/actividades/{actividad.pk}/programar", {"fecha": str(FUTURO), "hora_inicio": "23:30", "duracion": "60", "lugar": lugar.pk, "motivo": "x"})
    assert r.status_code == 400  # terminaría al día siguiente
    r = cg.post(f"/actividades/{actividad.pk}/programar", {"fecha": str(FUTURO), "hora_inicio": "18:00", "hora_fin": "19:00", "duracion": "90", "lugar": lugar.pk, "motivo": "x"})
    assert r.status_code == 400  # duración y término no coinciden


def test_crear_serie_semanal(cg, actividad, lugar):
    r = cg.post(f"/actividades/{actividad.pk}/serie", {"primera_fecha": str(FUTURO), "frecuencia": "7", "repeticiones": "4", "hora_inicio": "18:00", "hora_fin": "19:00", "lugar": lugar.pk})
    hijas = list(actividad.hijas.order_by("agendas__fecha"))
    assert r.status_code == 302 and len(hijas) == 4
    fechas = [h.agenda_vigente.fecha for h in hijas]
    assert fechas == [FUTURO + timedelta(days=7 * i) for i in range(4)]
    assert all(h.estado.codigo == "planificada" and h.responsable_id == actividad.responsable_id for h in hijas)
    from apps.nucleo.models import Auditoria

    assert Auditoria.objects.filter(accion="serie_creada").exists()


def test_serie_valida_y_no_desde_una_hija(cg, actividad, crear_actividad, lugar):
    assert cg.post(f"/actividades/{actividad.pk}/serie", {"primera_fecha": str(FUTURO), "frecuencia": "7", "repeticiones": "99", "hora_inicio": "18:00"}).status_code == 400
    hija = crear_actividad("Hija", actividad_padre=actividad)
    r = cg.post(f"/actividades/{hija.pk}/serie", {"primera_fecha": str(FUTURO), "frecuencia": "7", "repeticiones": "2", "hora_inicio": "18:00"})
    assert r.status_code == 400 and not hija.hijas.exists()


def test_calendario_filtra_por_zona_responsable_y_organizacion(cg, crear_actividad, crear_persona, lugar, gestor, universidad):
    from apps.actividades.models import ActividadOrganizacion

    resp = crear_persona("Resp")
    a = crear_actividad("Con todo", responsable=resp)
    b = crear_actividad("Sin nada")
    programar(a, gestor, lugar)
    programar(b, gestor, None)
    ActividadOrganizacion.objects.create(actividad=a, organizacion=universidad)
    rango = f"start={FUTURO - timedelta(days=2)}&end={FUTURO + timedelta(days=2)}"
    for filtro in (f"zona={lugar.direccion.comuna_id}", f"responsable={resp.pk}", f"organizacion={universidad.pk}"):
        titulos = [e["title"] for e in cg.get(f"/calendario/eventos?{rango}&{filtro}").json()]
        assert titulos == ["Con todo"], filtro
    html = cg.get("/calendario").content.decode()
    assert 'id="f-zona"' in html and 'id="f-responsable"' in html and 'id="f-organizacion"' in html


def test_confirmar_muestra_lo_compatible(cg, actividad, lugar, gestor, crear_persona, rol):
    actividad.responsable = crear_persona("Resp")
    actividad.save()
    programar(actividad, gestor, lugar)
    participar(actividad, crear_persona(), rol)
    html = cg.get(f"/actividades/{actividad.pk}/confirmar").content.decode()
    assert "✓" in html and "Capacidad compatible: 1 de 20" in html and "disponible en ese horario" in html
    assert "✓ Sin problemas detectados" in html
    codigos = {p.codigo for p in revisar(actividad) if p.nivel == "ok"}
    assert {"responsable_ok", "agenda_ok", "lugar_ok", "capacidad_ok", "horarios_ok"} <= codigos

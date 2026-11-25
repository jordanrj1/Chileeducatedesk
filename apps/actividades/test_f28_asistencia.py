"""Pruebas de F28 A (specs/f28/spec.md): asistencia por jornada. Una prueba por escenario AS-E1…AS-E17, más las
consultas fijas de la matriz y del panel del proyecto, el Excel, las jornadas desde la agenda y «+ Nueva jornada».
Todos los datos son ficticios."""
import importlib
import uuid
from datetime import date, time, timedelta
from io import BytesIO

import pytest
from django.apps import apps as registro
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.actividades import asistencia, servicios
from apps.actividades.models import CambioLista, Participacion, SesionActividad, SesionAsistencia
from apps.actividades.reglas import ReglaNegocio
from apps.nucleo.models import Auditoria

pytestmark = pytest.mark.django_db
HOY = date.today()
D1, D2, D3 = HOY - timedelta(days=2), HOY - timedelta(days=1), HOY


@pytest.fixture
def proyecto(db):
    from apps.proyectos.models import Proyecto

    return Proyecto.objects.create(nombre="Huertos Ficticios")


@pytest.fixture
def taller(crear_actividad, proyecto, gestor):
    """Taller de 3 días (antes de ayer, ayer y hoy): la fecha programada es el día 1; los días 2 y 3, «+ Nueva jornada»."""
    t = crear_actividad("Taller de compostaje", estado="confirmada", proyecto=proyecto, resultado="Se realizó")
    servicios.programar(t, gestor, D1, time(10), time(12), None, None)
    asistencia.nueva_jornada(t, gestor, D2, time(10), time(12))
    asistencia.nueva_jornada(t, gestor, D3, time(10), time(12))
    return t


def _dias(t):
    js = [j for j in asistencia.jornadas(t) if j.pk]
    assert [j.fecha for j in js] == [D1, D2, D3]
    return js


def _p(t, persona, rol, estado, desde=D1, **kw):
    return Participacion.objects.create(actividad=t, persona=persona, rol=rol, estado=estado, inscrito_en=desde, **kw)


def _lista(t, j):
    """Nombres de quienes aparecen en la lista de la jornada."""
    grupos = asistencia.por_persona(asistencia.participaciones(t))
    return [f.persona.nombres for f in asistencia.filas(j, grupos, asistencia.marcas(t))]


def _pasar(cg, t, j, marcas, accion="guardar", obs=None, version=None, envio=None):
    """Envía «Pasar lista» como el formulario: en_lista con todas las personas de la lista y la marca de las indicadas."""
    j = SesionActividad.objects.get(pk=j.pk) if j.pk else j
    grupos = asistencia.por_persona(asistencia.participaciones(t))
    filas = asistencia.filas(j, grupos, asistencia.marcas(t))
    datos = {"en_lista": [f.persona.pk for f in filas], "accion": accion,
             "_version": j.version_lista if version is None else version, "_envio": envio or uuid.uuid4().hex}
    for f in filas:  # como el formulario: cada fila envía la marca que tiene elegida
        datos[f"marca_{f.persona.pk}"] = f.codigo
    for persona, marca in marcas.items():
        datos[f"marca_{persona.pk}"] = marca
    for persona, texto in (obs or {}).items():
        datos[f"obs_{persona.pk}"] = texto
    return cg.post(f"/actividades/{t.pk}/jornadas/{j.pk or 'programada'}/lista", datos)


def _marca(j, persona):
    m = SesionAsistencia.objects.filter(sesion=j, participacion__persona=persona).exclude(marca="").first()
    return m.marca if m else ""


def _resumen(t, persona):
    return next(f["resumen"] for f in asistencia.matriz(t)["filas"] if f["persona"] == persona)


def _mensajes(r):
    return [str(m) for m in r.wsgi_request._messages]


# --- AS-E1 … AS-E17 ----------------------------------------------------------------------------------
def test_AS_E1_falta_el_dia_1_y_sigue_en_las_listas(cg, taller, crear_persona, rol, estado_part):
    ana = crear_persona("Ana")
    p = _p(taller, ana, rol("participante"), estado_part("confirmado"))
    d1, d2, d3 = _dias(taller)
    assert _pasar(cg, taller, d1, {ana: "ausente"}).status_code == 302
    p.refresh_from_db()
    assert p.estado.codigo == "confirmado" and p.asistencia is False  # la marca no cambia la inscripción
    assert "Ana" in _lista(taller, d2) and "Ana" in _lista(taller, d3)  # nadie desaparece por faltar
    _pasar(cg, taller, d2, {ana: "presente"})
    _pasar(cg, taller, d3, {ana: "presente"})
    r = _resumen(taller, ana)
    assert (r["presentes"], r["con_marca"], r["porcentaje"]) == (2, 3, 67)
    p.refresh_from_db()
    assert p.asistencia is True and p.estado.codigo == "confirmado"


def test_AS_E2_inscrito_el_dia_2_no_aparece_el_dia_1(cg, taller, crear_persona, rol, estado_part):
    beto = crear_persona("Beto")
    _p(taller, beto, rol("participante"), estado_part("confirmado"), desde=D2)
    d1, d2, d3 = _dias(taller)
    assert "Beto" not in _lista(taller, d1) and "Beto" in _lista(taller, d2) and "Beto" in _lista(taller, d3)
    r = _pasar(cg, taller, d1, {beto: "presente"})  # aunque se envíe, no se marca a quien no estaba inscrito ese día
    assert r.status_code == 302 and _marca(d1, beto) == ""
    _pasar(cg, taller, d2, {beto: "presente"})
    _pasar(cg, taller, d3, {beto: "presente"})
    res = _resumen(taller, beto)
    assert (res["presentes"], res["con_marca"], res["porcentaje"]) == (2, 2, 100)
    celdas = next(f["celdas"] for f in asistencia.matriz(taller)["filas"] if f["persona"] == beto)
    assert [c["en_lista"] for c in celdas] == [False, True, True]


def test_AS_E3_llega_alguien_sin_inscribir(cg, taller, crear_persona, rol, estado_part):
    d3 = _dias(taller)[2]
    html = cg.get(f"{taller.get_absolute_url()}?tab=participantes&jornada={d3.pk}").content.decode()
    assert "Agregar persona que llegó" in html and f"llego=1&amp;jornada={d3.pk}" in html
    form = cg.get(f"/actividades/{taller.pk}/participantes/nuevo?llego=1&jornada={d3.pk}")
    assert form.context["titulo"] == "Agregar persona que llegó" and f'name="jornada" value="{d3.pk}"' in form.content.decode()
    nueva = crear_persona("Llegada")
    r = cg.post(f"/actividades/{taller.pk}/participantes/nuevo", {"persona": nueva.pk, "rol": rol("participante").pk,
                                                                   "estado": estado_part("confirmado").pk, "llego": "1", "jornada": d3.pk})
    assert r.status_code == 302 and r["Location"].endswith(f"jornada={d3.pk}#pasar-lista")
    p = Participacion.objects.get(actividad=taller, persona=nueva)
    assert p.estado.codigo == "confirmado" and _marca(d3, nueva) == "presente" and p.asistencia is True
    # Si ya estaba inscrita con ese rol (p. ej. se digitó tarde), no es un error: queda «Presente» en esa jornada
    d1 = _dias(taller)[0]
    r = cg.post(f"/actividades/{taller.pk}/participantes/nuevo", {"persona": nueva.pk, "rol": rol("participante").pk,
                                                                   "estado": estado_part("confirmado").pk, "llego": "1", "jornada": d1.pk})
    p.refresh_from_db()
    assert r.status_code == 302 and _marca(d1, nueva) == "presente" and p.inscrito_en == D1
    assert Participacion.objects.filter(actividad=taller, persona=nueva).count() == 1


def test_AS_E4_reabrir_con_motivo_corregir_y_cerrar_queda_en_el_historial(cg, gestor, crear_actividad, proyecto, crear_persona, rol, estado_part):
    hace_una_semana = HOY - timedelta(days=7)
    t = crear_actividad("Charla pasada", estado="confirmada", proyecto=proyecto)
    servicios.programar(t, gestor, hace_una_semana, time(10), time(11), None, None)
    ana = crear_persona("Ana")
    _p(t, ana, rol("participante"), estado_part("confirmado"), desde=hace_una_semana)
    j = asistencia.jornadas(t)[0]
    r = _pasar(cg, t, j, {ana: "ausente"}, accion="cerrar")
    j = SesionActividad.objects.get(actividad=t)
    assert r.status_code == 302 and j.lista_cerrada and j.cerrada_por == gestor and j.cerrada_en
    assert cg.post(f"/actividades/{t.pk}/jornadas/{j.pk}/reabrir", {"motivo": "", "_envio": uuid.uuid4().hex}).status_code == 302
    j.refresh_from_db()
    assert j.lista_cerrada  # sin motivo no se reabre
    cg.post(f"/actividades/{t.pk}/jornadas/{j.pk}/reabrir", {"motivo": "Vino con certificado", "_envio": uuid.uuid4().hex})
    j.refresh_from_db()
    assert j.lista_abierta and j.cerrada_por is None
    _pasar(cg, t, j, {ana: "justificado"}, obs={ana: "Certificado médico"}, accion="cerrar")
    j.refresh_from_db()
    assert j.lista_cerrada
    marca = SesionAsistencia.objects.get(sesion=j)
    antes_despues = list(marca.history.order_by("history_id").values_list("marca", "observacion", "history_user_id"))
    assert antes_despues[0][:2] == ("ausente", "") and antes_despues[-1] == ("justificado", "Certificado médico", gestor.pk)
    cambios = list(CambioLista.objects.filter(sesion=j).order_by("fecha", "pk").values_list("accion", "motivo", "usuario_id"))
    assert cambios == [("cerrada", "", gestor.pk), ("reabierta", "Vino con certificado", gestor.pk), ("cerrada", "", gestor.pk)]
    html = cg.get(f"{t.get_absolute_url()}?tab=participantes&jornada={j.pk}").content.decode()
    assert "Vino con certificado" in html and "Solo lectura" in html
    assert Auditoria.objects.filter(accion="lista_reabierta").exists()


def test_AS_E5_dos_jornadas_el_mismo_dia_tienen_listas_independientes(cg, gestor, crear_actividad, proyecto, crear_persona, rol, estado_part):
    t = crear_actividad("Jornada doble", estado="confirmada", proyecto=proyecto)
    servicios.programar(t, gestor, HOY, time(9), time(12), None, None)
    ana = crear_persona("Ana")
    _p(t, ana, rol("participante"), estado_part("confirmado"), desde=HOY)
    tarde = asistencia.nueva_jornada(t, gestor, HOY, time(15), time(17), nombre="Tarde")
    manana, tarde2 = [j for j in asistencia.jornadas(t)]
    assert manana.pk and tarde2.pk == tarde.pk and manana.hora_inicio == time(9)  # la de la mañana quedó guardada primero
    _pasar(cg, t, manana, {ana: "presente"})
    assert _marca(manana, ana) == "presente" and _marca(tarde, ana) == ""
    _pasar(cg, t, tarde, {ana: "ausente"}, accion="cerrar")
    manana.refresh_from_db()
    tarde.refresh_from_db()
    assert manana.lista_abierta and tarde.lista_cerrada and _marca(manana, ana) == "presente"


def test_AS_E6_jornada_suspendida_por_lluvia(cg, taller, gestor, crear_persona, rol, estado_part):
    ana = crear_persona("Ana")
    _p(taller, ana, rol("participante"), estado_part("confirmado"))
    d1, d2, d3 = _dias(taller)
    _pasar(cg, taller, d1, {ana: "presente"}, accion="cerrar")
    r = cg.post(f"/actividades/{taller.pk}/jornadas/{d2.pk}/suspender", {"motivo": "Lluvia", "_envio": uuid.uuid4().hex})
    d2.refresh_from_db()
    assert r.status_code == 302 and d2.suspendida and d2.motivo_suspension == "Lluvia"
    _pasar(cg, taller, d2, {ana: "presente"})  # sin lista: no se marca
    assert _marca(d2, ana) == ""
    _pasar(cg, taller, d3, {ana: "ausente"}, accion="cerrar")
    res = _resumen(taller, ana)
    assert (res["presentes"], res["con_marca"], res["porcentaje"]) == (1, 2, 50)  # la suspendida no cuenta
    servicios.finalizar(taller, gestor)
    taller.refresh_from_db()
    assert taller.estado.codigo == "realizada"


def test_AS_E7_se_retira_el_dia_2(cg, taller, crear_persona, rol, estado_part):
    carla = crear_persona("Carla")
    p = _p(taller, carla, rol("participante"), estado_part("confirmado"))
    d1, d2, d3 = _dias(taller)
    _pasar(cg, taller, d1, {carla: "presente"})
    r = cg.post(f"/actividades/{taller.pk}/participantes/{p.pk}/retirar", {"fecha": D2.isoformat(), "motivo": "Se cambió de comuna"})
    p.refresh_from_db()
    assert r.status_code == 302 and p.estado.codigo == "retirado" and (p.retirado_en, p.motivo_retiro) == (D2, "Se cambió de comuna")
    assert not p.activa and _marca(d1, carla) == "presente"  # conserva el día 1
    assert "Carla" in _lista(taller, d2) and "Carla" not in _lista(taller, d3)
    assert cg.post(f"/actividades/{taller.pk}/participantes/{p.pk}/retirar", {"fecha": D2.isoformat(), "motivo": ""}).status_code == 400


def test_AS_E8_reincorporar_a_quien_se_quito_por_error(cg, taller, crear_persona, rol, estado_part):
    daniel = crear_persona("Daniel")
    p = _p(taller, daniel, rol("participante"), estado_part("confirmado"))
    d3 = _dias(taller)[2]
    asistencia.retirar(p, None, "Error de digitación", D1)
    assert "Daniel" not in _lista(taller, d3)
    html = cg.get(f"{taller.get_absolute_url()}?tab=beneficiarios").content.decode()
    assert f"/participantes/{p.pk}/reincorporar" in html
    r = cg.post(f"/actividades/{taller.pk}/participantes/{p.pk}/reincorporar", {"_envio": uuid.uuid4().hex})
    p.refresh_from_db()
    assert r.status_code == 302 and p.estado.codigo == "confirmado" and p.retirado_en is None and p.activa
    assert "Daniel" in _lista(taller, d3)


def test_AS_E9_justificado_con_certificado_no_baja_el_porcentaje(cg, taller, crear_persona, rol, estado_part):
    ana = crear_persona("Ana")
    _p(taller, ana, rol("participante"), estado_part("confirmado"))
    d1, d2, d3 = _dias(taller)
    _pasar(cg, taller, d1, {ana: "presente"})
    _pasar(cg, taller, d2, {ana: "justificado"}, obs={ana: "Certificado médico"})
    _pasar(cg, taller, d3, {ana: "presente"})
    assert SesionAsistencia.objects.get(sesion=d2).observacion == "Certificado médico"
    res = _resumen(taller, ana)
    assert (res["presentes"], res["con_marca"], res["justificados"], res["porcentaje"]) == (2, 2, 1, 100)


def test_AS_E10_atrasado_y_se_retiro_antes_cuentan_y_se_ven_en_la_matriz(cg, taller, crear_persona, rol, estado_part):
    ana, beto = crear_persona("Ana"), crear_persona("Beto")
    for x in (ana, beto):
        _p(taller, x, rol("participante"), estado_part("confirmado"))
    d1 = _dias(taller)[0]
    _pasar(cg, taller, d1, {ana: "atrasado", beto: "retiro_anticipado"})
    assert _resumen(taller, ana)["porcentaje"] == 100 and _resumen(taller, beto)["porcentaje"] == 100
    html = cg.get(f"{taller.get_absolute_url()}?tab=participantes").content.decode()
    matriz = html.split('id="matriz"')[1]
    assert 'fche-marca-celda--atrasado" title="Atrasado"' in matriz and 'fche-marca-celda--retiro_anticipado" title="Se retiró antes"' in matriz


def test_AS_E11_cerrar_con_personas_sin_marcar(cg, taller, gestor, crear_persona, rol, estado_part):
    ana, beto = crear_persona("Ana"), crear_persona("Beto")
    for x in (ana, beto):
        _p(taller, x, rol("participante"), estado_part("confirmado"))
    d1 = _dias(taller)[0]
    r = _pasar(cg, taller, d1, {ana: "presente"}, accion="cerrar")
    d1.refresh_from_db()
    assert d1.lista_abierta and _marca(d1, ana) == "presente"  # lo marcado se guarda; la lista no se cierra
    assert any("falta marcar a 1 persona" in m for m in _mensajes(r))
    with pytest.raises(ReglaNegocio, match="Marcar el resto como ausente"):
        asistencia.cerrar_lista(taller, d1, gestor)
    _pasar(cg, taller, d1, {}, accion="resto")
    assert _marca(d1, beto) == "ausente" and _marca(d1, ana) == "presente"
    _pasar(cg, taller, d1, {}, accion="cerrar")
    d1.refresh_from_db()
    assert d1.lista_cerrada


def test_AS_E12_feria_con_200_personas_sin_nombre(cg, gestor, crear_actividad, proyecto):
    t = crear_actividad("Feria ficticia", estado="confirmada", proyecto=proyecto, resultado="Mucha gente")
    servicios.programar(t, gestor, HOY, time(10), time(18), None, None)
    r = cg.post(f"/actividades/{t.pk}/jornadas/programada/conteo", {"_envio": uuid.uuid4().hex})
    j = SesionActividad.objects.get(actividad=t)
    assert r.status_code == 302 and r["Location"] == f"/actividades/{t.pk}/sesiones/{j.pk}/editar"
    with pytest.raises(ReglaNegocio, match="falta pasar lista"):  # la jornada guardada sin conteo ni lista no se resuelve sola
        servicios.finalizar(t, gestor)
    j.asistentes_sin_registro, j.conteo_mujeres, j.conteo_hombres = 200, 120, 80
    j.save()
    servicios.finalizar(t, gestor)
    t.refresh_from_db()
    assert t.estado.codigo == "realizada"


def test_AS_E13_finalizar_con_un_dia_pasado_sin_lista(cg, taller, gestor, crear_persona, rol, estado_part):
    ana = crear_persona("Ana")
    _p(taller, ana, rol("participante"), estado_part("confirmado"))
    d1, d2, d3 = _dias(taller)
    _pasar(cg, taller, d1, {ana: "presente"}, accion="cerrar")
    _pasar(cg, taller, d3, {ana: "presente"})  # abierta, con todos marcados: Finalizar la cierra
    with pytest.raises(ReglaNegocio) as e:
        servicios.finalizar(taller, gestor)
    assert e.value.mensajes == [f"Jornada 2 ({D2:%d-%m-%Y}): falta pasar lista. Pásala y ciérrala, suspende la jornada o registra un conteo sin nombres."]
    taller.refresh_from_db()
    assert taller.estado.codigo == "confirmada"
    html = cg.get(f"{taller.get_absolute_url()}?tab=resultados").content.decode()
    assert f"Jornada 2 ({D2:%d-%m-%Y})" in html and "se cerrará al finalizar" in html
    _pasar(cg, taller, d2, {ana: "ausente"})
    servicios.finalizar(taller, gestor)
    assert all(j.lista_cerrada for j in SesionActividad.objects.filter(actividad=taller))
    assert CambioLista.objects.filter(sesion=d3, accion="cerrada", motivo="Al finalizar la actividad").exists()


def test_AS_E14_persona_con_dos_roles_una_fila_y_una_marca(cg, taller, crear_persona, rol, estado_part):
    eva = crear_persona("Eva")
    _p(taller, eva, rol("tallerista"), estado_part("confirmado"))
    _p(taller, eva, rol("beneficiario"), estado_part("confirmado"))
    d1 = _dias(taller)[0]
    assert _lista(taller, d1) == ["Eva"]
    html = cg.get(f"{taller.get_absolute_url()}?tab=participantes&jornada={d1.pk}").content.decode()
    assert html.count(f'name="marca_{eva.pk}" id="m-{eva.pk}-presente"') == 1
    _pasar(cg, taller, d1, {eva: "presente"})
    _pasar(cg, taller, d1, {eva: "atrasado"})
    assert SesionAsistencia.objects.filter(sesion=d1, participacion__persona=eva).exclude(marca="").count() == 1
    filas = asistencia.matriz(taller)["filas"]
    assert len(filas) == 1 and "Tallerista" in filas[0]["roles"] and "Beneficiario" in filas[0]["roles"]
    assert set(Participacion.objects.filter(persona=eva).values_list("asistencia", flat=True)) == {True}


def test_AS_E15_doble_clic_y_dos_pestanas(cg, taller, crear_persona, rol, estado_part):
    ana = crear_persona("Ana")
    _p(taller, ana, rol("participante"), estado_part("confirmado"))
    d1 = _dias(taller)[0]
    marca_envio = uuid.uuid4().hex
    r1 = _pasar(cg, taller, d1, {ana: "presente"}, version=0, envio=marca_envio)
    r2 = _pasar(cg, taller, d1, {ana: "presente"}, version=0, envio=marca_envio)  # doble clic: la misma marca de envío
    d1.refresh_from_db()
    assert r1.status_code == r2.status_code == 302 and d1.version_lista == 1
    assert "Ya estaba guardado." in _mensajes(r2)
    assert SesionAsistencia.objects.get(sesion=d1).history.count() == 1
    r3 = _pasar(cg, taller, d1, {ana: "ausente"}, version=0)  # otra pestaña, abierta antes del primer guardado
    d1.refresh_from_db()
    assert _marca(d1, ana) == "presente" and d1.version_lista == 1
    assert asistencia.MENSAJE_VERSION in _mensajes(r3)


def test_AS_E16_lista_cerrada_es_de_solo_lectura(cg, cs, taller, crear_persona, rol, estado_part):
    ana = crear_persona("Ana")
    p = _p(taller, ana, rol("participante"), estado_part("confirmado"))
    d1 = _dias(taller)[0]
    _pasar(cg, taller, d1, {ana: "presente"}, accion="cerrar")
    html = cg.get(f"{taller.get_absolute_url()}?tab=participantes&jornada={d1.pk}").content.decode()
    lista = html.split('id="pasar-lista"')[1].split("</section>", 1)[0]
    assert f'name="marca_{ana.pk}"' not in lista and "Solo lectura" in lista and "Reabrir" in lista
    r = _pasar(cg, taller, d1, {ana: "ausente"})
    assert _marca(d1, ana) == "presente" and any("está cerrada" in m for m in _mensajes(r))
    cg.post(f"/actividades/{taller.pk}/sesiones/{d1.pk}/asistencia", {f"asistio_{p.pk}": "no"})  # la ruta de antes, igual
    assert _marca(d1, ana) == "presente"
    assert cs.post(f"/actividades/{taller.pk}/jornadas/{d1.pk}/lista", {"en_lista": [ana.pk], f"marca_{ana.pk}": "ausente"}).status_code == 403


def test_AS_E17_quienes_figuran_no_asistio_vuelven_a_su_tarea(gestor, crear_actividad, proyecto, crear_persona, rol, estado_part):
    t = crear_actividad("Tarea de antes", estado="confirmada", proyecto=proyecto)
    servicios.programar(t, gestor, D1, time(10), time(12), None, None)
    vino, falto = crear_persona("Vino"), crear_persona("Faltó")
    pv = Participacion.objects.create(actividad=t, persona=vino, rol=rol("participante"), estado=estado_part("asistio"), asistencia=True)
    pf = Participacion.objects.create(actividad=t, persona=falto, rol=rol("participante"), estado=estado_part("no_asistio"), asistencia=False)
    Participacion.objects.filter(pk__in=[pv.pk, pf.pk]).update(inscrito_en=None)  # como antes de la migración
    migracion = importlib.import_module("apps.actividades.migrations.0012_f28_datos_asistencia")
    migracion.migrar(registro, None)
    for p in (pv, pf):
        p.refresh_from_db()
    assert pv.estado.codigo == pf.estado.codigo == "confirmado" and pf.activa and pf.inscrito_en == D1
    j = SesionActividad.objects.get(actividad=t)
    assert (j.numero, j.fecha, j.hora_inicio, j.estado_lista) == (1, D1, time(10), "cerrada")
    assert (_marca(j, vino), _marca(j, falto)) == ("presente", "ausente")
    assert CambioLista.objects.filter(sesion=j, accion="migrada").exists()
    assert Auditoria.objects.filter(accion="asistencia_migrada", objeto=t.nombre).exists()
    assert pf.history.filter(history_change_reason="F28: asistencia por jornada", estado__codigo="confirmado").exists()
    nueva = asistencia.nueva_jornada(t, gestor, D2)
    assert "Faltó" in _lista(t, nueva)  # vuelve a aparecer en las jornadas siguientes
    migracion.migrar(registro, None)  # dos veces no duplica
    assert SesionActividad.objects.filter(actividad=t).count() == 2


# --- Jornadas, panel, Excel y consultas fijas -----------------------------------------------------
def test_la_fecha_programada_es_la_jornada_y_reprogramar_no_borra_listas(cg, gestor, crear_actividad, proyecto, crear_persona, rol, estado_part):
    t = crear_actividad("Visita", estado="confirmada", proyecto=proyecto)
    servicios.programar(t, gestor, D1, time(10), time(12), None, None)
    js = asistencia.jornadas(t)
    assert len(js) == 1 and js[0].pk is None and js[0].fecha == D1 and not SesionActividad.objects.filter(actividad=t).exists()
    servicios.programar(t, gestor, D2, time(10), time(12), None, None, "cambio de día")
    assert [j.fecha for j in asistencia.jornadas(t)] == [D2]  # sin lista, la jornada sigue a la fecha nueva
    ana = crear_persona("Ana")
    _p(t, ana, rol("participante"), estado_part("confirmado"))
    _pasar(cg, t, asistencia.jornadas(t)[0], {ana: "presente"})
    r = cg.post(f"/actividades/{t.pk}/programar", {"fecha": HOY.isoformat(), "hora_inicio": "10:00", "hora_fin": "12:00", "motivo": "otra vez"}, follow=True)
    assert any("ya tiene lista: se conserva" in str(m) for m in r.context["messages"])
    assert [j.fecha for j in asistencia.jornadas(t)] == [D2, HOY] and _marca(SesionActividad.objects.get(actividad=t, fecha=D2), ana) == "presente"


def test_nueva_jornada_por_pantalla(cg, taller):
    r = cg.get(f"/actividades/{taller.pk}/jornadas/nueva")
    assert r.status_code == 200 and "Nueva jornada" in r.content.decode()
    r = cg.post(f"/actividades/{taller.pk}/jornadas/nueva", {"fecha": (HOY + timedelta(days=7)).isoformat(), "hora_inicio": "15:00", "hora_fin": "14:00"})
    assert r.status_code == 400
    r = cg.post(f"/actividades/{taller.pk}/jornadas/nueva", {"fecha": (HOY + timedelta(days=7)).isoformat(), "hora_inicio": "15:00", "_envio": uuid.uuid4().hex})
    j = SesionActividad.objects.get(actividad=taller, numero=4)
    assert r.status_code == 302 and r["Location"].endswith(f"jornada={j.pk}#pasar-lista")
    html = cg.get(r["Location"]).content.decode()
    assert "La lista se pasa desde el día de la jornada" in html  # futura: aún sin lista


def test_excel_de_la_matriz_con_permiso(cg, cs, taller, crear_persona, rol, estado_part):
    from openpyxl import load_workbook

    ana = crear_persona("Ana")
    _p(taller, ana, rol("participante"), estado_part("confirmado"))
    _pasar(cg, taller, _dias(taller)[0], {ana: "atrasado"})
    assert cs.get(f"/actividades/{taller.pk}/asistencia/exportar").status_code == 403
    r = cg.get(f"/actividades/{taller.pk}/asistencia/exportar")
    assert r.status_code == 200 and r["Content-Type"].startswith("application/vnd.openxmlformats")
    filas = list(load_workbook(BytesIO(r.content))["Asistencia"].iter_rows(values_only=True))
    assert filas[0][:3] == ("Persona", "Rol", f"Jornada 1 {D1:%d-%m-%Y}") and filas[1][0].startswith("Ana") and filas[1][2] == "Atrasado"
    assert Auditoria.objects.filter(accion="exportacion", detalle__startswith="Matriz de asistencia").exists()


def test_pestana_asistencia_del_proyecto(cg, taller, proyecto, crear_persona, rol, estado_part):
    ana = crear_persona("Ana")
    _p(taller, ana, rol("participante"), estado_part("confirmado"))
    d1, d2, d3 = _dias(taller)
    _pasar(cg, taller, d1, {ana: "presente"})
    _pasar(cg, taller, d2, {ana: "ausente"})
    html = cg.get(f"/proyectos/{proyecto.pk}?tab=asistencia").content.decode()
    assert "Por tarea" in html and "Por persona" in html and f'{taller.get_absolute_url()}?tab=participantes#asistencia' in html
    res = asistencia.resumen_proyecto(proyecto)
    assert (res["tareas"][0]["jornadas"], res["tareas"][0]["inscritos"], res["tareas"][0]["promedio"]) == (3, 1, 50)
    assert (res["personas"][0]["presentes"], res["personas"][0]["con_marca"], res["personas"][0]["porcentaje"]) == (1, 2, 50)


def _poblar(t, n, crear_persona, rol, estado_part):
    for i in range(n):
        persona = crear_persona()
        _p(t, persona, rol("beneficiario" if i % 2 else "tallerista"), estado_part("confirmado"))
    for j in asistencia.jornadas(t):
        grupos = asistencia.por_persona(asistencia.participaciones(t))
        filas = asistencia.filas(j, grupos, asistencia.marcas(t))
        asistencia.guardar_lista(t, j, None, {f.persona.pk: ("presente", "") for f in filas[: len(filas) // 2]})


def test_matriz_y_panel_con_consultas_fijas(cg, gestor, crear_actividad, proyecto, crear_persona, rol, estado_part):
    medidas = []
    for n in (1, 12):
        t = crear_actividad(f"Taller {n}", estado="confirmada", proyecto=proyecto)
        servicios.programar(t, gestor, D1, time(10), time(12), None, None)
        asistencia.nueva_jornada(t, gestor, D2)
        asistencia.nueva_jornada(t, gestor, D3)
        _poblar(t, n, crear_persona, rol, estado_part)
        url = f"{t.get_absolute_url()}?tab=participantes"
        cg.get(url)
        with CaptureQueriesContext(connection) as c:
            r = cg.get(url)
        assert r.status_code == 200 and 'id="matriz"' in r.content.decode()
        medidas.append(len(c.captured_queries))
    assert medidas[0] == medidas[1], medidas
    with CaptureQueriesContext(connection) as c1:
        cg.get(f"/proyectos/{proyecto.pk}?tab=asistencia")
    t = crear_actividad("Otra tarea", estado="confirmada", proyecto=proyecto)
    servicios.programar(t, gestor, D1, time(10), time(12), None, None)
    _poblar(t, 5, crear_persona, rol, estado_part)
    with CaptureQueriesContext(connection) as c2:
        cg.get(f"/proyectos/{proyecto.pk}?tab=asistencia")
    assert len(c1.captured_queries) == len(c2.captured_queries)


def test_lista_apilada_y_matriz_con_nombres_fijos_en_el_celular():
    from pathlib import Path

    from django.conf import settings

    css = (Path(settings.BASE_DIR) / "static" / "css" / "fche.css").read_text(encoding="utf-8")
    bloque = css[css.index("F28 · Asistencia por jornada"):]
    assert ".fche-matriz__persona { position: sticky; left: 0;" in bloque and "overflow-x: auto" in bloque
    assert "@media (max-width: 767.98px)" in bloque and ".fche-lista-asistencia__form .fche-lista-asistencia__fila { grid-template-columns: minmax(0, 1fr);" in bloque

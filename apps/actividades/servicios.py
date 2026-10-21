"""Operaciones de la actividad que cambian estado o agenda. Siempre dentro de una transacción."""
from django.db import transaction
from django.utils import timezone

from apps.nucleo.auditoria import registrar
from apps.nucleo.models import EstadoActividad

from .models import Actividad, AgendaActividad
from .reglas import MOTIVO_OBLIGATORIO, TRANSICIONES, ReglaNegocio, conflicto_critico_permitido, revisar


def _estado(codigo):
    return EstadoActividad.objects.get(codigo=codigo)


def _sincronizar_estado_agenda(actividad):
    AgendaActividad.objects.filter(actividad=actividad, vigente=True).update(estado=actividad.estado)


@transaction.atomic
def programar(actividad, usuario, fecha, hora_inicio=None, hora_fin=None, lugar=None, modalidad=None, motivo="", enlace=""):
    """Crea la primera programación o, si ya existe, una nueva versión (reprogramar). La anterior se conserva."""
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    codigo = actividad.estado.codigo
    if codigo in ("cancelada", "realizada"):
        raise ReglaNegocio(f"No se puede programar una actividad {actividad.estado.nombre.lower()}.")
    if hora_inicio and hora_fin and hora_fin <= hora_inicio:
        raise ReglaNegocio("La hora de término debe ser posterior a la de inicio.")
    if lugar is not None and not lugar.activo:
        raise ReglaNegocio("El lugar elegido está desactivado.")
    vigente = actividad.agendas.filter(vigente=True).first()
    if vigente:
        igual = (vigente.fecha, vigente.hora_inicio, vigente.hora_fin, vigente.lugar_id, vigente.modalidad_id, vigente.enlace) == (
            fecha, hora_inicio, hora_fin, getattr(lugar, "pk", None), getattr(modalidad, "pk", None), enlace or ""
        )
        if igual:
            raise ReglaNegocio("No hay cambios respecto de la programación vigente.")
        if not motivo.strip():
            raise ReglaNegocio("Indica el motivo del cambio.")
        vigente.vigente = False
        vigente.save(update_fields=["vigente"])
    version = (actividad.agendas.order_by("-version").values_list("version", flat=True).first() or 0) + 1
    if codigo == "pendiente":
        actividad.estado = _estado("planificada")
    elif codigo in ("confirmada", "reprogramada") and vigente:
        actividad.estado = _estado("reprogramada")
        actividad.motivo_estado = motivo.strip()[:250]
    elif codigo == "suspendida":
        # AG-E11: reprogramar una actividad suspendida la reanuda
        if not motivo.strip():
            raise ReglaNegocio("Indica el motivo para reanudar la actividad.")
        actividad.estado = _estado("planificada")
        actividad.motivo_estado = f"Reanudada: {motivo.strip()}"[:250]
    if modalidad is not None:
        actividad.modalidad = modalidad
    actividad.save()
    hoy = timezone.localdate()
    ultimo_minuto = bool(vigente) and (vigente.fecha <= hoy or fecha <= hoy)  # AG-E10
    nueva = AgendaActividad.objects.create(
        actividad=actividad, version=version, vigente=True, fecha=fecha, hora_inicio=hora_inicio, hora_fin=hora_fin,
        lugar=lugar, modalidad=modalidad or actividad.modalidad, estado=actividad.estado, motivo_cambio=motivo.strip(), creado_por=usuario,
        enlace=enlace or "", ultimo_minuto=ultimo_minuto,
    )
    accion = "reprogramada_ultimo_minuto" if ultimo_minuto else ("reprogramada" if vigente else "programada")
    registrar(usuario, accion, actividad, f"v{version} {fecha:%d-%m-%Y} {motivo}".strip())
    return nueva


@transaction.atomic
def crear_serie(actividad, usuario, primera_fecha, frecuencia_dias, repeticiones, hora_inicio, hora_fin=None, lugar=None):
    """Crea `repeticiones` actividades dentro de `actividad`, una por fecha, ya programadas. Cada una se gestiona por separado."""
    from datetime import timedelta

    if actividad.actividad_padre_id:
        raise ReglaNegocio("La serie se crea desde la actividad principal, no desde una que ya está dentro de otra.")
    if actividad.estado.codigo in ("cancelada", "realizada"):
        raise ReglaNegocio("No se puede crear una serie desde una actividad cancelada o realizada.")
    creadas = []
    for i in range(repeticiones):
        fecha = primera_fecha + timedelta(days=frecuencia_dias * i)
        hija = Actividad.objects.create(
            nombre=f"{actividad.nombre} — {fecha:%d-%m-%Y}", actividad_padre=actividad, proyecto=actividad.proyecto, tipo=actividad.tipo,
            objetivo=actividad.objetivo, modalidad=actividad.modalidad, responsable=actividad.responsable, condiciones=actividad.condiciones,
            estado=_estado("pendiente"), creado_por=usuario,
        )
        programar(hija, usuario, fecha, hora_inicio, hora_fin, lugar, actividad.modalidad)
        creadas.append(hija)
    registrar(usuario, "serie_creada", actividad, f"{repeticiones} actividades cada {frecuencia_dias} días desde {primera_fecha:%d-%m-%Y}")
    return creadas


@transaction.atomic
def cambiar_estado(actividad, codigo, usuario, motivo=""):
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    actual = actividad.estado.codigo
    if codigo in ("confirmada", "realizada"):
        raise ReglaNegocio("Usa la acción específica (Confirmar / Finalizar actividad).")
    if codigo not in TRANSICIONES.get(actual, set()):
        raise ReglaNegocio(f"No se puede pasar de «{actividad.estado.nombre}» a «{_estado(codigo).nombre}».")
    if codigo in MOTIVO_OBLIGATORIO and not motivo.strip():
        raise ReglaNegocio("Indica el motivo.")
    actividad.estado = _estado(codigo)
    actividad.motivo_estado = motivo.strip()[:250]
    actividad.save()
    _sincronizar_estado_agenda(actividad)
    registrar(usuario, f"estado_{codigo}", actividad, motivo)
    return actividad


@transaction.atomic
def confirmar(actividad, usuario, acepta_advertencias=False, motivo_conflicto="", motivo_advertencias=""):
    """Revisa compatibilidad antes de confirmar. Nunca confirma con faltantes; los conflictos críticos solo si la opción está activa."""
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    if "confirmada" not in TRANSICIONES.get(actividad.estado.codigo, set()):
        raise ReglaNegocio(f"No se puede confirmar una actividad {actividad.estado.nombre.lower()}.")
    problemas = revisar(actividad)
    bloqueantes = [p for p in problemas if p.nivel == "bloqueante"]
    criticos = [p for p in problemas if p.nivel == "critico"]
    advertencias = [p for p in problemas if p.nivel == "advertencia"]
    if bloqueantes:
        raise ReglaNegocio(*[p.mensaje for p in bloqueantes])
    con_conflicto = False
    if criticos:
        if not conflicto_critico_permitido():
            raise ReglaNegocio("No se puede confirmar:", *[p.mensaje for p in criticos])
        if not motivo_conflicto.strip():
            raise ReglaNegocio("Hay conflictos críticos. Para confirmar igual, escribe el motivo.", *[p.mensaje for p in criticos])
        con_conflicto = True
    if advertencias and not acepta_advertencias:
        raise ReglaNegocio("Hay advertencias. Revísalas y marca «Confirmar de todos modos».", *[p.mensaje for p in advertencias])
    actividad.estado = _estado("confirmada")
    actividad.motivo_estado = motivo_conflicto.strip()[:250] if con_conflicto else ""
    actividad.save()
    _sincronizar_estado_agenda(actividad)
    detalle = []
    if con_conflicto:
        detalle.append(f"Conflictos críticos aceptados: {'; '.join(p.mensaje for p in criticos)}. Motivo: {motivo_conflicto.strip()}")
    if advertencias:  # VA-E9: queda registrado qué advertencias se ignoraron y por qué
        detalle.append(f"Advertencias aceptadas: {'; '.join(p.mensaje for p in advertencias)}" + (f". Motivo: {motivo_advertencias.strip()}" if motivo_advertencias.strip() else ""))
    registrar(usuario, "confirmada_con_conflicto" if con_conflicto else ("confirmada_con_advertencias" if advertencias else "confirmada"), actividad, " | ".join(detalle))
    return problemas


@transaction.atomic
def finalizar(actividad, usuario):
    """«Finalizar actividad»: exige asistencia (o «sin registro» explícito) y resultado. Queda *realizada* y de solo lectura."""
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    if "realizada" not in TRANSICIONES.get(actividad.estado.codigo, set()):
        raise ReglaNegocio(f"No se puede finalizar una actividad {actividad.estado.nombre.lower()}.")
    from .reglas import antes_de_la_fecha

    if antes_de_la_fecha(actividad):
        raise ReglaNegocio(f"La actividad es el {actividad.agenda_vigente.fecha:%d-%m-%Y}: se puede finalizar desde ese día.")
    faltan = []
    registrada = actividad.participaciones.filter(asistencia__isnull=False).exists()
    if not registrada and not actividad.asistencia_sin_registro:
        faltan.append("Registra la asistencia o marca «sin registro de asistencia».")
    if not actividad.resultado.strip():
        faltan.append("Falta registrar el resultado.")
    if faltan:
        raise ReglaNegocio(*faltan)
    actividad.estado = _estado("realizada")
    actividad.finalizada_en = timezone.now()
    actividad.finalizada_por = usuario
    actividad.save()
    _sincronizar_estado_agenda(actividad)
    registrar(usuario, "finalizada", actividad)
    return actividad


@transaction.atomic
def duplicar(actividad, usuario):
    """AT-E1: copia los datos de una actividad (sin participantes ni fechas) para repetirla."""
    from apps.documentos.origen import registrar_origen

    nueva = Actividad.objects.create(
        nombre=f"Copia de {actividad.nombre}"[:200], proyecto=actividad.proyecto, tipo=actividad.tipo, objetivo=actividad.objetivo,
        descripcion=actividad.descripcion, modalidad=actividad.modalidad, responsable=actividad.responsable, condiciones=actividad.condiciones,
        estado=_estado("pendiente"), creado_por=usuario,
    )
    nueva.tramos_etarios.set(actividad.tramos_etarios.all())
    for t in actividad.territorios.filter(vigente=True):
        t.pk = None
        t.actividad = nueva
        t.save()
    for o in actividad.organizaciones.filter(vigente=True):
        o.pk = None
        o.actividad = nueva
        o.save()
    registrar_origen(nueva, usuario, detalle=f"Duplicada de la actividad #{actividad.pk}")
    registrar(usuario, "actividad_duplicada", nueva, f"desde #{actividad.pk}")
    return nueva


@transaction.atomic
def reabrir(actividad, usuario, motivo):
    """Corrección excepcional [V#4]: solo con el permiso `reabrir_actividad`, que ningún rol tiene por defecto. Vuelve a «confirmada»."""
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    if actividad.estado.codigo != "realizada":
        raise ReglaNegocio("La actividad no está finalizada.")
    if not motivo.strip():
        raise ReglaNegocio("Indica el motivo para reabrir.")
    actividad.estado = _estado("confirmada")
    actividad.motivo_estado = motivo.strip()[:250]
    actividad.finalizada_en = None
    actividad.finalizada_por = None
    actividad.save()
    _sincronizar_estado_agenda(actividad)
    registrar(usuario, "reabierta", actividad, motivo)
    return actividad


def asegurar_organizacion(participacion):
    """F25 E4: la organización de procedencia del participante queda en la actividad como «Aporta personas», si la
    actividad aún no tenía ningún registro de esa organización (vigente o dado de baja: lo dado de baja no se reactiva).
    Un solo lugar para todas las vistas que guardan participaciones. A lo más tres consultas."""
    from apps.nucleo.models import TipoIntervencion

    from .models import ActividadOrganizacion

    org_id = participacion.institucion_id
    if not org_id or participacion.estado.codigo == "registro_erroneo":
        return None
    if ActividadOrganizacion.objects.filter(actividad_id=participacion.actividad_id, organizacion_id=org_id).exists():
        return None
    tipo = TipoIntervencion.objects.filter(codigo="aporta_personas").first()
    return ActividadOrganizacion.objects.create(actividad_id=participacion.actividad_id, organizacion_id=org_id, tipo_intervencion=tipo, vigente=True)

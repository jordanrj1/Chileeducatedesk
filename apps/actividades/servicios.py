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
def programar(actividad, usuario, fecha, hora_inicio=None, hora_fin=None, lugar=None, modalidad=None, motivo=""):
    """Crea la primera programación o, si ya existe, una nueva versión (reprogramar). La anterior se conserva."""
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    codigo = actividad.estado.codigo
    if codigo in ("cancelada", "realizada", "cerrada"):
        raise ReglaNegocio(f"No se puede programar una actividad {actividad.estado.nombre.lower()}.")
    if hora_inicio and hora_fin and hora_fin <= hora_inicio:
        raise ReglaNegocio("La hora de término debe ser posterior a la de inicio.")
    if lugar is not None and not lugar.activo:
        raise ReglaNegocio("El lugar elegido está desactivado.")
    vigente = actividad.agendas.filter(vigente=True).first()
    if vigente:
        igual = (vigente.fecha, vigente.hora_inicio, vigente.hora_fin, vigente.lugar_id, vigente.modalidad_id) == (
            fecha, hora_inicio, hora_fin, getattr(lugar, "pk", None), getattr(modalidad, "pk", None)
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
        raise ReglaNegocio("Reactiva la actividad antes de programarla.")
    if modalidad is not None:
        actividad.modalidad = modalidad
    actividad.save()
    nueva = AgendaActividad.objects.create(
        actividad=actividad, version=version, vigente=True, fecha=fecha, hora_inicio=hora_inicio, hora_fin=hora_fin,
        lugar=lugar, modalidad=modalidad or actividad.modalidad, estado=actividad.estado, motivo_cambio=motivo.strip(), creado_por=usuario,
    )
    registrar(usuario, "reprogramada" if vigente else "programada", actividad, f"v{version} {fecha:%d-%m-%Y} {motivo}".strip())
    return nueva


@transaction.atomic
def cambiar_estado(actividad, codigo, usuario, motivo=""):
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    actual = actividad.estado.codigo
    if codigo in ("confirmada", "cerrada"):
        raise ReglaNegocio("Usa la acción específica (confirmar / cerrar).")
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
def confirmar(actividad, usuario, acepta_advertencias=False, motivo_conflicto=""):
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
    registrar(usuario, "confirmada_con_conflicto" if con_conflicto else "confirmada", actividad, motivo_conflicto if con_conflicto else "")
    return problemas


@transaction.atomic
def cerrar(actividad, usuario):
    """Finalizar: exige asistencia (o «sin registro» explícito) y resultado."""
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    if actividad.estado.codigo != "realizada":
        raise ReglaNegocio("Solo se puede cerrar una actividad realizada.")
    faltan = []
    registrada = actividad.participaciones.filter(asistencia__isnull=False).exists()
    if not registrada and not actividad.asistencia_sin_registro:
        faltan.append("Registra la asistencia o marca «sin registro de asistencia».")
    if not actividad.resultado.strip():
        faltan.append("Falta registrar el resultado.")
    if faltan:
        raise ReglaNegocio(*faltan)
    actividad.estado = _estado("cerrada")
    actividad.cerrada_en = timezone.now()
    actividad.cerrada_por = usuario
    actividad.save()
    _sincronizar_estado_agenda(actividad)
    registrar(usuario, "cerrada", actividad)
    return actividad


@transaction.atomic
def reabrir(actividad, usuario, motivo):
    """Corrección excepcional [V#4]: solo con el permiso `reabrir_actividad`, que ningún rol tiene por defecto."""
    actividad = Actividad.objects.select_for_update().get(pk=actividad.pk)
    if actividad.estado.codigo != "cerrada":
        raise ReglaNegocio("La actividad no está cerrada.")
    if not motivo.strip():
        raise ReglaNegocio("Indica el motivo para reabrir.")
    actividad.estado = _estado("realizada")
    actividad.motivo_estado = motivo.strip()[:250]
    actividad.cerrada_en = None
    actividad.cerrada_por = None
    actividad.save()
    _sincronizar_estado_agenda(actividad)
    registrar(usuario, "reabierta", actividad, motivo)
    return actividad

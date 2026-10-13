"""AC-E1: bloqueo temporal por intentos fallidos. Se cuenta por lo escrito en «usuario o correo», exista o no la cuenta,
así el bloqueo no revela qué cuentas existen."""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.nucleo.models import Auditoria


def _identificadores(texto):
    texto = (texto or "").strip()
    User = get_user_model()
    u = User.objects.filter(Q(username__iexact=texto) | Q(email__iexact=texto)).first() if texto else None
    ids = {texto.lower()} if texto else set()
    if u:
        ids |= {u.username.lower(), (u.email or "").lower()} - {""}
    return ids


def intentos_recientes(texto):
    ids = _identificadores(texto)
    if not ids:
        return 0
    ahora = timezone.now()
    ventana = ahora - timedelta(minutes=getattr(settings, "BLOQUEO_MINUTOS", 15))
    cond = Q()
    for i in ids:
        cond |= Q(objeto__iexact=i)
    ultimo_reinicio = Auditoria.objects.filter(cond, accion__in=["ingreso", "desbloqueo"]).order_by("-fecha").values_list("fecha", flat=True).first()
    desde = max(ventana, ultimo_reinicio) if ultimo_reinicio else ventana
    return Auditoria.objects.filter(cond, accion="ingreso_fallido", fecha__gt=desde).count()


def bloqueado(texto):
    return intentos_recientes(texto) >= getattr(settings, "INTENTOS_MAXIMOS", 5)


def desbloquear(usuario_admin, usuario):
    from apps.nucleo.auditoria import registrar

    for i in {usuario.username, usuario.email} - {""}:
        registrar(usuario_admin, "desbloqueo", i.lower())

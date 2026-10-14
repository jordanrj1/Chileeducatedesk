"""Funciones para anotar y leer el origen de un dato (formulario, documento, planilla).
Las usan las demás apps al crear registros, y la pestaña Origen de cada ficha."""
from django.contrib.contenttypes.models import ContentType

from .models import OrigenDato

MODELOS_CON_ORIGEN = {"personas.persona", "organizaciones.organizacion", "lugares.lugar", "actividades.actividad", "proyectos.proyecto", "solicitudes.solicitud"}


def registrar_origen(obj, usuario, fuente="formulario", documento=None, detalle="", lote=None, verificacion="sin_verificar"):
    return OrigenDato.objects.create(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk, fuente=fuente, documento=documento, detalle=detalle, lote=lote,
        registrado_por=usuario if getattr(usuario, "is_authenticated", False) else None, estado_verificacion=verificacion,
    )


def origenes_de(obj):
    return OrigenDato.objects.filter(content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk).select_related("documento", "registrado_por")


def contexto_origen(obj, usuario):
    ct = ContentType.objects.get_for_model(obj)
    return {
        "origenes": origenes_de(obj),
        "url_origen_nuevo": f"/origen/{ct.app_label}/{ct.model}/{obj.pk}/nuevo",
        "puede_origen": usuario.has_perm("documentos.add_origendato"),
    }

"""Fusión controlada de fichas duplicadas (PE-E14, OR-E1, CO-E4). Solo el Administrador.

Todo lo que apuntaba a la ficha de origen pasa a la de destino. Lo que no se puede mover sin duplicar
(por ejemplo, la misma persona dos veces en la misma actividad con el mismo rol) se deja en la ficha de origen,
que queda desactivada con una nota. Nada se borra y todo queda en la auditoría.
"""
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction

from .auditoria import registrar

# Datos que se copian a la ficha que queda si allí están vacíos
COMPLETAR = {
    "Persona": ["apellido_paterno", "apellido_materno", "profesion", "sitio_web", "origen_id", "tipo_documento", "numero_documento",
                "nombre_social", "fecha_nacimiento", "nacionalidad", "nivel_educacional", "situacion_ocupacional", "habilidades", "idiomas", "canal_preferido_id"],
    "Organizacion": ["otro_identificador", "descripcion", "sitio_web", "direccion_id", "naturaleza_juridica", "domicilio_legal", "vigencia_desde", "vigencia_hasta"],
}


def relaciones(obj):
    """[(modelo, campo)] de los registros que apuntan a `obj` (sin las tablas de historial)."""
    res = []
    for rel in obj._meta.get_fields(include_hidden=True):
        if rel.auto_created and (rel.one_to_many or rel.one_to_one) and not rel.related_model.__name__.startswith("Historical"):
            res.append((rel.related_model, rel.field.name))
    return res


def vista_previa(origen):
    filas = []
    for modelo, campo in relaciones(origen):
        n = modelo._default_manager.filter(**{campo: origen}).count()
        if n:
            filas.append((str(modelo._meta.verbose_name_plural), n))
    return filas


@transaction.atomic
def fusionar(origen, destino, usuario, motivo):
    if type(origen) is not type(destino) or origen.pk == destino.pk:
        raise ValueError("Elige otra ficha del mismo tipo.")
    if not motivo.strip():
        raise ValueError("Indica el motivo de la fusión.")
    movidos, conservados = 0, []
    for modelo, campo in relaciones(origen):
        for obj in list(modelo._default_manager.filter(**{campo: origen})):
            setattr(obj, campo, destino)
            try:
                with transaction.atomic():
                    obj.save()
                movidos += 1
            except IntegrityError:
                conservados.append(f"{modelo._meta.verbose_name}: {obj}")
    # Origen del dato (relación genérica)
    from apps.documentos.models import OrigenDato

    ct = ContentType.objects.get_for_model(origen)
    movidos += OrigenDato.objects.filter(content_type=ct, object_id=origen.pk).update(object_id=destino.pk)
    # Completar datos vacíos de la ficha que queda
    nombre = type(origen).__name__
    unicos = {"rut_numero", "rut_dv"} if hasattr(origen, "rut_numero") else set()
    if unicos and origen.rut_numero and not destino.rut_numero:
        rut = (origen.rut_numero, origen.rut_dv)
        type(origen).objects.filter(pk=origen.pk).update(rut_numero=None, rut_dv=None)
        destino.rut_numero, destino.rut_dv = rut
    if nombre == "Persona" and origen.numero_documento and not destino.numero_documento:
        doc = (origen.tipo_documento, origen.numero_documento)
        type(origen).objects.filter(pk=origen.pk).update(tipo_documento="", numero_documento="")
        destino.tipo_documento, destino.numero_documento = doc
    for c in COMPLETAR.get(nombre, []):
        if c in ("tipo_documento", "numero_documento"):
            continue
        if not getattr(destino, c) and getattr(origen, c):
            setattr(destino, c, getattr(origen, c))
    destino.save()
    for m2m in ("perfiles", "areas_interes", "tramos_etarios"):  # perfiles, intereses y tramos de edad se suman
        if hasattr(destino, m2m):
            getattr(destino, m2m).add(*getattr(origen, m2m).all())
    # La ficha de origen se desactiva y queda la nota
    origen.refresh_from_db()
    origen.activo = False
    if hasattr(origen, "observaciones"):
        origen.observaciones = (f"Fusionada en la ficha #{destino.pk} ({destino}). Motivo: {motivo.strip()}\n" + origen.observaciones).strip()
    if hasattr(origen, "estado_registro_id"):
        from .models import EstadoRegistro

        origen.estado_registro = EstadoRegistro.objects.filter(codigo="fusionada").first() or origen.estado_registro
    origen.save()
    registrar(usuario, "fusion", f"{origen} → {destino}", f"{movidos} registros movidos; {len(conservados)} conservados en el origen. Motivo: {motivo}")
    return movidos, conservados

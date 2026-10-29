"""Crear una persona con la ficha rápida (F25 E1) desde cualquier formulario, sin salir de él.
Deja su estado (parte «incompleto»; F26 P2: luego se recalcula solo, ver `recalcular_estado`), sus contactos, la comuna donde vive, quién la creó y de
dónde salió el dato (docs/CONTEXTO.md §11.7). Lo usan la ventana «+ Crear persona» de los buscadores y «Crear persona nueva»
al agregar participantes; el modo rápido de Personas → Nueva usa `completar_ficha_rapida`."""
from django.db import transaction

from apps.documentos.origen import registrar_origen
from apps.nucleo.models import EstadoRegistro, TipoContacto

from .models import Contacto, PersonaDireccion


def estado_incompleto():
    return EstadoRegistro.objects.filter(codigo="incompleto").first()


def completar_ficha_rapida(persona, datos):
    """Contactos (correo principal; si no hay, el teléfono) y la comuna donde vive, como dirección de residencia."""
    correo = (datos.get("correo") or "").strip()
    telefono = (datos.get("telefono") or "").strip()
    if correo:
        Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="correo"), valor=correo, principal=True)
    if telefono:
        Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="telefono_movil"), valor=telefono, principal=not correo)
    if datos.get("comuna") and not persona.direcciones.filter(tipo="residencia").exists():  # solo la comuna: basta para el territorio
        from apps.territorio.models import Direccion

        PersonaDireccion.objects.create(persona=persona, direccion=Direccion.objects.create(comuna=datos["comuna"]), tipo="residencia")


def crear_persona_rapida(form, usuario, nota=""):
    """Crea la persona de una ficha rápida válida (`FichaRapidaForm`) con sus contactos, su comuna y su origen, todo o nada."""
    with transaction.atomic():
        persona = form.save(commit=False)
        persona.creado_por = usuario
        nota = (nota or "").strip()
        if nota:  # qué la distingue de otra ficha con un nombre parecido
            persona.observaciones = f"Se distingue de otra ficha parecida: {nota}"
        persona.estado_registro = estado_incompleto()
        persona.save()
        completar_ficha_rapida(persona, form.cleaned_data)
        registrar_origen(persona, usuario)
    return persona


def recalcular_estado(persona):
    """F26 P2: deja la ficha «incompleto» si `faltantes()` encuentra algo y «activo» si no. No toca los estados manuales
    (por verificar, desactualizado, fallecida, fusionada u otro que no sea activo o incompleto). Devuelve el código
    resultante. Se llama al guardar la persona y al guardar o desactivar sus contactos, direcciones y formación."""
    from .models import ESTADOS_CALCULADOS, Persona

    if not persona or not persona.pk:
        return None
    actual = EstadoRegistro.objects.filter(pk=persona.estado_registro_id).values_list("codigo", flat=True).first() if persona.estado_registro_id else None
    if actual is not None and actual not in ESTADOS_CALCULADOS:
        return actual
    fresca = Persona.objects.con_completitud().filter(pk=persona.pk).first()
    if fresca is None:
        return actual
    codigo = "incompleto" if fresca.faltantes() else "activo"
    if codigo != actual:
        estado = EstadoRegistro.objects.filter(codigo=codigo).first()
        if estado is not None:  # dato calculado: se escribe directo, sin sumar versiones al historial ni volver a recalcular
            Persona.objects.filter(pk=persona.pk).update(estado_registro=estado)
            persona.estado_registro = estado
    return codigo

"""Crear una persona con lo mínimo (nombre y, si lo hay, un contacto) desde cualquier formulario, sin salir de él.
Deja su estado (activo o incompleto), sus contactos, quién la creó y de dónde salió el dato (docs/CONTEXTO.md §11.7).
Lo usa la ventana «+ Crear persona» de los buscadores."""
from django.db import transaction

from apps.documentos.origen import registrar_origen
from apps.nucleo.models import EstadoRegistro, TipoContacto

from .models import Contacto, Persona


def crear_persona_rapida(datos, usuario, nota=""):
    """Crea la persona con sus contactos y su origen, todo o nada."""
    correo = (datos.get("correo") or "").strip()
    telefono = (datos.get("telefono") or "").strip()
    with transaction.atomic():
        persona = Persona(
            nombres=datos["nombres"].strip(), apellido_paterno=(datos.get("apellido_paterno") or "").strip(),
            apellido_materno=(datos.get("apellido_materno") or "").strip(), creado_por=usuario,
        )
        nota = (nota or "").strip()
        if nota:  # qué la distingue de otra ficha con un nombre parecido
            persona.observaciones = f"Se distingue de otra ficha parecida: {nota}"
        codigo = "activo" if (persona.apellido_paterno and (correo or telefono)) else "incompleto"
        persona.estado_registro = EstadoRegistro.objects.filter(codigo=codigo).first()
        persona.save()
        if correo:
            Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="correo"), valor=correo, principal=True)
        if telefono:
            Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="telefono_movil"), valor=telefono, principal=not correo)
        registrar_origen(persona, usuario)
    return persona

"""Componentes de interfaz: iconos SVG propios (sin dependencias), estados con color e iniciales."""
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# Iconos de trazo (24×24, color heredado). Dibujados para este proyecto: sin librerías externas.
ICONOS = {
    "inicio": '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    "solicitudes": '<path d="M3 13h5l2 3h4l2-3h5"/><path d="M5.5 5h13L21 13v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-6z"/>',
    "proyectos": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "actividades": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v3H9z"/><path d="M9 13l2 2 4-4"/>',
    "calendario": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "personas": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/><circle cx="17" cy="9" r="2.5"/><path d="M17.5 14.2c2.4.4 4 2.4 4 5.3"/>',
    "persona": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
    "persona_mas": '<circle cx="10" cy="8" r="4"/><path d="M3 21c0-4 3-7 7-7M18 13v6M15 16h6"/>',
    "organizaciones": '<rect x="4" y="3" width="10" height="18" rx="1"/><path d="M14 9h5a1 1 0 0 1 1 1v11M7.5 7h3M7.5 11h3M7.5 15h3M3 21h18"/>',
    "lugares": '<path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    "territorio": '<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z"/><path d="M9 4v14M15 6v14"/>',
    "reuniones": '<path d="M4 5h16v10H9l-5 4z"/><path d="M8 9h8M8 12h5"/>',
    "tareas": '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 12l3 3 5-6"/>',
    "documentos": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h4"/>',
    "importaciones": '<path d="M12 15V4M7 9l5-5 5 5"/><path d="M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
    "finanzas": '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18"/><circle cx="16.5" cy="14.5" r="1"/>',
    "catalogos": '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2" fill="var(--fche-relleno-icono, #fff)"/><circle cx="15" cy="12" r="2" fill="var(--fche-relleno-icono, #fff)"/><circle cx="7" cy="18" r="2" fill="var(--fche-relleno-icono, #fff)"/>',
    "administracion": '<path d="M12 3l7 3v5c0 5-3.5 8.5-7 10-3.5-1.5-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
    "ayuda": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5v.7"/><path d="M12 17h.01"/>',
    "buscar": '<circle cx="11" cy="11" r="7"/><path d="M16.5 16.5L21 21"/>',
    "mas": '<path d="M12 5v14M5 12h14"/>',
    "editar": '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    "descargar": '<path d="M12 4v11M7 10l5 5 5-5M4 19h16"/>',
    "volver": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "derecha": '<path d="M9 6l6 6-6 6"/>',
    "izquierda": '<path d="M15 6l-6 6 6 6"/>',
    "abajo": '<path d="M6 9l6 6 6-6"/>',
    "salir": '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="M10 8l-4 4 4 4M6 12h10"/>',
    "alerta": '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    "ok": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "error": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "cerrar": '<path d="M6 6l12 12M18 6L6 18"/>',
    "reloj": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "filtro": '<path d="M4 5h16l-6 7v6l-4 2v-8z"/>',
    "archivar": '<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8M10 12h4"/>',
    "copiar": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    "enlace": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "telefono": '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a1 1 0 0 1-1 1A16 16 0 0 1 4 5a1 1 0 0 1 1-1z"/>',
    "correo": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "candado": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "historial": '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5M12 8v4l3 2"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "rayo": '<path d="M13 3L5 14h6l-1 7 9-12h-6z"/>',
    "ojo": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "fusionar": '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="12" r="2"/><path d="M6 7v10M6 9c0 3 4 3 10 3"/>',
    "imprimir": '<path d="M7 9V3h10v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/>',
    "lista": '<path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"/>',
    "tendencia": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "usuarios_check": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6M16 11l2 2 4-4"/>',
    "dato_vacio": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 14h8"/>',
    "subir": '<path d="M12 20V9M7 14l5-5 5 5M4 5h16"/>',
}


@register.simple_tag
def icono(nombre, tam=18, clase=""):
    trazos = ICONOS.get(nombre, ICONOS["info"])
    return format_html(
        '<svg class="fche-icono {}" width="{}" height="{}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{}</svg>',
        clase, tam, tam, mark_safe(trazos),
    )


# Tono de color para cada estado (por su código estable)
TONOS = {
    "pendiente": "gris", "planificada": "azul", "confirmada": "verde", "reprogramada": "naranja", "suspendida": "amarillo",
    "cancelada": "rojo", "realizada": "morado",
    "en_seguimiento": "azul", "convertida": "verde", "descartada": "rojo",
    "invitado": "gris", "interesado": "azul", "disponible": "azul", "confirmado": "verde", "asistio": "verde", "no_asistio": "rojo",
    "rechazo": "rojo", "cancelo": "rojo", "lista_espera": "amarillo", "registro_erroneo": "gris",
    "activo": "verde", "incompleto": "amarillo", "por_verificar": "naranja", "desactualizado": "gris", "fallecida": "gris", "fusionada": "gris",
    "en_curso": "azul", "hecha": "verde",
    "enviada": "gris", "respondio": "azul", "aceptada": "verde", "rechazada": "rojo", "sin_respuesta": "amarillo", "cumplida": "verde",
    "preparacion": "gris", "postulado": "azul", "ejecucion": "verde", "finalizado": "morado", "suspendido": "amarillo", "cancelado": "rojo",
    "previa": "amarillo", "confirmado_lote": "verde", "revertido": "gris", "descartado": "rojo",
    "borrador": "gris", "adjudicada": "verde",
    # Textos visibles (cuando la columna trae la etiqueta y no el código)
    "en_preparacion": "gris", "en_ejecucion": "verde", "en_revision": "amarillo", "acepto": "verde",
    "anulado": "rojo", "desactivado": "gris", "inactivo": "gris", "bloqueado_por_intentos_fallidos": "rojo", "vigente": "verde", "anterior": "gris", "verificado": "verde", "sin_verificar": "gris", "vencida": "rojo",
}

COLUMNAS_ESTADO = {"Estado", "Registro", "Acceso"}


def badge_estado(codigo, texto):
    tono = TONOS.get(codigo, "gris")
    return format_html('<span class="fche-estado fche-estado--{}"><span class="fche-estado__punto" aria-hidden="true"></span>{}</span>', tono, texto)


@register.simple_tag
def estado(valor, texto=None, codigo=None):
    """{% estado actividad.estado %} con un catálogo; o {% estado "realizada" "Realizada" %} con código y texto."""
    if valor is None or valor == "":
        return "—"
    if hasattr(valor, "codigo"):
        return badge_estado(valor.codigo, texto or valor.nombre)
    return badge_estado(codigo or _codigo(valor), texto or str(valor))


def _codigo(texto):
    from django.utils.text import slugify

    return slugify(str(texto)).replace("-", "_")


@register.simple_tag
def celda(valor, encabezado=""):
    """Celda de un listado: los estados se muestran como pastilla de color; el resto, tal cual."""
    if valor is None or valor == "":
        return ""
    if hasattr(valor, "codigo") and type(valor).__name__.startswith("Estado"):
        return badge_estado(valor.codigo, valor.nombre)
    if encabezado in COLUMNAS_ESTADO:
        return badge_estado(_codigo(valor), str(valor))
    return valor


@register.filter
def iniciales(texto):
    partes = [p for p in str(texto or "").replace(",", " ").split() if p[:1].isalpha()]
    return ("".join(p[0] for p in partes[:2]) or "·").upper()


@register.filter
def tono_avatar(texto):
    """Color estable por nombre, para avatares de iniciales."""
    return f"tono-{sum(ord(c) for c in str(texto or '')) % 6}"


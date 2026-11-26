"""F28 B · Comprobante de un gasto: foto (JPG, PNG o WEBP) o PDF de hasta 5 MB. Se valida por su contenido (los primeros
bytes del archivo), no solo por la extensión, y se guarda como documento restringido ligado a la actividad (y al proyecto si
hay). Sin librería de imágenes: mismo método que la foto de la persona (apps/personas/models.py)."""
import os
import uuid

from django.core.exceptions import ValidationError

from apps.personas.models import formato_imagen, leer_cabecera

TAMANO_MAXIMO_MB = 5
FORMATOS = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "pdf": "application/pdf"}
AYUDA = "Foto de la boleta o factura (JPG, PNG o WEBP) o PDF, de hasta 5 MB. Se guarda como documento restringido."
ACCEPT = ".jpg,.jpeg,.png,.webp,.pdf,image/jpeg,image/png,image/webp,application/pdf"


def tipo_real(cabecera):
    """Tipo real del archivo según sus primeros bytes, o None si no es una imagen JPG/PNG/WEBP ni un PDF."""
    if cabecera[:5] == b"%PDF-":
        return "application/pdf"
    return formato_imagen(cabecera)


def validar_comprobante(archivo):
    ext = os.path.splitext(archivo.name)[1].lower().lstrip(".")
    if ext not in FORMATOS:
        raise ValidationError("El comprobante debe ser una foto JPG, PNG o WEBP, o un PDF. Otros tipos de archivo no se aceptan.")
    if not archivo.size:
        raise ValidationError("El archivo está vacío.")
    if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise ValidationError(f"El comprobante supera el máximo de {TAMANO_MAXIMO_MB} MB.")
    real = tipo_real(leer_cabecera(archivo))
    if real is None or real != FORMATOS[ext]:
        raise ValidationError("El archivo no es una foto JPG, PNG o WEBP ni un PDF válido (su contenido no coincide con la extensión).")
    return archivo


def guardar_comprobante(archivo, gasto, usuario):
    """Crea el documento restringido del comprobante y lo deja en el gasto (sin guardar el gasto). El nombre original no
    se conserva (puede traer datos de quien pagó)."""
    from apps.documentos.models import Documento
    from apps.nucleo.models import TipoDocumento

    ext = os.path.splitext(archivo.name)[1].lower()
    archivo.name = f"comprobante-{uuid.uuid4().hex}{ext}"
    doc = Documento.objects.create(
        nombre=f"Comprobante: {gasto.concepto}"[:200], archivo=archivo, tipo=TipoDocumento.objects.get(codigo="comprobante_de_gasto"),
        fecha=gasto.fecha, descripcion="Comprobante de un gasto (F28).", actividad_id=gasto.actividad_id, sesion_id=gasto.sesion_id,
        proyecto_id=gasto.proyecto_id, restringido=True, subido_por=usuario)
    gasto.documento = doc
    return doc

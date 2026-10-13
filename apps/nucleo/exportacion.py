"""Exportación autorizada a Excel (RF-28). Siempre queda en auditoría."""
from datetime import datetime
from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from .auditoria import registrar


def _seguro(valor):
    """Evita inyección de fórmulas en Excel y caracteres inválidos."""
    texto = ILLEGAL_CHARACTERS_RE.sub("", str(valor))
    return "'" + texto if texto[:1] in ("=", "+", "-", "@") and not texto.lstrip("+-").replace(" ", "").isdigit() else texto


def agregar_aviso(libro, usuario):
    """SE-E3: toda exportación declara que contiene datos personales y quién la generó."""
    from django.utils import timezone

    hoja = libro.create_sheet("Aviso")
    hoja.append(["Contiene datos personales. Uso interno de la Fundación Chile Edúcate; no compartir fuera de ella."])
    hoja.append([f"Exportado por {usuario.get_username() if usuario else '—'} el {timezone.localtime():%d-%m-%Y %H:%M}."])
    hoja.append(["Si este archivo se pierde o se envía por error, avisa al Administrador."])


def respuesta_xlsx(usuario, titulo, encabezados, filas):
    libro = Workbook()
    hoja = libro.active
    hoja.title = titulo[:31]
    hoja.append([_seguro(e) for e in encabezados])
    for fila in filas:
        hoja.append([_seguro(v) for v in fila])
    agregar_aviso(libro, usuario)
    buffer = BytesIO()
    libro.save(buffer)
    registrar(usuario, "exportacion", titulo, f"{len(filas)} filas")
    nombre = f"{titulo.lower().replace(' ', '_')}_{datetime.now():%Y%m%d_%H%M}.xlsx"
    r = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    r["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return r

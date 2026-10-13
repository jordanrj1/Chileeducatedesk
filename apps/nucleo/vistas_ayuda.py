"""CO-E5: el manual de uso dentro del sistema. Convierte el Markdown simple del manual a HTML seguro."""
import re
from pathlib import Path

from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView

from .vistas_base import Permiso403Mixin


def _en_linea(texto):
    t = escape(texto)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", t)  # los enlaces del manual apuntan a archivos: se deja el texto
    return t


def markdown_simple(md):
    html, lista = [], None
    for linea in md.splitlines():
        if lista and not re.match(r"^\s*(-|\d+\.)\s", linea):
            html.append(f"</{lista}>")
            lista = None
        if m := re.match(r"^(#{1,3})\s+(.*)", linea):
            nivel = len(m.group(1)) + 1
            html.append(f"<h{nivel} class='h{nivel + 2} mt-3'>{_en_linea(m.group(2))}</h{nivel}>")
        elif m := re.match(r"^\s*(-|\d+\.)\s+(.*)", linea):
            tipo = "ol" if m.group(1)[0].isdigit() else "ul"
            if lista != tipo:
                if lista:
                    html.append(f"</{lista}>")
                html.append(f"<{tipo}>")
                lista = tipo
            html.append(f"<li>{_en_linea(m.group(2))}</li>")
        elif linea.strip():
            html.append(f"<p>{_en_linea(linea)}</p>")
    if lista:
        html.append(f"</{lista}>")
    return mark_safe("\n".join(html))


class Ayuda(Permiso403Mixin, TemplateView):
    template_name = "nucleo/ayuda.html"

    def has_permission(self):
        return self.request.user.is_authenticated

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ruta = Path(settings.BASE_DIR) / "docs" / "manual_de_uso.md"
        ctx["manual"] = markdown_simple(ruta.read_text(encoding="utf-8")) if ruta.exists() else "El manual no está disponible."
        ctx["titulo"] = "Ayuda"
        return ctx

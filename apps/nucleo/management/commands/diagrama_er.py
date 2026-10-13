"""Genera docs/modelo/diagrama_er.md (Mermaid) desde los modelos reales. Uso: python manage.py diagrama_er"""
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models

GRUPOS = [
    ("Territorio, personas y organizaciones", ["territorio", "personas", "organizaciones", "cuentas"]),
    ("Lugares, proyectos y actividades", ["lugares", "proyectos", "actividades", "solicitudes"]),
    ("Coordinación, documentos, importaciones y finanzas", ["coordinacion", "documentos", "importaciones", "finanzas"]),
]
OMITIR = {"PermisoInicial"}


def _tipo(campo):
    if isinstance(campo, models.ForeignKey):
        return "FK"
    return {"CharField": "texto", "TextField": "texto", "SlugField": "texto", "EmailField": "texto", "URLField": "texto", "BooleanField": "bool",
            "DateField": "fecha", "DateTimeField": "fechahora", "TimeField": "hora", "JSONField": "json", "FileField": "archivo"}.get(campo.get_internal_type(), "numero")


class Command(BaseCommand):
    help = "Genera el diagrama entidad-relación (Mermaid) desde los modelos."

    def handle(self, *args, **opts):
        salida = ["# Modelo de datos (generado)", "", "Generado con `python manage.py diagrama_er` a partir de los modelos de Django. "
                  "Las tablas de historial (`Historical*`) y los catálogos se omiten del dibujo para que se pueda leer; los catálogos aparecen como `FK` a `nucleo`.", ""]
        for titulo, etiquetas in GRUPOS:
            modelos = [m for e in etiquetas for m in apps.get_app_config(e).get_models() if not m.__name__.startswith("Historical") and m.__name__ not in OMITIR]
            nombres = {m.__name__ for m in modelos}
            salida += [f"## {titulo}", "", "```mermaid", "erDiagram"]
            for m in modelos:
                salida.append(f"    {m.__name__} {{")
                for f in m._meta.concrete_fields:
                    marca = " PK" if f.primary_key else (" FK" if f.is_relation else "")
                    nulo = "" if f.primary_key else (' "opcional"' if f.null or getattr(f, "blank", False) else "")
                    salida.append(f"        {_tipo(f).replace('FK', 'id')} {f.name}{marca}{nulo}")
                salida.append("    }")
            for m in modelos:
                for f in m._meta.concrete_fields:
                    if f.is_relation and f.related_model.__name__ in nombres:
                        uno = "|o" if f.null else "||"
                        card = f"{uno}--||" if isinstance(f, models.OneToOneField) else f"{uno}--o{{"
                        salida.append(f'    {f.related_model.__name__} {card} {m.__name__} : "{f.name}"')
            salida += ["```", ""]
        destino = Path(settings.BASE_DIR) / "docs" / "modelo" / "diagrama_er.md"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text("\n".join(salida), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Diagrama escrito en {destino}"))

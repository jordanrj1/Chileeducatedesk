"""Registro de la app «núcleo» en Django.
El núcleo tiene lo que comparten todos los módulos: catálogos, auditoría, buscador, panel, plantillas comunes y utilidades."""
from django.apps import AppConfig


class NucleoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.nucleo"

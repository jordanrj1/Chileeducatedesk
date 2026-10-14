"""Registro de la app «importaciones» en Django.
Permite cargar listados desde una planilla (Excel, CSV o texto pegado) con vista previa y reversión."""
from django.apps import AppConfig


class ImportacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.importaciones"

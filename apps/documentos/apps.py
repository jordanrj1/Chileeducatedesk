"""Registro de la app «documentos» en Django.
Guarda los archivos de evidencia (cartas, minutas, certificados) y de dónde salió cada dato."""
from django.apps import AppConfig


class DocumentosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.documentos"

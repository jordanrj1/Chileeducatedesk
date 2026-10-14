"""Registro de la app «solicitudes» en Django: lo que llega a la Fundación (o lo que sale a buscar)
antes de saber si será una actividad."""
from django.apps import AppConfig


class SolicitudesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.solicitudes"

"""Registro de la app «actividades» en Django.
La app reúne lo central del sistema: la actividad, sus participantes, su agenda, sus sesiones y su cierre."""
from django.apps import AppConfig


class ActividadesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.actividades"

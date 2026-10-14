"""Registro de la app «territorio» en Django: región, provincia, comuna, sector y dirección,
la cadena de ubicación que comparten personas, organizaciones, lugares y actividades."""
from django.apps import AppConfig


class TerritorioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.territorio"

"""Registro de la app «comunidades» en Django.
Una comunidad es un grupo de personas (vecinos de una villa, un curso, un comité) al que se dirigen actividades."""
from django.apps import AppConfig


class ComunidadesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.comunidades"
    verbose_name = "comunidades"

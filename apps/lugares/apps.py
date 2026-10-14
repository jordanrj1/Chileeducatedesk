"""Registro de la app «lugares» en Django. Un lugar se anota una vez y se reutiliza en muchas actividades."""
from django.apps import AppConfig


class LugaresConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.lugares"

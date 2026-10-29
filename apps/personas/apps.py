"""Registro de la app «personas» en Django. Una persona se registra una vez y acumula su historia;
existir como persona no implica tener cuenta."""
from django.apps import AppConfig


class PersonasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.personas"

    def ready(self):
        from . import senales  # noqa: F401  (F26 P2: estado de la ficha calculado)

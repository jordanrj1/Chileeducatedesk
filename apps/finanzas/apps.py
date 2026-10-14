"""Registro de la app «finanzas» en Django. Es de 2.ª fase y queda oculta con SEGUNDA_FASE=False.
El dinero está fuera del alcance actual del proyecto."""
from django.apps import AppConfig


class FinanzasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.finanzas"

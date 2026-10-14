"""Registro de la app «coordinación» en Django.
Guarda el seguimiento: llamadas y correos (interacciones), invitaciones y solicitudes de apoyo; reuniones y tareas son de 2.ª fase."""
from django.apps import AppConfig


class CoordinacionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.coordinacion"

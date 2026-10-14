"""Registro de la app «proyectos» en Django. Un proyecto agrupa actividades que van juntas;
es opcional y ninguna actividad lo exige."""
from django.apps import AppConfig


class ProyectosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.proyectos"

"""Registro de la app «organizaciones» en Django: instituciones educativas, municipalidades, juntas de vecinos,
empresas, fundaciones y otras, cada una registrada una sola vez."""
from django.apps import AppConfig


class OrganizacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.organizaciones"

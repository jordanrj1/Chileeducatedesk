"""Punto de arranque que usa el servidor waitress para atender las páginas (lo llama iniciar.bat).
Usa los ajustes de producción (config/settings/produccion.py)."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.produccion')

application = get_wsgi_application()

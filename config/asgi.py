"""Punto de arranque alternativo (ASGI) que Django crea por defecto.
Este sistema no lo usa: arranca con waitress a través de wsgi.py."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

application = get_asgi_application()

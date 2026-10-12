"""Uso real con waitress. DEBUG debe ser False."""
from .base import *  # noqa: F401,F403

DEBUG = False
SESSION_COOKIE_HTTPONLY = True
# Con HTTPS (servidor web futuro) activar: SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE.

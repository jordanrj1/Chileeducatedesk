"""Uso real con waitress. DEBUG debe ser False."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False
SESSION_COOKIE_HTTPONLY = True
# Si el sistema se publica con HTTPS (servidor web futuro), definir HTTPS=True en .env.
if env.bool("HTTPS", default=False):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000

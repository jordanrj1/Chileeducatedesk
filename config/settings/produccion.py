"""Ajustes para el uso real con waitress: DEBUG apagado y cookies protegidas.
Si algún día se publica con HTTPS, HTTPS=True en .env activa las protecciones adicionales."""
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

# F26 Rb: rendimiento en el uso real.
# Estilos, scripts e imágenes con huella en el nombre (css/fche.3f2a….css), comprimidos (gzip) y guardados por el
# navegador por un año; al cambiar un archivo cambia su nombre, así nunca se ve una versión vieja. Requiere
# `collectstatic` (iniciar.bat lo corre al arrancar).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# Conexión a la base reutilizada entre peticiones (segundos; 0 = una conexión nueva por petición), con chequeo de salud
# para no usar una conexión que PostgreSQL ya cerró (p. ej. tras reiniciar el servicio).
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)  # noqa: F405
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405
# Sesión leída de la memoria (CACHES) y guardada también en la base: sobrevive a un reinicio del servidor.
# La expiración por inactividad (SESION_SEGUNDOS, SESSION_SAVE_EVERY_REQUEST) y el cierre de sesión funcionan igual.
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

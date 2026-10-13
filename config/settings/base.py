"""Ajustes comunes. Lo específico de cada entorno va en local.py / produccion.py."""
import sys
import tempfile
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "simple_history",
    "django_htmx",
    "apps.nucleo",
    "apps.cuentas",
    "apps.territorio",
    "apps.personas",
    "apps.organizaciones",
    "apps.lugares",
    "apps.proyectos",
    "apps.actividades",
    "apps.solicitudes",
    "apps.coordinacion",
    "apps.documentos",
    "apps.importaciones",
    "apps.finanzas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "apps.nucleo.fases.SegundaFaseMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.nucleo.contexto.navegacion",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="fche"),
        "USER": env("DB_USER", default="postgres"),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="5432"),
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = ["apps.cuentas.backends.CorreoOUsuarioBackend"]
# Segunda fase (reuniones, tareas, sesiones, beneficiarios, verificaciones, finanzas): ocultos por defecto.
SEGUNDA_FASE = env.bool("SEGUNDA_FASE", default=False)
# Para habilitar solo algunos: reuniones, tareas, sesiones, beneficiarios, verificaciones, postulaciones, finanzas
MODULOS_SEGUNDA_FASE = env.list("MODULOS_SEGUNDA_FASE", default=[])

# [V#3] ¿Se puede confirmar una actividad con incompatibilidad crítica, con motivo? Hoy: no.
CONFIRMAR_CON_CONFLICTO_CRITICO = env.bool("CONFIRMAR_CON_CONFLICTO_CRITICO", default=False)

from django.contrib.messages import constants as _mensajes

MESSAGE_TAGS = {_mensajes.ERROR: "danger"}  # Bootstrap usa «danger», no «error»

# A quién consultar si una cuenta está desactivada (AC-02). Ej.: «Manuel (correo@ejemplo.cl)».
CONTACTO_ADMINISTRADOR = env("CONTACTO_ADMINISTRADOR", default="")

LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/dashboard"
LOGOUT_REDIRECT_URL = "/login"

# Expiración por inactividad [P]: valor por confirmar con el cliente.
SESSION_COOKIE_AGE = env.int("SESION_SEGUNDOS", default=3600)
SESSION_SAVE_EVERY_REQUEST = True

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Para entrar desde otros equipos de la red [V#5]: lista de orígenes, p. ej. http://192.168.1.10:8000
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

LOG_DIR = Path(env("LOG_DIR", default=str(BASE_DIR / "logs")))
if "pytest" in sys.modules:  # las pruebas provocan errores a propósito: no deben ensuciar el registro real
    LOG_DIR = Path(tempfile.mkdtemp(prefix="fche_logs_pruebas_"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}},
    "handlers": {
        "consola": {"class": "logging.StreamHandler", "formatter": "simple"},
        "archivo": {"class": "logging.handlers.RotatingFileHandler", "filename": str(LOG_DIR / "fche.log"), "maxBytes": 2_000_000, "backupCount": 5, "formatter": "simple", "encoding": "utf-8"},
    },
    "root": {"handlers": ["consola", "archivo"], "level": "WARNING"},
}

# Archivos subidos: carpeta fuera del código (configurable).
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR.parent / "fche_media")))
MEDIA_URL = "/media/"

# Solo se sirve por vista con permiso, nunca como estático (ver docs/CONTEXTO.md §9).

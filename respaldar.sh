#!/usr/bin/env bash
# Respaldo de base de datos y documentos (Mac/Linux). Programar con cron, p. ej.: 0 2 * * * /ruta/fche/respaldar.sh
set -euo pipefail
cd "$(dirname "$0")"
export DJANGO_SETTINGS_MODULE=config.settings.produccion
.venv/bin/python manage.py respaldar "$@"

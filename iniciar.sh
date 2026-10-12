#!/usr/bin/env bash
# Arranca FCHE con waitress en Mac/Linux. Equivalente a iniciar.bat.
# Requiere .venv y .env configurados y PostgreSQL en marcha.
set -euo pipefail
cd "$(dirname "$0")"
export DJANGO_SETTINGS_MODULE=config.settings.produccion

# Si usas el clúster de desarrollo (~/pgdata-fche, puerto 5433) y está detenido, lo inicia.
PGBIN="$HOME/Applications/Postgres.app/Contents/Versions/17/bin"
PGDATA_DEV="$HOME/pgdata-fche"
if [ -x "$PGBIN/pg_ctl" ] && [ -d "$PGDATA_DEV" ] && ! "$PGBIN/pg_ctl" -D "$PGDATA_DEV" status >/dev/null 2>&1; then
  "$PGBIN/pg_ctl" -D "$PGDATA_DEV" -o "-p 5433 -c listen_addresses=127.0.0.1" -l "$PGDATA_DEV/server.log" start
fi

.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput -v0
# Solo este equipo. Para la red de la Fundación [V#5] cambiar 127.0.0.1 por 0.0.0.0.
exec .venv/bin/waitress-serve --listen=127.0.0.1:8000 config.wsgi:application

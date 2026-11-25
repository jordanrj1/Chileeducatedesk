#!/bin/sh
# Detiene FCHE (Docker) sin borrar datos. Para volver a usarlo: ./levantar.sh
cd "$(dirname "$0")"
docker compose --env-file .env.docker stop

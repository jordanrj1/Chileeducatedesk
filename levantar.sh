#!/bin/sh
# Levanta FCHE con Docker en Mac o Linux. Guía: docs/DESPLIEGUE_DOCKER.md
# La primera vez crea .env.docker con claves nuevas; las siguientes solo actualiza y arranca.
set -e
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Falta Docker Desktop. Instálalo desde https://www.docker.com/products/docker-desktop/ y vuelve a ejecutar este archivo."
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop no está abierto. Ábrelo, espera que diga «Engine running» y vuelve a ejecutar este archivo."
  exit 1
fi

if [ ! -f .env.docker ]; then
  cp .env.docker.example .env.docker
  clave=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 50)
  contrasena=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32)
  sed -i.bak -e "s/^SECRET_KEY=.*/SECRET_KEY=$clave/" -e "s/^DB_PASSWORD=.*/DB_PASSWORD=$contrasena/" .env.docker
  rm -f .env.docker.bak
  echo "Se creó .env.docker con claves nuevas. Guarda una copia en un lugar seguro: sin ella no se puede abrir la base."
fi

mkdir -p respaldos
docker compose --env-file .env.docker up -d --build

puerto=$(grep '^PUERTO=' .env.docker | cut -d= -f2)
puerto=${puerto:-8000}
echo "Esperando que FCHE responda (la primera vez tarda unos minutos)..."
i=0
until curl -fs -o /dev/null "http://localhost:$puerto/login"; do
  i=$((i + 1))
  if [ "$i" -gt 120 ]; then
    echo "FCHE no respondió. Revisa: docker compose --env-file .env.docker logs web"
    exit 1
  fi
  sleep 2
done

echo "FCHE listo: http://localhost:$puerto"
if ! docker compose --env-file .env.docker exec -T web python manage.py shell -c "from django.contrib.auth.models import User; import sys; sys.exit(0 if User.objects.exists() else 1)" >/dev/null 2>&1; then
  echo ""
  echo "Aún no hay cuentas. Crea la primera (te pedirá la contraseña):"
  echo "  docker compose --env-file .env.docker exec web python manage.py crear_usuario <usuario> --correo <correo> --rol Administrador"
fi
open "http://localhost:$puerto" >/dev/null 2>&1 || true

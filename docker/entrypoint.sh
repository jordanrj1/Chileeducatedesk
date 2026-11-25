#!/bin/sh
# Arranque de FCHE dentro del contenedor. Equivale a iniciar.sh / iniciar.bat:
# espera la base, respalda antes de migrar, carga el territorio oficial, prepara los estáticos y levanta waitress.
set -e

echo "FCHE: esperando la base de datos..."
intentos=0
until python manage.py comprobar_bd >/dev/null 2>&1; do
  intentos=$((intentos + 1))
  if [ "$intentos" -gt 60 ]; then
    echo "FCHE: no se pudo conectar a la base después de 2 minutos. Revisa 'docker compose logs db'."
    exit 1
  fi
  sleep 2
done

if ! python manage.py migrate --check >/dev/null 2>&1; then
  # En la primera instalación no hay nada que respaldar; después, nunca se migra sin respaldo.
  if python manage.py showmigrations --plan 2>/dev/null | grep -q "\[X\]"; then
    echo "FCHE: hay cambios de base de datos pendientes; se respalda antes de aplicarlos..."
    python manage.py respaldar || { echo "FCHE: el respaldo falló; no se aplican cambios."; exit 1; }
  fi
  python manage.py migrate --noinput
fi

python manage.py cargar_territorio --si-falta || echo "FCHE: no se pudo cargar el territorio oficial; el sistema arranca igual."
python manage.py vincular_zonas_proyectos || echo "FCHE: no se pudieron enlazar las zonas de los proyectos; el sistema arranca igual."
python manage.py collectstatic --noinput -v0

echo "FCHE: listo en http://localhost:${PUERTO:-8000}"
exec waitress-serve --listen=0.0.0.0:8000 --threads="${HILOS:-8}" config.wsgi:application

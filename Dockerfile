# Imagen de FCHE: Django + waitress, con pg_dump 17 para los respaldos.
# Se construye y levanta con docker compose (ver docs/DESPLIEGUE_DOCKER.md); no se usa sola.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.produccion

# Cliente de PostgreSQL 17 (el de Debian es más antiguo y pg_dump se niega a respaldar un servidor más nuevo).
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && install -d /usr/share/postgresql-common/pgdg \
 && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
 && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends postgresql-client-17 \
 && apt-get purge -y curl \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Usuario sin privilegios; los datos (documentos, respaldos, registros) viven fuera del código, en /datos.
RUN useradd --create-home --uid 1000 fche \
 && mkdir -p /datos/media /datos/respaldos /datos/logs \
 && chown -R fche:fche /app /datos
USER fche

EXPOSE 8000
ENTRYPOINT ["sh", "docker/entrypoint.sh"]

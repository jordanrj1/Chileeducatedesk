# Chileeducatedesk (FCHE)

Plataforma de gestión de actividades y banco institucional de la Fundación Chile Edúcate.
Contexto del proyecto y reglas de trabajo: [docs/CONTEXTO.md](docs/CONTEXTO.md). Especificaciones por feature: `specs/`.

## Instalación (Mac o Windows)

Requisitos: Python 3.12 (o compatible con Django 5.2 LTS) y PostgreSQL 14 o superior con la extensión `pg_trgm`.

| Paso | Mac / Linux | Windows |
|---|---|---|
| Entorno virtual | `python3 -m venv .venv` | `py -m venv .venv` |
| Dependencias | `.venv/bin/pip install -r requirements.txt` | `.venv\Scripts\pip install -r requirements.txt` |
| Configuración | `cp .env.example .env` y completar | `copy .env.example .env` y completar |
| Base de datos | crear la BD `fche` y ejecutar `CREATE EXTENSION pg_trgm;` | igual |
| Arrancar | `./iniciar.sh` | `iniciar.bat` |

El sistema queda en http://127.0.0.1:8000. Usuarios: se crean con `python manage.py createsuperuser` hasta que exista la gestión de usuarios (F03); luego asignarles el grupo Gestor o Administrador.

## Pruebas
`.venv/bin/python -m pytest -q` (Mac) · `.venv\Scripts\python -m pytest -q` (Windows)

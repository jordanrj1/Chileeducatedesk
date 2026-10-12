# Chileeducatedesk (FCHE)

Plataforma de gestión de actividades y banco institucional de la Fundación Chile Edúcate.
Contexto y reglas de trabajo: [docs/CONTEXTO.md](docs/CONTEXTO.md) · Manual: [docs/manual_de_uso.md](docs/manual_de_uso.md) · Entrega: [docs/entrega.md](docs/entrega.md) · Specs: `specs/`.

## Qué incluye
Personas, organizaciones y lugares reutilizables; solicitudes → proyectos → actividades; agenda versionada y calendario; revisión de compatibilidad antes de confirmar; búsqueda asistida; coordinación (interacciones, reuniones, tareas, invitaciones, colaboraciones); documentos y origen del dato; asistencia, resultados y cierre; historial y auditoría; búsqueda global y exportación a Excel; importación con revisión; finanzas por proyecto; roles Gestor y Administrador.

## Instalación (Mac o Windows)
Requisitos: Python 3.12 (o compatible con Django 5.2 LTS) y PostgreSQL 14 o superior.

| Paso | Mac / Linux | Windows |
|---|---|---|
| Entorno virtual | `python3 -m venv .venv` | `py -m venv .venv` |
| Dependencias | `.venv/bin/pip install -r requirements.txt` | `.venv\Scripts\pip install -r requirements.txt` |
| Configuración | `cp .env.example .env` y completar | `copy .env.example .env` y completar |
| Base de datos | crear la BD `fche` (la extensión `pg_trgm` se crea al migrar) | igual |
| Arrancar | `./iniciar.sh` | `iniciar.bat` |
| Respaldo | `./respaldar.sh` | `respaldar.bat` |

Luego: `python manage.py cargar_territorio comunas.csv` (archivo oficial CUT), `python manage.py crear_usuario …` (Gestor y Administrador) y, para ensayar, `python manage.py cargar_demo --si-estoy-seguro` (datos ficticios).

## Pruebas
`.venv/bin/python -m pytest -q` (Mac) · `.venv\Scripts\python -m pytest -q` (Windows)

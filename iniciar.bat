@echo off
REM Arranca FCHE con waitress. Requiere .venv y .env configurados y PostgreSQL en marcha.
cd /d "%~dp0"
set DJANGO_SETTINGS_MODULE=config.settings.produccion
call .venv\Scripts\activate.bat
python manage.py migrate --noinput
python manage.py collectstatic --noinput
REM Solo este equipo. Para la red de la Fundación [V#5] cambiar 127.0.0.1 por 0.0.0.0.
waitress-serve --listen=127.0.0.1:8000 config.wsgi:application
pause

@echo off
REM Respaldo de base de datos y documentos (Windows).
REM Programar en el Programador de tareas de Windows: acción "Iniciar un programa" -> este archivo, a diario (p. ej. 02:00).
cd /d "%~dp0"
set DJANGO_SETTINGS_MODULE=config.settings.produccion
call .venv\Scripts\activate.bat
python manage.py respaldar %*
if errorlevel 1 (
  echo El respaldo FALLO. Revisa el mensaje anterior.
  exit /b 1
)

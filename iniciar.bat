@echo off
REM Arranca FCHE con waitress. Requiere .venv y .env configurados y PostgreSQL en marcha.
cd /d "%~dp0"
set DJANGO_SETTINGS_MODULE=config.settings.produccion
call .venv\Scripts\activate.bat

REM OP-E3: comprobar la base antes de seguir
python manage.py comprobar_bd
if errorlevel 1 (
  echo.
  echo No se pudo conectar a PostgreSQL.
  echo  1. Abre "Servicios" de Windows y revisa que el servicio postgresql este "En ejecucion".
  echo  2. Revisa DB_HOST, DB_PORT, DB_USER y DB_PASSWORD en el archivo .env.
  echo  3. Mas ayuda: docs\entrega.md, seccion "Si algo falla".
  pause
  exit /b 1
)

REM OP-E7: si hay migraciones pendientes, primero se respalda
python manage.py migrate --check >nul 2>&1
if errorlevel 1 (
  echo Hay cambios de base de datos pendientes: se hace un respaldo antes de aplicarlos...
  python manage.py respaldar
  if errorlevel 1 (
    echo El respaldo fallo: no se aplican cambios. Revisa el mensaje anterior.
    pause
    exit /b 1
  )
  python manage.py migrate --noinput
)
REM Lista oficial de regiones, provincias y comunas: solo la carga si falta alguna comuna. Si falla, el sistema arranca igual.
python manage.py cargar_territorio --si-falta
if errorlevel 1 echo No se pudo cargar la lista oficial del territorio; el sistema arranca igual. Revisa el mensaje anterior.
REM Zona escrita de los proyectos: la enlaza con su comuna o sector si coincide con uno solo (nunca borra el texto).
python manage.py vincular_zonas_proyectos
if errorlevel 1 echo No se pudieron enlazar las zonas de los proyectos; el sistema arranca igual.
python manage.py collectstatic --noinput -v0
REM Solo este equipo. Para la red de la Fundacion [V#5] cambiar 127.0.0.1 por 0.0.0.0.
waitress-serve --listen=127.0.0.1:8000 config.wsgi:application
pause

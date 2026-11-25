@echo off
REM Detiene FCHE (Docker) sin borrar datos. Para volver a usarlo: levantar.bat
cd /d "%~dp0"
docker compose --env-file .env.docker stop
pause

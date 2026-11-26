@echo off
REM Levanta FCHE con Docker en Windows. Guia: docs\DESPLIEGUE_DOCKER.md
REM La primera vez crea .env.docker con claves nuevas; las siguientes solo actualiza y arranca.
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo Falta Docker Desktop. Instalalo desde https://www.docker.com/products/docker-desktop/ y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
  echo Docker Desktop no esta abierto. Abrelo, espera que diga "Engine running" y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)

if not exist .env.docker (
  powershell -NoProfile -Command "$k=[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N'); $p=[guid]::NewGuid().ToString('N'); (Get-Content .env.docker.example) -replace '^SECRET_KEY=.*',('SECRET_KEY='+$k) -replace '^DB_PASSWORD=.*',('DB_PASSWORD='+$p) | Set-Content -Encoding ascii .env.docker"
  echo Se creo .env.docker con claves nuevas. Guarda una copia en un lugar seguro: sin ella no se puede abrir la base.
)

if not exist respaldos mkdir respaldos
docker compose --env-file .env.docker up -d --build
if errorlevel 1 (
  echo No se pudo levantar FCHE. Revisa el mensaje anterior.
  pause
  exit /b 1
)

echo Esperando que FCHE responda (la primera vez tarda unos minutos)...
powershell -NoProfile -Command "for($i=0;$i -lt 120;$i++){try{Invoke-WebRequest -UseBasicParsing http://localhost:8000/login -TimeoutSec 3 | Out-Null; exit 0}catch{Start-Sleep 2}}; exit 1"
if errorlevel 1 (
  echo FCHE no respondio. Revisa: docker compose --env-file .env.docker logs web
  pause
  exit /b 1
)

echo FCHE listo: http://localhost:8000
echo Si es la primera vez, crea la primera cuenta (te pedira la contrasena):
echo   docker compose --env-file .env.docker exec web python manage.py crear_usuario USUARIO --correo CORREO --rol Superadministrador
start "" http://localhost:8000
pause

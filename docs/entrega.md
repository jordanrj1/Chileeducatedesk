# Entrega, instalación y operación (F21)

## Instalación en el equipo de la Fundación (Windows)
1. Instalar **Python 3.12** (marcar «Add to PATH») y **PostgreSQL 14 o superior** (incluye `pg_dump`). El usuario de la base necesita permiso para `CREATE EXTENSION pg_trgm` la primera vez (usar el superusuario `postgres` al migrar).
2. Copiar la carpeta del proyecto (p. ej. `C:\fche`). Crear la base: `createdb fche` y el usuario de aplicación.
3. `py -m venv .venv` → `.venv\Scripts\pip install -r requirements.txt`.
4. Copiar `.env.example` a `.env` y completar: `SECRET_KEY` (larga y aleatoria), `DB_*`, `ALLOWED_HOSTS`, `MEDIA_ROOT` (carpeta **fuera** del código, p. ej. `C:\fche_media`), `RESPALDO_DIR`.
5. `iniciar.bat` (migra, junta estáticos y arranca con `waitress` en `127.0.0.1:8000`).
6. Cargar el territorio con el archivo oficial CUT: `python manage.py cargar_territorio ruta\comunas.csv` (columnas: `region_codigo, region_nombre, provincia_codigo, provincia_nombre, comuna_codigo, comuna_nombre`).
7. Crear los usuarios: `python manage.py crear_usuario claudio --correo ... --rol Gestor` y `python manage.py crear_usuario admin --correo ... --rol Administrador`.
8. Opcional para ensayar: `python manage.py cargar_demo --si-estoy-seguro` (datos **ficticios**; no usar si ya hay datos reales).

En Mac/Linux: `./iniciar.sh`, `./respaldar.sh`.

## Acceso desde otros equipos o celulares [V#5]
Por defecto solo el equipo donde corre (`127.0.0.1`). Para la red de la Fundación: cambiar `--listen` a `0.0.0.0:8000` en `iniciar.bat`, agregar la IP/nombre a `ALLOWED_HOSTS` y a `CSRF_TRUSTED_ORIGINS` (p. ej. `http://192.168.1.10:8000`), y permitir el puerto en el firewall. Si se publica en internet, usar HTTPS y activar las cookies seguras en `config/settings/produccion.py`.

## Respaldos (RNF-10)
- `respaldar.bat` (o `./respaldar.sh`) genera en `RESPALDO_DIR` un `fche_bd_AAAAMMDD_HHMMSS.dump` (pg_dump) y un `fche_documentos_….zip`, y elimina los de más de 30 días.
- Programarlo a diario en el **Programador de tareas de Windows** (acción: iniciar `respaldar.bat`, 02:00).
- Guardar además una copia **fuera del equipo** (disco externo o nube institucional).
- **Restaurar** (procedimiento probado el 12-10-2026 con un respaldo real; coincidieron todas las tablas):
  1. Primero en una base aparte, para revisar sin riesgo: `createdb fche_revision` y `pg_restore --no-owner -d fche_revision archivo.dump`.
  2. Si está bien, detener el sistema y restaurar sobre la base real: `pg_restore --no-owner --clean --if-exists -d fche archivo.dump`.
  3. Descomprimir `fche_documentos_….zip` dentro de `MEDIA_ROOT`.
  4. Iniciar el sistema y revisar `/salud`.

## Antes de entregar (lista de verificación)
- [ ] `python manage.py test`/`pytest` sin fallos.
- [ ] `DEBUG=False`, `SECRET_KEY` propia, `.env` fuera del repositorio.
- [ ] Usuarios creados y permisos revisados en Administración → Roles.
- [ ] Territorio cargado; catálogos revisados con Claudio.
- [ ] Respaldo programado y restauración probada.
- [ ] Recorrido completo con Claudio: persona → proyecto → actividad → participantes → programar → confirmar → realizar → asistencia → resultado → cerrar → historial.
- [ ] Definir quién administra después del 30-11-2026 [V#1] y traspasar credenciales.

## Que el sistema arranque solo (OP-E5)
- **Windows:** Programador de tareas → «Crear tarea» → Desencadenador «Al iniciar el sistema» → Acción «Iniciar un programa»: `C:\fche\iniciar.bat` → marcar «Ejecutar tanto si el usuario inició sesión como si no». PostgreSQL ya arranca solo como servicio de Windows.
- **Mac:** Preferencias del Sistema → General → Ítems de inicio → agregar `iniciar.sh` (o un `launchd` con `RunAtLoad`).
- `iniciar` comprueba la base antes de arrancar y, si hay cambios de base pendientes, **respalda antes de aplicarlos** (OP-E3, OP-E7).

## Mudar el sistema a otro computador (OP-E6)
1. En el equipo antiguo: `respaldar.bat`. Copia la carpeta de respaldos (incluye `fche_config_….env`, la base y los documentos).
2. En el nuevo: instalar Python y PostgreSQL, copiar la carpeta del proyecto y restaurar `.env` desde `fche_config_….env`.
3. Restaurar la base y los documentos con el procedimiento de «Respaldos».
4. `iniciar.bat`, revisar `/salud` e ingresar con una cuenta conocida.

## Protección de los respaldos (SE-E4)
Los respaldos contienen todos los datos personales y la configuración. Guárdalos en un disco **cifrado** (BitLocker en Windows, FileVault en Mac) y nunca en una carpeta compartida.

## Si algo falla
- `/salud` responde `{"estado": "ok"}` cuando la base funciona.
- Los registros de errores están en `logs/fche.log`.
- Si cambió algo de la base, `python manage.py migrate` aplica las migraciones pendientes (siempre respaldar antes).

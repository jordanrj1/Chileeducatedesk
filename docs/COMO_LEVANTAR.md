# Cómo levantar el sistema y crear los usuarios

Pasos para instalar FCHE en el computador de la Fundación (Windows 10 u 11). Todos los comandos se escriben en el **Símbolo del sistema** (`cmd`), dentro de la carpeta del proyecto. **Ninguna contraseña está escrita en el repositorio:** cada una se elige al crear la cuenta.

> Un solo computador: el sistema solo se abre desde el mismo equipo donde corre (`http://127.0.0.1:8000`). No queda expuesto a la red ni a internet.

---

## 1. Instalar los programas (una sola vez)

1. **Python 3.12**, desde python.org. En el instalador, marca **«Add python.exe to PATH»**.
2. **PostgreSQL 17**, el instalador de EDB desde postgresql.org.
   - Anota la contraseña que eliges para el usuario `postgres`.
   - Deja el puerto en 5432.
   - El instalador trae `psql`, `pg_dump` y el servicio de Windows que arranca la base solo.
3. Copia la carpeta del proyecto a `C:\fche`.

## 2. Crear la base de datos (una sola vez)

Abre **«SQL Shell (psql)»** desde el menú Inicio. Entra con el usuario `postgres` y escribe:

```sql
CREATE USER fche WITH PASSWORD 'ESCRIBE-AQUI-UNA-CLAVE';
CREATE DATABASE fche OWNER fche;
\c fche
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
\q
```

- Cambia `ESCRIBE-AQUI-UNA-CLAVE` por una clave tuya. No la guardes en ningún archivo del proyecto; solo va en `.env` (paso 4).
- `pg_trgm` sirve para encontrar nombres parecidos (duplicados). `unaccent` sirve para buscar sin tildes.
- Se crean aquí, con el usuario `postgres`, porque el usuario `fche` no tiene permiso para crearlas.

## 3. Preparar Python (una sola vez)

```bat
cd C:\fche
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

`.venv` es el **entorno virtual**: una copia de Python solo para este proyecto, con sus propias librerías.

## 4. Configurar `.env` (una sola vez)

```bat
copy .env.example .env
notepad .env
```

Completa estas líneas; el resto puede quedar igual:

| Línea | Qué poner |
|---|---|
| `SECRET_KEY=` | Una clave larga y aleatoria. Para generarla: `.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG=False` | Déjalo en `False` |
| `DB_USER=fche` | El usuario del paso 2 |
| `DB_PASSWORD=` | La clave que elegiste en el paso 2 |
| `DB_PORT=5432` | El puerto de PostgreSQL |
| `MEDIA_ROOT=C:\fche_media` | Carpeta donde se guardan los archivos subidos. Va **fuera** de la carpeta del código. |
| `RESPALDO_DIR=C:\fche_respaldos` | Carpeta de respaldos |
| `PG_DUMP=C:\Program Files\PostgreSQL\17\bin\pg_dump.exe` | Ruta de `pg_dump`. Hace falta para los respaldos. |
| `CONTACTO_ADMINISTRADOR=` | Nombre o teléfono que verá quien tenga la cuenta desactivada |

`.env` **nunca** se sube al repositorio: `.gitignore` ya lo excluye.

## 5. Crear las tablas (la primera vez)

```bat
set DJANGO_SETTINGS_MODULE=config.settings.produccion
.venv\Scripts\python manage.py comprobar_bd
.venv\Scripts\python manage.py migrate
```

- `comprobar_bd` confirma que el sistema llega a la base.
- `migrate` crea todas las tablas, carga los catálogos iniciales (tipos, estados, roles…) y crea los dos roles, **Gestor** y **Administrador**, con sus permisos.

> Por qué a mano la primera vez: `iniciar.bat` hace un respaldo **antes** de aplicar cambios en la base. Si `PG_DUMP` no está bien configurado, el respaldo falla y no aplica nada. Hacer el primer `migrate` a mano evita ese tropiezo.

## 6. Cargar el territorio oficial

```bat
.venv\Scripts\python manage.py cargar_territorio
```

- Sin argumentos usa la lista oficial que ya trae el sistema: `apps/territorio/datos/cut_chile.csv` (16 regiones, 56 provincias y 346 comunas; fuentes en `apps/territorio/datos/LEEME.md`).
- `iniciar.bat` lo ejecuta solo con `--si-falta`: si ya están todas las comunas, no hace nada.
- `--simular` muestra lo que cambiaría, sin guardar nada. También acepta otro CSV con las columnas `region_codigo, region_nombre, provincia_codigo, provincia_nombre, comuna_codigo, comuna_nombre`.
- Antes de escribir revisa todo el archivo; si hay un error, no carga nada. Se puede ejecutar de nuevo sin duplicar ni borrar nada (la «Región Demo» sigue igual).
- Los **sectores** (villas, poblaciones, etapas) no vienen en ese archivo: los crea Claudio desde el sistema.

## 7. Crear las cuentas

Solo existen dos roles: **Administrador** (el programador) y **Gestor** (Claudio). Las personas registradas (estudiantes, voluntarios, vecinos) **no tienen cuenta**.

**Primero el Administrador:**
```bat
.venv\Scripts\python manage.py crear_usuario admin --correo admin@fundacion.cl --rol Administrador --nombres "Nombre" --apellidos "Apellido"
```

**Luego el Gestor:**
```bat
.venv\Scripts\python manage.py crear_usuario claudio --correo claudio@fundacion.cl --rol Gestor --nombres "Claudio" --apellidos "Apellido"
```

- Usa los correos reales de cada uno; los de arriba son de ejemplo.
- **Dónde se elige la contraseña:** el comando la **pide por teclado** dos veces y no la muestra mientras se escribe.
- Debe tener al menos 10 caracteres, no ser una contraseña común y no ser solo números.
- **No uses** la opción `--password`: la contraseña quedaría en el historial de comandos.

**Después, desde la pantalla:**
- Cada uno puede cambiar su contraseña en **Mi cuenta → Cambiar contraseña**.
- Si alguien la olvida, el Administrador la restablece en **Administración → Usuarios → la cuenta → Restablecer contraseña**. No hay recuperación por correo [V#9].
- Las cuentas nuevas se crean en **Administración → Usuarios → «+ Nuevo usuario»** y **siempre para una persona ya registrada** en Personas.
- Para ligar la cuenta de Claudio a su ficha, registra a Claudio en Personas. Luego, como Administrador, edita su cuenta y elige esa persona.

## 8. Datos de demostración (opcional, solo para ensayar)

```bat
.venv\Scripts\python manage.py cargar_demo --si-estoy-seguro
```

- Solo funciona con la base **vacía**: si ya hay personas o proyectos, se niega.
- **No crea usuarios ni contraseñas.**
- Todo lo que crea es ficticio:
  - territorio: «Región Demo», «Provincia Demo» y «Comuna Demo», sin sectores;
  - organizaciones: «Universidad Demo», con la carrera «Trabajo Social Demo», y «Junta de Vecinos Demo»;
  - 9 personas: «Coordinadora Demo», «Voluntario1» a «Voluntario5 Demo» y «Vecina1» a «Vecina3 Demo»;
  - el lugar «Sede Demo», con capacidad 25;
  - el «Proyecto Demo de alfabetización» con dos actividades: «Taller Demo 1», programado en 7 días con 3 voluntarios y 3 vecinas, y «Taller Demo 2 (sin programar)»;
  - la comunidad «Vecinos de la Villa Demo» y una sesión con minuta.
- **No lo uses en el computador real** si ya hay datos de verdad.

## 9. Arrancar y usar

- Doble clic en **`iniciar.bat`**. Hace esto:
  1. comprueba la base;
  2. si hay cambios pendientes, respalda y luego los aplica;
  3. prepara los estilos;
  4. arranca el servidor `waitress`.
- Abre el navegador en **http://127.0.0.1:8000** e ingresa con el correo (o el usuario) y la contraseña.
- La ventana negra debe quedar abierta mientras se usa el sistema. Para detenerlo, ciérrala.
- `/salud` responde `{"estado": "ok"}` si la base funciona.

## 10. Respaldos diarios

- `respaldar.bat` guarda en `RESPALDO_DIR` una copia de la base (`fche_bd_….dump`) y otra de los documentos (`fche_documentos_….zip`).
- **Hay que programarlo** en el **Programador de tareas** de Windows: «Crear tarea básica» → diaria a las 02:00 → «Iniciar un programa» → `C:\fche\respaldar.bat`.
- Cómo restaurar: `docs/entrega.md`, sección Respaldos.
- Los respaldos tienen todos los datos personales: guárdalos en un disco cifrado (BitLocker).

## 11. Que arranque solo al encender el computador (opcional)

Programador de tareas → «Crear tarea» → desencadenador **«Al iniciar el sistema»** → acción `C:\fche\iniciar.bat` → marcar «Ejecutar tanto si el usuario inició sesión como si no». PostgreSQL ya arranca solo como servicio.

## 12. Si algo falla

| Síntoma | Qué revisar |
|---|---|
| «No se pudo conectar a PostgreSQL» | En «Servicios» de Windows, que `postgresql-x64-17` esté «En ejecución». Revisa `DB_*` en `.env`. |
| «No se encontró pg_dump» | La línea `PG_DUMP=` de `.env` |
| Error al ingresar | Tras 5 intentos fallidos la cuenta se bloquea 15 minutos (`INTENTOS_MAXIMOS`, `BLOQUEO_MINUTOS`). |
| Cualquier otro error | El archivo `logs\fche.log` |

---

## En la Mac de desarrollo (como está hoy)

- La base es un PostgreSQL propio en el puerto **5433**; no es el de Windows.
- Se arranca con `./iniciar.sh`, que también enciende esa base si estaba apagada.
- Las pruebas se corren con `.venv/bin/python -m pytest -q`.
- Ya existen dos cuentas de desarrollo, **`gestor`** y **`admin`**, sobre los datos de demostración. Su contraseña **no está en el repositorio**. Para cambiarla:

```bash
.venv/bin/python manage.py changepassword gestor
.venv/bin/python manage.py changepassword admin
```

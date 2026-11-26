# Instalar y usar FCHE con Docker (Mac y Windows)

Esta guía es para quien instala el sistema en un computador nuevo: Claudio, en el equipo de la Fundación, o la persona técnica que lo apoye. Con Docker no hay que instalar Python ni PostgreSQL. Todo viene en dos contenedores: la aplicación y su base de datos.

---

## 1. Qué instalar (una sola vez)

| Programa | Para qué | Dónde |
|---|---|---|
| **Docker Desktop** | Corre la aplicación y la base de datos | https://www.docker.com/products/docker-desktop/ |
| **Git** o **GitHub Desktop** | Descarga el código y sus actualizaciones | https://git-scm.com/ · https://desktop.github.com/ |
| Navegador | Usar el sistema | Chrome, Edge, Firefox o Safari |

**Windows:** Docker Desktop pide activar **WSL 2** durante la instalación; acepta y reinicia si lo solicita.

**Requisitos mínimos:** 8 GB de RAM y 10 GB de disco libre.

---

## 2. Primera instalación

1. **Descarga el código.** El repositorio es privado: pide acceso al dueño de la cuenta de GitHub.
   ```
   git clone git@github.com:jordanrj1/Chileeducatedesk.git
   cd Chileeducatedesk
   ```
   Con GitHub Desktop: *File → Clone repository* y elige la carpeta.
2. **Abre Docker Desktop** y espera a que diga **«Engine running»**.
3. **Levanta el sistema:**
   - **Mac:** abre la Terminal en la carpeta del proyecto y ejecuta `./levantar.sh`.
   - **Windows:** haz doble clic en `levantar.bat`.

   La primera vez tarda entre 3 y 10 minutos, porque descarga las imágenes y prepara la base. El script:
   - crea `.env.docker` con claves nuevas al azar;
   - arranca la base y la aplicación;
   - aplica la estructura de datos y carga las 346 comunas oficiales;
   - abre el navegador en http://localhost:8000.
4. **Guarda una copia de `.env.docker`** en un lugar seguro, como un pendrive o un gestor de contraseñas. Sin ese archivo no se puede abrir la base de datos.
5. **Crea la primera cuenta, de Superadministrador** (solo la primera vez; te pedirá la contraseña):
   ```
   docker compose --env-file .env.docker exec web python manage.py crear_usuario admin --correo admin@ejemplo.cl --rol Superadministrador
   ```
   Desde la pantalla (Administración → Usuarios) el Superadministrador crea las demás cuentas, como la de Claudio con rol Gestor, siempre para una persona ya registrada.

---

## 3. Uso diario

| Quiero… | Mac | Windows |
|---|---|---|
| Abrir el sistema | http://localhost:8000 | http://localhost:8000 |
| Encenderlo (si se detuvo) | `./levantar.sh` | doble clic en `levantar.bat` |
| Detenerlo sin borrar nada | `./detener.sh` | doble clic en `detener.bat` |

El sistema arranca solo cuando se abre Docker Desktop. Para que también arranque al encender el equipo, activa en Docker Desktop *Settings → General → «Start Docker Desktop when you sign in»*.

---

## 4. Respaldos

Antes de cada actualización que cambia la base, el sistema se respalda solo. Para un respaldo manual:
```
docker compose --env-file .env.docker exec web python manage.py respaldar
```
Los respaldos quedan en la carpeta `respaldos/` del proyecto: el `.dump` es la base y el `.zip`, los documentos subidos. Cópialos periódicamente a otro disco o a la nube institucional. **No los subas a GitHub.**

**Restaurar un respaldo** (con el sistema encendido; reemplaza los datos actuales):
```
docker compose --env-file .env.docker exec -T db pg_restore -U fche -d fche --clean --if-exists < respaldos/fche_bd_AAAAMMDD_HHMMSS.dump
```

---

## 5. Actualizar a una versión nueva

1. `git pull` (o *Fetch / Pull* en GitHub Desktop).
2. Ejecuta de nuevo `levantar.sh` o `levantar.bat`. Reconstruye la aplicación, **respalda la base** y aplica los cambios.

---

## 6. Acceso desde otros equipos (opcional)

Por privacidad, el sistema responde solo en el mismo computador.

- **Red local de la oficina:**
  1. En `.env.docker`, cambia `ACCESO=0.0.0.0`.
  2. Agrega la IP del equipo, por ejemplo `192.168.1.20`, a `ALLOWED_HOSTS` y a `CSRF_TRUSTED_ORIGINS` (`http://192.168.1.20:8000`).
  3. Vuelve a levantar el sistema.
- **Desde fuera de la oficina:** usa **Tailscale** (https://tailscale.com, gratis para uso personal).
  - Crea una red privada cifrada entre los equipos autorizados, sin exponer el sistema a internet.
  - Instálalo en el servidor y en el equipo que se conecta, e inicia sesión con la misma cuenta.
  - Agrega el nombre de Tailscale del servidor a `ALLOWED_HOSTS` y a `CSRF_TRUSTED_ORIGINS`.

---

## 7. ¿Y publicarlo en internet gratis?

FCHE guarda datos personales, incluidos datos de menores y datos sensibles. Con la Ley 21.719, vigente desde el 01-12-2026, la Fundación responde por dónde y cómo se guardan. Por eso:

| Opción | Sirve | Motivo |
|---|---|---|
| Docker en el PC de la Fundación + Tailscale | ✅ Recomendado | Los datos no salen de la Fundación; gratis; acceso cifrado. |
| Servidor privado pequeño (VPS) con Docker y HTTPS | ✅ Si se necesita web | Cerca de US$5 al mes; control total; requiere a alguien técnico para mantenerlo. |
| Vercel | ❌ | Está pensado para páginas y funciones cortas. No mantiene una base PostgreSQL ni archivos subidos. |
| Render (plan gratis) | ❌ | La base gratuita se borra a los 30 días y el servicio se apaga si no se usa. |
| Railway o Fly.io (gratis) | ⚠️ | Crédito limitado o tarjeta obligatoria. Sirven para una demostración, no para datos reales. |

**Siempre:** repositorio de GitHub **privado**, `.env.docker` fuera de GitHub y respaldos en un lugar seguro.

---

## 8. Si algo falla

| Síntoma | Qué hacer |
|---|---|
| «Falta Docker Desktop» | Instálalo (paso 1) y ábrelo. |
| «Docker Desktop no está abierto» | Ábrelo y espera «Engine running». |
| La página no carga | `docker compose --env-file .env.docker logs web` muestra el motivo. |
| «Falta DB_PASSWORD» | Se ejecutó `docker compose` sin `--env-file .env.docker`; usa los scripts `levantar`. |
| El puerto 8000 está ocupado | En `.env.docker` cambia `PUERTO=8080`, vuelve a levantar y entra a http://localhost:8080. |
| Se perdió `.env.docker` | Restaura tu copia. Sin ella no se puede abrir la base: hay que instalar de cero y restaurar un respaldo. |

**Ver el estado:** `docker compose --env-file .env.docker ps`.

**Borrar todo y empezar de cero:** `docker compose --env-file .env.docker down -v`. **Este comando elimina la base y los documentos**, así que respalda antes.

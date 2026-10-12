# F01 — Base técnica, navegación e instalación (spec)

Fuentes: docs/CONTEXTO.md §3, §5, §6, §9, §10; RF-01, RNF-01, RNF-05, RNF-06, RNF-09, RNF-14.

## Qué
Esqueleto ejecutable del sistema, sin lógica de negocio:
- Proyecto Django con ajustes `base` / `local` / `produccion` y variables en `.env`. [O/P]
- Apps vacías: nucleo, cuentas, territorio, personas, organizaciones, lugares, solicitudes, actividades, documentos.
- Layout: menú lateral, encabezado con cierre de sesión, breadcrumb y buscador global visible (sin resultados aún).
- Ingreso y cierre de sesión. Dos grupos: **Gestor** y **Administrador**. [O]
- Estáticos locales (Bootstrap, HTMX), sin CDN. FullCalendar se agrega en F10.
- Pantallas 403 y 404 propias. Endpoint `/salud` que confirma que la base responde.
- `iniciar.bat` y `.env.example`.

## Por qué
Todas las features siguientes cuelgan de esta base; debe funcionar sin internet y poder mudarse a un servidor web sin reescribir (docs/CONTEXTO.md §5).

## Criterios de aceptación
1. Con `.env` válido y PostgreSQL arriba, `iniciar.bat` levanta el sistema con `waitress`.
2. Usuario anónimo en cualquier ruta salvo `/login` y `/salud` es enviado a `/login`.
3. Ingreso correcto lleva a `/dashboard` (vacío por ahora). Cierre de sesión visible.
4. Usuario autenticado sin grupo/permiso recibe pantalla 403 propia; ruta inexistente, 404 propia.
5. `/salud` responde 200 con la base viva y 503 si no responde; no expone datos.
6. Ningún recurso se carga desde internet.
7. Pruebas: arranque, ingreso, 403 sin permiso, `/salud`.

## Fuera de F01
Usuarios y gestión de roles (F03), recuperación de contraseña [V#9], expiración por inactividad (decisión [P], se deja el ajuste listo, valor a confirmar), módulos de negocio.

## Decisiones abiertas
- [V#5] Acceso desde celular/red: define `ALLOWED_HOSTS` y a qué interfaz escucha waitress. Por defecto solo `127.0.0.1`.
- Versión de Python/Django: el sistema tiene Python 3.9; se necesita instalar una versión compatible con el Django LTS vigente.

# F29 — Superadministrador

**Fuente:** decisión del usuario del 25-11-2026 [D-u]. Cambia la decisión cerrada de roles de `docs/CONTEXTO.md` §3 y §9: hasta ahora eran Gestor y Administrador; desde ahora son **Gestor** y **Superadministrador**.

## 1. Roles
| Rol | Para quién | Qué puede |
|---|---|---|
| **Gestor** | Claudio, la operación diaria | Todo lo operativo (personas, organizaciones, lugares, comunidades, solicitudes, proyectos, actividades, asistencia, gastos, documentos, cargas, exportar) y **agregar o editar** valores de catálogos. No puede desactivar catálogos, administrar cuentas ni roles, ver la auditoría, reabrir actividades ni unir fichas. |
| **Superadministrador** | La persona de mantenimiento o programación | **Todos los permisos del sistema**, parametrizados: cuentas y roles (crear, editar, desactivar, restablecer contraseña), estructura de catálogos (agregar, editar, desactivar y unir valores), auditoría, respaldos, datos sensibles, exportaciones, reabrir actividades, unir fichas y la pantalla de permisos por rol. |

- **El Superadministrador reemplaza al Administrador.**
  - Una migración de datos renombra el grupo «Administrador» a «Superadministrador», le asigna todos los permisos y conserva a sus usuarios.
  - El código y las pantallas dejan de mencionar «Administrador».
- **Todos los permisos:** también los que se agreguen en el futuro. Al migrar o al arrancar, `asegurar_permisos_superadmin()` le asigna cada permiso nuevo.
- **Nunca se borra nada con historia,** ni siquiera con acceso total: se desactiva, se anula o se revoca (`docs/CONTEXTO.md` §3).

## 2. Creación y protección
- La primera cuenta de Superadministrador se crea **solo por consola**: `crear_usuario <usuario> --correo … --rol Superadministrador`.
- Desde la pantalla, un Superadministrador puede crear otras cuentas, de Gestor o de Superadministrador, siempre para una persona ya registrada.
- **Siempre debe quedar al menos un Superadministrador activo.** No se puede desactivar ni quitar el rol al último.
- Cada acción sobre cuentas, roles, catálogos y permisos queda en la auditoría, con usuario y fecha.

## 3. Pantallas
- **Administración** (menú «Configuración»), solo para el Superadministrador:
  - Usuarios;
  - Roles y permisos: matriz por módulo y acción, con «Restablecer permisos iniciales»;
  - Catálogos, con desactivar y unir;
  - Auditoría;
  - Respaldos: último respaldo y botón «Respaldar ahora».
- **Gestor:** ve Catálogos, donde puede agregar y editar, pero no ve Usuarios, Roles, Auditoría ni Respaldos.

## 4. Pruebas
Quedan dentro de la campaña de 200 pruebas, área **FP-RP** (`docs/pruebas/PLAN_PRUEBAS.md`):
- el Gestor recibe 403 en cada pantalla de Superadministrador;
- el Superadministrador puede todo;
- el último Superadministrador no se puede desactivar;
- los permisos nuevos se asignan solos;
- la migración de Administrador a Superadministrador conserva a los usuarios.

## Criterios
- Migración de datos reversible: vuelve a renombrar el grupo.
- Se actualizan `docs/CONTEXTO.md` §3 y §9, el manual de uso y `docs/DESPLIEGUE_DOCKER.md`, que debe pedir `--rol Superadministrador`.

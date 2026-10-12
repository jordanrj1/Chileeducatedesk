# F03 — Usuarios, roles y permisos

Fuente: tablero «Metodología Kanban Chile educate», tarjeta F03; docs/oficiales.

## Qué y por qué
El Administrador define quién entra y qué puede hacer; el sistema bloquea acciones no autorizadas aunque se acceda por URL directa.

## Criterios de aceptación (implementados)
- Cada usuario tiene un rol (Gestor/Administrador).
- Administración → Usuarios: crear, editar, cambiar rol, activar/desactivar, restablecer contraseña (solo Administrador [V#9]).
- Administración → Roles: configurar permisos por acción (ver, crear, editar, exportar…); no existe «eliminar».
- 403 propio en el servidor para todo lo no permitido.
- Persona ≠ cuenta (1 a 0..1): `PerfilCuenta`. Desde la pantalla, la persona es obligatoria (US-01); lista con último ingreso.
- Cuenta desactivada: mensaje claro y a quién consultar, solo si la contraseña es correcta (AC-02).

## Estado
Implementada y probada. Pendiente: validación con el usuario final (F20).

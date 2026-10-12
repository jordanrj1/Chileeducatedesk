# F02 — Ingreso y sesión de usuarios

Fuente: tablero «Metodología Kanban Chile educate», tarjeta F02; docs/oficiales.

## Qué y por qué
Quien está autorizado ingresa y el resto no ve nada. La cuenta se reserva para quien opera; las personas del banco no tienen cuenta (tarjeta F02).

## Criterios de aceptación (implementados)
- Usuario válido entra (usuario o correo).
- Datos incorrectos: «No fue posible iniciar sesión. Revisa tus datos.»
- Cuenta desactivada no ingresa (mismo mensaje, sin revelar cuál cuenta existe).
- Pantallas privadas redirigen al login sin sesión.
- Cerrar sesión; expiración por inactividad (60 min [P]).

## Estado
Implementada y probada. Pendiente: validación con el usuario final (F20).

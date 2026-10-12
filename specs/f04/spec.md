# F04 — Banco de personas

Fuente: tablero «Metodología Kanban Chile educate», tarjeta F04; docs/oficiales.

## Qué y por qué
Registrar a cada persona una sola vez y enriquecer su ficha con el tiempo (tarjeta F04).

## Criterios de aceptación (implementados)
- Persona sin cuenta; solo el nombre es obligatorio (ficha rápida).
- Búsqueda por nombre/RUT y detección de duplicados antes de crear (RUT, correo, teléfono, nombre parecido con pg_trgm); nunca fusiona sola.
- RUT módulo 11, único si existe; teléfonos normalizados a +56.
- Contactos, direcciones, formación, experiencia, disponibilidad, cargos, contacto de emergencia y verificaciones (sensibles: permiso `ver_sensibles`).
- Historial, trayectoria y origen del dato.

## Estado
Implementada y probada. Pendiente: validación con el usuario final (F20).

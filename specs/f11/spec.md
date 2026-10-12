# F11 — Compatibilidad antes de confirmar

Fuente: tablero «Metodología Kanban Chile educate», tarjeta F11; docs/oficiales.

## Qué y por qué
Detectar problemas antes de confirmar algo que no se podrá cumplir.

## Criterios de aceptación (implementados)
- Faltantes (responsable, fecha/hora, lugar o virtual) bloquean.
- Críticos: capacidad excedida, lugar ocupado/desactivado; impiden confirmar. Opción `CONFIRMAR_CON_CONFLICTO_CRITICO` (apagada) permite confirmar con motivo [V#3].
- Advertencias: persona con otra actividad, fuera de la disponibilidad declarada, fecha pasada, sin participantes; se aceptan explícitamente.
- Cada problema se explica con el motivo.

## Estado
Implementada y probada. Pendiente: validación con el usuario final (F20).

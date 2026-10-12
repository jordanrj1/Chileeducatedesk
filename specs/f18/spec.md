# F18 — Importar información histórica

Fuente: tablero «Metodología Kanban Chile educate», tarjeta F18; docs/oficiales.

## Qué y por qué
Aprovechar lo que la Fundación ya tiene, sin cargar datos sin revisar.

## Criterios de aceptación (implementados)
- Archivo (CSV, TXT, XLSX) o texto pegado → vista previa (nuevos, existentes, duplicados, errores) → corrección → confirmación.
- Nada se guarda antes de confirmar; los pendientes bloquean la confirmación.
- Teléfonos leídos como texto y normalizados; nombres «Nombre Apellido» y «Apellido, Nombre».
- Origen registrado en cada dato; la planilla original queda como evidencia restringida; el lote es reversible.
- Tipos: listado de actividad, personas, organizaciones, lugares. Los PDF/Word históricos siguen siendo evidencia, no tablas.

## Estado
Implementada y probada. Pendiente: validación con el usuario final (F20).

# Preguntas abiertas (estado al 12-10-2026)

Lo construido deja cada punto detrás de una opción fácil de cambiar. Nada se implementó en silencio.

## Para Claudio / Manuel
| # | Tema | Cómo quedó hoy | Dónde cambiarlo |
|---|---|---|---|
| 1 | Quién administra después del 30-11 | Hay un rol Administrador; falta nombrar a la persona | `crear_usuario`, docs/entrega.md |
| 2 | Menores de edad (datos, autorización del apoderado, plazo) | No hay campos especiales; los datos sensibles van tras `ver_sensibles` | Persona (F04) |
| 3 | Confirmar con incompatibilidad crítica | **No** se permite. Con `CONFIRMAR_CON_CONFLICTO_CRITICO=True` se permite con motivo, y queda en auditoría | `.env` |
| 4 | Reabrir una actividad finalizada (realizada) | Solo con el permiso `reabrir_actividad` (nadie lo tiene por defecto); vuelve a «confirmada» | Administración → Roles |
| 5 | Acceso desde celular/red | Solo el equipo local (`127.0.0.1`) | docs/entrega.md |
| 6 | Notificaciones internas o por correo | No hay; el dashboard muestra lo pendiente | — |
| 7 | Proyecto o campaña | Agrupador opcional con ficha; ninguna actividad lo exige | — |
| 8 | Alcance del matching | Resuelto por el tablero (F16) | — |
| 9 | Recuperar contraseña | La restablece el Administrador | Administración → Usuarios |
| 10 | Documentos que emite la Fundación y caducidad de verificaciones | Se registra tipo, folio, emisor y fecha de emisión; verificaciones con «vigente hasta» | Documentos / Persona |
| 11 | ¿Quién ve Finanzas? | Solo Gestor; el Administrador puede recibir el permiso | Administración → Roles |
| 12 | Estado «interesado» al importar un listado | Se usa «interesado» [P] | `importaciones/procesar.py` |
| 13 | ¿Cuándo se habilita la segunda fase? | Oculta (`SEGUNDA_FASE=False`) | `.env` |
| 14 | Series de actividades (AG-07) | Cada repetición es una actividad dentro de la original [P] | — |
| 15 | ¿A quién consultar si una cuenta está desactivada? | Configurable | `CONTACTO_ADMINISTRADOR` en `.env` |

## Para el equipo de desarrollo
- Falta el **Excel de requerimientos con las filas en amarillo** y el **archivo oficial CUT** de comunas.
- `iniciar.bat`, `respaldar.bat` y la instalación en Windows no se pudieron probar en el equipo de desarrollo (Mac).
- La validación con Claudio (F20) y la prueba real de restauración de un respaldo (F21) están pendientes.
- Extensiones menores a la sección 7 de docs/CONTEXTO.md: `Interaccion.accion_cumplida`, `Actividad.motivo_estado`, campos de cierre de `Actividad`, `ActividadTerritorio.vigente`.

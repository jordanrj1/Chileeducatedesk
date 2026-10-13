# Estado de los escenarios hipotéticos

Cruce del catálogo «FCHE — Escenarios hipotéticos» con el sistema al 12-10-2026. Las pruebas automáticas llevan el ID del escenario en su nombre (`apps/nucleo/test_escenarios_catalogo.py`).

✅ resuelto y probado · 🟡 resuelto en parte (se explica) · [V] depende de una decisión (ver `docs/cuestionario_manuel.md`) · ⬜ no hecho

| Tema | ✅ Resueltos | 🟡 En parte | [V] Por decidir | ⬜ No hechos |
|---|---|---|---|---|
| Acceso (AC) | E1 bloqueo · E2, E3 borrador · E4 · E5 · E7 · E8 | — | E6 emergencia sin Administrador · E9 equipos permitidos | — |
| Personas (PE) | E1 comparación · E2 nota · E3 · E4 documento extranjero · E5 · E8 sin tildes · E10 fallecida · E12 · E13 · E14 fusión · E15 consentimiento (F22: registro, revocación y avisos) | E9 mayoría de edad: F22 calcula la edad y avisa si falta apoderado o su autorización; qué datos conservar y por cuánto sigue [V#2] | E6 RUT con dígito dudoso (hoy se rechaza) · E11 eliminar datos | E7 buscar por apellido anterior (el historial lo guarda, la búsqueda no lo usa) |
| Organizaciones (OR) | E1 fusión · E3 · E5 · E6 cerrar autoridades · E7 · E8 · E9 · E10 | E2 el nombre anterior queda en el historial, no se busca | E4 sedes | — |
| Lugares (LU) | E1 · E2 · E3 · E6 · E8 enlace · E9 · E10 · E11 | — | E4 domicilio particular · E5 visibilidad de direcciones · E7 itinerante (sesiones, 2ª fase) | — |
| Solicitudes (SO) | E1 repetida · E4 reabrir · E5 adjuntos · E6 antigüedad · E7 | — | E2 una solicitud, varias actividades (hoy: vía proyecto) · E3 actividad sin solicitud (hoy: se permite) | — |
| Interacciones (IN) | E1 sin respuesta · E3 · E4 movida · E6 · E8 · E9 | E2 la respuesta tiene fecha, no se liga a la versión de agenda | E7 envío masivo de cartas | E5 aviso de «cargo cerrado» al contactar |
| Actividades (AT) | E1 duplicar · E4 · E5 · E6 reasignar · E7 · E8 · E9 · E11 · E13 · E14 · E15 · E16 | E12 en realizada solo «persona que llegó» | E2 dividir · E3 fusionar · E10 roles que ocupan cupo (ajuste listo) | — |
| Agenda (AG) | E1 · E2 · E3 · E4 · E7 · E8 · E9 · E10 · E11 · E13 · E14 · E15 | — | E2 advertir en vez de bloquear (ajuste [V#3]) · E6 varios días · E12 corregir fecha de una realizada | E5 cruzar la medianoche |
| Compatibilidad (VA) | E1 · E2 · E3 · E4 · E6 · E7 · E8 · E9 | — | E5 verificación vencida con menores | — |
| Documentos (DO) | E1 · E2 · E3 repetido · E4 · E5 · E6 versiones · E7 · E8 · E11 · E12 · E13 | E9 se archiva con motivo; borrar el archivo es decisión | E10 imágenes de menores | — |
| Asistencia (RE) | E1 · E3 tardía · E5 · E6 · E8 · E9 · E2 asistentes sin identificar (F22: conteo agregado por sesión, por edad y género) | E4 asistencia sí; otros datos tras finalizar [V] · E7 se escribe «Sin registro» en el resultado | — | — |
| Historial (HI) | E1 · E2 quitar por error · E4 · E6 · E7 | E3 varios contactos con vigencia; la fuente es por ficha · E5 se muestran los últimos 50 cambios | — | — |
| Búsqueda (BU) | E1 · E2 · E3 · E4 · E5 · E7 | — | E6 columnas sensibles en exportaciones | — |
| Cargas (IG) | E1 mapeo · E2 · E3 · E4 · E5 · E7 · E8 · E9 · E10 · E11 · E12 · E13 · E14 | — | — | E6 no aplica: las cargas no traen fechas |
| Interfaz (UI) | E1 · E2 · E3 · E4 · E5 · E6 · E7 · E8 · E9 · E10 · E12 · E13 · E14 · E15 | — | E11 acciones masivas | — |
| Seguridad (SE) | E1 · E3 aviso en exportaciones · E5 · E7 · E2 retiro de consentimiento (F22: se revoca con fecha, no se borra) | E4 guía de disco cifrado · E8 una cuenta por persona; cambio periódico es política | E6 menores en exportaciones · E9, E10 inhabilidades | — |
| Operación (OP) | E1 · E2 disco · E3 · E4 respaldo atrasado · E6 · E7 · E8 | E5 guía de arranque automático | — | E9 hora del equipo |
| Continuidad (CO) | E2 · E4 unir valores · E5 ayuda · E6 | — | E1 reemplazo de Claudio · E3 traspaso del Administrador | — |
| Caducidad (CD) | E1 · E2 · E3 · E4 · E5 · E6 | — | — | — |

## Botones según el estado (sección 3 del catálogo)
Aplicado, con dos diferencias deliberadas:
- Una actividad **pendiente** no tiene «Reprogramar» porque aún no hay agenda; usa «Programar».
- En una actividad **realizada** se corrigen asistencia y resultado (queda registrado), se agrega solo la «persona que llegó» y no se editan los demás datos sin «Reabrir» [V].

## Recorridos completos (R1–R8)
Cubiertos por pruebas automáticas en sus partes de sistema: R1 (jornada con talleres, cambio de lugar, más asistentes que inscritos), R2 (serie semanal, cancelar una sesión), R3 (listado de 40 con duplicados, sin RUT, carreras inexistentes, doble carga y reversión), R4 (virtual con enlace y reprogramación del mismo día), R5 (solicitud sin contacto y repetida), R6 (lugar de otra organización, capacidad y roles), R7 (cambio de directorio y certificado vencido), R8 (respaldo y restauración probados). Falta recorrerlos **con Claudio** en el navegador.

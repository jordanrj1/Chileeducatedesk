# Plan de pruebas funcionales de FCHE

**Decisión del 25-11-2026:** se reemplazan las 888 pruebas automáticas anteriores por una campaña de **200 pruebas funcionales documentadas**. Las anteriores siguen recuperables desde la historia de git. Las pruebas corren sobre una base limpia, con respaldo previo, y usan solo datos ficticios.

## 1. Objetivo
1. Comprobar que cada proceso funciona de punta a punta como lo usaría el Gestor, incluso alguien que entra por primera vez.
2. Buscar errores a propósito con datos extremos, entradas maliciosas, permisos insuficientes y concurrencia.
3. Medir el rendimiento y la carga: tiempo y consultas por página, con 10.000 personas.
4. Dejar evidencia de cada prueba: propósito, condición previa, método, código, resultado esperado y resultado obtenido.

## 2. Entorno controlado
| Elemento | Definición |
|---|---|
| Base de datos | PostgreSQL 17. Cada ejecución crea su propia base de pruebas (`TEST_DB_NAME`) y la destruye al terminar. La base de desarrollo se limpia una vez, con respaldo, y queda con datos de demostración. |
| Datos | Ficticios y válidos: RUT con módulo 11, teléfonos +56 9, correos `@ejemplo.invalid`. Hay tres volúmenes: **pequeño** (lo mínimo por prueba), **mediano** (500 personas) y **grande** (10.000 personas, 300 organizaciones, 1.000 actividades). |
| Herramientas | pytest y pytest-django (ya permitidas). El cliente HTTP de Django ejecuta la aplicación completa: URL, permisos, formularios y plantillas. `CaptureQueriesContext` cuenta consultas, `EXPLAIN` revisa planes y `time.perf_counter` mide tiempos. |
| Supervisión | Ninguna: todo corre sin intervención con `.venv/bin/python -m pytest pruebas/`. |

## 3. Cómo se documenta cada prueba
Cada prueba lleva el decorador `@caso(...)` con:
- `id`: `FP-<área>-NNN`;
- `area`;
- `proposito`: para qué existe;
- `precondicion`: qué debe existir antes, por ejemplo «persona creada»;
- `metodo`: funcional, negativo, borde, seguridad, rendimiento, carga o base de datos;
- `esperado`.

Al terminar, el complemento `pruebas/conftest.py` genera `docs/pruebas/REPORTE.md` y `REPORTE.xlsx` con una fila por caso. La fila muestra los campos anteriores, el resultado obtenido (pasó, falló u omitido), la duración, las consultas a la base y la ubicación del código.

## 4. Áreas (200 casos)
| Área | Prefijo | Casos | Qué cubre |
|---|---|---|---|
| Usuario nuevo e ingreso | FP-US | 15 | Ingreso, bloqueo por intentos, sesión vencida, «Atrás», 403/404/429, primer recorrido sin ayuda, mensajes vacíos que orientan |
| Personas y duplicados | FP-PE | 25 | Ficha rápida y completa, RUT válido o inválido, duplicados por RUT, correo, teléfono y nombre; contacto compartido; foto; consentimiento; menores; completitud |
| Organizaciones y vínculos | FP-OR | 15 | Alta, duplicados, vínculo con o sin cargo, rol, relación con lugares y comunidades, fusión |
| Actividades, tareas y agenda | FP-AC | 25 | Crear, programar, reprogramar (versiones), confirmar, cupos, solicitud → actividad, finalizar, solo lectura, reabrir |
| Asistencia por jornada | FP-AS | 20 | Lista por día, cinco marcas, cierre, reapertura, suspensión, retiro y reincorporación, persona que llegó, matriz, porcentaje |
| Gastos y finanzas | FP-GA | 20 | Gasto por jornada y tarea, comprobante, estados, anulación, presupuesto del proyecto, exportación, permisos |
| Solicitudes y proyectos | FP-SP | 15 | Estados, pestañas, conversión, finalizar proyecto, informe, indicadores |
| Roles y permisos | FP-RP | 20 | Gestor frente a Superadministrador, acceso por URL directa, catálogos (agregar y desactivar), exportaciones, datos sensibles |
| Seguridad | FP-SE | 15 | Inyección SQL y XSS en búsquedas y formularios, archivos falsos (bytes y extensión), CSRF, envío doble, límite de peticiones, documentos protegidos |
| Rendimiento y carga | FP-RN | 15 | Tiempo y consultas fijas por página con 10.000 personas, búsqueda global, listas paginadas, matriz de asistencia, exportación grande |
| Base de datos | FP-BD | 10 | Integridad (únicos, PROTECT, una agenda vigente), índices usados (`EXPLAIN`), distribución de filas, transacciones atómicas, migraciones limpias |
| Importación y exportación | FP-IM | 5 | Planilla con vista previa, errores por fila, reversión del lote, Excel con y sin permiso |

## 5. Condiciones y orden (dependencias reales del sistema)
1. **Territorio** cargado: región → comuna → sector. Lo exigen las direcciones y los lugares.
2. **Catálogos sembrados:** estados, roles, tipos y categorías.
3. **Cuentas:** Gestor y Superadministrador.
4. **Persona** → contacto → vínculo con una organización o comunidad. Para vincular, la persona debe existir: si no existe, se crea desde el buscador.
5. **Actividad o tarea** → programación (agenda) → participantes → jornadas → asistencia → gastos → resultado → finalizar.
6. **Proyecto** como agrupador opcional: tareas, asistencia, gastos frente a presupuesto e informe.

Cada caso declara su condición previa. Los datos los arman fábricas (`pruebas/fabricas.py`), no otras pruebas, así que los casos son independientes entre sí.

## 6. Criterios de aceptación
| Tipo | Criterio |
|---|---|
| Funcional | El resultado coincide con lo esperado en pantalla y en la base. |
| Rendimiento | Con 10.000 personas: lista o ficha en menos de 500 ms y consultas fijas (no crecen con los datos). |
| Seguridad | Ninguna entrada maliciosa se ejecuta ni se muestra sin escapar; todo acceso sin permiso responde 403. |
| Base de datos | Ninguna restricción se puede violar desde la interfaz; las búsquedas frecuentes usan índice. |

## 7. Hallazgos
Cada prueba que falla y cada observación de diseño o lógica va a `docs/pruebas/HALLAZGOS.md` con:
- **severidad:** crítica, alta, media o baja;
- pasos para reproducir;
- resultado obtenido frente al esperado;
- propuesta de corrección.

Los hallazgos se corrigen **después**, en una entrega aparte.

## 8. Ejecución
```
.venv/bin/python -m pytest pruebas/ -q                     # 200 casos
.venv/bin/python -m pytest pruebas/ -q -m "not carga"      # sin los de 10.000 personas
```
Los casos de carga llevan la marca `carga`, porque tardan más.

# F28 — Plan

**Rama:** `feature/f28-asistencia-por-jornada-y-gastos` (desde F27, que aún no está en `main`).

1. **A. Asistencia por jornada:**
   - `SesionAsistencia` con marca de 5 valores, observación, quién y cuándo, más historial;
   - estado de la lista en `SesionActividad` (abierta, cerrada, suspendida), con quién la cerró, cuándo y el motivo de reapertura;
   - una marca por persona (con varios roles);
   - inscripción «retirado» con fecha y motivo, más «Reincorporar»;
   - «Pasar lista» por jornada, con «+ Agregar persona que llegó», «Marcar el resto como ausente», cerrar y reabrir;
   - resumen calculado por persona y `Participacion.asistencia` como resumen;
   - la marca ya no cambia el estado de inscripción;
   - matriz en la tarea y pestaña «Asistencia» del proyecto, con Excel;
   - jornadas desde la agenda y «+ Nueva jornada»;
   - Finalizar con jornadas pasadas resueltas;
   - migración de datos del punto 6.
2. **B. Gastos:**
   - `Movimiento` con actividad y jornada;
   - catálogo de categorías con descripción;
   - comprobante validado y protegido;
   - estados registrado, revisado y anulado;
   - pestaña «Gastos» en la tarea y la actividad;
   - suma en el proyecto frente al presupuesto;
   - gasto al cerrar la lista;
   - visible sin la segunda fase.
3. **C. Interfaz y escenarios:**
   - pulido con el perfil de diseño ERP/CRM (matriz, tarjetas, celular);
   - `docs/escenarios_estado.md` con AS-E1…E17 y GA-E1…E10;
   - manual de uso.

**Restricciones:**
- migraciones aditivas o de datos;
- sin dependencias nuevas;
- sin rastro de la herramienta en el repositorio;
- sin commits hasta revisar;
- después, commits con referencias.

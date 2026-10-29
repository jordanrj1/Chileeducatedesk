# F26 — Tareas
1. [x] **P1a:**
   - «Pasar lista» único, con casilla por fila, «Marcar todos» y «Sin registro»;
   - Beneficiarios de solo lectura;
   - asistencia calculada desde las sesiones;
   - «+ Agregar persona» único, con «Guardar y agregar otra».

   Pruebas: `apps/actividades/test_f26_lista.py`.
2. [x] **P1b:**
   - solicitud → actividad en un paso, con «Programar ahora», y «Crear tarea en el proyecto»;
   - solicitudes con un solo «+ Nueva» y pestañas por estado;
   - Inicio con «Para hoy y vencidas»;
   - finalizar exige fecha;
   - Calendario dentro de Actividades;
   - «Historial de cargas» en Configuración;
   - un solo botón de filtros.

   Pruebas: `apps/nucleo/test_f26_p1b.py`.
3. [x] **P2a:**
   - `diferencias_datos` (solo lectura);
   - `vincular()` en todas las creaciones implícitas;
   - catálogo `RolOrganizacion` y `PersonaOrganizacion.rol`;
   - procedencia calculada, con «Actualizar también su vínculo».

   Pruebas: `apps/personas/test_f26_vincular.py`.
4. [x] **P2b:**
   - bloque «Tipo de persona» con «Organización y comunidad» una sola vez;
   - `faltantes()` y `recalcular_estado()`;
   - responsable en el equipo y referente en el padrón, con migración de datos;
   - apoderado por contacto de emergencia;
   - procedencia con cualquier organización.

   Pruebas: `apps/personas/test_f26_completitud.py`.
5. [x] **P3a:**
   - «De un vistazo» en la persona;
   - actividad suelta con 8 pestañas y alias;
   - «Finalizar proyecto», con conclusión, estado sugerido e informe Excel;
   - indicadores del período.

   Pruebas: `apps/nucleo/test_f26_p3a.py`.
6. [x] **P3b:**
   - 5 plantillas sin uso eliminadas;
   - Documentos, Interacciones y el formulario de dirección unidos;
   - «Tipo de persona» en el Resumen;
   - inventario rehecho (141 plantillas).
7. [x] **Paquete I, interfaz por módulo:**
   - **Ia (piezas comunes):**
     - un solo botón «Filtros»;
     - áreas de texto de 3 filas que crecen;
     - «Desactivar» en «Más acciones»;
     - «Sin completar (n)»;
     - «Origen» dentro de Historial;
     - nombres «Tareas» y «Historial de cargas»;
     - dirección plegada.

     Pruebas: `apps/nucleo/test_f26_ia.py`.
   - **Ib (fichas 360° y listas):**
     - «De un vistazo» en organización, comunidad y lugar;
     - columnas nuevas en personas y organizaciones;
     - vínculos sin grupos vacíos;
     - pestañas en una fila en el celular;
     - listados como tarjetas en el celular (`fche-tabla-apilable`);
     - capturador del celular a 400 px reales.

     Pruebas: `apps/nucleo/test_f26_ib.py`.
8. [x] **Paquete R (envíos, duplicados, límites y rendimiento):**
   - **Ra:**
     - envío único en el servidor y en HTMX, con «Guardando…»;
     - Enter que no envía a medias;
     - aviso de duplicados en 5 módulos;
     - límite de peticiones con pantalla 429.

     Pruebas: `apps/nucleo/test_f26_ra.py`.
   - **Rb:**
     - estáticos comprimidos con huella;
     - conexión persistente;
     - sesión `cached_db`;
     - pestañas HTMX solo con la ficha;
     - consultas repetidas eliminadas;
     - caché de los buscadores.

     Pruebas: `apps/nucleo/test_f26_rb.py`.
9. [x] **Paquete P (pulido):**
   - **Calendario:** colores de las insignias, título y filtros comunes.
   - **Buscar:** «Desde» y «Hasta» y «Ver todos (n)».
   - **Plurales:** correctos en todo el sistema.
   - **Catálogos:** agrupados y con buscador.

   Pruebas: `apps/nucleo/test_f26_p.py`.
10. [ ] **Revisión del usuario y commits:** pendiente de aprobación.
11. [ ] **Validar lo [P] y [V]** con Claudio o Manuel:
   - responsable como Coordinador;
   - comuna para quedar «activo»;
   - cifras del Inicio;
   - estado sugerido del proyecto;
   - definición de los indicadores.
12. [ ] **Recalcular el estado de las personas existentes** (`recalcular_estado`): pendiente de confirmación del usuario.
13. [ ] **Paquete 4, Finanzas → «Aportes y recursos»:** pendiente de confirmación del usuario.

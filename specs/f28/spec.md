# F28 — Asistencia por jornada y gastos de las actividades

**Fuente:** pedido del usuario (14-11-2026) y sus decisiones del mismo día [D-u]: 5 marcas, lista abierta, cerrada y reabrir, rendición simple de gastos visible, y devolver a su tarea a quienes quedaron como «No asistió». Lo que no se decidió con el usuario es [P]; lo que debe validar el tutor es [V].

## Diagnóstico
- **Por qué «desaparecen» las personas:** al pasar lista, quien queda sin marcar cambia su **estado de inscripción** a «No asistió». `Participacion.activa` excluye ese estado, así que la persona deja de aparecer en la lista del día siguiente y deja de ocupar cupo. Se mezcla «está en la tarea» con «vino tal día».
- **Asistencia en dos lugares:** una marca única en la participación («Pasar lista») y otra por sesión (`SesionAsistencia`).
- **Finanzas desconectadas:** `Movimiento` e `ItemPresupuesto` solo se ligan al proyecto y están ocultos en la segunda fase. No hay gasto por actividad ni por día, ni comprobante con foto.

## 1. Tres conceptos separados [D-u]
| Concepto | Qué es | Dónde se guarda |
|---|---|---|
| **Inscripción** | La persona está en la tarea o actividad con un rol. Estados de inscripción: invitado, interesado, confirmado, inscrito, lista de espera, rechazó, canceló, retirado, registro erróneo. **Pasar lista nunca la cambia.** | `Participacion` |
| **Jornada** | Cada día o bloque en que se realiza la tarea: fecha, horas y lugar. Una tarea tiene una o varias; puede haber dos el mismo día (mañana y tarde). | `SesionActividad` (en pantalla, «Jornada») |
| **Asistencia del día** | La marca de una persona inscrita en una jornada, con observación, quién la marcó y cuándo, y su historial. | `SesionAsistencia` |

- **Marcas** [D-u]: **Presente · Atrasado · Se retiró antes · Justificado · Ausente**, con observación opcional por persona.
  - Presente, Atrasado y Se retiró antes cuentan como asistencia.
  - Justificado no cuenta como asistencia, pero tampoco como inasistencia en el porcentaje [P].
- **Resumen por persona (calculado):** días presentes, porcentaje de asistencia y última marca. `Participacion.asistencia` queda como resumen, para Finalizar y los indicadores:
  - verdadero, si fue a una jornada o más;
  - falso, si todas sus marcas son ausencias;
  - vacío, si no tiene marcas.
- **Una marca por persona y jornada,** aunque tenga dos roles en la tarea [P].

## 2. La lista del día [D-u]
- **Quiénes aparecen:** las inscripciones activas en la fecha de la jornada.
  - Quien fue agregado después de esa fecha no aparece en los días anteriores.
  - Quien fue retirado antes de esa fecha no aparece en los días siguientes.
  - **Nadie desaparece por faltar.**
- **Estados de la lista:**
  - **Abierta:** se marca y se guarda tantas veces como haga falta.
  - **Cerrada:** solo lectura, con quién la cerró y cuándo.
  - **Reabrir:** pide motivo y queda en el historial.
  - Cerrar exige que todas las personas tengan marca, o usar «Marcar el resto como ausente».
- **Llegó sin estar inscrita:** «+ Agregar persona que llegó», desde la misma lista, la inscribe (rol participante, o el que se elija) y la deja Presente en esa jornada.
- **Quitar de la tarea:** la inscripción pasa a «retirado», con fecha y motivo. Conserva sus asistencias y no aparece en las jornadas siguientes. «Reincorporar» deshace un retiro hecho por error.
- **Jornada suspendida** (lluvia, paro…): sin lista y con motivo. No cuenta para el porcentaje.
- **Público masivo:** la jornada admite además un conteo sin nombres, por edad y sexo, como hoy.
- **Al cerrar la lista** (opcional): foto de evidencia del día y «¿Hubo gastos este día?», que abre el registro de gasto de esa jornada.

## 3. Panel de asistencia [D-u]
- **En la tarea o actividad** (pestaña «Equipo y asistencia»):
  - **matriz** de personas por jornadas, con la marca de cada día;
  - **por persona:** total de días y porcentaje;
  - **por jornada:** cantidad de presentes sobre inscritos y estado de la lista;
  - **filtros:** equipo ejecutor y beneficiarios;
  - **«Pasar lista»** de la jornada de hoy, o de la elegida;
  - **exportar** a Excel, con permiso.
- **En el proyecto:** pestaña «Asistencia» con el resumen por tarea (jornadas, inscritos, porcentaje promedio) y por persona (tareas, días y porcentaje), con enlaces.
- **Celular:** la matriz se desplaza de lado con la columna de nombres fija, y «Pasar lista» queda como lista apilada.

## 4. Jornadas [P]
- Cada día programado en la agenda crea su jornada. También se puede agregar con «+ Nueva jornada» (fecha, horas, lugar).
- Reprogramar la agenda no borra jornadas con lista: avisa.
- **Finalizar la tarea exige** que toda jornada pasada tenga la lista cerrada, esté suspendida o tenga conteo sin nombres. También exige el resultado.

## 5. Gastos de la actividad (rendición simple) [D-u] [V]
- **`Movimiento` de tipo gasto** con actividad y jornada opcionales (migración aditiva) y estos datos:
  - **categoría:** catálogo con descripción: alimentación, traslado, materiales, arriendo de espacio, servicios u honorarios, impresión y difusión, otros;
  - **monto en pesos y fecha;**
  - **pagado por:** una persona;
  - **proveedor:** texto u organización;
  - **comprobante:** foto JPG, PNG o WEBP, o PDF, de hasta 5 MB. Se valida por su contenido y se guarda como documento restringido, servido solo con permiso.
- **Estados:** registrado → revisado → anulado (con motivo). Un gasto revisado no se edita: se anula y se registra de nuevo.
- **Dónde se ve:**
  - **en la tarea o actividad:** pestaña «Gastos» con la lista por jornada, el total, los que no tienen comprobante y un Excel con permiso de exportar;
  - **en el proyecto:** gasto por tarea, jornada y categoría frente al presupuesto (`ItemPresupuesto`), con aviso si se excede.
- **Visible siempre,** sin depender de la segunda fase. Los aportes y donaciones siguen en la segunda fase.
- **[V] tutor:** el reglamento oficial deja finanzas, pagos y contabilidad fuera de esta etapa. Esto es solo un registro de gastos con comprobante; no hay pagos, reembolsos ni contabilidad.

## 6. Datos actuales [D-u]
Migración de datos, reversible como no-op:
- las participaciones en «Asistió» o «No asistió» vuelven a «Inscrito»;
- en las actividades con marcas y sin jornadas se crea la jornada 1, con la fecha vigente de la agenda;
- cada marca existente pasa a esa jornada (verdadero → Presente; falso → Ausente) y la lista queda cerrada como «migrada»;
- se registra en el historial.

## 7. Escenarios (cada uno con su prueba)
**Asistencia**

| ID | Escenario | Resultado esperado |
|---|---|---|
| AS-E1 | Taller de 3 días; Ana falta el día 1 | Ana aparece en la lista de los días 2 y 3; su porcentaje es 67 % si asiste ambos |
| AS-E2 | Beto se inscribe el día 2 | No aparece en la lista del día 1; sí en el 2 y el 3; su porcentaje se calcula sobre 2 jornadas |
| AS-E3 | Llega alguien sin inscribir | «+ Agregar persona que llegó» la inscribe y queda Presente ese día |
| AS-E4 | Error en una lista cerrada de hace una semana | Reabrir con motivo, corregir y cerrar; el historial muestra antes, después, quién y cuándo |
| AS-E5 | Dos jornadas el mismo día (mañana y tarde) | Dos listas independientes |
| AS-E6 | Jornada suspendida por lluvia | Sin lista; no cuenta para el porcentaje; Finalizar la acepta |
| AS-E7 | Carla se retira el día 2 | Queda «retirado», conserva el día 1 y no aparece desde el día 3 |
| AS-E8 | Se quitó a Daniel por error | «Reincorporar» lo devuelve y vuelve a aparecer |
| AS-E9 | Justificado con certificado | Marca «Justificado» con observación; no baja el porcentaje |
| AS-E10 | Atrasado o se retiró antes | Cuenta como asistencia; se ve la marca en la matriz |
| AS-E11 | Cerrar con personas sin marcar | No deja, o «Marcar el resto como ausente» |
| AS-E12 | Feria con 200 personas sin nombre | Conteo sin nombres en la jornada; Finalizar lo acepta |
| AS-E13 | Finalizar con un día pasado sin lista | Avisa qué jornada falta y no finaliza |
| AS-E14 | Persona con dos roles en la tarea | Una sola fila y una sola marca por jornada |
| AS-E15 | Doble clic en «Guardar lista» o dos pestañas abiertas | Se guarda una sola vez; la segunda pestaña avisa que la lista cambió |
| AS-E16 | Lista cerrada, se intenta marcar | Solo lectura; el servidor rechaza el POST |
| AS-E17 | Personas que hoy figuran como «No asistió» | Vuelven a su tarea, con la marca en la jornada 1 |

**Gastos**

| ID | Escenario | Resultado esperado |
|---|---|---|
| GA-E1 | Al cerrar la lista, foto de la boleta de colación | Gasto ligado a la jornada, con comprobante protegido |
| GA-E2 | Gasto sin comprobante | Se guarda y queda marcado «Sin comprobante» en la lista y en el proyecto |
| GA-E3 | Gasto cargado en la tarea equivocada (sin revisar) | Se edita la tarea o la jornada; queda en el historial |
| GA-E4 | Monto mal digitado en un gasto ya revisado | No se edita: se anula con motivo y se registra de nuevo |
| GA-E5 | Traslado semanal que cubre varios días | Gasto de la tarea sin jornada |
| GA-E6 | Lo pagó una voluntaria | «Pagado por» la persona; el reembolso queda fuera [V] |
| GA-E7 | El proyecto supera su presupuesto | Aviso en el proyecto con la diferencia |
| GA-E8 | Comprobante GIF, ejecutable o de más de 5 MB | Rechazado con un mensaje claro |
| GA-E9 | Actividad suelta sin proyecto | Gastos igual, sin comparación con el presupuesto |
| GA-E10 | Quien solo puede ver intenta exportar los gastos | 403 |

## Criterios
- **Migraciones:** aditivas, más la de datos del punto 6. Sin dependencias nuevas; las fotos se validan por sus bytes.
- **Funcionamiento:**
  - funciona sin JavaScript;
  - sin consultas en bucle: la matriz y los paneles hacen un número fijo de consultas;
  - envío único y límites de F26 aplicados.
- **Pruebas:** cada escenario tiene su prueba, y `docs/escenarios_estado.md` está al día.
- **Interfaz:** con el perfil de diseño ERP/CRM (tarjetas, matriz legible, celular).

# Historias de usuario por proceso, y cómo probarlas

Auditoría del 14-10-2026. Se organiza por **procesos**: lo que Claudio hace de principio a fin. Cada proceso junta las historias de usuario que cubre (sus códigos están en `docs/Requerimientos_por_modulo_FCHE.md`; el estado de cada una, con su evidencia, en `CUMPLIMIENTO.md`).

**Cómo probar.**
1. Levanta el sistema (`docs/COMO_LEVANTAR.md`) e ingresa en `http://127.0.0.1:8000` con la cuenta `gestor`. Para lo del Administrador, usa la cuenta `admin`.
2. Los ejemplos usan los **datos de demostración** (todos ficticios): «Taller Demo 1», «Voluntario1 Demo», «Universidad Demo», «Sede Demo», «Comuna Demo», «Proyecto Demo de alfabetización».
3. Todo lo que crees al probar queda guardado. Usa nombres inventados.

---

## Cuántos procesos hay

**21 procesos** que Claudio puede hacer hoy:
- **13 del núcleo** (P1 a P13), los de `docs/Procesos_y_pruebas_de_Claudio.md`.
- **8 que ya existen en el sistema** y amplían el núcleo (P14 a P21). Puedes decidir si se quedan visibles.

| # | Proceso | Quién |
|---|---|---|
| P1 | Entrar y ver el panel | Gestor y Administrador |
| P2 | Crear una actividad y completarla con el tiempo | Gestor |
| P3 | Agregar personas a la actividad (aunque no existan) | Gestor |
| P4 | Agregar organizaciones, colaboradores y donadores | Gestor |
| P5 | Dónde y cuándo: programar, reprogramar, lugar y zona | Gestor |
| P6 | Registrar contactos y pendientes | Gestor |
| P7 | Guardar y ver documentos | Gestor |
| P8 | Asistencia, resultado y cierre | Gestor |
| P9 | Fichas e historial | Gestor (el Administrador solo mira) |
| P10 | Buscar | Gestor y Administrador |
| P11 | Proyectos (opcional) | Gestor |
| P12 | Catálogos (listas de opciones) | Gestor agrega; Administrador desactiva |
| P13 | Cuentas, roles, auditoría y respaldos | Administrador |
| P14 | Solicitudes y oportunidades | Gestor |
| P15 | Comunidades (grupos) | Gestor |
| P16 | Territorio: qué se hizo en una comuna o sector | Gestor |
| P17 | Cargar un listado desde una planilla | Gestor |
| P18 | Sesiones y minutas | Gestor |
| P19 | Revisar compatibilidad y buscar candidatos | Gestor |
| P20 | Exportar a Excel | Gestor (y Administrador) |
| P21 | Corregir errores sin borrar | Gestor; unir fichas solo el Administrador |

---

## P1 · Entrar y ver el panel

- **Con qué fin:** que solo entren personas autorizadas y que Claudio vea qué tiene pendiente.
- **Historias:** HU-AC-01 a 07, HU-DA-01, HU-DA-02 y HU-DA-05.
- **Rutas del proceso:** `/login` → `/dashboard` → `/mi-cuenta` → `/mi-cuenta/clave` → `/logout`.
- **Qué hace:**
  - Ingresa con correo o usuario.
  - Muestra el Panel: actividades incompletas, solicitudes sin respuesta, personas por completar, próximas acciones e invitaciones sin respuesta.
  - Cierra la sesión tras 60 minutos sin uso.
  - Bloquea la cuenta 15 minutos tras 5 intentos fallidos.
- **Qué no hace:** no recupera la contraseña por correo; la restablece el Administrador.
- **Cómo probarlo:**
  1. Abre `http://127.0.0.1:8000/personas` sin haber ingresado → te lleva al ingreso. Al entrar, vuelves a Personas.
  2. Ingresa con una contraseña mala → el mensaje no dice si falló el usuario o la contraseña.
  3. Ingresa bien → llegas al Panel con tu nombre arriba a la derecha.
  4. Menú de tu nombre → Mi cuenta → Cambiar contraseña.
  5. Como `admin`, desactiva la cuenta `gestor`. Intenta entrar como `gestor` → te explica que la cuenta está desactivada. **Vuelve a activarla.**
  6. Cierra sesión y pulsa Atrás en el navegador → **pendiente de verificar** (`PRUEBAS.md` §4).
- **Esperado:** nadie ve datos sin ingresar; el Panel dice por dónde partir.

## P2 · Crear una actividad y completarla con el tiempo

- **Con qué fin:** anotar un evento aunque falten datos y completarlo después.
- **Historias:** HU-AT-01 a 04, 07 a 09 y 11; NF-01.
- **Rutas del proceso:** `/dashboard` («+ Actividad») o `/actividades` → `/actividades/nueva` → `/actividades/<n>` → `/actividades/<n>/editar` → `/actividades/<n>/estado`.
- **Qué hace:**
  - Crea con **solo el nombre**: el tipo y lo demás son opcionales. Queda en estado **Pendiente**.
  - Después se agregan objetivo, descripción, modalidad, responsable, condiciones, área temática, público, territorio, proyecto y actividad padre.
  - Un aviso arriba de la ficha dice **qué falta para confirmar**.
- **Qué no hace:** no exige fecha, lugar ni personas para crear.
- **Qué impide:** guardar sin nombre; que una actividad sea su propia «padre»; suspender o cancelar sin motivo.
- **Cómo probarlo:**
  1. «+ Actividad» → nombre «Prueba de taller» y tipo Taller → Guardar. Abre la ficha en estado Pendiente.
  2. Editar → escribe objetivo y descripción → Guardar. Quedan en la pestaña Información.
  3. Borra el nombre y guarda → avisa que falta.
  4. Cambiar estado → Cancelada sin motivo → lo pide.
- **Esperado:** la actividad existe desde el primer clic y se va completando.

## P3 · Agregar personas a la actividad

- **Con qué fin:** anotar quién participa, aunque todavía no esté registrado.
- **Historias:** HU-AT-05, HU-PE-01, HU-PE-02, HU-PE-07, HU-DA-04 y HU-IG-01.
- **Rutas del proceso:**
  - ficha `/actividades/<n>?tab=participantes`;
  - `/actividades/<n>/participantes/nuevo`, con el buscador `/personas/opciones`;
  - `/actividades/<n>/participantes/rapido` si la persona no existe;
  - `/actividades/<n>/participantes/<p>/editar`;
  - `/personas/<n>`.
- **Qué hace:**
  - Busca a la persona escribiendo parte del nombre y le asigna rol y estado.
  - Si no existe, la crea con solo el nombre y queda **agregada**, en estado de registro «incompleto».
  - Antes de crearla avisa si hay alguien parecido: «Usar existente» o «Crear de todos modos».
- **Qué no hace:** no crea una cuenta de usuario y no exige RUT.
- **Qué avisa:** si se supera la capacidad del lugar (deja seguir).
- **Qué impide:** la misma persona con el mismo rol dos veces en la actividad.
- **Cómo probarlo:**
  1. Taller Demo 1 → Participantes → «+ Agregar participante» → escribe «Voluntario4» → elígelo, rol Voluntario → Guardar. Aparece en la lista.
  2. Repite lo mismo → avisa que ya está con ese rol.
  3. «+ Agregar participante» → «Créala aquí mismo» → nombre «Rosa» y apellido «Inventada» → rol Estudiante → Guardar. Queda creada y agregada.
  4. Crea otra vez a «Rosa Inventada» del mismo modo → muestra la existente con «Usar existente».
  5. Abre la ficha de Rosa → pestaña Participaciones → aparece Taller Demo 1.

## P4 · Agregar organizaciones, colaboradores y donadores

- **Con qué fin:** dejar claro quién más participó y cómo.
- **Historias:** HU-AT-06, HU-OR-01 a 08 y HU-IN-05.
- **Rutas del proceso:**
  - ficha `/actividades/<n>?tab=organizaciones`;
  - `/actividades/<n>/organizaciones/nuevo`, con el buscador `/organizaciones/opciones`;
  - `/organizaciones/nueva`;
  - `/organizaciones/<n>`;
  - para pedir apoyo: `/colaboraciones/nueva?actividad=<n>`.
- **Qué hace:**
  - Vincula la organización con **cómo intervino**: solicita, articula, coordina, facilita espacio, aporta personas o **aporta recursos** (el donador, sin montos).
  - Guarda también su persona de contacto.
  - En la ficha de la organización se ven sus actividades, personas con cargo y fechas, carreras (si es institución educativa) y contactos con propósito.
- **Qué no hace:** no lleva montos de dinero.
- **Qué impide:** repetir la misma organización con el mismo tipo de intervención; carreras en una organización que no es educativa; una segunda organización marcada como «la Fundación».
- **Cómo probarlo:**
  1. Taller Demo 1 → Organizaciones → «+ Agregar» → escribe «junta» → Junta de Vecinos Demo, «Facilita espacio» → Guardar.
  2. Agrega Universidad Demo con «Aporta personas».
  3. Abre Universidad Demo → «Actividades y proyectos» → aparece Taller Demo 1.
  4. Organizaciones → «+ Nueva» → «Universidad Demo» → avisa del parecido.
- **Pendiente:** si los donadores deben llevar montos (`Procesos` §7.1). Hoy no.

## P5 · Dónde y cuándo

- **Con qué fin:** programar la actividad y cambiar la fecha sin perder la anterior.
- **Historias:** HU-AG-01 a 07, HU-LU-01 a 05, HU-AT-03 y HU-TE-01 a 04.
- **Rutas del proceso:**
  - agenda: `/actividades/<n>?tab=agenda` → `/actividades/<n>/programar` (+ `/lugares/crear-rapido`) → `/actividades/<n>/serie`;
  - calendario: `/calendario`;
  - lugares: `/lugares`, `/lugares/<n>`;
  - territorio de la actividad: `/actividades/<n>/territorios/nuevo`.
- **Qué hace:**
  - Cada programación es una **versión** (fecha, horas, lugar, motivo y quién). Reprogramar pide motivo y deja la anterior visible.
  - Se puede programar **sin lugar**.
  - Se puede indicar solo la **zona** (comuna o sector) aunque no haya lugar.
  - El calendario muestra mes, semana o lista; un clic abre la actividad.
  - Crea series semanales.
- **Qué no hace:** no bloquea un choque de horario al programar; lo revisa al **confirmar** (ver P19).
- **Qué impide:** hora de término anterior a la de inicio; programar en un lugar desactivado; programar una actividad cancelada o realizada; reprogramar sin motivo o sin cambios; editar una versión anterior.
- **Cómo probarlo:**
  1. «Prueba de taller» (de P2) → Agenda → Programar → fecha de la próxima semana, 18:00 a 20:00 → «+ Crear lugar» → nombre «Biblioteca Inventada», tipo Sala, comuna Comuna Demo → queda elegido → Guardar. Pasa a Planificada.
  2. Reprogramar → otra hora → motivo «cambio de horario» → la versión 1 queda como histórica con el motivo.
  3. Calendario → clic en el evento → abre la actividad.
  4. Otra actividad → Información → Territorios → «+ Agregar» → Comuna Demo, sin lugar → se guarda.
- **Ojo:**
  - Crear un lugar desde la agenda **no deja elegir el sector**: se agrega editando el lugar.
  - La base de demostración solo tiene «Comuna Demo», sin sectores, hasta cargar el archivo oficial.

## P6 · Registrar contactos y pendientes

- **Con qué fin:** recordar a quién llamó, qué le dijeron y qué falta.
- **Historias:** HU-IN-01 a 05 y HU-DA-01.
- **Rutas del proceso:** «Registrar interacción» en la ficha de una persona, organización, solicitud o actividad → `/interacciones/nueva?persona=<n>` (o `?organizacion=`, `?solicitud=` o `?actividad=`) → `/interacciones/<n>` → `/dashboard`.
- **Qué hace:** guarda fecha, canal (llamado, correo, mensaje, reunión…), con quién, resultado y **próxima acción con fecha**. La próxima acción aparece en el Panel hasta marcarla cumplida.
- **Qué no hace:** no envía mensajes ni correos. Solo registra.
- **Qué impide:** guardar sin «con quién» (persona u organización); poner fecha de próxima acción sin escribir la acción.
- **Cómo probarlo:**
  1. Universidad Demo → «Registrar interacción» → Llamado, resultado «Enviarán listado», próxima acción «Recibir listado» para mañana → Guardar.
  2. Ve al Panel → aparece «Recibir listado».
  3. Vuelve a Universidad Demo → pestaña «Actividades y proyectos», al final → se ve la llamada.
- **Ojo:** en la organización, las llamadas están al final de «Actividades y proyectos», no en una pestaña propia (propuesta 4 del inventario).

## P7 · Guardar y ver documentos

- **Con qué fin:** tener a mano cartas, minutas y certificados como evidencia.
- **Historias:** HU-DO-01 a 06 y HU-IG-06.
- **Rutas del proceso:**
  - pestaña Documentos de una ficha → `/documentos/nuevo?actividad=<n>` o `/documentos/asociar?actividad=<n>`;
  - `/documentos/<n>`, `/documentos/<n>/archivo` (descargar), `/documentos/<n>/ver` y `/documentos/<n>/transcribir`;
  - `/documentos`.
- **Qué hace:**
  - Sube el archivo a la carpeta de documentos y guarda tipo, fecha, descripción, quién lo subió, folio, emisor y vencimiento.
  - **Asocia** un mismo archivo a otra ficha sin copiarlo.
  - Marca documentos **restringidos**.
  - Transcribe datos con el documento a la vista.
  - Archiva sin borrar.
- **Qué no hace:** no tiene galería ni trata las imágenes de forma especial.
- **Qué impide:** tipos no permitidos, archivos vacíos o de más de 25 MB; abrir un documento restringido sin permiso (403); subir un documento sin ligarlo a ninguna ficha.
- **Cómo probarlo:**
  1. Taller Demo 1 → Documentos → «Subir nuevo» → un PDF cualquiera, tipo Carta → Guardar.
  2. Clic en el documento → Descargar.
  3. Intenta subir un archivo `.exe` → lo rechaza con mensaje.
  4. Marca el documento como restringido. Copia su dirección de descarga. Ábrela con una cuenta sin permiso → 403.
  5. Otra actividad → Documentos → «Asociar existente» → elige el mismo → queda en ambas.

## P8 · Asistencia, resultado y cierre

- **Con qué fin:** dejar anotado quién fue y cómo salió.
- **Historias:** HU-RE-01 a 04 y HU-AT-09.
- **Rutas del proceso:** `/actividades/<n>?tab=asistencia` → `/actividades/<n>/asistencia` (+ `/actividades/<n>/participantes/nuevo?llego=1`) → `/actividades/<n>?tab=resultados` → `/actividades/<n>/resultados` → `/actividades/<n>/finalizar` → `/actividades/<n>/participantes/<p>/constancia`.
- **Qué hace:**
  - Marca la asistencia por persona.
  - Agrega a quien llegó sin estar previsto.
  - Guarda observaciones, incidencias y resultado.
  - **Finalizar** exige asistencia (o marcar «sin registro de asistencia») y resultado. Deja la actividad **Realizada** y de solo lectura.
- **Qué no hace:** no deja finalizar ni marcar asistencia **antes del día** de la actividad.
- **Qué impide:** finalizar sin asistencia ni «sin registro», o sin resultado; editar una actividad realizada.
- **Cómo probarlo:** necesitas una actividad programada **para hoy**.
  1. Programa «Prueba de taller» para hoy.
  2. Asistencia → marca a cada persona → Guardar.
  3. «+ Agregar persona que llegó» → elige a alguien o créalo → queda como asistente.
  4. Pulsa Finalizar sin resultado → explica qué falta.
  5. Resultados → escribe el resultado → Finalizar → queda Realizada. En el Calendario aparece como realizada.

## P9 · Fichas e historial

- **Con qué fin:** saber todo lo que pasó con una persona, organización, lugar o actividad, y pasar de una a otra con un clic.
- **Historias:** HU-PE-03 a 11, HU-HI-01 a 05, HU-LU-02, HU-OR-07, HU-DA-03 y NF-05.
- **Rutas del proceso:** `/personas/<n>`, `/organizaciones/<n>`, `/lugares/<n>`, `/actividades/<n>` y `/comunidades/<n>`, cada una con `?tab=historial`; `…/editar`; `…/alternar` (desactivar).
- **Qué hace:**
  - Cada ficha tiene pestañas y enlaces a las fichas relacionadas.
  - El Historial muestra qué cambió, quién y cuándo, con el valor anterior. La pestaña Origen dice de dónde salió cada dato.
  - Desactivar no borra: la persona sigue en sus actividades pasadas, pero no se ofrece para nuevas.
  - «← Volver» conserva los filtros y avisa si hay cambios sin guardar.
- **Qué no hace:** no existe el botón Eliminar.
- **Cómo probarlo:**
  1. Abre Voluntario1 Demo → Participaciones → aparece Taller Demo 1.
  2. Contactos → edita su teléfono → Historial → aparece el cambio, tu usuario y la hora.
  3. Desde Participaciones, clic en Taller Demo 1 → llegas a la actividad.
  4. Pulsa «← Volver» → regresas a la persona.
  5. Escribe en un formulario y pulsa Volver → pregunta si quieres salir sin guardar.

## P10 · Buscar

- **Con qué fin:** encontrar algo sin saber en qué sección está.
- **Historias:** HU-BU-01 a 03 y HU-BU-05.
- **Rutas del proceso:** la caja de arriba → `/buscar?q=…`; los filtros de cada listado (`/personas?…`, `/actividades?…`).
- **Qué hace:**
  - Busca en personas, organizaciones, actividades, lugares, documentos y minutas.
  - Encuentra sin tildes ni mayúsculas, y teléfonos en cualquier formato.
  - Agrupa los resultados por tipo.
  - Los desactivados aparecen marcados.
  - Respeta los permisos: no muestra documentos restringidos a quien no puede verlos.
- **Cómo probarlo:**
  1. Busca «vecina» → aparecen las tres vecinas demo.
  2. Crea a «María Inventada» y busca «maria inventada» → la encuentra.
  3. Actividades → filtra por estado Pendiente.
  4. Busca «xyz123» → mensaje claro de que no hay resultados.

## P11 · Proyectos (opcional)

- **Con qué fin:** agrupar actividades que van juntas. Es una petición del tutor y está por validar [V#7].
- **Historias:** HU-AT-11, HU-PR-01 y HU-PR-02.
- **Rutas del proceso:** `/proyectos` → `/proyectos/nuevo` → `/proyectos/<n>` (pestañas) → `/actividades/nueva?proyecto=<n>`.
- **Qué hace:** ficha con equipo, organizaciones, comunidades, actividades, alcance, documentos e historial.
- **Qué no hace:** no exige proyecto a ninguna actividad.
- **Cómo probarlo:**
  1. Proyectos → «+ Nuevo» → nombre «Campaña inventada» → Guardar.
  2. Pestaña Actividades → «+ Nueva actividad» → queda ligada.
  3. Edita «Prueba de taller» → Proyecto = Campaña inventada.
  4. El proyecto muestra las dos actividades.
  5. Crea otra actividad sin proyecto → se puede.

## P12 · Catálogos

- **Con qué fin:** que Claudio agregue un tipo nuevo sin pedírselo al programador.
- **Historias:** HU-CA-01 a 03.
- **Rutas del proceso:** Menú → Catálogos → `/administracion/catalogos/` → `/administracion/catalogos/<catalogo>/` → `…/<n>/editar` y `…/<n>/alternar` (desactivar, solo Administrador).
- **Qué hace:** agrega y edita valores. El Administrador desactiva y une valores repetidos.
- **Qué no hace:** no borra valores.
- **Cómo probarlo:**
  1. Catálogos → Tipos de actividad → «+ Agregar valor» → «Conversatorio» → Guardar.
  2. «+ Actividad» → el tipo Conversatorio aparece en la lista.
  3. Como `admin`, desactívalo → ya no aparece para actividades nuevas, y la que lo usaba lo conserva.
  4. Busca un botón Eliminar → no existe.

## P13 · Cuentas, roles, auditoría y respaldos (Administrador)

- **Con qué fin:** controlar quién entra y no perder los datos.
- **Historias:** HU-US-01 a 05, HU-AC-06 y HU-HI-06; NF-04.
- **Rutas del proceso:** `/administracion/` → `/administracion/usuarios` → `…/nuevo`, `…/<n>/editar`, `…/<n>/alternar`, `…/<n>/clave` y `…/<n>/desbloquear` → `/administracion/roles` → `/administracion/auditoria`. Los respaldos se hacen con `respaldar.bat`, fuera de la pantalla.
- **Qué hace:**
  - Crea cuentas solo para personas registradas, con rol Gestor o Administrador.
  - Desactiva sin borrar, restablece contraseñas y desbloquea.
  - Ajusta los permisos de cada rol.
  - La auditoría filtra por fecha y acción.
- **Qué no hace:** no crea cuentas para estudiantes ni voluntarios; no hay un botón de respaldo en pantalla.
- **Cómo probarlo:**
  1. Como `admin`: Usuarios → «+ Nuevo usuario» → elige a «Coordinadora Demo» → rol Gestor → Guardar.
  2. Desactívala.
  3. Entra como `gestor` → no ve «Administración». Escribir `/administracion/usuarios` da 403.
  4. Auditoría → aparecen «usuario creado» y «usuario desactivado».
  5. Respaldo: `respaldar.bat`, y restaurar en una base aparte (`docs/entrega.md`).

## P14 · Solicitudes y oportunidades

- **Con qué fin:** no perder un pedido o una idea antes de saber si se hará.
- **Historias:** HU-SO-01 a 06.
- **Rutas del proceso:** `/solicitudes` → `/solicitudes/nueva` → `/solicitudes/<n>` → `…/estado` → `…/crear-actividad` o `…/crear-proyecto` → `…/reabrir`.
- **Qué hace:** registra casi sin datos; el contacto puede quedar «por identificar». Se sigue como pendiente, en seguimiento, convertida o descartada (con motivo). Se convierte en actividad sin reescribir.
- **Cómo probarlo:**
  1. «+ Solicitud» → solo el motivo «Colegio pide charla» → Guardar.
  2. La ficha dice «Por identificar» y «Abierta hace 0 días».
  3. «Crear actividad» → se abre la actividad con el motivo ya escrito.

## P15 · Comunidades (grupos)

- **Con qué fin:** registrar grupos (vecinos de una villa, un curso, un comité) con sus integrantes, y dirigirles actividades. Es lo más cercano al «grupo» que mencionaste.
- **Rutas del proceso:** `/comunidades` → `/comunidades/nueva` → `/comunidades/<n>` → `…/integrantes/nuevo` → `/actividades/nueva?comunidad=<n>`.
- **Cómo probarlo:**
  1. Abre «Vecinos de la Villa Demo» → Integrantes (las 3 vecinas).
  2. «+ Actividad para esta comunidad» → la actividad nace dirigida a ella.

## P16 · Territorio: qué se hizo en una comuna o sector

- **Con qué fin:** responder «¿qué hemos hecho en esta comuna?» y crear cosas ya ubicadas.
- **Historias:** HU-TE-03, HU-TE-05 y HU-BU-05.
- **Rutas del proceso:** `/territorio` → `/territorio/region/<n>` → `/territorio/comuna/<n>` (pestañas Resumen, Sectores, Comunidades, Organizaciones, Personas, Lugares, Actividades y Alcance) → `/territorio/sector/<n>` → `…/exportar`.
- **Cómo probarlo:**
  1. Territorio → Comuna Demo → Resumen con cifras.
  2. Clic en una cifra → abre su pestaña.
  3. «+ Actividad» desde la comuna → la actividad nace con la comuna como zona.

## P17 · Cargar un listado desde una planilla

- **Con qué fin:** no escribir uno por uno los estudiantes que manda una institución.
- **Historias:** HU-AT-10 y HU-IG-02 a 05.
- **Rutas del proceso:** Participantes → «Cargar listado», o `/importaciones/nueva` → `/importaciones/<n>/revisar` → confirmar → `/importaciones/<n>` → `…/revertir`.
- **Qué hace:**
  - Lee Excel, CSV o texto pegado, con los teléfonos como texto.
  - Separa «Apellido, Nombre».
  - Muestra cuatro grupos: nuevos, existentes, posibles duplicados y errores.
  - **No guarda nada hasta confirmar**, y se puede revertir.
- **Cómo probarlo:**
  1. En Taller Demo 1 → «Cargar listado» → pega dos líneas inventadas («Pérez, Luis;9 1111 2222» y «Voluntario2 Demo»).
  2. Revisar → Luis aparece como nuevo y Voluntario2 como existente.
  3. Confirmar → quedan agregados.
  4. Importaciones → la carga → Revertir.

## P18 · Sesiones y minutas

- **Con qué fin:** anotar cada encuentro de una actividad que se repite: qué se hizo, avances, acuerdos y quién asistió.
- **Rutas del proceso:** `/actividades/<n>?tab=sesiones` → `/actividades/<n>/sesiones/nuevo` → `/actividades/<n>/sesiones/<s>` → `…/asistencia`.
- **Cómo probarlo:** Taller Demo 1 → «Sesiones y minutas» → abre «Diagnóstico y presentación» → lee la minuta y su asistencia.

## P19 · Revisar compatibilidad y buscar candidatos

- **Con qué fin:** que el sistema ayude a armar la actividad y avise de problemas, **sin decidir por Claudio**.
- **Historias:** HU-VA-01 a 05 y HU-LU-05.
- **Rutas del proceso:** `/actividades/<n>/confirmar` y `/actividades/<n>/candidatos`.
- **Qué hace:**
  - Al confirmar, muestra ✓ lo compatible, ⚠ las advertencias y ✕ las incompatibilidades, cada una con su motivo.
  - Busca personas, lugares y organizaciones candidatas con sus razones.
  - Nunca agrega a nadie solo.
- **Qué impide:**
  - confirmar sin responsable, fecha o lugar;
  - confirmar con el lugar ocupado o con más personas que su capacidad (se puede permitir con `CONFIRMAR_CON_CONFLICTO_CRITICO` [V#3]).
- **Cómo probarlo:**
  1. Taller Demo 1 → Confirmar → revisa la lista.
  2. Participantes → «Buscar candidatos» → filtra por institución Universidad Demo.

## P20 · Exportar a Excel

- **Con qué fin:** llevar lo que se ve en pantalla a un informe.
- **Historias:** HU-BU-04.
- **Rutas del proceso:** «Exportar» en cada listado (`/personas/exportar?…` y otros), `/territorio/comuna/<n>/exportar` y `/personas/<n>/datos-personales`.
- **Qué hace:** exporta con los filtros aplicados. Exige permiso, deja registro en la auditoría y agrega un aviso de confidencialidad. Neutraliza fórmulas en las celdas.
- **Pendiente:** tu documento pone las «exportaciones masivas» fuera de alcance. Ver `ALCANCE.md` §3.

## P21 · Corregir errores sin borrar

- **Con qué fin:** arreglar equivocaciones sin perder la historia.
- **Rutas del proceso:**
  - `/actividades/<n>/participantes/<p>/quitar`: pide motivo y queda como «registro erróneo»;
  - `/interacciones/<n>/editar` (mover una interacción a la persona correcta);
  - `/personas/<n>/fusionar` y `/organizaciones/<n>/fusionar` (unir fichas repetidas, **solo Administrador**);
  - `…/alternar` (desactivar y reactivar);
  - `/documentos/<n>/reemplazar` (conserva la versión anterior).
- **Cómo probarlo:** Taller Demo 1 → Participantes → «Quitar» a Rosa Inventada → motivo «agregada por error» → sale de la lista y queda en el historial.

---

## El día a día de Claudio

| Pasa esto | Claudio hace esto | Proceso | Dónde |
|---|---|---|---|
| Llama una universidad y quiere hacer una actividad | Registra la solicitud (o crea la actividad directo) y anota la llamada | P14, P2, P6 | `+ Solicitud` o `+ Actividad` |
| Llega una persona que no está registrada | La crea desde la actividad con lo que sepa | P3 | Participantes → «Créala aquí mismo» |
| La institución manda una planilla de estudiantes | La carga, revisa los duplicados y confirma | P17 | Participantes → «Cargar listado» |
| Cambia la fecha o se cae la sede | Reprograma con el motivo | P5 | Agenda → Reprogramar |
| Solo sabe que «es en Hualpén» | Indica la comuna como zona, sin lugar | P5, P16 | Información → Territorios |
| Alguien pregunta «¿qué hicimos con esa organización?» | Abre su ficha | P9, P4 | Organización → Actividades y proyectos |
| La Dirección pregunta qué se hace en una comuna | Abre la comuna, o la exporta | P16, P20 | Territorio → la comuna |
| Le prometen enviar algo mañana | Registra el contacto con próxima acción | P6 | «Registrar interacción» |
| Recibe una carta o un certificado | Lo sube a la actividad o a la persona | P7 | Documentos → «Subir nuevo» |
| Una ficha en papel trae datos de una persona | Transcribe con el documento al lado | P7 | Documento → «Transcribir» |
| Termina la actividad | Marca asistencia, escribe el resultado y finaliza | P8 | Asistencia → Resultados → Finalizar |
| Llegó alguien que no estaba | Lo agrega como asistente | P8 | Asistencia → «+ Agregar persona que llegó» |
| Cada martes hay sesión del taller | Anota la minuta de la sesión | P18 | Sesiones y minutas |
| Agregó a alguien por error | Lo quita con motivo (queda en el historial) | P21 | Participantes → Quitar |
| Una persona quedó registrada dos veces | Le pide al Administrador unir las fichas | P21 | Persona → Unir (Administrador) |
| Cambió la directiva de la junta | Cierra los cargos antiguos y agrega los nuevos | P4, P9 | Organización → Personas relacionadas |
| Quiere ver todo lo de una campaña | Abre el proyecto | P11 | Proyectos |
| Necesita un tipo de actividad nuevo | Lo agrega en Catálogos | P12 | Catálogos |
| Una persona pide sus datos personales | Descarga su Excel de datos | P20 | Persona → «Datos personales» |
| Olvidó su contraseña | El Administrador la restablece | P13 | Administración → Usuarios |

---

## Alcance y limitaciones

### Lo que se ve
- Registrar y consultar actividades, personas, organizaciones, comunidades, lugares, territorio, documentos, contactos, sesiones y resultados.
- Dos perfiles: Gestor (opera) y Administrador (cuida el sistema).
- Funciona sin internet, en un solo computador.

### Lo que no hace
- No tiene portal público ni cuentas para alumnos, voluntarios o vecinos.
- No envía mensajes, correos ni notificaciones.
- No se usa desde otros equipos ni desde el celular: el servidor solo escucha en el propio computador.
- No maneja dinero. La app de finanzas está oculta.
- No tiene galería ni trata las imágenes de forma especial.
- No asigna personas por su cuenta: solo sugiere.

### Lo oculto que conviene saber
- **Segunda fase oculta:** reuniones con asistentes, tareas, beneficiarios, verificaciones, postulaciones y finanzas existen, pero no aparecen (`SEGUNDA_FASE=False`). Se encienden en `.env`.
- **Datos sensibles:** la ficha de persona tiene pestañas con 🔒: Direcciones, Contacto de emergencia, Datos sensibles, Apoderados y Verificaciones (esta última es de 2.ª fase), más Consentimientos. Las de emergencia, sensibles, apoderados y verificaciones solo las ve quien tiene el permiso «ver datos sensibles». **Hoy el Gestor y el Administrador tienen ese permiso.** `DATOS_SENSIBLES=False` oculta la pestaña Datos sensibles.
- Una persona **desactivada** sigue en sus actividades pasadas, pero no se ofrece como candidata.
- Un documento **restringido** no se abre pegando su dirección, ni aparece en la búsqueda de quien no tiene permiso.
- Toda descarga, exportación, ingreso, cuenta creada y cambio de rol queda en la **auditoría**, aunque no se vea en pantalla.
- Cada cambio de una ficha queda en su **Historial**, con la versión anterior.
- Tras 5 intentos fallidos, la cuenta se bloquea 15 minutos.
- La sesión se cierra tras 60 minutos sin uso.
- Antes de aplicar cambios en la base, `iniciar.bat` hace un respaldo.

### Restricciones fijas (lo que el sistema impide)
1. Entrar sin cuenta, con la cuenta desactivada o sin permiso (403).
2. Guardar un RUT inválido o uno que ya tiene otra persona.
3. Agregar a la misma persona con el mismo rol dos veces en una actividad.
4. Una hora de término anterior a la de inicio.
5. Borrar algo con historia: no hay botón Eliminar; se desactiva, se archiva o se cancela.
6. Modificar una programación anterior: se crea una versión nueva.
7. Confirmar sin responsable, fecha y lugar (o modalidad virtual).
8. Confirmar con el lugar ocupado o sobre su capacidad, salvo que se active el ajuste [V#3].
9. Finalizar sin asistencia (o «sin registro») y sin resultado.
10. Editar una actividad realizada o reabrir una cancelada.
11. Subir un archivo de tipo no permitido, vacío o de más de 25 MB.
12. Un sector que no pertenece a la comuna de la dirección.

### Lo que avisa pero deja seguir (flexible)
- Una persona u organización que parece repetida: «Usar existente» o «Crear de todos modos».
- Pasar la capacidad del lugar al agregar participantes.
- Una persona que ya tiene otra actividad a esa hora.
- Una fecha que ya pasó, o un fin de semana o feriado.
- Un lugar que pertenece a una organización que no está en la actividad.
- Una actividad próxima sin participantes (aviso en el Panel).

### Lo que es opcional (nada obligatorio salvo lo mínimo)
- **Persona:** solo el nombre. RUT, contactos y dirección se agregan después.
- **Actividad:** solo el nombre. Tipo, fecha, lugar, personas y proyecto se agregan después.
- **Solicitud:** casi nada; el contacto puede quedar «por identificar».
- **Organización:** nombre y tipo. RUT y dirección son opcionales.
- **Lugar, zona y proyecto:** opcionales en la actividad.

### Rigideces detectadas (propuestas, no aplicadas)

| Dónde | Hoy | Propuesta para hacerlo más flexible |
|---|---|---|
| Confirmar actividad | Bloquea si falta responsable, fecha o lugar | Mantener (es la regla de docs/CONTEXTO.md) o pasar a aviso, como dice tu documento §6 |
| Capacidad y lugar ocupado | Bloquean la confirmación | Activar `CONFIRMAR_CON_CONFLICTO_CRITICO` para confirmar indicando un motivo [V#3] |
| Asistencia y finalizar | Solo desde el día de la actividad | Permitir registrar antes, con aviso |
| Cancelada | No se puede reabrir | Permitir volver a Pendiente con motivo |
| Crear lugar desde la agenda | Exige tipo; no ofrece sector | Tipo opcional y agregar el sector |
| Interacción | Exige persona u organización | Permitir «por identificar», como en las solicitudes |
| Documento | Debe quedar ligado a una ficha | Permitir subirlo suelto y ligarlo después |
| Ficha de persona | Hasta 18 pestañas | Agrupar las menos usadas en «Más datos» |

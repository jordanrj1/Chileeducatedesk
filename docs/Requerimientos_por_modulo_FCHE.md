# FCHE — Requerimientos por módulo
Roles, historias de usuario, botones y justificación

Etiquetas: [O] oficial (documentos 01 a 06) · [D] evidencia en documentos reales de FCHE · [P] propuesta de diseño · [V] por validar con Claudio o Manuel.
Entre paréntesis va el ID del requerimiento (AC-01, PE-03, etc.) para poder seguirlo.

---

## ROLES

**Gestor (Claudio, Director Ejecutivo).** Es el actor principal. Tiene la única cuenta operativa y hace toda la digitación: registra solicitudes, personas, organizaciones, lugares, actividades, agenda, interacciones, asistencia, resultados y documentos. Consulta el historial, busca y exporta. Puede agregar valores a los catálogos. No administra cuentas ni la estructura técnica.

**Administrador (programador).** Crea y desactiva cuentas, asigna roles, administra la estructura de los catálogos, consulta la auditoría, administra respaldos y migraciones, y carga el territorio oficial. Puede ver todos los datos, pero solo para mantenimiento. No digita la operación diaria.

**Personas sin cuenta.** Estudiantes, practicantes, ayudantes, voluntarios, tutores, beneficiarios, vecinos, contactos de instituciones y autoridades. Existen en el sistema, tienen historial y aparecen en las actividades, pero **no ingresan**. La cuenta no se crea al registrar una persona [O, doc 01, 02, 06].

**Opcionales que no se crean ahora:** un operador interno adicional y un tutor externo con cuenta [O, doc 02].

---

## MÓDULO 1 · ACCESO Y SESIÓN (AC)

**Por qué existe.** El sistema guarda datos personales de voluntarios, estudiantes y menores. Sin acceso controlado cualquiera podría verlos o modificarlos. [O, RF-01, RNF-01]

**Quién lo usa.** Gestor: ingresa y administra su propia cuenta. Administrador: ingresa y restablece contraseñas de otras cuentas.

**Cómo lo ve Claudio.** Abre el navegador y ve una pantalla simple con el logo de FCHE, el campo de correo, el de contraseña y el botón [Ingresar]. Al entrar llega al Panel. Arriba a la derecha ve su nombre, y al hacer clic aparecen [Mi cuenta] y [Cerrar sesión]. Si abre cualquier enlace sin haber ingresado, vuelve a la pantalla de ingreso.

**Historias de usuario**
- HU-AC-01. Como Gestor, quiero ingresar con mi correo y mi contraseña, para trabajar con los permisos que me corresponden. (AC-01)
- HU-AC-02. Como Gestor, quiero que, si mi cuenta está desactivada, el sistema me explique con claridad que no puedo entrar y a quién consultar, para no pensar que es una falla. (AC-02)
- HU-AC-03. Como Gestor, quiero que mi sesión se cierre sola después de un rato sin uso, para que nadie vea datos personales si dejo el computador abierto. (AC-04) [P]
- HU-AC-04. Como Gestor, quiero cambiar mi contraseña desde Mi cuenta, para mantenerla segura. (AC-05)
- HU-AC-05. Como Gestor, quiero ver una pantalla clara cuando no tengo permiso o cuando la página no existe, con un botón para volver, para no quedarme perdido. (AC-06)
- HU-AC-06. Como Administrador, quiero restablecer la contraseña de una cuenta, para ayudar cuando se olvida. (AC-05) [V]
- HU-AC-07. Como Gestor, quiero que todas las pantallas privadas me pidan ingresar si no hay sesión, para que nadie entre por un enlace directo. (AC-03)

**Botones.** [Ingresar] · [Mi cuenta] · [Cambiar contraseña] · [Guardar] · [Cerrar sesión] · [Volver] · [Ir al inicio]

**Reglas.** Si los datos son incorrectos, el mensaje no revela si el correo existe. La recuperación sin ayuda del administrador es [V].

---

## MÓDULO 2 · USUARIOS, ROLES Y PERMISOS (US)

**Por qué existe.** La operación y la administración son trabajos distintos. Hay que decidir quién entra y qué puede hacer, sin crear una cuenta para cada persona registrada. [O, doc 02, RF-02]

**Quién lo usa.** Solo el Administrador. Claudio no ve esta sección en su menú.

**Cómo lo ve el Administrador.** En Administración → Usuarios ve una tabla con nombre, correo, rol, estado y último ingreso. Con [+ Nuevo usuario] busca una persona ya registrada, elige el rol y el estado, y guarda. Si la persona no existe, primero se registra en Personas.

**Historias de usuario**
- HU-US-01. Como Administrador, quiero crear una cuenta solo para una persona ya registrada, para que la cuenta y la ficha de la persona sean la misma identidad. (US-01)
- HU-US-02. Como Administrador, quiero asignar uno de dos roles, Gestor o Administrador, para que cada quien haga lo que corresponde. (US-02)
- HU-US-03. Como Administrador, quiero desactivar o reactivar una cuenta sin borrar a la persona, para quitar el acceso conservando su historial. (US-03)
- HU-US-04. Como Administrador, quiero que el sistema registre quién creó una cuenta y quién cambió un rol, para tener trazabilidad. (US-05)
- HU-US-05. Como Gestor, quiero que mis permisos se revisen en el servidor y no solo en la pantalla, para que un botón oculto no se pueda usar por otro camino. (US-04)

**Botones.** [+ Nuevo usuario] · [Buscar persona] · [Editar] · [Cambiar rol] · [Activar] · [Desactivar] · [Restablecer contraseña] · [Guardar] · [Cancelar]

**Reglas.** Una persona tiene como máximo una cuenta. Las cuentas no se eliminan. El Administrador ve los datos solo para mantenimiento (US-06) [P].

---

## MÓDULO 3 · TERRITORIO (TE)

**Por qué existe.** Claudio muchas veces sabe "es en Hualpén" o "San Pedro de la Costa, etapa 2" antes de tener un lugar. Los documentos de FCHE usan región, comuna, sector, villa o población, y las mismas direcciones se repiten en personas, organizaciones y lugares. [D]

**Quién lo usa.** Gestor: consulta y crea sectores que falten. Administrador: carga el territorio oficial.

**Cómo lo ve Claudio.** En Territorio navega región → provincia → comuna. La ficha de una comuna tiene pestañas de Sectores, Lugares, Organizaciones y Actividades, con un contador en cada una. Dentro de un sector puede haber otros sectores. En cualquier formulario de dirección elige región, provincia, comuna y sector en cascada, y si el sector no existe lo crea con [+ Crear sector] sin salir.

**Historias de usuario**
- HU-TE-01. Como Gestor, quiero elegir una dirección por región, provincia, comuna y sector, para no escribirla a mano ni equivocarme. (TE-01, TE-03)
- HU-TE-02. Como Gestor, quiero registrar sectores dentro de sectores, por ejemplo las etapas de San Pedro de la Costa, para reflejar cómo se nombran los lugares en realidad. (TE-02)
- HU-TE-03. Como Gestor, quiero ver desde una comuna o un sector sus lugares, organizaciones y actividades, para responder "qué hemos hecho en Hualpén". (TE-04)
- HU-TE-04. Como Gestor, quiero crear un sector nuevo desde el formulario y que el sistema reconozca nombres escritos distinto, para no tener el mismo sector repetido. (TE-06)
- HU-TE-05. Como Gestor, quiero que cada municipalidad quede ligada a su comuna, para encontrarla desde el territorio. (TE-05) [P]
- HU-TE-06. Como Administrador, quiero cargar región, provincia y comuna desde una fuente oficial, para que no dependan de lo que alguien escriba. (TE-01)

**Botones.** [+ Crear sector] · [Editar sector] · [Agregar nombre alternativo] · [Ver actividades de esta comuna] · [Ver lugares] · [Ver organizaciones] · [Volver]

**Reglas.** El sector debe pertenecer a la comuna de la dirección. Región y provincia no se guardan en cada dirección: se deducen de la comuna.

---

## MÓDULO 4 · PERSONAS (PE)

**Por qué existe.** Una misma persona aparece en minutas, fichas, cartas y actividades. Hoy se repite en cada documento. El sistema la guarda una vez y acumula su trayectoria. [O, RF-03, RF-04, RF-05, doc 04]

**Quién lo usa.** Gestor: crea, edita, relaciona y desactiva. Administrador: solo mantenimiento.

**Cómo lo ve Claudio.** En Personas ve el buscador y los filtros (tipo de relación, organización, comuna, estado del registro), con la lista debajo y el botón [+ Nueva persona]. Al crear elige entre ficha rápida (nombre y un contacto) y ficha completa. La ficha de una persona tiene pestañas: Datos, Contactos, Formación y organizaciones, Participaciones, Documentos e Historial. Los datos restringidos muestran un candado.

**Historias de usuario**
- HU-PE-01. Como Gestor, quiero registrar a una persona solo con su nombre, para no perder a alguien mientras reúno el resto de sus datos. (PE-01, PE-02)
- HU-PE-02. Como Gestor, quiero que el sistema me muestre posibles coincidencias por nombre, RUT o correo antes de crear, para no duplicar a nadie. Debo poder elegir [Usar existente] o [Crear de todos modos]. (PE-04, NF-09)
- HU-PE-03. Como Gestor, quiero escribir el RUT con o sin puntos y que el sistema lo valide y lo guarde igual, para que "12.345.678-5" y "12345678-5" sean la misma persona. Si no tengo RUT, debo poder seguir. (PE-03)
- HU-PE-04. Como Gestor, quiero anotar de dónde llegó la persona (invitación, difusión, interés propio, derivación o búsqueda activa), para conocer cómo se acerca la gente. (PE-05)
- HU-PE-05. Como Gestor, quiero agregar varios contactos a una persona (teléfono móvil o fijo, correo, sitio web, red social) y que el teléfono quede en un formato único. (PE-06)
- HU-PE-06. Como Gestor, quiero relacionar a una persona con instituciones, carreras y organizaciones, indicando cargo y fechas, para ver su recorrido. (PE-07)
- HU-PE-07. Como Gestor, quiero que una persona acumule roles (estudiante, practicante, ayudante, voluntario, tutor, contacto institucional) sin crear otra ficha. (PE-08)
- HU-PE-08. Como Gestor, quiero marcar si un registro está activo, incompleto, por verificar o desactualizado, para saber qué completar primero. (PE-09)
- HU-PE-09. Como Gestor, quiero ver una ficha con datos, contactos, formación, participaciones, documentos e historial, para tener todo en un solo lugar. (PE-11)
- HU-PE-10. Como Gestor, quiero que datos como el contacto de emergencia o la información de menores se pidan solo cuando hacen falta y con acceso restringido. (PE-12) [V]
- HU-PE-11. Como Gestor, quiero desactivar a una persona en vez de eliminarla, para no perder su historial. (PE-10)

**Botones.** [+ Nueva persona] · [Ficha rápida] · [Ficha completa] · [Buscar] · [Ver] · [Editar] · [Agregar contacto] · [Agregar organización o carrera] · [Agregar documento] · [Ver historial] · [Desactivar] · [Guardar] · [Guardar y completar después] · [Usar existente] · [Crear de todos modos] · [← Volver]

**Reglas.** Solo el nombre es obligatorio. El RUT es único cuando existe. El sistema avisa de duplicados pero no fusiona ni bloquea por su cuenta. Los cargos y las relaciones son históricos.

---

## MÓDULO 5 · ORGANIZACIONES Y CARRERAS (OR)

**Por qué existe.** Universidades, municipalidades, juntas de vecinos, empresas y fundaciones aparecen en cartas, minutas y postulaciones, con varios contactos y cargos que cambian. [O, RF-06, RF-07, RF-08]

**Quién lo usa.** Gestor: crea y mantiene. Administrador: solo mantenimiento.

**Cómo lo ve Claudio.** En Organizaciones ve una lista con buscador y filtro por tipo. La ficha tiene pestañas: Datos, Contactos, Personas relacionadas (con cargo y fechas), Carreras (solo para instituciones educativas), Actividades, Documentos e Historial. La propia Fundación aparece como una organización más, marcada como propia, con sus contactos por propósito (institucional, cartas, donaciones).

**Historias de usuario**
- HU-OR-01. Como Gestor, quiero registrar organizaciones con un tipo común (institución educativa, municipalidad, junta o comité, empresa o partner, fundación u ONG, otra), para tratarlas igual. (OR-01)
- HU-OR-02. Como Gestor, quiero buscar antes de crear y no duplicar una organización por cada contacto. (OR-02)
- HU-OR-03. Como Gestor, quiero mantener varios contactos y varias personas por organización, con su cargo y fechas, para saber quién era presidente en cada período. (OR-03)
- HU-OR-04. Como Gestor, quiero asociar carreras a una institución educativa, para ordenar a los estudiantes por institución y carrera. (OR-04)
- HU-OR-05. Como Gestor, quiero guardar el RUT o la personalidad jurídica cuando existan, sin que sean obligatorios. (OR-05)
- HU-OR-06. Como Gestor, quiero registrar a la propia Fundación como organización con contactos por propósito, porque hoy circulan más de un teléfono y un correo. (OR-06)
- HU-OR-07. Como Gestor, quiero ver las actividades en las que participó una organización, para responder "qué hicimos con ellos". (OR-07)
- HU-OR-08. Como Gestor, quiero desactivar una organización sin eliminarla. (OR-08)

**Botones.** [+ Nueva organización] · [Buscar] · [Ver] · [Editar] · [Agregar contacto] · [Agregar persona con cargo] · [Agregar carrera] · [Agregar documento] · [Ver actividades] · [Ver historial] · [Desactivar] · [Guardar] · [← Volver]

**Reglas.** Los cargos son históricos: el directorio no se reemplaza, se cierra y se abre uno nuevo. Una organización puede estar registrada sin que tenga cuenta.

---

## MÓDULO 6 · LUGARES (LU)

**Por qué existe.** Las actividades se hacen en bibliotecas, sedes vecinales, comisarías, salones y espacios virtuales. La capacidad y las condiciones deciden si se puede usar. [O, RF-16]

**Quién lo usa.** Gestor.

**Cómo lo ve Claudio.** Una lista de lugares con buscador. La ficha muestra Datos, Dirección, Capacidad y condiciones, y Actividades realizadas. Al programar una actividad puede crear un lugar nuevo en un modal sin salir de la agenda.

**Historias de usuario**
- HU-LU-01. Como Gestor, quiero registrar un lugar con dirección, comuna, sector, capacidad y condiciones. (LU-01)
- HU-LU-02. Como Gestor, quiero reutilizar un lugar en varias actividades y ver su historial de uso. (LU-02)
- HU-LU-03. Como Gestor, quiero indicar la organización dueña del lugar, por ejemplo una biblioteca municipal. (LU-03)
- HU-LU-04. Como Gestor, quiero crear un lugar desde la agenda sin salir de la actividad. (LU-04)
- HU-LU-05. Como Gestor, quiero que la capacidad del lugar cuente cuando se valida una actividad. (LU-05)

**Botones.** [+ Nuevo lugar] · [Buscar] · [Ver] · [Editar] · [Ver actividades realizadas] · [Desactivar] · [Guardar] · [← Volver]

---

## MÓDULO 7 · SOLICITUDES Y OPORTUNIDADES (SO)

**Por qué existe.** Una actividad nace de una solicitud externa o de una búsqueda activa, y muchas veces con datos incompletos. Hay que registrarla antes de saber si se hará. [O, RF-09, RF-10, doc 01, doc 04]

**Quién lo usa.** Gestor.

**Cómo lo ve Claudio.** En Solicitudes ve una lista con estado, origen y fecha. [+ Nueva solicitud] y [+ Nueva oportunidad] abren el mismo formulario: origen, canal, fecha, motivo, contacto (persona u organización, o "por identificar") y estado. La ficha muestra sus interacciones y un botón [Crear actividad].

**Historias de usuario**
- HU-SO-01. Como Gestor, quiero registrar una solicitud aunque casi no tenga datos, para no perder un contacto. (SO-01)
- HU-SO-02. Como Gestor, quiero guardar origen (externo o búsqueda activa), canal, fecha, motivo y estado. (SO-02)
- HU-SO-03. Como Gestor, quiero dejar el contacto como "por identificar" cuando no sé quién llamó. (SO-03)
- HU-SO-04. Como Gestor, quiero seguir cada solicitud como pendiente, en seguimiento, convertida o descartada con motivo. (SO-04) [P]
- HU-SO-05. Como Gestor, quiero convertir una solicitud en actividad sin volver a escribir sus datos. (SO-05)
- HU-SO-06. Como Gestor, quiero que una solicitud pueda quedar sin actividad. (SO-06)

**Botones.** [+ Nueva solicitud] · [+ Nueva oportunidad] · [Registrar interacción] · [Cambiar estado] · [Crear actividad] · [Descartar] · [Guardar] · [← Volver]

---

## MÓDULO 8 · INTERACCIONES Y CONVOCATORIA (IN)

**Por qué existe.** Gran parte del trabajo es llamar, escribir, reunirse y esperar respuesta. Hoy eso se pierde en llamadas y mensajes. El sistema solo **registra**: la comunicación misma se hace por fuera (WhatsApp, correo y automatizaciones están fuera de esta etapa). [O, RF-11, RF-21]

**Quién lo usa.** Gestor.

**Cómo lo ve Claudio.** Dentro de una solicitud, actividad, persona u organización hay [Registrar interacción], con tipo (llamada, correo, mensaje, reunión), con quién, fecha, resultado y próxima acción con fecha. Dentro de una actividad hay una lista de convocados, con su estado de interés y disponibilidad, y las invitaciones y solicitudes de apoyo con su estado.

**Historias de usuario**
- HU-IN-01. Como Gestor, quiero registrar un llamado, correo, mensaje o reunión con fecha, canal, contacto y resultado. (IN-01)
- HU-IN-02. Como Gestor, quiero anotar la próxima acción con fecha y verla en pendientes. (IN-02)
- HU-IN-03. Como Gestor, quiero asociar una interacción a una persona, organización, solicitud o actividad. (IN-03)
- HU-IN-04. Como Gestor, quiero registrar a quién contacté y su interés y disponibilidad, para saber con quién cuento. (IN-04)
- HU-IN-05. Como Gestor, quiero registrar invitaciones y solicitudes de apoyo como enviada, respondió, aceptó, rechazó o sin respuesta. (IN-05) [D/P]

**Botones.** [Registrar interacción] · [+ Nueva invitación] · [+ Solicitud de apoyo] · [Marcar respuesta] · [Guardar] · [← Volver]

**Reglas.** El sistema no envía mensajes. Una reunión es un tipo de interacción en esta etapa; asistentes y compromisos son segunda fase.

---

## MÓDULO 9 · ACTIVIDADES (AT)

**Por qué existe.** La actividad es el centro del sistema. Une personas, organizaciones, lugar, agenda, documentos y resultados, y puede nacer incompleta y completarse. [O, RF-12 a RF-15, doc 01]

**Quién lo usa.** Gestor. Administrador solo mantenimiento.

**Cómo lo ve Claudio.** En Actividades ve la lista con filtros por fecha, estado, zona, organización y responsable. La ficha central tiene arriba el nombre, el estado y los botones principales, y pestañas: Información, Participantes, Organizaciones, Agenda, Coordinación, Documentos, Resultados e Historial. Un aviso muestra qué falta para poder confirmar.

**Historias de usuario**
- HU-AT-01. Como Gestor, quiero crear una actividad con nombre y tipo, y completarla después. (AT-01)
- HU-AT-02. Como Gestor, quiero registrar objetivo, condiciones, estado y zona. (AT-02)
- HU-AT-03. Como Gestor, quiero indicar uno o varios territorios aunque aún no haya lugar, por ejemplo "Hualpén". (AT-03) [P]
- HU-AT-04. Como Gestor, quiero marcar si la actividad es presencial, virtual o híbrida. (AT-04)
- HU-AT-05. Como Gestor, quiero agregar personas con su rol, estado y asistencia, sin repetir la misma persona y rol. (AT-05)
- HU-AT-06. Como Gestor, quiero agregar organizaciones indicando cómo intervienen y quién es su contacto. (AT-06)
- HU-AT-07. Como Gestor, quiero asignar un responsable de la Fundación, sobre todo cuando no viene un tutor. (AT-07)
- HU-AT-08. Como Gestor, quiero que una jornada contenga otras actividades, como charlas y talleres. (AT-08) [P]
- HU-AT-09. Como Gestor, quiero cambiar el estado de una actividad indicando el motivo. (AT-11)
- HU-AT-10. Como Gestor, quiero cargar un listado de participantes desde una planilla, para no escribirlos uno por uno. (AT-12) [P]
- HU-AT-11. Como Gestor, quiero agrupar actividades bajo un proyecto o campaña si hace falta, sin que sea obligatorio. (AT-09) [V]

**Estados de actividad [O, RF-29]:** planificada, confirmada, reprogramada, suspendida, cancelada, realizada, y pendiente (oportunidad abierta).

**Estados de participación [P]:** invitado, interesado, disponible, confirmado, asistió, no asistió, rechazó, canceló.

**Botones.** [+ Nueva actividad] · [Editar] · [Cambiar estado] · [Agregar participante] · [Buscar candidatos] · [Cargar listado] · [Agregar organización] · [Programar] · [Reprogramar] · [Registrar interacción] · [Agregar documento] · [Registrar asistencia] · [Registrar resultado] · [Ver historial] · [← Volver]

**Reglas.** Crear nunca se bloquea por datos faltantes. Una persona no puede repetirse con el mismo rol en una actividad. Si no existe la persona, se crea en un modal y queda seleccionada.

---

## MÓDULO 10 · AGENDA Y CALENDARIO (AG)

**Por qué existe.** Fechas, lugares y personas cambian por imprevistos. Hay que saber cuál es la programación vigente y qué hubo antes. [O, RF-17, RF-18, RF-29, RNF-15]

**Quién lo usa.** Gestor.

**Cómo lo ve Claudio.** En la pestaña Agenda de una actividad ve la programación vigente (fecha, horario, lugar, estado) y el historial de versiones anteriores. En Calendario ve el mes, la semana o una lista, con los estados diferenciados. Al hacer clic en un evento se abre la actividad.

**Historias de usuario**
- HU-AG-01. Como Gestor, quiero programar fecha, hora de inicio y término, duración, lugar y estado. (AG-01)
- HU-AG-02. Como Gestor, quiero reprogramar y que el sistema conserve la programación anterior. (AG-02)
- HU-AG-03. Como Gestor, quiero que haya una sola programación vigente por actividad, para no confundirme. (AG-03)
- HU-AG-04. Como Gestor, quiero registrar el motivo de cada cambio, y que quede quién lo hizo y cuándo. (AG-04)
- HU-AG-05. Como Gestor, quiero ver el calendario por mes, semana y lista, con los estados distinguibles. (AG-05) [O: estados; P: vistas]
- HU-AG-06. Como Gestor, quiero filtrar el calendario por estado, zona, responsable y organización. (AG-06)
- HU-AG-07. Como Gestor, quiero crear una serie de actividades repetidas, como un taller semanal. (AG-07) [P]

**Botones.** [Programar] · [Reprogramar] · [Ver versiones anteriores] · [Crear serie] · [Mes] · [Semana] · [Lista] · [Filtrar] · [Guardar] · [Cancelar]

**Reglas.** Reprogramar pide motivo. La versión anterior no se edita ni se borra. La opción de reprogramar una actividad realizada es [V].

---

## MÓDULO 11 · COMPATIBILIDAD Y BÚSQUEDA ASISTIDA (VA)

**Por qué existe.** Armar una actividad exige combinar necesidad, personas, lugar, capacidad y fecha. El sistema ayuda a detectar problemas y a encontrar candidatos, pero **nunca decide por Claudio**. [O, RF-19, RF-20, RF-22, doc 06]

**Quién lo usa.** Gestor.

**Cómo lo ve Claudio.** Al pulsar [Confirmar actividad], el sistema revisa y muestra una lista: ✓ compatible, ⚠ advertencia o ✕ incompatibilidad crítica, siempre con el motivo ("el lugar tiene capacidad para 20 y hay 35 inscritos"). Con [Buscar candidatos] abre filtros (zona, área, disponibilidad, institución, carrera, cantidad) y recibe resultados con razones y conflictos. Cada candidato tiene un botón [Agregar a la actividad].

**Historias de usuario**
- HU-VA-01. Como Gestor, quiero que el sistema revise capacidad, horario y condiciones antes de confirmar. (VA-01)
- HU-VA-02. Como Gestor, quiero que los problemas me aparezcan con su motivo, para corregirlos. (VA-02)
- HU-VA-03. Como Gestor, quiero que detecte choques de horario del lugar y de las personas. (VA-03)
- HU-VA-04. Como Gestor, quiero buscar candidatos por tipo de persona, organización, zona, área, disponibilidad, institución, carrera y cantidad. (VA-04)
- HU-VA-05. Como Gestor, quiero ver las razones de cada resultado, y decidir yo. (VA-05)

**Botones.** [Confirmar actividad] · [Buscar candidatos] · [Aplicar filtros] · [Limpiar] · [Ver ficha] · [Agregar a la actividad] · [Corregir] · [← Volver]

**Reglas.** Si se puede confirmar con una incompatibilidad crítica, indicando un motivo, es [V]: RF-22 dice "impedir o advertir". El alcance exacto del matching también es [V] (VA-06).

---

## MÓDULO 12 · DOCUMENTOS (DO)

**Por qué existe.** Cartas, minutas, certificados, fichas y fotos son la evidencia de lo que se hizo. Se guardan como respaldo, y lo que importa de ellos se registra como datos. [O, RF-23, D]

**Quién lo usa.** Gestor. Administrador solo mantenimiento.

**Cómo lo ve Claudio.** En la pestaña Documentos de una actividad (o de una persona u organización) ve la lista con nombre, tipo, fecha y un candado en los restringidos. Con [+ Agregar documento] elige entre [Subir nuevo] y [Asociar existente]. En Documentos busca por tipo, persona, actividad o fecha.

**Historias de usuario**
- HU-DO-01. Como Gestor, quiero adjuntar y asociar documentos a una actividad. (DO-01)
- HU-DO-02. Como Gestor, quiero guardar tipo, nombre, fecha, descripción y quién lo subió. (DO-02)
- HU-DO-03. Como Gestor, quiero usar un mismo documento en una persona y en una actividad sin duplicar el archivo. (DO-03) [P]
- HU-DO-04. Como Gestor, quiero marcar documentos como restringidos, para que solo se vean con permiso. (DO-04)
- HU-DO-05. Como Gestor, quiero que el sistema me avise si el archivo es de un tipo o tamaño no permitido. (DO-05)
- HU-DO-06. Como Gestor, quiero guardar folio, emisor, fecha de emisión y vencimiento en certificados y documentos oficiales. (DO-06) [D/P]

**Botones.** [+ Agregar documento] · [Subir nuevo] · [Asociar existente] · [Ver] · [Descargar] · [Marcar como restringido] · [Guardar] · [← Volver]

**Reglas.** Los archivos se guardan fuera del código y los datos del documento en la base (DO-07). Un documento es evidencia, no se convierte en tablas (DO-08).

---

## MÓDULO 13 · ASISTENCIA, RESULTADOS Y CIERRE (RE)

**Por qué existe.** Una actividad no debería terminar solo en "realizada", sino con la información de lo que ocurrió: quién fue, qué pasó y qué quedó. [O, RF-24]

**Quién lo usa.** Gestor.

**Cómo lo ve Claudio.** Después de la actividad abre Asistencia y ve la lista de participantes con una marca por persona. Si llega alguien que no estaba previsto, lo busca o lo crea al momento. En Resultados escribe observaciones, incidencias y resultado, y adjunta evidencias. Al final pulsa [Finalizar actividad] y la actividad queda como realizada.

**Historias de usuario**
- HU-RE-01. Como Gestor, quiero marcar la asistencia de cada persona. (RE-01)
- HU-RE-02. Como Gestor, quiero agregar en el momento a alguien que llegó sin estar previsto. (RE-02)
- HU-RE-03. Como Gestor, quiero registrar observaciones, incidencias, resultado y evidencias. (RE-03)
- HU-RE-04. Como Gestor, quiero poder finalizar escribiendo "sin registro" cuando falta información, para no inventar datos. (RE-04) [P/V]

**Botones.** [Registrar asistencia] · [+ Agregar persona que llegó] · [Registrar resultado] · [Adjuntar evidencia] · [Marcar sin registro] · [Finalizar actividad] · [Guardar] · [← Volver]

**Reglas.** Los mínimos para finalizar (RE-05) y la posibilidad de reabrir o corregir una actividad realizada (RE-06) son [V].

---

## MÓDULO 14 · HISTORIAL Y TRAZABILIDAD (HI)

**Por qué existe.** Dentro de unos años Claudio querrá saber quién participó, con qué organización, dónde, y qué cambió. Esa memoria es el principal valor del sistema. [O, RF-25, RF-26, RNF-04]

**Quién lo usa.** Gestor: consulta el historial. Administrador: consulta además la auditoría.

**Cómo lo ve Claudio.** Cada ficha (persona, organización, lugar, actividad) tiene una pestaña Historial en forma de línea de tiempo: qué ocurrió, quién lo registró, cuándo y de qué fuente. Con un clic pasa de una ficha a otra: de la persona a la actividad, de la actividad a la organización o al lugar.

**Historias de usuario**
- HU-HI-01. Como Gestor, quiero ver el historial de una persona, organización, lugar o actividad. (HI-01)
- HU-HI-02. Como Gestor, quiero que se registre usuario, fecha, acción y cambios importantes. (HI-02)
- HU-HI-03. Como Gestor, quiero que los cambios conserven la versión anterior. (HI-03)
- HU-HI-04. Como Gestor, quiero saber de qué fuente salió un dato (formulario, carga de listado o documento de origen). (HI-04) [P]
- HU-HI-05. Como Gestor, quiero recorrer el historial de una ficha a otra con un clic. (HI-05)
- HU-HI-06. Como Administrador, quiero consultar la auditoría completa para investigar un cambio. (HI-02)

**Botones.** [Ver historial] · [Ver actividad] · [Ver persona] · [Ver organización] · [Filtrar por fecha] · [← Volver]

---

## MÓDULO 15 · BÚSQUEDA, CONSULTAS Y EXPORTACIÓN (BU)

**Por qué existe.** Claudio piensa "necesito encontrar a esta persona", no "en qué tabla está". [O, RF-27, RF-28]

**Quién lo usa.** Gestor y Administrador (exportar).

**Cómo lo ve Claudio.** Arriba, siempre visible, está el buscador global. Escribe un nombre y recibe resultados agrupados: Personas, Organizaciones, Actividades, Lugares, Documentos. Cada módulo tiene además su propia búsqueda con filtros, orden y paginación. Con [Exportar] descarga lo que está viendo, con los filtros aplicados.

**Historias de usuario**
- HU-BU-01. Como Gestor, quiero buscar en todo el sistema desde un solo lugar. (BU-01) [P]
- HU-BU-02. Como Gestor, quiero filtrar actividades por fecha, estado, zona, organización, institución y responsable. (BU-02)
- HU-BU-03. Como Gestor, quiero que cada módulo tenga su búsqueda, con orden y paginación. (BU-03)
- HU-BU-04. Como Gestor, quiero exportar lo que estoy viendo respetando mis permisos. (BU-04)
- HU-BU-05. Como Gestor, quiero poder responder "qué hicimos con esta organización" o "qué actividades hubo en esta comuna". (BU-05)

**Botones.** [Buscar] · [Aplicar filtros] · [Limpiar] · [Ordenar] · [Exportar] · [Ver] · [← Volver]

---

## MÓDULO 16 · CATÁLOGOS Y CONFIGURACIÓN (CA)

**Por qué existe.** Los tipos de actividad, los roles y los estados cambian con el tiempo. Claudio no debería depender del programador para agregar un tipo nuevo. [O, RF-30, RNF-12]

**Quién lo usa.** Gestor: agrega valores. Administrador: estructura y desactivación.

**Cómo lo ve Claudio.** En Configuración ve la lista de catálogos (tipos de actividad, roles de participación, tipos de organización, estados, canales). Dentro de cada uno puede agregar valores con [+ Agregar valor]. El Administrador, además, puede [Desactivar].

**Historias de usuario**
- HU-CA-01. Como Gestor, quiero agregar valores a los catálogos, para adaptar el sistema sin cambiar el código. (CA-01, CA-02)
- HU-CA-02. Como Administrador, quiero desactivar un valor sin borrarlo, para no perder el historial. (CA-03)
- HU-CA-03. Como Gestor, quiero que el sistema no me deje borrar un valor ya usado. (CA-04)

**Botones.** [+ Agregar valor] · [Editar] · [Desactivar] · [Guardar] · [Cancelar]

---

## MÓDULO 17 · INGESTA DE DATOS (IG)

**Por qué existe.** Claudio es el único que digita, y tiene mucha información en papel, Word y planillas. Hay que hacer la carga cómoda, para que el tiempo de una persona no sea el cuello de botella. [P, D]

**Quién lo usa.** Gestor.

**Cómo lo ve Claudio.** Para registrar a alguien rápido usa la ficha rápida. En el Panel ve una cola de registros incompletos, ordenada por actividades próximas. Para cargar un listado que mandó una institución, lo sube o pega y ve una vista previa con cuatro grupos: nuevos, ya existentes, posibles duplicados y errores. Solo cuando confirma, los datos entran. Para transcribir un documento, lo ve a un lado y el formulario al otro.

**Historias de usuario**
- HU-IG-01. Como Gestor, quiero una ficha rápida con nombre y un dato de contacto, para registrar mientras hablo por teléfono. (IG-01)
- HU-IG-02. Como Gestor, quiero ver una lista de registros incompletos, priorizando a quienes participan en actividades próximas. (IG-02)
- HU-IG-03. Como Gestor, quiero cargar un listado con vista previa de nuevos, existentes, posibles duplicados y errores, y confirmar solo después. (IG-03)
- HU-IG-04. Como Gestor, quiero poder revertir una carga si me equivoqué. (IG-03)
- HU-IG-05. Como Gestor, quiero que RUT, teléfonos y nombres se ordenen solos al ingresar, aunque lleguen como "Nombre Apellido" o "Apellido, Nombre". (IG-04)
- HU-IG-06. Como Gestor, quiero ver el documento junto al formulario mientras transcribo. (IG-05) [P]

**Botones.** [Ficha rápida] · [Completar ahora] · [Completar después] · [Cargar listado] · [Pegar datos] · [Ver vista previa] · [Confirmar carga] · [Revertir carga] · [Cancelar]

**Reglas.** Los teléfonos de las planillas se leen como texto. La importación histórica masiva es [V], porque el tutor pudo marcarla como fuera de esta etapa (IG-06). La carga de un listado por actividad sí es operación normal [O, doc 06].

---

## MÓDULO 18 · PANEL Y NAVEGACIÓN (DA)

**Por qué existe.** Claudio abre el sistema para saber qué tiene que hacer hoy, no para ver tablas. [P]

**Quién lo usa.** Gestor y Administrador.

**Cómo lo ve Claudio.** Al ingresar ve un panel con lo pendiente: actividades incompletas, solicitudes sin respuesta, personas incompletas y tareas por vencer, y acciones rápidas ([+ Solicitud], [+ Actividad], [+ Persona], [+ Organización], [+ Lugar]). El menú lateral tiene Inicio, Solicitudes, Actividades, Calendario, Personas, Organizaciones, Lugares, Documentos y Administración (solo para el Administrador).

**Historias de usuario**
- HU-DA-01. Como Gestor, quiero ver lo pendiente al entrar, para saber por dónde partir. (DA-01)
- HU-DA-02. Como Gestor, quiero un menú simple con los módulos principales. (DA-02)
- HU-DA-03. Como Gestor, quiero un botón "Volver" y un camino de migas en cada ficha, y un aviso si hay cambios sin guardar. (DA-03)
- HU-DA-04. Como Gestor, quiero buscar, seleccionar o crear una persona, organización o lugar sin salir de la actividad. (DA-04)
- HU-DA-05. Como Gestor, quiero que cada pantalla me diga si está cargando, vacía, sin resultados, con error o sin permiso. (DA-05)
- HU-DA-06. Como Gestor, quiero poder consultar el sistema desde el celular. (DA-06) [V]

**Botones.** [+ Solicitud] · [+ Actividad] · [+ Persona] · [+ Organización] · [+ Lugar] · [Ver pendientes] · [Reintentar] · [← Volver]

**Reglas.** Todo listado tiene búsqueda, filtros, orden y paginación. Con un sistema local, cómo llega el celular (red de la Fundación o solo el equipo) es [V].

---

## MÓDULO 19 · PROYECTO O CAMPAÑA, OPCIONAL (PR)

**Por qué existe.** "Proyecto" no existe en el modelo oficial, que va de Solicitud a Actividad. Sí aparece la idea de campaña (por ejemplo, alfabetización) y el tutor pidió ver las actividades agrupadas. [V]

**Quién lo usa.** Gestor.

**Cómo lo ve Claudio.** Una tarjeta de proyecto o campaña que, al abrirla, muestra su equipo, organizaciones y actividades.

**Historias de usuario**
- HU-PR-01. Como Gestor, quiero agrupar actividades bajo un proyecto o campaña, sin que ninguna actividad lo exija. (PR-01) [V]
- HU-PR-02. Como Gestor, quiero ver dentro de un proyecto su equipo, organizaciones y actividades. (PR-02) [V]

**Botones.** [+ Nuevo proyecto] · [Agregar actividad] · [Ver equipo] · [Ver organizaciones] · [Editar]

---

## REGLAS TRANSVERSALES (NF)

- Crear un registro nunca se bloquea por datos faltantes. Solo se exige algo al confirmar y al cerrar. (NF-01)
- Toda validación se repite en el servidor. (NF-02)
- Los datos personales se minimizan y se distinguen en generales, restringidos y sensibles. (NF-03)
- La base y los archivos se respaldan a diario. (NF-04)
- Nunca se elimina un registro que tiene historia. (NF-05)
- El sistema responde con agilidad y puede crecer. (NF-06)
- El sistema funciona sin internet. (NF-07) [P]
- El diseño no cierra la puerta a integraciones futuras. (NF-08)
- Se avisa de duplicados antes de crear personas u organizaciones. (NF-09)

---

## SEGUNDA FASE (con evidencia en documentos reales, no oficial)

Reuniones con asistentes, temas y compromisos · Tareas con varios responsables · Sesiones de una actividad · Beneficiarios identificados · Talleres como diseño reutilizable · Verificaciones de personas con vigencia · Requisitos documentales de fondos concursables · Divisiones electorales · Finanzas (donaciones, presupuesto y movimientos).

---

## PENDIENTES POR VALIDAR

1. Recuperación de contraseña sin el administrador (AC-05).
2. Qué datos de menores se conservan y por cuánto tiempo (PE-12).
3. Si se puede confirmar una actividad con una incompatibilidad crítica, con motivo (VA-02).
4. Alcance exacto del matching (VA-06).
5. Mínimos para finalizar una actividad y si se puede reabrir (RE-05, RE-06).
6. Proyecto o campaña como agrupador opcional (AT-09, PR-01, PR-02).
7. Importación histórica masiva (IG-06).
8. Acceso desde celular a un sistema local (DA-06).
9. Notificaciones internas o por correo (no definidas).
10. Quién será Administrador después del 30-11-2026.

# Inventario de plantillas HTML

Auditoría del 14-10-2026, rama `auditoria/documentacion`. Generado revisando, para cada plantilla, qué vista la nombra (`template_name`, pestañas, `render`) y qué otra plantilla la incluye o la extiende (`include`, `extends`). No se borró ni se movió nada.

## Por qué hay tantas

Hay **108 plantillas**. Parecen muchas, pero casi ninguna es una página completa repetida. El sistema arma cada pantalla con piezas:

- **Una plantilla común por tipo de pantalla** (`generico/`): el listado, el formulario y la ficha con pestañas son las mismas para todos los módulos. Por eso `generico/formulario.html` la usan 99 rutas y `generico/lista.html` 23.
- **Una plantilla por pestaña.** Cada ficha (actividad, persona, organización, comuna…) tiene pestañas, y cada pestaña es un archivo corto. Solo la actividad tiene 14 pestañas y la persona 18. Esto explica casi la mitad de los archivos.
- **Fichas cortas a propósito.** `lugares/ficha.html` o `proyectos/ficha.html` tienen 6 líneas: toman la ficha común y le agregan solo la línea de cabecera de ese módulo (estado, comuna, capacidad…). Están casi vacías porque la ficha común hace el resto, no porque falte algo.
- **Trozos reutilizables** (nombre con `_` al inicio): la tabla de documentos, la dirección en cascada, las migas de pan, la paginación. Se escriben una vez y se incluyen donde hagan falta.

## Resumen

| Estado | Cantidad | Qué significa |
|---|---|---|
| En uso | 41 | Página completa que abre una ruta. |
| Fragmento | 53 | Pestaña de una ficha o trozo reutilizable. |
| Casi vacía, a propósito | 10 | Extiende una plantilla común y agrega muy poco. Cumple su función. |
| Duplicada | 3 | Casi igual a otra; conviene unificarlas. |
| Sin uso | 1 | Nadie la usa. |
| **Total** | **108** | De ellas, 6 pertenecen a la 2.ª fase y no se ven con `SEGUNDA_FASE=False`. |

Además existe la carpeta vacía `templates/componentes/` (git no la guarda; es un resto local).

Procesos: P1 a P13 son los de `docs/Procesos_y_pruebas_de_Claudio.md`. «Grupo» = comunidades. «2F» = segunda fase.

## Marco general

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `base.html` | la extienden 31 plantillas (todas las páginas) | Todos | En uso | Marco de todas las páginas: menú lateral, barra superior con el buscador, migas de pan y mensajes. |

## Núcleo: panel, buscador, ayuda

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `nucleo/administracion.html` | ninguna | P13 | **Sin uso** | Página provisoria de F01 («se agrega en las siguientes features»). La reemplazó administracion/indice.html. |
| `nucleo/ayuda.html` | `/ayuda` | P1 | En uso | Muestra el manual de uso dentro del sistema. |
| `nucleo/buscar.html` | `/buscar` | P10 | En uso | Resultados del buscador de arriba, agrupados por personas, organizaciones, actividades, lugares y documentos. |
| `nucleo/dashboard.html` | `/dashboard` | P1 | En uso | Panel de inicio: lo pendiente de hoy (actividades incompletas, solicitudes sin respuesta, personas por completar, próximas acciones) y accesos rápidos. |

## Ingreso y cuenta propia

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `cuentas/login.html` | `/login` | P1 | En uso | Pantalla de ingreso con usuario y contraseña. |
| `cuentas/mi_cuenta.html` | `/mi-cuenta` | P1 | En uso | Datos de la cuenta propia y enlace para cambiar la contraseña. |

## Pantallas de error

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `errores/403.html` | cualquier ruta con error 403 | P1 | En uso | Pantalla «no tienes permiso», con botón para volver. |
| `errores/404.html` | cualquier ruta con error 404 | P1 | En uso | Pantalla «la página no existe», con botón para volver. |
| `errores/500.html` | cualquier ruta con error 500 | P1 | En uso | Pantalla de error interno, sin mostrar detalles técnicos. |

## Piezas comunes (se reutilizan en todos los módulos)

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `generico/_breadcrumb.html` | incluida en 16 plantillas, p. ej. `actividades/candidatos.html` | Todos | Fragmento | Trozo que dibuja las migas de pan (Inicio › Actividades › …). |
| `generico/_campo.html` | incluida en 11 plantillas, p. ej. `actividades/pestanas/resultados.html` | Todos | Fragmento | Trozo que dibuja un campo de formulario con su etiqueta, ayuda y error. |
| `generico/_campos.html` | incluida en `generico/formulario.html`, `personas/nueva.html` | Todos | Fragmento | Trozo que dibuja un formulario completo, agrupado por secciones. |
| `generico/_hijos.html` | 7 rutas, p. ej. `/actividades/<int:pk>`, `/comunidades/<int:pk>` | P3/P4/P9 | Fragmento | Pestaña común para listas dentro de una ficha (contactos, cargos, carreras, organizaciones de una actividad…) con su botón «+ Agregar». |
| `generico/_historial.html` | 7 rutas, p. ej. `/comunidades/<int:pk>`, `/finanzas/<int:pk>` | P9 | Fragmento | Pestaña Historial: qué cambió, quién y cuándo, con la versión anterior. |
| `generico/_paginacion.html` | incluida en `generico/lista.html` | P10 | Fragmento | Trozo con los botones de página anterior y siguiente de los listados. |
| `generico/desactivar.html` | `…/<id>/desactivar` de persona, organización, lugar, comunidad | P9 | En uso | Pide confirmar antes de desactivar un registro y muestra qué quedará afectado. Nunca borra. |
| `generico/detalle.html` | `/colaboraciones/<int:pk>`, `/interacciones/<int:pk>`, `/invitaciones/<int:pk>` | P6 | En uso | Vista simple de un registro sin pestañas (interacción, invitación, solicitud de apoyo). |
| `generico/ficha.html` | 5 rutas, p. ej. `/documentos/<int:pk>`, `/finanzas/<int:pk>` | P9 | En uso | Ficha común con cabecera, botones y pestañas. Las fichas de cada módulo la extienden y solo agregan su cabecera. |
| `generico/formulario.html` | 99 rutas, p. ej. `/actividades/<int:pk>/comunidades/<int:hijo_pk>/alternar`, `/actividades/<int:pk>/comunidades/<int:hijo_pk>/editar` | Todos | En uso | Formulario común para crear o editar cualquier registro, con avisos y botón Volver. |
| `generico/fusionar.html` | `/personas/<id>/fusionar`, `/organizaciones/<id>/fusionar` | P3 | En uso | Une dos fichas repetidas de la misma persona u organización, eligiendo cuál queda. |
| `generico/lista.html` | 23 rutas, p. ej. `/actividades`, `/actividades/exportar` | P10 | En uso | Listado común a todos los módulos: buscador, filtros, orden, paginación, botón crear y exportar. |

## Actividades (el centro)

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `actividades/calendario.html` | `/calendario` | P5 | En uso | Calendario por mes, semana o lista; un clic en el evento abre la actividad. |
| `actividades/candidatos.html` | `/actividades/<int:pk>/candidatos` | P3 | En uso | Búsqueda de candidatos con razones y conflictos. Sugiere, nunca agrega solo. |
| `actividades/confirmar.html` | `/actividades/<int:pk>/confirmar` | P2 | En uso | Revisión antes de confirmar: lista de lo compatible, advertencias e incompatibilidades, con su motivo. |
| `actividades/constancia.html` | `/actividades/<int:pk>/participantes/<int:part_pk>/constancia` | P8 | En uso | Constancia de participación de una persona, lista para imprimir. |
| `actividades/duplicar.html` | `/actividades/<int:pk>/duplicar` | P2 | En uso | Crear una actividad nueva copiando otra, sin participantes ni fechas. |
| `actividades/ficha.html` | `/actividades/<int:pk>` | P2 | En uso | Cabecera de la ficha de actividad: estado, tipo, fecha vigente, comuna y botones (confirmar, programar, finalizar). |
| `actividades/participante_form.html` | `/actividades/<int:pk>/participantes/nuevo` | P3 | Casi vacía, a propósito: solo agrega al formulario común el enlace «créala aquí mismo» | Formulario para agregar un participante; si no existe, ofrece crearlo ahí mismo. |
| `actividades/participante_rapido.html` | `/actividades/<int:pk>/participantes/rapido` | P3 | En uso | Crear una persona nueva con solo el nombre y dejarla agregada a la actividad. |
| `actividades/pestanas/agenda.html` | `/actividades/<int:pk>` | P5 | Fragmento (pestaña) | Pestaña Agenda: programación vigente y versiones anteriores, con botones programar y reprogramar. |
| `actividades/pestanas/alcance.html` | 5 rutas, p. ej. `/actividades/<int:pk>`, `/comunidades/<int:pk>` | P9 | Fragmento (pestaña) | Pestaña Alcance: cuántas personas, horas y comunidades alcanzó. La reutilizan comuna, sector, comunidad y proyecto. |
| `actividades/pestanas/asistencia.html` | `/actividades/<int:pk>` | P8 | Fragmento (pestaña) | Pestaña Asistencia: marcar quién asistió y agregar a quien llegó sin estar previsto. |
| `actividades/pestanas/coordinacion.html` | `/actividades/<int:pk>` | P6 | Fragmento (pestaña) | Pestaña Coordinación: llamadas, correos y reuniones registradas sobre la actividad, y próximas acciones. |
| `actividades/pestanas/documentos.html` | `/actividades/<int:pk>` | P7 | **Duplicada** (de `documentos/pestanas/lista.html`) | Pestaña Documentos de la actividad (subir o asociar). Casi igual a documentos/pestanas/lista.html. |
| `actividades/pestanas/historial.html` | `/actividades/<int:pk>` | P9 | Fragmento (pestaña) | Pestaña Historial de la actividad: cambios de la ficha y de sus participantes. |
| `actividades/pestanas/info.html` | `/actividades/<int:pk>` | P2 | Fragmento (pestaña) | Pestaña Información de la actividad: objetivo, descripción, modalidad, responsable, territorios y actividades hijas. |
| `actividades/pestanas/participantes.html` | `/actividades/<int:pk>` | P3 | Fragmento (pestaña) | Pestaña Participantes: personas con su rol y estado, botones agregar, crear en el momento, cargar listado y buscar candidatos. |
| `actividades/pestanas/publico.html` | `/actividades/<int:pk>` | P2 | Fragmento (pestaña) | Pestaña Público y comunidades: a qué comunidades y territorios va dirigida la actividad. |
| `actividades/pestanas/resultados.html` | `/actividades/<int:pk>` | P8 | Fragmento (pestaña) | Pestaña Resultados: observaciones, incidencias, resultado y botón Finalizar. |
| `actividades/pestanas/sesiones.html` | `/actividades/<int:pk>` | P8 | Fragmento (pestaña) | Pestaña Sesiones y minutas: cada encuentro de una actividad que se repite, con su minuta. |
| `actividades/programar.html` | `/actividades/<int:pk>/programar` | P5 | En uso | Formulario para programar o reprogramar fecha, hora y lugar (con «+ Crear lugar» en ventana). |
| `actividades/quitar.html` | `/actividades/<int:pk>/participantes/<int:part_pk>/quitar` | P3 | En uso | Quitar a un participante agregado por error: pide el motivo y lo deja como «registro erróneo», sin borrarlo. |
| `actividades/sesion.html` | `/actividades/<int:pk>/sesiones/<int:sid>` | P8 | En uso | Ficha de una sesión: fecha, minuta, asistencia de esa sesión y acuerdos. |

## Personas

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `personas/direccion.html` | `/personas/<int:pk>/direcciones/nuevo` | P5 | Casi vacía, a propósito: solo junta el tipo de dirección con la cascada de territorio | Agregar una dirección a una persona eligiendo región, comuna y sector en cascada. |
| `personas/ficha.html` | `/personas/<int:pk>` | P9 | Casi vacía, a propósito: solo agrega la línea de cabecera a la ficha común | Cabecera de la ficha de persona: estado del registro, perfiles, comuna y botones. |
| `personas/nueva.html` | `/personas/nueva` | P3 | En uso | Crear persona: ficha rápida o completa, con aviso de posibles duplicados antes de guardar. |
| `personas/pestanas/consentimientos.html` | `/personas/<int:pk>` | P9 | Fragmento (pestaña) | Pestaña Consentimientos: qué autorizó la persona o su apoderado y cuándo. |
| `personas/pestanas/datos.html` | `/personas/<int:pk>` | P9 | Fragmento (pestaña) | Pestaña Datos de la persona: nombre, RUT, origen, estado y observaciones. |
| `personas/pestanas/sensibles.html` | `/personas/<int:pk>` | P9 | Fragmento (pestaña) | Pestaña Datos sensibles 🔒 (género, pueblo originario, salud, discapacidad), solo con permiso y consentimiento. |
| `personas/pestanas/trayectoria.html` | `/personas/<int:pk>` | P9 | Fragmento (pestaña) | Pestaña Participaciones: todas las actividades de la persona, con rol y asistencia. |

## Organizaciones

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `organizaciones/ficha.html` | `/organizaciones/<int:pk>` | P4 | Casi vacía, a propósito: solo agrega la línea de cabecera a la ficha común | Cabecera de la ficha de organización: tipo, estado, comuna y sitio web. |
| `organizaciones/formulario.html` | `/organizaciones/<int:pk>/editar`, `/organizaciones/nueva` | P4 | En uso | Crear o editar organización, con aviso de duplicados y dirección en cascada. |
| `organizaciones/pestanas/actividades.html` | `/organizaciones/<int:pk>` | P4/P9 | Fragmento (pestaña) | Pestaña Actividades y proyectos: responde «¿qué hicimos con ellos?». |
| `organizaciones/pestanas/info.html` | `/organizaciones/<int:pk>` | P4 | Fragmento (pestaña) | Pestaña Información de la organización. |
| `organizaciones/pestanas/personas.html` | `/organizaciones/<int:pk>` | P4 | Fragmento (pestaña) | Pestaña Personas relacionadas: cargos con fechas (quién era presidente en cada período). |

## Lugares

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `lugares/ficha.html` | `/lugares/<int:pk>` | P5 | Casi vacía, a propósito: solo agrega la línea de cabecera a la ficha común | Cabecera de la ficha de lugar: tipo, comuna y capacidad. |
| `lugares/formulario.html` | `/lugares/<int:pk>/editar`, `/lugares/nuevo` | P5 | Casi vacía, a propósito: solo agrega la dirección en cascada al formulario común | Crear o editar lugar con su dirección en cascada. |
| `lugares/pestanas/disponibilidad.html` | `/lugares/<int:pk>` | P5 | Fragmento (pestaña) | Pestaña Disponibilidad: elegir un día y ver qué actividades ocupan el lugar. |
| `lugares/pestanas/info.html` | `/lugares/<int:pk>` | P5 | Fragmento (pestaña) | Pestaña Información del lugar: dirección, capacidad, condiciones y dueño. |
| `lugares/pestanas/uso.html` | `/lugares/<int:pk>` | P5/P9 | Fragmento (pestaña) | Pestaña Uso histórico: actividades realizadas en el lugar. |

## Solicitudes y oportunidades

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `solicitudes/ficha.html` | `/solicitudes/<int:pk>` | P2 | Casi vacía, a propósito: solo agrega la línea de cabecera a la ficha común | Cabecera de la ficha de solicitud: estado, origen, días abierta y contacto. |
| `solicitudes/nueva.html` | `/solicitudes/nueva` | P2 | En uso | Formulario de nueva solicitud u oportunidad (casi sin datos obligatorios). |
| `solicitudes/pestanas/info.html` | `/solicitudes/<int:pk>` | P2 | Fragmento (pestaña) | Pestaña Información de la solicitud, con botón Crear actividad. |
| `solicitudes/pestanas/interacciones.html` | `/solicitudes/<int:pk>` | P6 | **Duplicada** (de `coordinacion/_interacciones.html`) | Pestaña Seguimiento: contactos registrados sobre la solicitud. |

## Documentos

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `documentos/_lista.html` | incluida en `actividades/pestanas/documentos.html`, `documentos/pestanas/lista.html`, `proyectos/pestanas/documentos.html` | P7 | Fragmento | Trozo con la tabla de documentos (nombre, tipo, fecha, candado, descargar). |
| `documentos/asociar.html` | `/documentos/asociar` | P7 | Casi vacía, a propósito: solo agrega una frase y un campo oculto al formulario común | Asociar un documento ya subido a otra ficha, sin copiar el archivo. |
| `documentos/nuevo.html` | `/documentos/nuevo` | P7 | En uso | Subir un documento y asociarlo a una actividad, persona, organización o proyecto. |
| `documentos/pestanas/datos.html` | `/documentos/<int:pk>` | P7 | Fragmento (pestaña) | Pestaña Datos de la ficha de documento: tipo, fechas, folio, emisor y dónde está asociado. |
| `documentos/pestanas/lista.html` | `/organizaciones/<int:pk>`, `/personas/<int:pk>`, `/solicitudes/<int:pk>` | P7 | Fragmento (pestaña) | Pestaña Documentos de persona, organización y solicitud. |
| `documentos/pestanas/origen.html` | 6 rutas, p. ej. `/actividades/<int:pk>`, `/lugares/<int:pk>` | P9 | Fragmento (pestaña) | Pestaña Origen: de qué documento o carga salió cada dato de la ficha. |
| `documentos/transcribir.html` | `/documentos/<int:pk>/transcribir` | P7 | En uso | Documento a un lado y formulario al otro para copiar sus datos. |

## Proyectos (agrupador opcional)

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `proyectos/ficha.html` | `/proyectos/<int:pk>` | P11 | Casi vacía, a propósito: solo agrega la línea de cabecera a la ficha común | Cabecera de la ficha de proyecto: estado, zona, fechas y responsable. |
| `proyectos/pestanas/actividades.html` | `/proyectos/<int:pk>` | P11 | Fragmento (pestaña) | Pestaña Actividades del proyecto, con «+ Nueva actividad» ya ligada. |
| `proyectos/pestanas/beneficiarios.html` | `/proyectos/<int:pk>` | P11 · 2F | Fragmento (pestaña) · oculta (2.ª fase) | Pestaña Beneficiarios del proyecto (2F: oculta). |
| `proyectos/pestanas/documentos.html` | `/proyectos/<int:pk>` | P11/P7 | **Duplicada** (de `documentos/pestanas/lista.html`) | Pestaña Documentos del proyecto. Casi igual a documentos/pestanas/lista.html. |
| `proyectos/pestanas/presupuesto.html` | `/proyectos/<int:pk>` | 2F | Fragmento (pestaña) · oculta (2.ª fase) | Pestaña Presupuesto del proyecto (2F finanzas: oculta). |
| `proyectos/pestanas/resumen.html` | `/proyectos/<int:pk>` | P11 | Fragmento (pestaña) | Pestaña Resumen del proyecto: estado, zona, área, fechas y responsable. |

## Comunidades (grupos)

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `comunidades/ficha.html` | `/comunidades/<int:pk>` | Grupo | Casi vacía, a propósito: solo agrega la línea de cabecera y un botón a la ficha común | Cabecera de la ficha de comunidad (grupo de vecinos, curso, comité…): tipo, territorio e integrantes. |
| `comunidades/pestanas/actividades.html` | `/comunidades/<int:pk>` | Grupo/P9 | Fragmento (pestaña) | Pestaña Actividades y proyectos de la comunidad. |
| `comunidades/pestanas/info.html` | `/comunidades/<int:pk>` | Grupo | Fragmento (pestaña) | Pestaña Información de la comunidad. |

## Coordinación (interacciones; reuniones y tareas son 2.ª fase)

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `coordinacion/_interacciones.html` | `/personas/<int:pk>` | P6 | Fragmento | Pestaña Interacciones de la persona: llamadas, correos y reuniones con ella. |
| `coordinacion/pestanas/compromisos.html` | `/reuniones/<int:pk>` | 2F | Fragmento (pestaña) · oculta (2.ª fase) | Compromisos de una reunión (2F: oculta). |
| `coordinacion/pestanas/reunion_datos.html` | `/reuniones/<int:pk>` | 2F | Fragmento (pestaña) · oculta (2.ª fase) | Datos de una reunión con asistentes (2F: oculta). |
| `coordinacion/pestanas/tarea_datos.html` | `/tareas/<int:pk>` | 2F | Fragmento (pestaña) · oculta (2.ª fase) | Datos de una tarea con responsables (2F: oculta). |

## Carga de listados

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `importaciones/resumen.html` | `/importaciones/<int:pk>` | P3 | En uso | Resumen de una carga ya hecha, con botón para revertirla. |
| `importaciones/revisar.html` | `/importaciones/<int:pk>/revisar` | P3 | En uso | Vista previa de una planilla: nuevos, existentes, posibles duplicados y errores, antes de confirmar. |

## Territorio

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `territorio/_comunas_con_presencia.html` | incluida en `territorio/indice.html`, `territorio/region.html` | P5 | Fragmento | Trozo con las tarjetas de comunas con trabajo (índice y región). |
| `territorio/_direccion.html` | incluida en `lugares/formulario.html`, `organizaciones/formulario.html`, `personas/direccion.html` | P5 | Fragmento | Trozo de dirección en cascada: región → comuna → sector, con «+ Crear sector». |
| `territorio/ficha.html` | `/territorio/comuna/<int:pk>`, `/territorio/sector/<int:pk>` | P5/P9 | En uso | Cabecera de la ficha de comuna o sector: región, municipalidad y botones «+ Comunidad / Organización / Lugar / Actividad». |
| `territorio/indice.html` | `/territorio` | P5/P10 | En uso | «Dónde trabajamos»: comunas con trabajo registrado, buscador de comuna y todas las regiones. |
| `territorio/pestanas/_persona.html` | incluida en `territorio/pestanas/personas.html` | P9 | Fragmento | Trozo: una fila de persona con su comunidad y perfiles. |
| `territorio/pestanas/actividades.html` | `/territorio/comuna/<int:pk>`, `/territorio/sector/<int:pk>` | P9 | Fragmento (pestaña) | Pestaña Actividades de la comuna o sector. |
| `territorio/pestanas/comunidades.html` | `/territorio/comuna/<int:pk>`, `/territorio/sector/<int:pk>` | Grupo | Fragmento (pestaña) | Pestaña Comunidades de la comuna o sector. |
| `territorio/pestanas/lugares.html` | `/territorio/comuna/<int:pk>`, `/territorio/sector/<int:pk>` | P5 | Fragmento (pestaña) | Pestaña Lugares de la comuna o sector. |
| `territorio/pestanas/nombres.html` | `/territorio/sector/<int:pk>` | P5 | Fragmento (pestaña) | Pestaña Nombres alternativos de un sector (para reconocer escrituras distintas). |
| `territorio/pestanas/organizaciones.html` | `/territorio/comuna/<int:pk>`, `/territorio/sector/<int:pk>` | P4 | Fragmento (pestaña) | Pestaña Organizaciones de la comuna, agrupadas por tipo. |
| `territorio/pestanas/personas.html` | `/territorio/comuna/<int:pk>`, `/territorio/sector/<int:pk>` | P9 | Fragmento (pestaña) | Pestaña Personas: residentes y miembros de comunidades de la comuna. |
| `territorio/pestanas/resumen.html` | `/territorio/comuna/<int:pk>`, `/territorio/sector/<int:pk>` | P5/P9 | Fragmento (pestaña) | Pestaña Resumen de la comuna: cifras clicables, organizaciones por tipo, tabla por sector, próximas actividades y minutas. |
| `territorio/pestanas/sectores.html` | `/territorio/comuna/<int:pk>`, `/territorio/sector/<int:pk>` | P5 | Fragmento (pestaña) | Pestaña Sectores de la comuna (con sectores dentro de sectores). |
| `territorio/region.html` | `/territorio/region/<int:pk>` | P5 | En uso | Ficha de región: comunas con presencia y lista por provincia. |

## Administración (solo Administrador)

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `administracion/catalogo.html` | `/administracion/catalogos/<slug:slug>/` | P12 | En uso | Valores de un catálogo, con agregar, editar y desactivar. |
| `administracion/catalogos.html` | `/administracion/catalogos/` | P12 | En uso | Lista de catálogos (listas de opciones) que se pueden editar. |
| `administracion/indice.html` | `/administracion/` | P13 | En uso | Menú de Administración (solo Administrador): usuarios, roles, catálogos, auditoría, respaldos. |
| `administracion/rol_editar.html` | `/administracion/roles/<int:pk>` | P13 | En uso | Marcar o desmarcar los permisos de un rol. |
| `administracion/roles.html` | `/administracion/roles` | P13 | En uso | Lista de roles (Gestor, Administrador) y sus permisos. |
| `administracion/usuario_form.html` | `/administracion/usuarios/<int:pk>/editar`, `/administracion/usuarios/nuevo` | P13 | En uso | Crear o editar una cuenta, eligiendo una persona ya registrada y su rol. |

## Finanzas (2.ª fase, fuera de alcance)

| Plantilla | Vista y ruta que la usan | Proceso | Estado | Para qué existe |
|---|---|---|---|---|
| `finanzas/pestanas/datos.html` | `/finanzas/<int:pk>` | 2F | Fragmento (pestaña) · oculta (2.ª fase) | Datos de un movimiento de dinero (2F: oculta, fuera de alcance). |

## Propuestas (no aplicadas: esperan tu respuesta)

1. **Borrar `nucleo/administracion.html`.** Es la página provisoria de F01; la reemplazó `administracion/indice.html`. Nadie la usa.
2. **Unificar las 3 pestañas de Documentos** (`actividades/pestanas/documentos.html`, `proyectos/pestanas/documentos.html` y `documentos/pestanas/lista.html`) en una sola. Las tres muestran la misma tabla con «Subir nuevo» y «Asociar existente»; solo cambia el enlace, que la vista ya puede pasar (como hacen persona y organización).
3. **Unificar las 4 listas de interacciones** (`solicitudes/pestanas/interacciones.html`, `coordinacion/_interacciones.html`, el bloque de `actividades/pestanas/coordinacion.html` y el de `organizaciones/pestanas/actividades.html`) en `coordinacion/_interacciones.html`. Hoy cada una muestra los contactos con un formato algo distinto.
4. **Darle a la organización su propia pestaña «Interacciones».** Hoy sus llamadas aparecen al final de la pestaña «Actividades y proyectos», donde cuesta encontrarlas (P6, paso 3).
5. **Decidir la 2.ª fase.** Seis plantillas (reuniones, compromisos, tareas, beneficiarios, presupuesto, movimientos) están ocultas. Las de dinero (`finanzas/…`, `proyectos/pestanas/presupuesto.html`) están fuera de alcance según tu documento: se pueden dejar ocultas o quitar con su app.
6. **Revisar la ficha de persona.** Tiene hasta 18 pestañas (6 con candado). Para el uso diario de Claudio bastan Datos, Contactos, Organizaciones y cargos, Participaciones, Documentos e Historial; el resto se podría agrupar en una sola pestaña «Más datos».
7. Borrar la carpeta vacía `templates/componentes/`.

No se propone unificar las fichas cortas ni las pantallas de error: son cortas porque reutilizan la plantilla común, y juntarlas movería decisiones de pantalla al código Python.

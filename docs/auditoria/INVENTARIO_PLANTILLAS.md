# Inventario de plantillas HTML

Primera versión: auditoría del 14-10-2026 (108 plantillas). **Actualizado el 26-10-2026 (F26, Paquete 3, «Plantillas»)**: se eliminaron las sin uso y se unieron las duplicadas. La tabla de abajo sale de la cabecera de cada plantilla (`{# Qué es #}` y `{# Dónde se usa #}`).

## Por qué hay tantas

El sistema arma cada pantalla con piezas:

- **Una plantilla común por tipo de pantalla** (`generico/`): el listado, el formulario y la ficha con pestañas son las mismas para todos los módulos.
- **Una plantilla por pestaña o sección.** Cada ficha (actividad, persona, organización, comuna…) tiene pestañas, y cada pestaña o sección es un archivo corto.
- **Fichas cortas a propósito.** `lugares/ficha.html` o `proyectos/ficha.html` toman la ficha común y le agregan solo su línea de cabecera.
- **Trozos reutilizables** (nombre con `_` al inicio): la tabla de documentos, la dirección en cascada, la lista de interacciones, las migas de pan, la paginación. Se escriben una vez y se incluyen donde hagan falta.

## Resumen (26-10-2026)

| Concepto | Cantidad |
|---|---|
| Plantillas antes de esta limpieza (después de F24 a F26 P3a) | 148 |
| Eliminadas sin uso | −5 |
| Eliminadas al unir duplicadas | −3 |
| Parcial nuevo (dirección en el formulario) | +1 |
| **Total actual** | **141** |
| · páginas (las abre una ruta o las extienden otras) | 58 |
| · fragmentos (pestañas, secciones y trozos `_`) | 83 |
| Sin uso | 0 |
| Duplicadas conocidas | 0 |

Cómo se verificó que una plantilla no se usa: su ruta no aparece en ningún `.py` ni `.html` (`template_name`, tuplas de pestañas, `render`, `render_to_string`, `include`, `extends`, `BloqueDeSeccion`). `FichaBase` no compone nombres de plantilla: cada pestaña declara su ruta completa en `pestanas` y los alias (`alias_pestanas`, `ALIAS_TAREA`, `ALIAS_PERSONA`) solo traducen claves viejas a claves de pestañas que existen. Tampoco hay nombres armados con f-strings.

## Eliminadas (F26 P3)

| Plantilla | Por qué no se usaba |
|---|---|
| `actividades/pestanas/asistencia.html` | La pestaña Asistencia se quitó en F25 E7; `?tab=asistencia` es alias de `participantes` (`ALIAS_TAREA`). |
| `personas/pestanas/datos.html` | La pestaña Datos se volvió Resumen; `?tab=datos` es alias de `resumen` (`ALIAS_PERSONA`). |
| `personas/pestanas/experiencia.html` | La experiencia es una sección de Estudios (`_seccion_hijos.html`); `?tab=experiencia` es alias de `estudios`. |
| `territorio/_direccion.html` | Reemplazada por `territorio/_ubicacion.html`; ninguna plantilla la incluía (su cabecera estaba desactualizada). |
| `nucleo/administracion.html` | Página provisoria de F01; `/administracion/` usa `administracion/indice.html`. |

## Unidas (F26 P3)

| Antes | Después | Dónde se usa el parcial unificado |
|---|---|---|
| `actividades/pestanas/documentos.html`, `proyectos/pestanas/documentos.html` y `documentos/pestanas/lista.html` | `documentos/pestanas/lista.html` (variables `url_nuevo_doc`, `url_asociar_doc`, `titulo_documentos`, `sin_contador_documentos`, que pasa cada `ctx_documentos`) | Pestaña Documentos de actividad o tarea, proyecto, organización, persona y solicitud. |
| `solicitudes/pestanas/interacciones.html`, `coordinacion/_interacciones.html`, el bloque de interacciones de `actividades/pestanas/coordinacion.html` y el de `organizaciones/pestanas/actividades.html` | `coordinacion/_interacciones.html` (modo línea de tiempo o `compacto`; opciones `con_quien`, `con_vinculos`, `recortar`, `marcar_cumplidas`, `sin_hora`, `sin_proxima`, `titulo_interacciones`, `vacio_interacciones`, `url_nueva_interaccion`) | Persona (Participaciones), solicitud (Seguimiento, la pestaña apunta directo al parcial), actividad suelta (sección Coordinación de Información) y organización (Últimos contactos). |
| Bloque de dirección en cascada copiado en `lugares/formulario.html`, `organizaciones/_direccion.html` y `personas/direccion.html` | `territorio/_direccion_form.html` (recibe `form_direccion`; `sin_errores` donde el formulario común ya muestra los errores) | Formularios de lugar, organización (dentro de su sección «Contacto y dirección») y dirección de la persona. |

Mostrar una dirección no tenía copias: las fichas usan `{{ objeto.direccion }}` (`Direccion.__str__`) con etiquetas distintas, así que no se creó un parcial para eso.

Lo que se ve no cambió: las cuatro listas de interacciones se compararon renderizando la versión anterior y la nueva con los mismos datos (con y sin interacciones) y el HTML resultante es idéntico salvo espacios.

Además, en la pestaña Resumen de la persona el bloque de tarjetas por tipo se llama ahora **«Tipo de persona»** (antes «Tipo de registro»), como en el formulario.

## Pendiente (propuestas que siguen abiertas)

1. **Darle a la organización su propia pestaña «Interacciones».** Hoy sus contactos aparecen al final de «Actividades y proyectos».
2. **Decidir la 2.ª fase.** Las plantillas de reuniones, compromisos, tareas internas, presupuesto y movimientos siguen ocultas con `SEGUNDA_FASE=False`.
3. Borrar la carpeta vacía `templates/componentes/` si existe en algún equipo (git no la guarda).

Procesos: P1 a P13 son los de `docs/Procesos_y_pruebas_de_Claudio.md`. «Grupo» = comunidades. «2F» = segunda fase.

## Inventario completo

### (raíz) (1)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `base.html` | la extienden todas las páginas | Todos | Página | Marco de todas las páginas: menú lateral, barra superior con el buscador, migas de pan y mensajes. |

### actividades (26)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `actividades/_panel_persona.html` | pestañas Participantes («Equipo y asistencia») y Beneficiarios de /actividades/<int:pk> y /proyectos/<int:proyecto_pk>/tareas/<int:pk> | P3 | Fragmento | Panel lateral con el resumen de una persona (se llena al hacer clic en su nombre; sin JavaScript el nombre abre la ficha). |
| `actividades/_vista.html` | /actividades (actividades/lista.html) y /calendario | P5 | Fragmento | Selector «Lista / Calendario» de Actividades (F26 P1b): el calendario es otra vista de las mismas actividades. |
| `actividades/beneficiario_form.html` | /actividades/<int:pk>/beneficiarios/registrar | P3/P8 | Página | Registrar un beneficiario en una tarea: ficha rápida, rol, de qué grupo viene y, si es menor de edad, su apoderado o contacto de emergencia (restringido). Avisa si la persona ya existe. |
| `actividades/calendario.html` | /calendario | P5 | Página | Calendario por mes, semana o lista; un clic en el evento abre la actividad. |
| `actividades/candidatos.html` | /actividades/<int:pk>/candidatos | P3 | Página | Búsqueda de candidatos con razones y conflictos. Sugiere, nunca agrega solo. |
| `actividades/confirmar.html` | /actividades/<int:pk>/confirmar | P2 | Página | Revisión antes de confirmar: lista de lo compatible, advertencias e incompatibilidades, con su motivo. |
| `actividades/constancia.html` | /actividades/<int:pk>/participantes/<int:part_pk>/constancia | P8 | Página | Constancia de participación de una persona, lista para imprimir. |
| `actividades/duplicar.html` | /actividades/<int:pk>/duplicar | P2 | Página | Crear una actividad nueva copiando otra, sin participantes ni fechas. |
| `actividades/ficha.html` | /actividades/<int:pk> | P2 | Página | Cabecera de la ficha de actividad o tarea: estado junto al nombre, una línea con tipo, fecha, lugar y comuna; «Editar» a la vista y confirmar, programar, finalizar y cambiar estado en «Más acciones». |
| `actividades/lista.html` | /actividades | P5 | Página | Listado de actividades (y tareas) con el selector «Lista / Calendario» encima de los filtros. |
| `actividades/participante_form.html` | /actividades/<int:pk>/participantes/nuevo (también llegan aquí /participantes/rapido y /beneficiarios/registrar) | P3/P8 | Página | El único «+ Agregar persona» de la actividad o tarea (F26 P1a): persona (si no existe, «+ Crear persona» del buscador abre la ficha rápida), rol, cargo, estado, de qué grupo viene, «Llegó / asistió» y, con permiso de datos sensibles, el apoderado o contacto de emergencia de un menor. «Guardar y agregar otra» mantiene el rol, el estado y el grupo. |
| `actividades/participante_otro_rol.html` | /actividades/<int:pk>/participantes/usar/<int:persona_pk> | P3 | Página | Confirmar que se agrega a una persona que ya participa en la actividad con otro rol (F25 E3). |
| `actividades/participante_rapido.html` | /actividades/<int:pk>/participantes/rapido | P3 | Página | Ficha rápida de terreno: crea una persona (solo el nombre es obligatorio; RUT, comuna y de qué grupo viene, opcionales) y la deja agregada. |
| `actividades/pestanas/agenda.html` | /actividades/<int:pk>; en una tarea va dentro de Información («Fecha y reprogramaciones») | P5 | Fragmento | Pestaña Agenda: programación vigente y versiones anteriores, con botones programar y reprogramar. |
| `actividades/pestanas/alcance.html` | 5 rutas, p. ej. /actividades/<int:pk> | P9 | Fragmento | Pestaña Alcance: cuántas personas, horas y comunidades alcanzó. La reutilizan comuna, sector, comunidad y proyecto. |
| `actividades/pestanas/beneficiarios.html` | /proyectos/<int:proyecto_pk>/tareas/<int:pk> y /actividades/<int:pk> | P3/P8 | Fragmento | Pestaña Beneficiarios de una tarea o actividad suelta (F26 P3a): quienes asisten (rol Beneficiario o Participante) con rol · cargo, procedencia, comunidad, edad y asistencia (solo lectura: se marca en «Pasar lista» de «Equipo y asistencia», F26 P1a); para quien tiene permiso, el apoderado o contacto de emergencia de los menores (🔒). |
| `actividades/pestanas/coordinacion.html` | dentro de la pestaña Información de una actividad suelta, /actividades/<int:pk> (F26 P3a: ya no es pestaña) | P6 | Fragmento | Sección Coordinación: llamadas, correos y reuniones registradas sobre la actividad, y próximas acciones. |
| `actividades/pestanas/historial.html` | /actividades/<int:pk>; en una tarea incluye al final el origen de los datos | P9 | Fragmento | Pestaña Historial de la actividad: cambios de la ficha y de sus participantes. |
| `actividades/pestanas/info.html` | /actividades/<int:pk>; reúne además Público y comunidades, «Fecha y reprogramaciones» y, solo en la actividad suelta, Coordinación (F26 P3a) | P2 | Fragmento | Pestaña Información de la actividad: objetivo, descripción, modalidad, responsable, territorios y actividades hijas. |
| `actividades/pestanas/participantes.html` | /actividades/<int:pk> y /proyectos/<int:proyecto_pk>/tareas/<int:pk> (también la pestaña Beneficiarios de una actividad suelta con la segunda fase) | P3/P8 | Fragmento | Pestaña Participantes (en una tarea, «Equipo y asistencia»): «Pasar lista» (F26 P1a: un solo formulario con todos, por grupo, una casilla «Asistió» por fila, «Marcar todos», «Sin registro de asistencia» y un solo «Guardar asistencia», desde el día de la actividad; en pantalla angosta es una lista apilada), el detalle por grupo con rol, estado, procedencia y asistencia, panel lateral con el resumen de cada persona, y botones «+ Agregar persona», buscar candidatos y cargar listado. |
| `actividades/pestanas/publico.html` | dentro de la pestaña Información de /actividades/<int:pk> (F26 P3a: ya no es pestaña) | P2 | Fragmento | Sección Público y comunidades: a qué comunidades va dirigida la actividad o tarea (el territorio va en «Zona»). |
| `actividades/pestanas/resultados.html` | /actividades/<int:pk> (pestaña Cierre); al final, el Alcance (F26 P3a: antes su propia pestaña) | P8 | Fragmento | Pestaña Resultados: observaciones, incidencias, resultado y botón Finalizar. |
| `actividades/pestanas/sesiones.html` | /actividades/<int:pk> | P8 | Fragmento | Pestaña Sesiones y minutas: cada encuentro de una actividad que se repite, con su minuta. |
| `actividades/programar.html` | /actividades/<int:pk>/programar | P5 | Página | Formulario para programar o reprogramar fecha, hora y lugar (con «+ Crear lugar» en ventana). |
| `actividades/quitar.html` | /actividades/<int:pk>/participantes/<int:part_pk>/quitar | P3 | Página | Quitar a un participante agregado por error: pide el motivo y lo deja como «registro erróneo», sin borrarlo. |
| `actividades/sesion.html` | /actividades/<int:pk>/sesiones/<int:sid> | P8 | Página | Ficha de una sesión: fecha, minuta, asistencia de esa sesión y acuerdos. |

### administracion (6)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `administracion/catalogo.html` | /administracion/catalogos/<slug:slug>/ | P12 | Página | Valores de un catálogo, con agregar, editar y desactivar. |
| `administracion/catalogos.html` | /administracion/catalogos/ | P12 | Página | Lista de catálogos (listas de opciones) que se pueden editar. |
| `administracion/indice.html` | /administracion/ | P13 | Página | Menú de Administración (solo Administrador): usuarios, roles, catálogos, auditoría, respaldos. |
| `administracion/rol_editar.html` | /administracion/roles/<int:pk> | P13 | Página | Marcar o desmarcar los permisos de un rol. |
| `administracion/roles.html` | /administracion/roles | P13 | Página | Lista de roles (Gestor, Administrador) y sus permisos. |
| `administracion/usuario_form.html` | /administracion/usuarios/<int:pk>/editar, /administracion/usuarios/nuevo | P13 | Página | Crear o editar una cuenta, eligiendo una persona ya registrada y su rol. |

### comunidades (3)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `comunidades/ficha.html` | /comunidades/<int:pk> | Grupo | Página | Cabecera de la ficha de comunidad (grupo de vecinos, curso, comité…): tipo, territorio e integrantes. |
| `comunidades/pestanas/actividades.html` | /comunidades/<int:pk> | Grupo/P9 | Fragmento | Pestaña Actividades y proyectos de la comunidad. |
| `comunidades/pestanas/info.html` | /comunidades/<int:pk> | Grupo | Fragmento | Pestaña Información de la comunidad. |

### coordinacion (4)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `coordinacion/_interacciones.html` | /personas/<int:pk>?tab=participaciones, /solicitudes/<int:pk>?tab=interacciones (Seguimiento), /actividades/<int:pk> (sección Coordinación de Información), /organizaciones/<int:pk>?tab=actividades (Últimos contactos) | P6 | Fragmento | Lista de interacciones (llamadas, correos, reuniones) de cualquier ficha. Única plantilla de interacciones (F26 P3). |
| `coordinacion/pestanas/compromisos.html` | /reuniones/<int:pk> | 2F | Fragmento | Compromisos de una reunión (2F: oculta). |
| `coordinacion/pestanas/reunion_datos.html` | /reuniones/<int:pk> | 2F | Fragmento | Datos de una reunión con asistentes (2F: oculta). |
| `coordinacion/pestanas/tarea_datos.html` | /tareas/<int:pk> | 2F | Fragmento | Datos de una tarea con responsables (2F: oculta). |

### cuentas (2)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `cuentas/login.html` | /login | P1 | Página | Pantalla de ingreso con usuario y contraseña. |
| `cuentas/mi_cuenta.html` | /mi-cuenta | P1 | Página | Datos de la cuenta propia y enlace para cambiar la contraseña. |

### documentos (7)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `documentos/_lista.html` | se incluye en documentos/pestanas/lista.html | P7 | Fragmento | Trozo con la tabla de documentos (nombre, tipo, fecha, candado, descargar). |
| `documentos/asociar.html` | /documentos/asociar | P7 | Página | Asociar un documento ya subido a otra ficha, sin copiar el archivo. |
| `documentos/nuevo.html` | /documentos/nuevo | P7 | Página | Subir un documento y asociarlo a una actividad, persona, organización o proyecto. |
| `documentos/pestanas/datos.html` | /documentos/<int:pk> | P7 | Fragmento | Pestaña Datos de la ficha de documento: tipo, fechas, folio, emisor y dónde está asociado. |
| `documentos/pestanas/lista.html` | /actividades/<int:pk>, /proyectos/<int:pk>, /organizaciones/<int:pk>, /personas/<int:pk>, /solicitudes/<int:pk> | P7 | Fragmento | Pestaña Documentos de toda ficha (subir o asociar). Variables: documentos, url_nuevo_doc, url_asociar_doc; opcionales titulo_documentos (por defecto «Documentos») y sin_contador_documentos. |
| `documentos/pestanas/origen.html` | 6 rutas, p. ej. /actividades/<int:pk> | P9 | Fragmento | Pestaña Origen: de qué documento o carga salió cada dato de la ficha. |
| `documentos/transcribir.html` | /documentos/<int:pk>/transcribir | P7 | Página | Documento a un lado y formulario al otro para copiar sus datos. |

### errores (3)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `errores/403.html` | cualquier página que responda con error 403 | P1 | Página | Pantalla «no tienes permiso», con botón para volver. |
| `errores/404.html` | cualquier página que responda con error 404 | P1 | Página | Pantalla «la página no existe», con botón para volver. |
| `errores/500.html` | cualquier página que responda con error 500 | P1 | Página | Pantalla de error interno, sin mostrar detalles técnicos. |

### finanzas (1)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `finanzas/pestanas/datos.html` | /finanzas/<int:pk> | 2F | Fragmento | Datos de un movimiento de dinero (2F: oculta, fuera de alcance). |

### generico (17)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `generico/_breadcrumb.html` | se incluye en 16 plantillas, p. ej. actividades/candidatos.html | Todos | Fragmento | Trozo que dibuja las migas de pan (Inicio › Actividades › …). |
| `generico/_campo.html` | se incluye en 12 plantillas, p. ej. actividades/pestanas/resultados.html | Todos | Fragmento | Trozo que dibuja un campo de formulario con su etiqueta, ayuda y error. |
| `generico/_campos.html` | se incluye en generico/formulario.html (Personas → Nueva y Editar usan personas/_formulario_persona.html) | Todos | Fragmento | Trozo que dibuja un formulario completo, agrupado por secciones (las plegadas van en un bloque que se abre con un clic). |
| `generico/_crear_rapida.html` | /personas/crear-rapida y /organizaciones/crear-rapida, dentro de la ventana de base.html | P3 y P4 | Fragmento | Contenido de la ventana «+ Crear…» que se abre desde un buscador: pide lo mínimo y avisa si el registro podría ya existir. |
| `generico/_filtro_campo.html` | generico/_filtros.html, con principal=True en la barra y principal=False en el panel | P10 | Fragmento | Trozo que dibuja un filtro de listado: lista desplegable (con grupos), casilla, fecha, número o texto. A la vista va compacto; dentro del panel «Filtros», con su rótulo visible. |
| `generico/_filtros.html` | generico/lista.html, en los listados que heredan de ListaBase (personas, actividades, documentos, lugares…) | P10 | Fragmento | Barra de filtros de los listados: buscador, 2 o 3 filtros a la vista, un solo botón «Filtros» que despliega los demás y los aplica con «Aplicar filtros» (funciona sin JavaScript; con él, cambiar un filtro a la vista lo aplica al tiro; sin otros filtros, el botón es «Filtrar») y la línea con cuántos resultados hay, los filtros aplicados como etiquetas con × y «Limpiar filtros», que conserva el orden. |
| `generico/_hijos.html` | 7 rutas, p. ej. /actividades/<int:pk> | P3/P4/P9 | Fragmento | Pestaña común para listas dentro de una ficha (contactos, cargos, carreras, organizaciones de una actividad…) con su botón «+ Agregar». |
| `generico/_historial.html` | 7 rutas, p. ej. /comunidades/<int:pk> | P9 | Fragmento | Pestaña Historial: qué cambió, quién y cuándo, con la versión anterior. |
| `generico/_paginacion.html` | se incluye en generico/lista.html | P10 | Fragmento | Trozo con los botones de página anterior y siguiente de los listados. |
| `generico/_selector_multiple.html` | generico/_campo.html, en todo campo de selección múltiple (perfiles, áreas de interés, facilitadores…) | Todos | Fragmento | Trozo que dibuja una selección múltiple desplegable: botón con el resumen de lo elegido, buscador y casillas (sin JavaScript, casillas en un bloque plegable). |
| `generico/_tramos.html` | pestaña Público de la actividad e Información de la comunidad | P2 | Fragmento | Tramos de edad de un registro como etiquetas, con el texto anterior escrito a mano (si lo hay) marcado «por revisar». |
| `generico/desactivar.html` | desactivar persona, organización, lugar o comunidad | P9 | Página | Pide confirmar antes de desactivar un registro y muestra qué quedará afectado. Nunca borra. |
| `generico/detalle.html` | /colaboraciones/<int:pk>, /interacciones/<int:pk>, /invitaciones/<int:pk> | P6 | Página | Vista simple de un registro sin pestañas (interacción, invitación, solicitud de apoyo). |
| `generico/ficha.html` | 5 rutas, p. ej. /documentos/<int:pk> | P9 | Página | Ficha común con cabecera y pestañas. Arriba el título y su estado, una línea de datos clave separados por «·», UNA acción principal (Editar) y el resto en «Más acciones»; los avisos van juntos en una caja suave. |
| `generico/formulario.html` | 99 rutas, p. ej. /actividades/<int:pk>/comunidades/<int:hijo_pk>/alternar | Todos | Página | Formulario común para crear o editar cualquier registro, con avisos y botón Volver. |
| `generico/fusionar.html` | unir personas u organizaciones repetidas | P3 | Página | Une dos fichas repetidas de la misma persona u organización, eligiendo cuál queda. |
| `generico/lista.html` | 23 rutas, p. ej. /actividades | P10 | Página | Listado común a todos los módulos: barra de filtros (generico/_filtros.html), tabla, paginación, botón crear y exportar. |

### importaciones (2)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `importaciones/resumen.html` | /importaciones/<int:pk> | P3 | Página | Resumen de una carga ya hecha, con botón para revertirla. |
| `importaciones/revisar.html` | /importaciones/<int:pk>/revisar | P3 | Página | Vista previa de una planilla: nuevos, existentes, posibles duplicados y errores, antes de confirmar. |

### lugares (6)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `lugares/ficha.html` | /lugares/<int:pk> | P5 | Página | Cabecera de la ficha de lugar: tipo, comuna y capacidad. |
| `lugares/formulario.html` | /lugares/<int:pk>/editar, /lugares/nuevo | P5 | Página | Crear o editar lugar con su dirección en cascada y lo que ya hay en la comuna elegida. |
| `lugares/pestanas/disponibilidad.html` | /lugares/<int:pk> | P5 | Fragmento | Pestaña Disponibilidad: elegir un día y ver qué actividades ocupan el lugar. |
| `lugares/pestanas/info.html` | /lugares/<int:pk> | P5 | Fragmento | Pestaña Información del lugar: dirección, capacidad, condiciones y dueño. |
| `lugares/pestanas/personas.html` | /lugares/<int:pk>?tab=personas | P9 | Fragmento | Pestaña Personas del lugar: quienes estudian, trabajan o participan ahí, y los estudiantes de esta sede. |
| `lugares/pestanas/uso.html` | /lugares/<int:pk> | P5/P9 | Fragmento | Pestaña Uso histórico: actividades realizadas en el lugar. |

### nucleo (3)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `nucleo/ayuda.html` | /ayuda | P1 | Página | Muestra el manual de uso dentro del sistema. |
| `nucleo/buscar.html` | /buscar | P10 | Página | Resultados del buscador de arriba, agrupados por personas, organizaciones, actividades, lugares y documentos. |
| `nucleo/dashboard.html` | /dashboard | P1 | Página | Panel de inicio: «Para hoy y vencidas» arriba, indicadores que no repiten las tarjetas, «Indicadores del período» con Mes · Trimestre · Año (F26 P3a, por ?periodo=, sin JavaScript), los próximos 7 días y lo pendiente (actividades incompletas, solicitudes sin respuesta, personas por completar, próximas acciones). Crear algo nuevo se hace desde «+ Nuevo». |

### organizaciones (6)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `organizaciones/_direccion.html` | /organizaciones/nueva y /organizaciones/<int:pk>/editar, desde generico/_campos.html (bloque «direccion» de OrganizacionForm) | P4 | Fragmento | Dirección de la organización (ubicación en cascada, calle y número) dentro de la sección «Contacto y dirección» del formulario. |
| `organizaciones/ficha.html` | /organizaciones/<int:pk> | P4 | Página | Cabecera de la ficha de organización: tipo, estado, comuna y sitio web. |
| `organizaciones/formulario.html` | /organizaciones/<int:pk>/editar, /organizaciones/nueva | P4 | Página | Crear o editar organización por secciones (la dirección en cascada va en «Contacto y dirección»), con aviso de duplicados. |
| `organizaciones/pestanas/actividades.html` | /organizaciones/<int:pk> | P4/P9 | Fragmento | Pestaña Actividades y proyectos: responde «¿qué hicimos con ellos?». |
| `organizaciones/pestanas/info.html` | /organizaciones/<int:pk> | P4 | Fragmento | Pestaña Información de la organización. |
| `organizaciones/pestanas/personas.html` | /organizaciones/<int:pk> | P4 | Fragmento | Pestaña Personas relacionadas: cargos con fechas (quién era presidente en cada período). |

### personas (26)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `personas/_fichas.html` | personas/_formulario_persona.html (Personas → Nueva y Editar) | P3 | Fragmento | «Tipo de persona» (F26 P2: un solo bloque): el tipo principal (estudiante, vecino o vecina, invitado o voluntario), otros perfiles, su organización y comunidad (una sola vez) y debajo la sección de cada tipo marcado. |
| `personas/_formulario_persona.html` | personas/nueva.html y personas/editar.html | P3 | Fragmento | Formulario de la persona por secciones, con el «Tipo de persona» y la sección de cada tipo justo después de Identificación y Contacto. |
| `personas/_relaciones.html` | personas/nueva.html (/personas/nueva) | P3 | Fragmento | Sección «Relaciones» al registrar una persona: filas para unirla a proyectos o tareas y actividades, cada una con su rol (F26 P2: la organización y la comunidad se piden una vez, en «Tipo de persona»). |
| `personas/_resumen.html` | /personas/<int:pk>/resumen, cargado en el panel lateral de la pestaña Participantes | P3/P8 | Fragmento | Resumen corto de una persona (contacto, comuna, organizaciones, formación, comunidades y últimas actividades) para el panel lateral. |
| `personas/direccion.html` | /personas/<int:pk>/direcciones/nuevo | P5 | Página | Agregar una dirección a una persona eligiendo región, comuna y sector en cascada. |
| `personas/editar.html` | /personas/<int:pk>/editar | P3 | Página | Editar persona, con su «Tipo de persona» y la sección de cada tipo marcado. |
| `personas/ficha.html` | /personas/<int:pk> | P9 | Página | Cabecera de la ficha de persona: estado del registro junto al nombre, una línea con perfil, edad, comuna y contacto principal, avisos (menor de edad, consentimientos) en una sola caja y las acciones secundarias en «Más acciones». |
| `personas/ficha_tipo.html` | /personas/<int:pk>/fichas/<codigo>, desde «Editar» en su tarjeta de la pestaña Datos | P3 | Página | Editar los datos de un tipo de registro de la persona (estudiante, vecino o vecina, invitado o voluntario). |
| `personas/fichas/_campos.html` | personas/_fichas.html y personas/ficha_tipo.html | P3 | Fragmento | Cuerpo de una sección de tipo de registro con un solo formulario (invitado o voluntario): sus campos en dos columnas. |
| `personas/fichas/_estudiante.html` | personas/_fichas.html y personas/ficha_tipo.html | P3 | Fragmento | Cuerpo de la sección «Estudiante»: institución → sede y carrera en cascada, estado, jornada, año que cursa y año de inicio. |
| `personas/fichas/_estudios.html` | sección Estudiante de Personas → Nueva, Editar y su tarjeta; pestaña Formación (agregar y editar) | P3 | Fragmento | Institución → sede o casa matriz y carrera, en cascada, con «+ Crear sede» y «+ Crear carrera» (se crean al guardar). |
| `personas/fichas/_estudios_dependientes.html` | personas/fichas/_estudios.html; /personas/estudios/dependientes la vuelve a dibujar al cambiar la institución | P3 | Fragmento | Sede o casa matriz y carrera de la institución elegida, con «+ Crear sede» (nombre y comuna) y «+ Crear carrera». |
| `personas/fichas/_vecino.html` | personas/_fichas.html y personas/ficha_tipo.html | P3 | Fragmento | Cuerpo de la sección «Vecino o vecina»: dirección y comunidad en cascada, edad y sexo, y el hogar 🔒 (conteos sin nombres y familiares ya registrados). |
| `personas/nueva.html` | /personas/nueva | P3 | Página | Crear persona: ficha rápida o completa, con su «Tipo de persona» (estudiante, vecino, invitado, voluntario), sus relaciones y aviso de posibles duplicados antes de guardar. |
| `personas/pestanas/_fichas_tarjetas.html` | personas/pestanas/resumen.html (/personas/<int:pk>, pestaña Resumen) | P9 | Fragmento | Bloque «Tipo de persona»: una tarjeta por tipo de la persona (estudiante, vecino o vecina, invitado, voluntario), con su resumen y «Editar». El hogar va con 🔒. |
| `personas/pestanas/_seccion_hijos.html` | personas/pestanas/contacto.html, estudios.html y privacidad.html (/personas/<int:pk>) | P9 | Fragmento | Una sección de una pestaña de la persona (contactos, direcciones, formación…) como tarjeta suave, con su lista y su «+ Agregar». Recibe `x` (el contexto de la sección), y opcionales `titulo_seccion` y `ayuda`. |
| `personas/pestanas/consentimientos.html` | /personas/<int:pk> | P9 | Fragmento | Pestaña Consentimientos: qué autorizó la persona o su apoderado y cuándo. |
| `personas/pestanas/contacto.html` | /personas/<int:pk>?tab=contacto (también ?tab=contactos, direcciones o emergencia) | P9 | Fragmento | Pestaña Contacto de la persona: contactos, direcciones 🔒 y contacto de emergencia 🔒 (este último solo con permiso de datos sensibles), cada uno con su «+ Agregar». |
| `personas/pestanas/estudios.html` | /personas/<int:pk>?tab=estudios (también ?tab=formacion, experiencia o disponibilidad) | P9 | Fragmento | Pestaña Estudios y trayectoria de la persona: formación, experiencia (la que se arma sola con los cargos y roles terminados y la de fuera de la Fundación) y disponibilidad. |
| `personas/pestanas/historial.html` | /personas/<int:pk>?tab=historial (también ?tab=origen) | P9 | Fragmento | Pestaña Historial de la persona: qué cambió, quién y cuándo, y al final el origen de los datos (de qué formulario, carga o documento salieron). |
| `personas/pestanas/participaciones.html` | /personas/<int:pk>?tab=participaciones (también ?tab=trayectoria o interacciones) | P9 | Fragmento | Pestaña Participaciones de la persona: actividades con rol y asistencia, horas, invitaciones (y reuniones y tareas con la segunda fase) e interacciones con ella. Los cargos y proyectos están en «Cargos y vínculos». |
| `personas/pestanas/privacidad.html` | /personas/<int:pk>?tab=privacidad (también ?tab=sensibles, apoderados, consentimientos o verificaciones) | P9 | Fragmento | Pestaña Privacidad 🔒 de la persona: datos sensibles, apoderados, consentimientos y verificaciones (con la segunda fase activa). Cada sección se ve solo con su permiso; sin ninguno, la pestaña no aparece. |
| `personas/pestanas/resumen.html` | /personas/<int:pk> (también ?tab=datos) | P9 | Fragmento | Pestaña Resumen de la persona: arriba «De un vistazo» (F26 P3a: organización y cargo, formación y comunidades vigentes, próxima actividad, últimas 3 participaciones y lo que le falta, con enlaces); luego solo los datos con valor (los vacíos, plegados en «Sin completar (N)» con «Completar ficha»), contacto principal, dirección vigente y una tarjeta por tipo de registro (estudiante, vecino…). |
| `personas/pestanas/sensibles.html` | /personas/<int:pk> | P9 | Fragmento | Sección Datos sensibles 🔒 de la pestaña Privacidad (género, pueblo originario, salud, discapacidad, tramo del Registro Social de Hogares), solo con permiso y consentimiento. |
| `personas/pestanas/trayectoria.html` | personas/pestanas/participaciones.html (/personas/<int:pk>) | P9 | Fragmento | Sección de participaciones de la persona: actividades con rol y asistencia, horas, invitaciones, reuniones y tareas (los cargos y proyectos están en «Cargos y vínculos»). |
| `personas/pestanas/vinculos.html` | /personas/<int:pk>?tab=vinculos (también ?tab=comunidades) | P9 | Fragmento | Pestaña Cargos y vínculos de la persona: organizaciones con cargo, estudios, lugares, comunidades (con «+ Comunidad»), proyectos y actividades, vigentes y terminados, con enlaces. |

### proyectos (6)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `proyectos/ficha.html` | /proyectos/<int:pk> | P11 | Página | Cabecera de la ficha de proyecto: estado, zona, fechas y responsable. |
| `proyectos/finalizar.html` | /proyectos/<int:pk>/finalizar | P11 | Página | «Finalizar proyecto» (F26 P3a): avisa cuántas tareas siguen abiertas (con enlaces), sugiere el estado según sus tareas sin imponerlo [V#7], pide la conclusión y ofrece descargar el informe en Excel. |
| `proyectos/pestanas/actividades.html` | /proyectos/<int:pk>?tab=tareas (también ?tab=actividades, nombre antiguo) | P11 | Fragmento | Pestaña Tareas del proyecto: sus tareas con fecha, lugar o comunidad, estado, participantes y asistencia, y «+ Nueva tarea». |
| `proyectos/pestanas/beneficiarios.html` | /proyectos/<int:pk> | P11 · 2F | Fragmento | Pestaña Beneficiarios del proyecto (2F: oculta). |
| `proyectos/pestanas/presupuesto.html` | /proyectos/<int:pk> | 2F | Fragmento | Pestaña Presupuesto del proyecto (2F finanzas: oculta). |
| `proyectos/pestanas/resumen.html` | /proyectos/<int:pk> | P11 | Fragmento | Pestaña Resumen del proyecto: estado, zona (sus territorios y el texto anterior, si lo hay), área, fechas, responsable, la conclusión (al finalizar, F26 P3a) y los resultados de sus tareas. |

### solicitudes (4)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `solicitudes/ficha.html` | /solicitudes/<int:pk> | P2 | Página | Cabecera de la ficha de solicitud: estado, origen, días abierta y contacto. |
| `solicitudes/lista.html` | /solicitudes | P2 | Página | Listado de solicitudes y oportunidades con pestañas por estado (con su contador) encima de la lista. |
| `solicitudes/nueva.html` | /solicitudes/nueva | P2 | Página | Formulario de nueva solicitud u oportunidad (casi sin datos obligatorios). |
| `solicitudes/pestanas/info.html` | /solicitudes/<int:pk> | P2 | Fragmento | Pestaña Información de la solicitud, con botón Crear actividad. |

### territorio (18)

| Plantilla | Dónde se usa | Proceso | Tipo | Para qué existe |
|---|---|---|---|---|
| `territorio/_como_funciona.html` | se incluye en territorio/indice.html y territorio/pestanas/resumen.html (/territorio, /territorio/comuna/<int:pk>, /territorio/sector/<int:pk>) | P5 | Fragmento | Bloque plegable «Cómo funciona el territorio»: de dónde salen regiones, comunas y sectores, qué reúne cada comuna o sector y qué se puede hacer. |
| `territorio/_comunas_con_presencia.html` | se incluye en territorio/indice.html, territorio/region.html | P5 | Fragmento | Trozo con las tarjetas de comunas con trabajo (índice y región). |
| `territorio/_contexto_lugar.html` | dentro de territorio/_ubicacion.html, en /lugares/nuevo y /lugares/<int:pk>/editar | P5 | Fragmento | Panel «En <comuna> ya hay…»: sectores, comunidades, lugares y organizaciones de la comuna elegida, para reutilizarlos en vez de crearlos de nuevo. |
| `territorio/_destinos.html` | crear y editar actividad (/actividades/nueva, /actividades/<id>/editar) y proyecto (/proyectos/nuevo, /proyectos/<id>/editar) | P2 · P11 | Fragmento | Sección «¿Dónde?»: lo ya indicado (con «Quitar») y filas región → comuna → sector para agregar uno o más territorios. |
| `territorio/_direccion_form.html` | se incluye en lugares/formulario.html, organizaciones/_direccion.html y personas/direccion.html | P5 | Fragmento | Campos de una dirección en un formulario: ubicación en cascada (región → comuna → sector, con «+ Crear sector») más calle, número, block, depto y referencia. Única copia (F26 P3). Recibe `form_direccion`; `sin_errores` cuando el formulario común ya muestra sus errores generales. |
| `territorio/_ubicacion.html` | dirección de lugar, organización y persona; formulario de comunidad; /territorio/ubicacion la vuelve a dibujar al cambiar una lista | P5 | Fragmento | Ubicación en cascada: región → comuna → sector (la provincia es opcional), con «+ Crear sector», la comunidad si se pide y, en un lugar, lo que ya hay en la comuna. |
| `territorio/ficha.html` | /territorio/comuna/<int:pk>, /territorio/sector/<int:pk> | P5/P9 | Página | Cabecera de la ficha de comuna o sector: región, código, municipalidad, estado junto al nombre y, en «Más acciones», «+ Comunidad / Organización / Lugar», exportar y «Desactivar / Reactivar sector». |
| `territorio/indice.html` | /territorio | P5/P10 | Página | «Dónde trabajamos»: comunas con trabajo registrado, buscador de comuna y todas las regiones; avisa si falta la lista oficial y explica cómo funciona el territorio. |
| `territorio/pestanas/_persona.html` | se incluye en territorio/pestanas/personas.html | P9 | Fragmento | Trozo: una fila de persona con su comunidad y perfiles. |
| `territorio/pestanas/actividades.html` | /territorio/comuna/<int:pk>, /territorio/sector/<int:pk> | P9 | Fragmento | Pestaña Actividades de la comuna o sector. |
| `territorio/pestanas/comunidades.html` | /territorio/comuna/<int:pk>, /territorio/sector/<int:pk> | Grupo | Fragmento | Pestaña Comunidades de la comuna o sector. |
| `territorio/pestanas/lugares.html` | /territorio/comuna/<int:pk>, /territorio/sector/<int:pk> | P5 | Fragmento | Pestaña Lugares de la comuna o sector. |
| `territorio/pestanas/nombres.html` | /territorio/sector/<int:pk> | P5 | Fragmento | Pestaña Nombres alternativos de un sector (para reconocer escrituras distintas). |
| `territorio/pestanas/organizaciones.html` | /territorio/comuna/<int:pk>, /territorio/sector/<int:pk> | P4 | Fragmento | Pestaña Organizaciones de la comuna, agrupadas por tipo. |
| `territorio/pestanas/personas.html` | /territorio/comuna/<int:pk>, /territorio/sector/<int:pk> | P9 | Fragmento | Pestaña Personas: residentes y miembros de comunidades de la comuna. |
| `territorio/pestanas/resumen.html` | /territorio/comuna/<int:pk>, /territorio/sector/<int:pk> | P5/P9 | Fragmento | Pestaña Resumen de la comuna: cifras clicables, organizaciones por tipo, tabla por sector, próximas actividades, minutas y el bloque «Cómo funciona el territorio». |
| `territorio/pestanas/sectores.html` | /territorio/comuna/<int:pk>, /territorio/sector/<int:pk> | P5 | Fragmento | Pestaña Sectores de la comuna (con sectores dentro de sectores); los desactivados se marcan y se pueden reactivar desde su ficha. |
| `territorio/region.html` | /territorio/region/<int:pk> | P5 | Página | Ficha de región: comunas con presencia y lista por provincia; la que no es de la lista oficial lleva «De demostración». |

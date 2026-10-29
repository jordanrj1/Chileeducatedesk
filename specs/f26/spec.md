# F26 — CRM más expedito: operación diaria, una sola verdad y ficha 360°

**Fuente:** auditoría del 22-10-2026 con tres enfoques (datos e ingesta, pantallas y flujos, lógica y módulos) y decisiones del usuario el mismo día. Paquetes 1, 2 y 3. «Tarea» dentro del proyecto y «Actividad» suelta, con las mismas pestañas. Se eliminan las plantillas sin uso y se unen las duplicadas. **Sin commits** hasta que el usuario revise.

**Pendiente de confirmar:** Finanzas → «Aportes y recursos» (paquete 4, no marcado).

## Paquete 1 · Operación diaria más rápida
**P1a. Pasar lista y agregar personas**
- **Pasar lista:**
  - **Formulario:** uno solo para toda la actividad o tarea, en «Equipo y asistencia». Lista a todos agrupados (equipo ejecutor, invitados y contactos, beneficiarios), con una **casilla «Asistió» por fila**, «Marcar todos» y **un solo «Guardar asistencia»**.
  - **«Sin registro de asistencia»:** se marca a nivel de la actividad.
  - **Al guardar:** una fila sin marcar queda «No asistió».
  - **En pantalla angosta:** es una lista apilada, no una tabla ancha.
- **Beneficiarios:** la pestaña muestra su asistencia y enlaza a «Pasar lista».
- **Varios días:** la asistencia de la participación se calcula desde las sesiones. Asistió si fue al menos a una sesión; no asistió si estuvo ausente en todas. Se puede corregir a mano.
- **Un solo «+ Agregar persona»:**
  - pide la persona (con «+ Crear persona» en el buscador, que usa la ficha rápida), el rol, el cargo, «¿De qué grupo viene?» y la casilla «Llegó / asistió»;
  - el bloque de menor de edad (apoderado o contacto de emergencia) aparece cuando el rol es de beneficiario;
  - **«Guardar y agregar otra»** mantiene el rol y el grupo.
  - Los botones duplicados salen («Crear persona nueva», «+ Agregar persona que llegó», «Crear y marcar asistencia»). Sus rutas siguen funcionando.

**P1b. Solicitudes, Inicio y menú**
- **Solicitud → actividad en un paso:**
  - «Crear actividad» abre el formulario de nueva actividad relleno con la solicitud, con una sección opcional **«Programar ahora»** (fecha, horas, lugar);
  - al guardar, la solicitud queda «convertida» y ligada;
  - desde una solicitud convertida en proyecto se ofrece «Crear tarea en el proyecto».
- **Inicio:**
  - tarjeta **«Para hoy y vencidas»**: próximas acciones de hoy o vencidas, actividades y tareas con fecha pasada sin finalizar, y documentos y consentimientos por vencer;
  - sin repetir los indicadores con las tarjetas;
  - sin «Acciones rápidas», porque ya está «+ Nuevo»;
  - «Tareas por vencer» pasa a llamarse «Próximas acciones».
- **Finalizar exige fecha:** finalizar una actividad sin programación se rechaza con un mensaje claro.
- **Menú:**
  - el Calendario es una vista dentro de Actividades (Lista / Calendario);
  - «Cargar planilla» y «+ Proyecto» van en «+ Nuevo»;
  - el historial de cargas va en Configuración.
- **Listas:** un solo botón de filtros.
- **Solicitudes:** un solo «+ Nueva» y pestañas por estado con contador.

## Paquete 2 · Una sola verdad para los datos
- **Informe de diferencias** (solo lectura, `manage.py diferencias_datos`): participaciones cuya institución no aparece en un vínculo, referentes fuera del padrón, responsables fuera del equipo, personas con un perfil sin los hechos que lo respalden, y sedes en texto.
- **Servicio único `vincular()`:** está detrás de «¿De qué grupo viene?» y de todas las puertas (participante, beneficiario, relaciones, ficha de vecino, importación, contactos de solicitud y de organizaciones en actividades y proyectos). Crea o reutiliza `PersonaOrganizacion`, `PersonaFormacion` (estudiante en institución educativa) o `ComunidadMiembro`, sin duplicar.
- **Catálogo «Rol en la organización»:** estudiante, docente, funcionario o funcionaria, dirigente, socio o socia, practicante, autoridad, otro. Se guarda en un FK nuevo `PersonaOrganizacion.rol`; el cargo libre se mantiene. Migración aditiva que lee el prefijo del texto actual.
- **Institución de procedencia:** en la participación acepta cualquier organización activa («Institución u organización de procedencia»).
- **Procedencia calculada:** la participación muestra la institución y la comunidad calculadas desde el vínculo. Al corregirlas se ofrece «actualizar también su vínculo».
- **Formulario de persona sin datos dobles:**
  - la organización y la comunidad se piden una sola vez (en el bloque del tipo: «Organización y comunidad»; la institución del estudiante, la organización del invitado y la comunidad del vecino van en su sección); «Relaciones» queda para proyectos, tareas y actividades;
  - «Tipo de registro» y «Otros perfiles» se unen en un solo bloque.
- **Completitud calculada:** `Persona.faltantes()` (apellido, contacto, comuna y lo propio de su tipo: estudiante → formación vigente; vecino → comuna donde vive o su comunidad; voluntario e invitado → su ficha). La ficha completa también pide la comuna donde vive. El estado «incompleto» o «activo» se recalcula al guardar, salvo los estados manuales (por verificar, desactualizado, fallecida, fusionada). La cola del Inicio muestra «le falta: …».
- **Responsable y referente:**
  - el responsable del proyecto entra solo al equipo (marcado como responsable; si otro lo estaba, se desmarca y sigue en el equipo); marcar a alguien del equipo como responsable cambia también el responsable del proyecto;
  - **[P]** el responsable de una actividad o tarea entra solo a su equipo ejecutor, con el rol «Coordinador» (o el primer rol activo del equipo ejecutor) si aún no está con un rol de ese grupo;
  - una migración de datos aplica estas reglas a lo ya registrado: solo crea las filas que faltan;
  - el referente de una comunidad se toma de su padrón (rol referente o dirigente);
  - el apoderado registrado como contacto de emergencia cuenta para el aviso de menor sin apoderado.

## Paquete 3 · Ficha 360° y orden
- **Resumen 360° de la persona:** organización y cargo vigentes, formación, comunidades, últimas 3 participaciones, próxima actividad y lo que le falta.
- **Mismas pestañas:** la actividad suelta usa las mismas 8 pestañas que la tarea (Coordinación queda como sección dentro de Información, solo en las actividades sueltas).
- **«Finalizar proyecto»:** avisa si quedan tareas abiertas, pide la conclusión y ofrece un informe en Excel (tareas, asistencia, alcance, aliados). El estado del proyecto se **sugiere** según sus tareas, sin imponerlo [V#7].
- **Indicadores por período para la Dirección** en el Inicio: actividades realizadas, personas distintas alcanzadas, horas, organizaciones aliadas y comunas atendidas.
- **Hecho en P3a (26-10-2026):**
  - Resumen 360°: bloque «De un vistazo» arriba de la pestaña Resumen (reutiliza `cargos_y_vinculos()` y `faltantes()`); la formación vigente y la comunidad ya no se repiten en las tarjetas por tipo.
  - Actividad suelta con las 8 pestañas de la tarea. Alias: agenda, publico y coordinacion → Información; **alcance → Cierre** (el Alcance va al final de Cierre, también en la tarea); origen → Historial; asistencia → Equipo y asistencia. Los cupos se ven en Beneficiarios. [P]
  - «Finalizar proyecto» (`/proyectos/<id>/finalizar`, permiso `proyectos.change_proyecto`) e informe (`/proyectos/<id>/informe`, permiso `proyectos.exportar_proyecto`). **Migración aditiva `proyectos 0004`: `Proyecto.conclusion` (TextField).** Estado sugerido [P, V#7]: con tareas abiertas → «Suspendido»; todas canceladas → «Cancelado»; si no → «Finalizado». El usuario elige. Informe sin RUT ni menores por nombre salvo `personas.exportar_persona` (como F23); nunca contactos.
  - Indicadores del período (`/dashboard?periodo=mes|trimestre|anio`, en curso hasta hoy) [P]: realizadas = estado «realizada» con fecha vigente en el período; personas = asistentes distintos (de `alcance()`); horas = `alcance()["horas"]`; aliadas = organizaciones distintas de esas actividades; comunas = por el lugar o la zona.
- **Plantillas:**
  - se eliminan las 5 sin uso: `actividades/pestanas/asistencia.html`, `personas/pestanas/datos.html`, `personas/pestanas/experiencia.html`, `territorio/_direccion.html` y `nucleo/administracion.html`;
  - se unen la pestaña Documentos (en `documentos/pestanas/lista.html`), las listas de interacciones (en `coordinacion/_interacciones.html`) y el bloque de dirección;
  - se actualiza `docs/auditoria/INVENTARIO_PLANTILLAS.md`.

## Paquete I · Interfaz por módulo (26-10-2026, pedido del usuario: «sigue mejorando la interfaz de cada módulo»)
Revisión visual de listas, fichas y formularios de todos los módulos. [P] salvo lo que ya estaba decidido.

**Ia. Piezas comunes**
- **Botón de filtros igual en todas las listas:** mismo texto («Filtros»), estilo y tamaño que los demás botones. Hoy algunas dicen «Filtrar» en azul y con letra más grande.
- **Solicitudes:** sin el selector «Estado», porque ya están las pestañas por estado.
- **Áreas de texto de 3 filas** que crecen al escribir. Hoy miden unas 10 filas («Objetivo», «¿Quiénes?», «Descripción»).
- **Ayuda de «Responsable» corta:** «Queda en el equipo automáticamente». Se quita la ruta larga por Organizaciones.
- **«Desactivar»** (organización, comunidad, lugar) va en «Más acciones», no como botón suelto al pie de Información.
- **Campos vacíos de las fichas plegados** en «Sin completar (n)», como en la persona. Hoy se ven muchos «—».
- **Estado de la organización:** una sola insignia (estado de la ficha). «Inactiva» aparece solo cuando lo está.
- **«Origen» dentro de Historial** en proyecto, organización y lugar, como en la actividad. Las direcciones viejas siguen funcionando por alias.
- **Nombres:**
  - en el proyecto se dice «Tareas», no «Actividades» (columna de la lista y Resumen);
  - «Historial de cargas» y «Cargar planilla» en vez de «Importaciones» y «Nueva importación».
- **Dirección:** block, depto y referencia van plegados en «Más datos de la dirección».
- **Organización nueva:** «Esta ficha es la de la Fundación» va en «Datos legales», que está plegado.

**Ib. Fichas 360° y listas**
- **«De un vistazo» en organización, comunidad y lugar:**
  - **Organización:** personas vinculadas, actividades y proyectos con la última y la próxima, contacto principal y última interacción.
  - **Comunidad:** integrantes, referente, última y próxima actividad.
  - **Lugar:** veces usado, última y próxima actividad.
  - Número fijo de consultas.
- **Lista de personas:** Nombre · Perfil · Contacto (correo o teléfono principal) · Comuna · Edad · Estado de la ficha. RUT 🔒 solo con permiso. «Origen» pasa a filtro.
- **Lista de organizaciones:** se agregan «Personas» y «Actividades» (conteos).
- **«Cargos y vínculos» de la persona:** solo los grupos con datos; los vacíos se resumen en una línea.
- **Pestañas en celular:** las de las fichas y las de estado de Solicitudes van en una sola fila con desplazamiento horizontal, y la pestaña activa queda a la vista. Hoy ocupan 3 o 4 filas a 400 px.

## Paquete R · Envíos, duplicados, límites y rendimiento (26-10-2026)
Pedido del usuario: «mejora lo que es en base a renderización, solicitudes, como duplicados, guardados con botón y límite de peticiones». [P] salvo lo indicado.

**Diagnóstico (medición con 153 páginas, base de desarrollo)**
- **Tiempos:** 8 ms promedio y 62 ms la más lenta, con 17,6 consultas promedio.
- **Consultas repetidas** que crecerán con los datos:
  - Nueva persona: 58 consultas, 19 repetidas;
  - Buscar: 36 consultas, 13 repetidas;
  - Historial y Beneficiarios de la tarea: 13 y 8 repetidas;
  - ficha de persona: 5 o 6 repetidas.
- **Envío doble:** el JavaScript bloquea el segundo envío de los formularios normales, pero no el de los formularios HTMX (crear rápido en ventana, «Crear sector», «Crear y seleccionar»). En el servidor no hay protección: sin JavaScript, o al volver y reenviar, se crea dos veces.
- **Duplicados:** se avisa en personas y organizaciones, no en lugares, comunidades, proyectos, actividades ni solicitudes.
- **Límite de peticiones:** solo existe en el ingreso (`apps/cuentas/bloqueo.py`).
- **Servidor:**
  - estáticos sin compresión ni caché larga;
  - una conexión nueva a la base en cada petición;
  - sesión leída de la base en cada petición;
  - las pestañas por HTMX reciben la página completa.

**Ra. Envío único, guardado y duplicados**
- **Envío único en el servidor:** cada formulario de creación lleva una marca de un solo uso. Si llega dos veces, la segunda no crea nada y lleva a lo que creó la primera, con el aviso «Ya estaba guardado».
- **En el navegador:**
  - los formularios y botones HTMX se bloquean mientras se envían (`hx-disabled-elt`, `hx-sync`);
  - el botón pulsado muestra «Guardando…» (`aria-busy`).
- **Enter en formularios largos de alta y edición:** pasa al campo siguiente y no envía el formulario a medias. Se guarda solo con el botón. Excepción: los buscadores y los formularios de una sola línea.
- **Aviso de posibles duplicados:**
  - **lugar:** mismo nombre en la misma comuna;
  - **comunidad:** mismo nombre en la misma comuna o sector;
  - **proyecto:** mismo nombre;
  - **actividad:** mismo nombre y misma fecha, o mismo nombre en el mismo proyecto;
  - **solicitud:** misma organización o persona con motivo parecido en los últimos 30 días.

  Se muestra antes de guardar, con enlaces, y se guarda igual con «Es distinto, guardar». Nunca bloquea ni fusiona solo.
- **Límite de peticiones por usuario** con la caché de Django, sin dependencias nuevas:
  - envíos (POST): 60 por minuto;
  - búsquedas y buscadores: 120 por minuto;
  - exportaciones e informes: 10 por minuto.

  Al pasarse, se muestra una pantalla 429 propia, en español y con el tiempo de espera. Las cifras se ajustan en `.env`: `LIMITE_ENVIOS_MINUTO`, `LIMITE_BUSQUEDAS_MINUTO` y `LIMITE_EXPORTACIONES_MINUTO`.
- **Hecho (26-10-2026):** `apps/nucleo/envio_unico.py` (marca `_envio` con `{% marca_envio %}` en `generico/formulario.html` y en la ventana «+ Crear…»), `apps/nucleo/duplicados.py` con `AvisoDuplicadosMixin` y `generico/_aviso_duplicados.html`, `apps/nucleo/limites.py` con `errores/429.html`, y «Guardando…» y Enter en `static/js/fche.js`. Pruebas en `apps/nucleo/test_f26_ra.py`. La comparación de nombres no distingue mayúsculas ni tildes; el motivo de la solicitud se compara por similitud (≥ 30 %) [P].

**Rb. Rendimiento**
- **Producción:**
  - estáticos con `CompressedManifestStaticFilesStorage` de whitenoise, con nombres con huella y caché larga;
  - conexión persistente (`CONN_MAX_AGE` con chequeo de salud);
  - sesión `cached_db`.
- **Pestañas por HTMX:** el servidor devuelve solo la ficha, no la página completa, y un clic nuevo cancela el anterior (`hx-sync`).
- **Consultas repetidas:** se eliminan en las páginas del diagnóstico, con pruebas de número fijo de consultas.
- **Buscadores:** guardan en memoria las respuestas ya pedidas, para no repetir la misma petición.
- **Hecho (26-10-2026):**
  - `config/settings/produccion.py`: `STORAGES` con `CompressedManifestStaticFilesStorage`, `CONN_MAX_AGE` (`.env`, 60 por omisión) con `CONN_HEALTH_CHECKS` y sesión `cached_db`. Se quitó de `static/vendor/bootstrap` la referencia a los `.map` que no existen (rompía `collectstatic`).
  - Pestañas: `FichaBase.solo_ficha()` y `generico/_solo_ficha.html` (la ficha extiende `marco_ficha`), con `hx-sync="#ficha-completa:replace"`. Una pestaña pasa de unos 25 KB a unos 8 KB.
  - Consultas: `apps/nucleo/memo.py` (memoria de una petición), usada por los buscadores, los `ModelChoiceField` de `BootstrapMixin`, la ubicación en cascada y los catálogos de las filas. Además, precargas en la ficha de persona y en `/buscar`, y la agenda vigente leída una vez en la ficha de actividad o tarea.
  - Buscadores: `Map` con tope de 60 entradas en `static/js/selector.js`. Se vacía al crear desde «+ Crear» o al guardar por HTMX.
  - Pruebas en `apps/nucleo/test_f26_rb.py`.

## Paquete P · Pulido de Calendario, Buscar y Catálogos (26-10-2026) [P]
- **Calendario:**
  - **Título del mes:** «octubre de 2026» con mayúscula solo al inicio. Hoy sale «Octubre De 2026» por un `text-transform: capitalize`.
  - **Colores por estado:** los mismos de las insignias del resto del sistema, desde una sola fuente. Hoy «planificada» es gris en el calendario y azul en las listas.
  - **Título del evento:** corto (el nombre). El proyecto y el lugar van en el detalle al pasar el mouse.
  - **Filtros:** la barra común de filtros (los textos no se cortan).
  - **Botón:** «+ Nueva actividad», como en la lista.
- **Buscar:**
  - las fechas con etiqueta «Desde» y «Hasta»;
  - la barra común de filtros;
  - cada grupo muestra hasta 5 resultados con «Ver todos (n)», que lleva a la lista del módulo filtrada.
- **Plurales:** sin «actividad(es)», «tarea(s)» ni «participación(es)». Se usa el plural correcto según la cifra en todo el sistema.
- **Catálogos:**
  - agrupados por área: Actividades, Personas, Organizaciones, Lugares y territorio, Documentos;
  - un buscador para filtrar las tarjetas.

## Criterios
- Flujo de una tarea con 5 de equipo y 20 beneficiarios: de unos 90 clics a unos 40.
- Solicitud → actividad programada: de 9 clics a 5.
- No quedan datos con dos verdades sin aviso.
- Las pruebas existentes siguen pasando (se ajustan solo las que leen pantallas que cambiaron a propósito), y hay pruebas esenciales nuevas.
- Migraciones solo aditivas o de datos.
- La eliminación de plantillas se hace después de verificar que nada las usa.

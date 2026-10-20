# FCHE — Plataforma de gestión de actividades y banco institucional

Contexto permanente del proyecto. Léelo completo antes de tocar código.
Fundación Chile Edúcate (FCHE). Práctica profesional: 14-09-2026 al 30-11-2026. Fecha de este documento: 12-10-2026 (quedan ~7 semanas).

---

## 0. Reglas de trabajo (contrato contigo)

1. **No inventes requisitos.** Cada decisión de negocio lleva una etiqueta:
   - **[O]** oficial: documentos `docs/oficiales/01` a `06`.
   - **[D]** evidencia en documentos reales de FCHE (minutas, cartas, fichas, postulaciones, certificados).
   - **[P]** propuesta de diseño, aún no aprobada por el cliente.
   - **[V]** por validar con Claudio (cliente) o Manuel (tutor).
2. **Lo marcado [V] no se implementa en silencio.** Pregúntame, o impleméntalo detrás de una opción fácil de cambiar y déjalo anotado en la spec.
3. **Trabajo por feature (F01…F21), con método Spec-Driven:** `specs/fXX/spec.md` (qué y por qué) → `plan.md` (cómo) → `tasks.md` (pasos). Breves. Primero la spec, luego el código. Si cambia una decisión, actualiza primero la spec.
4. **Pide permiso antes de:** instalar software del sistema, borrar datos o migraciones, agregar dependencias que no estén en la sección 5, o cambiar una decisión de la sección 3.
5. **Datos:** nunca uses datos reales (RUT, teléfonos, nombres, cuentas bancarias) en código, fixtures ni tests. Todo dato de prueba es ficticio. Los documentos reales viven en `docs/reales/` (ignorada por git).
6. **Idioma:** interfaz en español de Chile. Modelos, campos, URLs y mensajes de commit en español. Lo propio del framework en inglés.
7. Commits pequeños, una rama por feature (`feature/f04-personas`). Nunca subas `.env`, bases de datos ni archivos subidos.
8. Al terminar cada tarea, entrégame: qué hiciste, qué probaste, qué quedó pendiente y qué preguntas tienes.

---

## 0.5 Decisiones vigentes (actualizado 12-10-2026)

Fuentes, de más a menos reciente: **«FCHE — Requerimientos por módulo»** (HU con IDs AC, US, TE, PE…; trazabilidad en `specs/trazabilidad_requerimientos.md`), el **tablero de GitHub** (tarjetas F01–F21) y este documento. Donde difieren, prevalece el más reciente.

- **Finalizar actividad** exige asistencia (o «sin registro» explícito) y resultado, y la deja **realizada** y de solo lectura. **No existe el estado «cerrada».** Reabrir: permiso `reabrir_actividad`, que nadie tiene por defecto [V#4].
- **Segunda fase** (reuniones con asistentes y compromisos, tareas, beneficiarios, verificaciones, finanzas): está construida pero **oculta** con `SEGUNDA_FASE=False` en `.env`. Con `True` se muestra. Sin ella, la reunión es un canal de interacción y el panel muestra las próximas acciones. **Las sesiones (bitácora con minuta) son siempre visibles desde F22 (13-10-2026).**
- **F22 Ingesta ampliada (13-10-2026, decidido con el usuario; spec en `specs/f22/`):**
  - persona con identificación, perfil, intereses y habilidades;
  - **datos sensibles en sección restringida**: permiso `ver_sensibles`, consentimiento obligatorio y ajuste `DATOS_SENSIBLES`;
  - consentimientos (se revocan, no se borran) y apoderados;
  - formación del estudiante ampliada;
  - **Comunidad como registro propio** (app `comunidades`) con padrón;
  - actividad con público objetivo, comunidades destinatarias y equipo ejecutor frente a asistentes (grupo del rol);
  - participación con institución, comunidad y horas;
  - pestaña **Alcance** en actividad, proyecto y comunidad;
  - planillas con columnas nuevas.
  Amplía la sección 7 con autorización expresa del usuario; lo [V] queda listado en la spec.
- **F23 Contenedor Territorio (13-10-2026; spec en `specs/f23/`):** la comuna y el sector son contenedores (Resumen con indicadores, personas residentes, alcance, índice «Dónde trabajamos»). Exportar el resumen a Excel exige el permiso `territorio.exportar_territorio`; RUT y contactos solo con `exportar_persona`, sin menores por nombre ni pertenencia a comunidades indígenas. Lo [V] queda en la spec.
- **F24 Cascada, buscadores y fichas por tipo (14 a 19-10-2026; spec en `specs/f24/`):** el usuario pidió tablas relacionales normalizadas, no texto libre ni JSON.
  - **Buscadores:** despliegan a los registrados al hacer clic, con «+ Crear» en una ventana.
  - **Selección múltiple y filtros:** la selección múltiple es desplegable; los filtros muestran pocos principales y el resto en «Más filtros».
  - **Territorio oficial:** `apps/territorio/datos/cut_chile.csv` (346 comunas; se carga con `cargar_territorio`) y ubicación en cascada en todo formulario.
  - **Catálogos nuevos:** tramos de edad (`TramoEtario`, selección múltiple), naturaleza jurídica, parentesco, tipo de invitado y estado del voluntario.
  - **Proyecto:** `ProyectoTerritorio`.
  - **Fichas por tipo de persona:** `PerfilPersona.ficha`. El estudiante usa `PersonaFormacion` con la sede como `Lugar`; además existen `FichaVecino` con `IntegranteHogar` (conteos) y `FamiliarVinculado`, `FichaInvitado` y `FichaVoluntario`.
  - **Persona:** `Persona.sexo` es un dato general opcional. El hogar es restringido 🔒, sin consentimiento extra; el tramo RSH sigue como dato sensible.
  - **Rol:** cada rol de participación tiene un perfil asociado.
  - Lo [V] queda en la spec.
- **Proyecto** es agrupador opcional con su ficha (equipo, organizaciones, actividades) [V#7]. Ninguna actividad lo exige.
- **Catálogos:** el Gestor agrega y edita valores; **desactivar** es solo del Administrador.
- **Cuentas:** desde la pantalla, una cuenta se crea solo para una persona ya registrada. La primera cuenta se crea por consola (`crear_usuario`).
- **Territorio:** dirección en cascada y nombres alternativos de sector (`SectorAlias`).
- **Documentos:** se puede asociar un documento existente a otra ficha sin copiar el archivo; tienen fecha de vencimiento; transcribir datos con el documento al lado (origen «por revisar»).
- **Escenarios hipotéticos:** el catálogo de escenarios se aplicó; estado de cada ID en `docs/escenarios_estado.md`. Pruebas con el ID del escenario en `apps/nucleo/test_escenarios_catalogo.py`.
- **Ajustes en `.env` además de los anteriores:** `DATOS_SENSIBLES`, `MODULOS_SEGUNDA_FASE`, `ROLES_FUERA_DE_CAPACIDAD`, `FERIADOS`, `INTENTOS_MAXIMOS`, `BLOQUEO_MINUTOS`, `SIN_RESPUESTA_DIAS`, `RESPALDO_MAX_DIAS`, `CONTACTO_ADMINISTRADOR`.
- **Commits:** sin líneas de coautoría ni marcas de herramientas.
- Apps además de la sección 6: `proyectos`, `coordinacion`, `finanzas`, `importaciones`, `comunidades`.
- **Interfaz:**
  - sistema de diseño propio en `static/css/fche.css` (tokens, componentes) e iconos SVG propios en `{% load fche %}` (`icono`, `estado`, `celda`, `iniciales`);
  - formularios por secciones con el atributo `secciones` del form (BootstrapMixin).
- Sigue sin estar en el repositorio el Excel con las filas en amarillo ni el archivo oficial CUT.

Cómo trabajar: `.venv/bin/python -m pytest -q` (Mac) o `.venv\Scripts\python -m pytest -q` (Windows). Uso: `docs/manual_de_uso.md`; entrega: `docs/entrega.md`; specs: `specs/fXX/`.

---

## 1. Qué es el proyecto

FCHE coordina actividades educativas y comunitarias con personas, instituciones, municipalidades, juntas de vecinos y empresas. Hoy la información está dispersa en Word, PDF, Excel, minutas, cartas y mensajes. Eso genera duplicación, pérdida de contexto y dificultad para reconstruir quién participó, con quién y dónde.

**Propósito [O]:** un sistema centralizado donde personas, organizaciones y lugares se registran **una sola vez**, se reutilizan en distintas actividades y acumulan historial. Un buscador y filtros ayudan a armar nuevas actividades. Cada cambio de fecha o lugar conserva la versión anterior.

**Principio rector [O]:** existir como persona, organización o participante **no implica tener cuenta**. La cuenta es solo para quien necesita autenticarse y operar.

**Flujo central [O]:**
`Solicitud / oportunidad → Actividad → coordinación → ejecución → resultados → historial → banco enriquecido`

La **Actividad** es la unidad central. Persona, Organización y Lugar son maestros reutilizables.

---

## 2. Alcance y plazo

**Dentro (MVP) [O]:** acceso y roles, personas, organizaciones y carreras, lugares, solicitudes/oportunidades, interacciones, actividades, participación, agenda versionada, calendario, búsqueda y filtros, validación de compatibilidad, documentos, asistencia y resultados, historial, trazabilidad básica, exportación autorizada, catálogos.

**Fuera de esta etapa [O]:** donaciones, inventario, contabilidad, pagos, integración con WhatsApp, n8n/automatizaciones, IA.

**Fuera por decisión del proyecto [P]:** portal público de inscripción y registro de personas por sí mismas. La información de estudiantes llega como listado, planilla o correo y la ingresa Claudio.

**Nota:** el tutor marcó en amarillo, en el Excel de requerimientos, filas que "no corresponden ahora" (según lo relatado: auditoría avanzada, importación histórica, IA, WhatsApp, n8n, donaciones, historial documental avanzado). **Ese Excel no está en este repositorio.** Pídelo al usuario antes de planificar F16, F18 y F19.

---

## 3. Decisiones cerradas

| Tema | Decisión |
|---|---|
| Stack | Django + PostgreSQL + plantillas de Django con Bootstrap y HTMX |
| Entorno | Local, Windows. Podría alojarse en la web más adelante (aún no definido) |
| Roles | **Gestor** (Claudio, único digitador) y **Administrador** (programador). Operador adicional: opcional [O], no se crea |
| Digitación | Toda la ingesta la hace Claudio |
| Registro | Sin portal público. Sin autoservicio |
| Persona ≠ Cuenta | Relación 1 a 0..1 [O] |
| Punto de entrada | Solicitud/Oportunidad → Actividad (0..1 a 1) [O]; opcionalmente Proyecto como agrupador [V#7] |
| Borrado | No se elimina información con historial: se desactiva, cancela o cierra |
| Agenda | Reprogramar crea una versión nueva y conserva la anterior [O] |
| Matching | Sugiere candidatos con razones y conflictos (F16, implementado). **Nunca asigna solo** [O] |
| Estados de actividad [O] | planificada, confirmada, reprogramada, suspendida, cancelada, realizada y **pendiente** (oportunidad abierta) |
| Cierre | «Finalizar actividad» exige asistencia (o «sin registro») y resultado; queda *realizada* y de solo lectura. Reabrir: permiso especial |
| Respaldos | `pg_dump` diario más copia de la carpeta de documentos [O, RNF-10] |

---

## 4. Pendientes: pregunta, no asumas

1. **[V]** ¿Quién será Administrador después del 30-11? (el programador, el tutor u otra persona).
2. **[V]** Menores de edad: qué datos se conservan, autorización del apoderado y por cuánto tiempo.
3. **[V]** Si una actividad con incompatibilidad crítica se puede confirmar de todos modos, con motivo. RF-22 dice "impedir o advertir".
4. **[V]** Si una actividad realizada se puede reabrir o corregir.
5. **[V]** Acceso desde celular (RNF-06 [O]) con un sistema local: ¿red de la Fundación o solo el equipo donde corre?
6. **[V]** Notificaciones internas o por correo: hoy no hay ninguna definida.
7. **[V]** Proyecto/campaña como agrupador opcional: confirmar con Manuel.
8. **[V]** Alcance real del matching (RF-19/20 son MVP oficial, pero el tutor pudo marcarlo).
9. **[V]** Recuperación de contraseña: hoy solo la restablece el Administrador.
10. **[V]** Qué documentos emite la Fundación (constancias, informes) y cada cuánto caducan verificaciones y listas de autoridades.

---

## 5. Stack y entorno (Windows)

- **Python** con entorno virtual (`.venv`) y **Django LTS vigente** (verifica la versión estable al iniciar).
- **PostgreSQL** como servicio de Windows. Extensión `pg_trgm` para búsqueda aproximada y duplicados.
- **Dependencias permitidas:** `psycopg`, `django-simple-history`, `django-htmx`, `whitenoise`, `waitress`, `openpyxl`, `django-environ` (o `python-decouple`), `pytest-django` (opcional). Cualquier otra, consúltala.
- **Estáticos locales (sin CDN):** Bootstrap, HTMX y FullCalendar se incluyen en `static/vendor/` para que funcione sin internet.
- **Servidor:** `waitress` (no `runserver` en uso real). Script `iniciar.bat` para arrancar. `respaldar.bat` con `pg_dump` y copia de documentos (se programa en el Programador de tareas de Windows).
- **Configuración:** variables en `.env` (clave secreta, base de datos, `DEBUG`, `ALLOWED_HOSTS`). Ajustes separados `base.py`, `local.py`, `produccion.py`. Rutas con `pathlib`, nunca fijas. Archivos subidos en una carpeta **fuera del código**.
- **Regional:** `LANGUAGE_CODE = "es-cl"`, `TIME_ZONE = "America/Santiago"`.
- Pensado para poder mudarse a un servidor web sin reescribir: migraciones versionadas en git, sin lógica atada a una máquina.

---

## 6. Estructura sugerida

```
fche/
├── config/                 # settings (base, local, produccion), urls, wsgi
├── apps/
│   ├── nucleo/             # layout, buscador global, dashboard, utilidades, auditoría
│   ├── cuentas/            # Gestor / Administrador, permisos, mi cuenta
│   ├── territorio/         # región, provincia, comuna, sector, dirección
│   ├── personas/           # persona, contactos, formación
│   ├── organizaciones/     # organización, carreras, cargos
│   ├── lugares/
│   ├── solicitudes/        # solicitud/oportunidad, interacciones
│   ├── actividades/        # actividad, participación, agenda, resultados
│   └── documentos/
├── templates/  static/  media/  (media fuera del repo)
├── specs/                  # fXX/spec.md, plan.md, tasks.md
├── docs/oficiales/         # 01–06 (fuente de verdad) y docs/bpmn/*.bpmn
├── docs/reales/            # documentos reales de FCHE (en .gitignore)
├── iniciar.bat  respaldar.bat  .env.example
```

---

## 7. Modelo de datos

Una sola base relacional, organizada en grupos lógicos. **No** uses el DDL de Oracle generado antes: es documentación. La base nace de los modelos de Django.

### 7.1 Territorio [O/D]
`region 1─N provincia 1─N comuna 1─N sector (con sector_padre opcional)`; `direccion` es una tabla compartida por personas, organizaciones y lugares.
- `sector` es jerárquico: *San Pedro de la Costa* contiene Etapa 1 a 4, y existen villas y poblaciones. `tipo` ∈ {sector, etapa, villa, población, barrio}.
- `direccion`: calle, número, block, depto, referencia, `comuna`, `sector` opcional. **El sector debe pertenecer a la comuna** (valida en `clean()` y, si es posible, con constraint).
- Región y provincia no se guardan en la dirección: se deducen de la comuna.
- Cargar regiones, provincias y comunas desde la **fuente oficial (códigos CUT)**, no a mano. Pídeme el archivo o confirma la fuente.

### 7.2 Personas [O/D]
- `persona`: `nombres` (obligatorio), `apellido_paterno`, `apellido_materno`, `rut_numero` + `rut_dv` (opcionales), `origen`, `estado_registro`, `observaciones`, `activo`, `creado_por`, `creado_en`.
- **RUT:** guardar sin puntos, validar módulo 11, dígito `K` en mayúscula, **único si existe**. Hay personas sin RUT.
- `contacto`: tipo (teléfono móvil, teléfono fijo, correo, sitio web, red social), valor, valor normalizado (teléfono en formato internacional), principal, vigente. Pertenece a una persona, a una organización o a un cargo.
- `persona_direccion` con tipo (residencia, procedencia).
- `persona_formacion`: organización educativa, carrera, estado (estudiante, egresado, titulado), años, vigente. La carrera debe pertenecer a esa institución.
- `persona_organizacion`: organización, cargo, `tipo_cargo` (directorio, funcional, autoridad), fecha de inicio y término. Los cargos son **históricos**.
- Datos mínimos oficiales: nombre, identificador, contacto, origen, observaciones. Formación, experiencia, contacto de emergencia y similares vienen de la ficha de voluntario [D]: pídelos solo cuando hagan falta (RNF-02, minimización).

### 7.3 Organizaciones [O/D]
- `organizacion`: nombre, `tipo` (institución educativa, municipalidad, junta de vecinos o comité, empresa/partner, fundación/ONG, otra), identificador opcional, estado, `es_propia` (la Fundación misma), `activo`.
- `carrera`: pertenece a una organización educativa (RF-08).
- Una municipalidad se relaciona con una comuna (una por comuna).
- Los contactos de FCHE misma tienen **propósito** (institucional, cartas, donaciones): hay más de un teléfono y correo en circulación.

### 7.4 Lugares [O]
`lugar`: nombre, tipo, `direccion`, capacidad, condiciones, `organizacion_propietaria` opcional, activo.

### 7.5 Solicitud, interacción, actividad [O]
- `solicitud` (oportunidad): origen, canal, fecha, motivo, estado, persona y organización de contacto **opcionales**, `actividad` (0..1).
- `interaccion`: fecha, canal, con quién (persona u organización), resultado, próxima acción y fecha; opcionalmente ligada a una solicitud o actividad.
- `actividad`: nombre, `tipo`, objetivo, descripción, `estado`, modalidad (presencial, virtual, híbrida), responsable (persona), condiciones, `proyecto` opcional, `actividad_padre` opcional [P] (una jornada contiene charlas y talleres [D]).
- `actividad_territorio` [P]: una actividad puede dirigirse a varios territorios y de distinto nivel. Exactamente un nivel (región, provincia, comuna o sector) no nulo por fila. Permite saber "es en Hualpén" aunque aún no haya lugar.
- `participacion` (persona–actividad): rol, estado, asistencia, observaciones, fecha. Único por (actividad, persona, rol).
- `actividad_organizacion`: tipo de intervención, **persona de contacto opcional** [O, doc 04], observaciones.
- `agenda_actividad`: `version`, `vigente`, fecha, hora de inicio y término, duración, lugar, estado, motivo del cambio. **Una sola vigente por actividad** (constraint parcial). Al reprogramar, la anterior pasa a histórica.
- `documento`: archivo, tipo, fecha, descripción, **actividad** [O, RF-23]; asociaciones opcionales a persona u organización [P]; `restringido` (booleano); folio, emisor y fecha de emisión cuando aplique.
- Resultados: observaciones, incidencias y resultado por actividad; la asistencia vive en la participación.
- `proyecto` [V]: nombre, descripción, estado. Solo agrupador.

### 7.6 Segunda fase (diseñar sin construir todavía) [D/P]
Reunión (asistentes, objetivos, asuntos, compromisos), tarea con varios responsables, sesión de actividad, beneficiarios, taller como diseño reutilizable, verificación de persona (restringida y con vigencia), colaboración (solicitud de apoyo con estado), requisitos documentales de fondos, divisiones electorales, donaciones y movimientos bancarios.

### 7.7 Reglas de integridad
- `on_delete=PROTECT` por defecto. La interfaz **no ofrece "Eliminar"** sobre registros con historia.
- **Buscar antes de crear** persona y organización: coincidencia por RUT, correo y nombre aproximado (`pg_trgm`). Se muestra y se decide: nunca se fusiona ni se bloquea solo por no tener RUT.
- Historial de cambios con `django-simple-history` en persona, organización, lugar, actividad, participación y solicitud.
- Nada de lógica de negocio en las plantillas.

---

## 8. Catálogos iniciales (editables desde la interfaz)

- **estado_actividad:** planificada, confirmada, reprogramada, suspendida, cancelada, realizada, pendiente.
- **estado_solicitud [P]:** pendiente, en seguimiento, convertida, descartada.
- **estado_participacion [P]:** invitado, interesado, disponible, confirmado, asistió, no asistió, rechazó, canceló. (El registro de interés y disponibilidad es RF-21 [O].)
- **rol_participacion [O/D]:** estudiante, practicante, ayudante, voluntario, tutor, tallerista, coordinador, participante, beneficiario, contacto institucional.
- **tipo_organizacion [O].** **tipo_actividad [D]:** taller, charla, jornada, live, difusión, campaña. **tipo_contacto, canal, modalidad, origen_persona** (invitación, difusión, interés propio, derivación, búsqueda activa [O]). **estado_registro [P]:** activo, incompleto, por verificar, desactualizado.

---

## 9. Roles y permisos (siempre validados en el servidor)

- **Gestor (Claudio):** todo lo operativo (solicitudes, actividades, personas, organizaciones, lugares, agenda, resultados, documentos, cargas, historial, exportar) y agregar valores a catálogos.
- **Administrador (programador):** usuarios y roles, estructura de catálogos, auditoría, respaldos y migraciones. Puede ver todos los datos, **solo para mantenimiento**.
- Un permiso por acción (ver, crear, editar, reprogramar, cerrar, exportar), mediante grupos de Django. Rechazo con 403, con pantalla propia.
- Los documentos restringidos se sirven con una vista que comprueba permiso, nunca como archivo estático.

---

## 10. Navegación y UX

**Rutas:** `/login`, `/dashboard`, `/buscar`, `/solicitudes[/<id>]`, `/actividades[/<id>]`, `/personas[/<id>]`, `/organizaciones[/<id>]`, `/lugares[/<id>]`, `/territorio`, `/calendario`, `/documentos`, `/importaciones` (carga de listados), `/mi-cuenta`, `/administracion/...`, `/403`, `/404`.

**Patrones obligatorios:**
- **Dashboard** = qué tengo que hacer hoy: actividades incompletas, solicitudes sin respuesta, personas incompletas, tareas por vencer, acciones rápidas.
- **Buscador global** visible siempre: personas, organizaciones, actividades, lugares y documentos.
- **Fichas con pestañas internas** (la sección cambia dentro de la ficha). Se abre una ficha propia solo al entrar a otro registro (actividad, persona, organización, lugar).
- **Crear desde el contexto:** al agregar un participante, organización o lugar: buscar → seleccionar; si no existe, un modal lo crea y queda seleccionado, sin salir.
- **Breadcrumb y `[← Volver]`** en toda ficha. Volver no modifica datos y avisa si hay cambios sin guardar.
- **Guardar borrador:** crear nunca se bloquea por datos faltantes. Solo se exige algo al confirmar y al cerrar [V, mínimos propuestos]:
  - Confirmar: responsable, fecha y hora, lugar o modalidad virtual, capacidad compatible.
  - Cerrar: asistencia (o "sin registro" explícito) y resultado.
- Todo listado tiene búsqueda, filtros, orden y paginación. Todo registro con historia: ver, editar, relacionar, desactivar, ver historial.
- Estados de pantalla en todas: cargando, vacío, sin resultados, error, sin permiso, guardando, guardado, confirmación.
- Responsive (Bootstrap).

---

## 11. Ingesta de datos (la hace Claudio)

1. **Ficha rápida:** nombre y un dato de contacto; el resto después. Tres niveles: rápida, completa, "completar luego".
2. **Cola de incompletos** en el dashboard, priorizando personas de actividades próximas.
3. **Carga de listado por actividad:** subir o pegar la planilla que manda una institución → vista previa (nuevos, existentes, posibles duplicados, errores) → confirmar. Lote registrado (archivo, usuario, fecha, cifras) y **reversible**.
4. **Teléfonos al importar:** leer las celdas como texto y normalizar a formato internacional. Nombres: aceptar "Nombre Apellido" y "Apellido, Nombre" y separarlos.
5. **Ingesta asistida [P]:** documento a un lado, formulario al otro. Sin lectura automática.
6. Los PDF y Word históricos son **evidencia**, no se convierten en tablas. Se extrae solo el dato estructurado y se vincula el documento original.
7. Cada dato conserva su **fuente** (formulario, lote, documento de origen) y fecha de captura.

La **importación histórica masiva** puede estar fuera del MVP según lo marcó el tutor [V]; la carga por actividad sí es operación normal [O].

---

## 12. Seguridad y privacidad

- Sesión con expiración por inactividad [P], validadores de contraseña, cierre de sesión visible.
- `SECRET_KEY` y credenciales solo en `.env`. `DEBUG=False` fuera de desarrollo.
- Minimización de datos [O, RNF-02]: no pidas más campos de los necesarios. Distingue datos **generales**, **restringidos** (dirección, RUT, documentos personales) y **sensibles** (menores, verificaciones, contacto de emergencia).
- Nunca guardes en datos de prueba, ni en el repositorio, cuentas bancarias ni documentos reales.
- Revisa la nueva ley de protección de datos personales con el tutor.
- Exportaciones solo para usuarios autorizados.

---

## 13. Plan de features (propuesta de orden para ~7 semanas) [P]

| Fase | Features | Estado |
|---|---|---|
| A (sem. 1–2) | F01 base, navegación e instalación en Windows · F02 ingreso y sesión · F03 usuarios y 2 roles · territorio y catálogos · F04 personas · F05 organizaciones y carreras · F06 lugares | MVP |
| B (sem. 3–4) | F07 solicitudes/oportunidades · F09 actividades, participación y carga de listado · F10 agenda versionada y calendario · F11 compatibilidad y validaciones | MVP |
| C (sem. 5–6) | F12 interacciones (y reuniones/tareas en versión simple) · F13 documentos, asistencia, resultados y cierre · F14 historial y trazabilidad básica · F15 búsqueda global, filtros y exportación | MVP |
| D (sem. 7) | F20 pruebas y validación con el usuario · F21 entrega local, respaldos, manual de uso | MVP |
| Según tutor | F16 matching [V] · F17 catálogos avanzados · F18 importación histórica masiva [V] | Por confirmar |
| Posterior | F19 presupuesto, aportes, donaciones, fuera de esta etapa [O] | Fuera |

---

## 14. Definición de terminado (por feature)

- `spec.md`, `plan.md` y `tasks.md` existen y reflejan lo construido.
- Modelos con migraciones. Datos iniciales de catálogos como *fixtures* ficticios.
- Pruebas automáticas mínimas: RUT, duplicados, agenda con una sola versión vigente, permisos (403), "no se elimina con historia", normalización de teléfonos.
- Pantallas con estados (cargando, vacío, error, sin permiso), breadcrumb y volver.
- Validación en servidor, no solo en pantalla.
- Revisión manual con un recorrido completo: crear persona → crear actividad → agregar participante → programar → reprogramar → registrar asistencia → ver historial.

---

## 15. Qué no hacer

- No crear cuentas para estudiantes, voluntarios, beneficiarios ni instituciones.
- No agregar portal público ni autoservicio.
- No implementar WhatsApp, IA, pagos, inventario, contabilidad ni automatizaciones.
- No usar el DDL de Oracle ni su estructura de 43 o 65 tablas como referencia de construcción.
- No eliminar físicamente registros con historial.
- No usar CDN ni servicios externos: el sistema debe funcionar sin internet.
- No ampliar el modelo con campos que no estén en la sección 7 sin preguntarme.
- No dar por oficial lo marcado [P] o [V].

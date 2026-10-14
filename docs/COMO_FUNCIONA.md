# Cómo funciona FCHE por dentro

Explicación en palabras simples: qué pasa cuando Claudio hace clic, dónde queda cada dato, cómo se conectan las tablas, qué son los catálogos y los perfiles, y cómo se manejan proyectos y documentos. Guía de uso pantalla a pantalla: `docs/manual_de_uso.md`. Historias con pruebas: `docs/auditoria/HISTORIAS_Y_PRUEBAS.md`.

---

## 1. La idea

- FCHE es una página web que corre en **un solo computador**. Claudio la abre en el navegador y no necesita internet.
- **La actividad es el centro.** Personas, organizaciones, comunidades y lugares se anotan **una sola vez** y después se **vinculan** a todas las actividades que haga falta.
- Lo que «hizo» una persona no se escribe aparte: es la lista de actividades donde está vinculada.

```
  PERSONA ──participa (rol, estado, asistencia)──┐
  ORGANIZACIÓN ──interviene (cómo, contacto)─────┤
  COMUNIDAD ──es el público──────────────────────┼── ACTIVIDAD ── agenda (versiones: fecha, hora, lugar)
  TERRITORIO (comuna o sector, sin lugar aún) ───┤                 └─ LUGAR ── dirección ── sector ── comuna ── provincia ── región
                                                 ├── documentos (evidencia)
                                                 ├── interacciones (llamadas, correos, próxima acción)
                                                 ├── sesiones y minutas
                                                 └── resultado (asistencia, observaciones, incidencias)
  SOLICITUD ──se convierte en──▶ ACTIVIDAD        PROYECTO ──agrupa (opcional)──▶ ACTIVIDADES
```

## 2. El camino de un clic: agregar un participante

Cada clic recorre siempre el mismo camino: **pantalla → ruta → vista → datos → plantilla**.

- **Ruta:** la dirección que aparece en el navegador.
- **Vista:** la función de Python que decide qué hacer.
- **Datos:** las tablas de la base.
- **Plantilla:** el archivo HTML que dibuja la página.

**Ejemplo real:** Claudio está en la actividad 7 y agrega a una voluntaria.

| Paso | Qué ve o hace Claudio | Qué pasa por dentro | Dónde está |
|---|---|---|---|
| 1. Pantalla | Abre la actividad, pestaña **Participantes**, y pulsa **«+ Agregar participante»** | La pestaña es un trozo HTML dentro de la ficha. El botón solo aparece si su rol tiene permiso para agregar. | `templates/actividades/pestanas/participantes.html` |
| 2. Ruta | El navegador va a `/actividades/7/participantes/nuevo` | La lista de rutas dice qué vista atiende esa dirección | `apps/actividades/urls.py:24` |
| 3. Vista (mostrar) | Ve un formulario: persona (con buscador), rol y estado | La vista `ParticipanteNuevo` **revisa en el servidor** el permiso `actividades.add_participacion` (sin él, pantalla 403), busca la actividad y arma el formulario | `apps/actividades/views.py:601-615`; formulario en `apps/actividades/forms.py:106` |
| 4. Plantilla | El formulario con sus etiquetas, ayuda y botones Guardar y Volver | `participante_form.html` toma el formulario común y agrega «¿No encuentras a la persona? Créala aquí mismo» | `templates/actividades/participante_form.html` → `templates/generico/formulario.html` → `templates/base.html` |
| 5. Guardar | Escribe «Vol», elige «Voluntario3 Demo», rol Voluntario, y pulsa Guardar | La vista recibe los datos y los **valida**: que la persona no esté ya con ese rol y que la actividad admita participantes | `apps/actividades/views.py:617-639` |
| 6. Datos | — | Se crea **una fila** en la tabla de vínculos `actividades_participacion` con la actividad, la persona, el rol, el estado, quién la creó y cuándo. La base **impide** repetir persona y rol en la misma actividad, aunque alguien salte la pantalla. El cambio queda además en la tabla de historial. | `apps/actividades/models.py:133-154` |
| 7. Respuesta | Vuelve a la pestaña Participantes con el mensaje «agregada como voluntario». Si se pasó la capacidad del lugar, ve un **aviso**, pero no un bloqueo. | La vista redirige a `/actividades/7?tab=participantes` | `apps/actividades/views.py:631-639` |

**Si la persona no existe:** pulsa «Créala aquí mismo» y va a `/actividades/7/participantes/rapido`.
- Ahí la vista `ParticipanteRapido` (`apps/actividades/views.py:641-687`) pide solo nombre y rol, más correo y teléfono si los tiene.
- **Antes de crear, busca parecidos.** Si encuentra alguno, muestra «Usar existente» y «Crear de todos modos».
- Luego crea, de una sola vez, la **persona** (con estado «incompleto»), sus contactos y el **vínculo** con la actividad.
- Vuelve a la actividad. La ficha de la persona se completa después.

**El menú y los botones cambian según el rol.**
- El menú está definido en `apps/nucleo/contexto.py:3-31`: cada opción lleva el permiso que exige, y solo se dibuja si el usuario lo tiene.
- Lo mismo pasa con los botones de cada ficha.
- Y aunque alguien escriba la dirección a mano, la vista vuelve a revisar el permiso.

## 3. Dónde se guarda todo

| Qué | Dónde | Comentario |
|---|---|---|
| **Datos** (personas, actividades, vínculos, catálogos…) | Base de datos **PostgreSQL** llamada `fche`, en el mismo computador | 70 tablas propias (16 son catálogos), 17 tablas de historial y las tablas de Django (cuentas, sesiones) |
| **Archivos subidos** (documentos) | La carpeta que diga `MEDIA_ROOT` en `.env` (por ejemplo `C:\fche_media`), **fuera del código**, ordenados en `documentos/AAAA/MM/` | Nunca se abren directo: pasan por una vista que revisa el permiso y deja registro (`/documentos/<id>/archivo`) |
| **Respaldos** | La carpeta de `RESPALDO_DIR` (por ejemplo `C:\fche_respaldos`) | Una copia de la base y un zip de los documentos por día |
| **Configuración y claves** | El archivo `.env` | No se sube al repositorio |
| **Registro de errores** | `logs/fche.log` | |
| **Código** | Carpetas `apps/` (lógica), `templates/` (pantallas), `static/` (estilos, iconos, Bootstrap, HTMX y calendario, todo local) | |

## 4. Las tablas y cómo se relacionan

**Las relaciones no se arman a mano.** Cada botón «+ Agregar» de una ficha crea una fila en una **tabla de vínculo**. Esa fila guarda las dos puntas (por ejemplo, persona y actividad) y los datos propios del vínculo (rol, estado, asistencia).

### 4.1 Maestros: se anotan una vez

| Tabla | Qué guarda | Se relaciona con |
|---|---|---|
| **Persona** | Nombre (lo único obligatorio), RUT opcional, origen, estado del registro, perfiles, observaciones | Contactos, direcciones, formación, cargos, participaciones, comunidades, documentos |
| **Organización** | Nombre, tipo, RUT u otro identificador, si es la propia Fundación, dirección | Carreras, personas con cargo, contactos, actividades, lugares que le pertenecen |
| **Lugar** | Nombre, tipo, dirección, capacidad, condiciones, organización dueña | Agenda de actividades |
| **Comunidad** (tu «grupo») | Nombre, tipo (vecinal, educativa, personas mayores…), comuna y sector, organización que la representa | Integrantes (personas), actividades, proyectos |
| **Territorio**: región → provincia → comuna → sector | La cadena de ubicación. El **sector** cubre villas, poblaciones, etapas y barrios, y puede tener sectores dentro. Hay nombres alternativos para reconocer escrituras distintas. | Direcciones, comunidades, actividades |
| **Dirección** | Calle, número, comuna y sector. **El sector debe ser de esa comuna.** | La usan personas, organizaciones y lugares |

### 4.2 El centro

| Tabla | Qué guarda |
|---|---|
| **Actividad** | Nombre, tipo, objetivo, descripción, estado, modalidad, responsable, proyecto (opcional), actividad padre (una jornada que contiene charlas), área temática, público objetivo |
| **Agenda de la actividad** | Cada programación es una **versión**: fecha, horas, lugar y motivo del cambio. Solo una está vigente; las anteriores quedan como historia y no se editan. |
| **Sesión** | Cada encuentro de una actividad que se repite, con su minuta (desarrollo, avances, acuerdos, próximos pasos) y su asistencia |

### 4.3 Vínculos (tablas intermedias)

| Vínculo | Une | Datos propios |
|---|---|---|
| Participación | persona ↔ actividad | rol, estado, asistencia, horas, observaciones |
| Intervención | organización ↔ actividad | cómo intervino (solicita, coordina, facilita espacio, aporta personas, aporta recursos…), persona de contacto |
| Público | comunidad ↔ actividad | beneficiarios estimados |
| Territorio de la actividad | comuna o sector ↔ actividad | «es en Hualpén» aunque aún no haya lugar |
| Cargo | persona ↔ organización | cargo, tipo (directorio, funcional, autoridad), fecha de inicio y de término (histórico) |
| Formación | persona ↔ institución y carrera | estado (estudiante, egresado, titulado), años |
| Integrante | persona ↔ comunidad | rol (integrante, dirigente, referente, vocero) |
| Equipo, organizaciones y comunidades del proyecto | persona, organización o comunidad ↔ proyecto | rol o tipo |

### 4.4 Seguimiento, evidencia y control

| Tabla | Para qué |
|---|---|
| **Solicitud** | Lo que llega (o lo que sale a buscar Claudio) antes de ser actividad. Puede quedar sin actividad. |
| **Interacción** | Una llamada, un correo, un mensaje o una reunión, con resultado y **próxima acción** con fecha. Se liga a una persona, una organización, una solicitud o una actividad. |
| **Invitación** y **solicitud de apoyo** | A quién se invitó y qué organización se pidió que apoye, con su respuesta |
| **Documento** | El archivo y sus datos (tipo, fecha, folio, emisor, vencimiento, restringido). Se liga a una ficha. |
| **Origen del dato** | De dónde salió un dato: el sistema, un documento, una planilla, una llamada… |
| **Lote de importación** | Cada planilla cargada, con sus filas, para poder revertirla |
| **Historial** | Una copia de cada versión de persona, organización, lugar, actividad, participación, solicitud y otras. Así se ve qué cambió, quién y cuándo. |
| **Auditoría** | Acciones importantes: ingresos, exportaciones, descargas, cuentas creadas, roles cambiados |

### 4.5 Segunda fase (existen, pero ocultas)

Reunión con asistentes, tarea con responsables, beneficiarios del proyecto, verificaciones de personas, postulaciones a fondos, presupuesto y movimientos de dinero. Con `SEGUNDA_FASE=False` en `.env` no aparecen ni se pueden abrir.

## 5. Catálogos (las listas de opciones)

Un **catálogo** es una lista de opciones de un menú desplegable.
- Se administran en **Menú → Catálogos** (`/administracion/catalogos/`).
- **Claudio (Gestor) agrega y edita** valores. **El Administrador desactiva** los que ya no se usan.
- **Nada se borra:** un valor desactivado deja de ofrecerse en registros nuevos, pero los antiguos lo conservan.

| Catálogo | Para qué | Valores de hoy |
|---|---|---|
| Estados de actividad | En qué punto está | Pendiente, Planificada, Confirmada, Reprogramada, Suspendida, Cancelada, Realizada |
| Tipos de actividad | Qué clase de actividad | Taller, Charla, Jornada, Live, Difusión, Campaña |
| Roles de participación | Cómo participa la persona | Estudiante, Practicante, Ayudante, Voluntario, Tutor, Tallerista, Coordinador, Participante, Beneficiario, Contacto institucional |
| Estados de participación | Si va a asistir | Invitado, Interesado, Disponible, Confirmado, Asistió, No asistió, Rechazó, Canceló, En lista de espera, Registro erróneo |
| Tipos de intervención | Cómo participó una organización | Solicita, Articula, Coordina, Facilita espacio, Aporta personas, **Aporta recursos** (donadores, sin montos) |
| Tipos de organización | Qué clase de organización | Institución educativa, Municipalidad, Junta de vecinos o comité, Empresa o partner, Fundación u ONG, Otra |
| Tipos de lugar | Qué clase de lugar | Sede, Sala, Salón comunitario, Establecimiento educacional, Espacio público, Otro |
| Modalidades | Cómo se hace | Presencial, Virtual, Híbrida |
| Canales | Por dónde fue el contacto | Llamado, Correo, Mensaje, Reunión, Presencial, Otro |
| Tipos de contacto | Qué dato de contacto es | Teléfono móvil, Teléfono fijo, Correo, Sitio web, Red social |
| Orígenes de persona | Cómo llegó a la Fundación | Invitación, Difusión, Interés propio, Derivación, Búsqueda activa |
| Estados de registro | Qué tan completa está la ficha | Activo, Incompleto, Por verificar, Desactualizado, Fallecida/o, Fusionada en otra ficha |
| Estados de solicitud | Seguimiento | Pendiente, En seguimiento, Convertida, Descartada |
| Tipos de documento | Qué es el archivo | Minuta, Carta, Ficha, Postulación, Certificado, Listado, Acta, Otro |
| Perfiles de persona | Quién es la persona, fuera de una actividad | Estudiante, Vecino o vecina de la comunidad, Voluntario o voluntaria, Tallerista o profesional, Dirigente social, Docente o académico, Funcionario institucional, Beneficiario o beneficiaria, Apoderado o apoderada |
| Áreas temáticas | Tema de la actividad o del interés | Educación, Educación financiera, Salud y bienestar, Medioambiente, Emprendimiento y empleo, Tecnología y alfabetización digital, Cultura y artes, Deporte y recreación, Personas mayores, Infancia y juventud, Inclusión y discapacidad, Vivienda y barrio, Participación ciudadana |

**Listas fijas.** Algunas listas están en el código y **no** se editan desde la pantalla:
- el tipo de sector (sector, etapa, villa, población, barrio);
- el tipo de comunidad;
- el estado de un proyecto (en preparación, postulado, en ejecución, finalizado, suspendido, cancelado);
- el estado de una invitación (enviada, respondió, aceptó, rechazó, sin respuesta).

Cambiarlas requiere al programador.

### Los estados de la actividad y cómo se pasa de uno a otro

| Estado | En palabras simples | Desde aquí puede pasar a |
|---|---|---|
| **Pendiente** | Una idea o una solicitud, todavía sin fecha. Es el estado al crearla. | Planificada (al programarla) o Cancelada |
| **Planificada** | Ya tiene fecha; falta confirmar | Confirmada, Suspendida, Cancelada o Realizada |
| **Confirmada** | Está todo listo. Para confirmar se exige responsable, fecha y lugar (o modalidad virtual). | Reprogramada, Suspendida, Cancelada o Realizada |
| **Reprogramada** | Se cambió la fecha o el lugar después de confirmar | Confirmada, Suspendida, Cancelada o Realizada |
| **Suspendida** | Se detuvo y puede volver (pide motivo) | Planificada o Cancelada |
| **Cancelada** | No se hará (pide motivo). **No se puede reabrir.** | — |
| **Realizada** | Se hizo. Se llega **solo** con «Finalizar», que exige asistencia (o «sin registro») y resultado. Queda de solo lectura. | Solo con el permiso especial «reabrir», que nadie tiene por defecto [V#4] |

Las reglas están en `apps/actividades/reglas.py:7-17`.

## 6. Perfiles: qué ve cada uno

La palabra «perfil» se usa para dos cosas distintas.

**1. El rol de la cuenta** (quién entra al sistema). Solo hay dos:

| | Gestor (Claudio) | Administrador (programador) |
|---|---|---|
| Para qué | Toda la operación diaria | Cuidar el sistema |
| Menú | Inicio, Solicitudes, Proyectos, Actividades, Calendario, Personas, Organizaciones, Comunidades, Lugares, Territorio, Documentos, Importaciones, Catálogos, Ayuda | Lo mismo para **mirar**, más **Administración** |
| Crea y edita | Personas, organizaciones, lugares, comunidades, solicitudes, actividades, agenda, participantes, asistencia, resultados, documentos, cargas. **Agrega** valores a catálogos. | Cuentas, roles y permisos. **Desactiva** valores de catálogos. **Une** fichas repetidas. |
| No puede | Administrar cuentas, desactivar valores de catálogo, unir fichas, reabrir una actividad realizada, ver la auditoría | Digitar la operación (no crea personas ni actividades) |

- Los permisos de cada rol se ven y se ajustan en **Administración → Roles** (`apps/cuentas/roles.py`).
- *Hallazgo:* hoy el Administrador también puede ver datos sensibles y documentos restringidos, y exportar personas. Ver la pregunta 4 del resumen de la auditoría.

**2. El perfil de una persona registrada** (estudiante, vecina, voluntario, dirigente…). Es un dato de su ficha, sale del catálogo «Perfiles de persona» y sirve para filtrar y buscar. **No da acceso al sistema:** las personas registradas no tienen cuenta.

## 7. Proyectos: cómo verlos y cómo crearlos

Un **proyecto** agrupa actividades que van juntas, por ejemplo una campaña de alfabetización. **Es opcional:** ninguna actividad lo exige [V#7].

- **Ver:** Menú → **Proyectos** (`/proyectos`) → clic en uno. La ficha muestra estado, zona, fechas y responsable. Sus pestañas son:
  - Resumen;
  - Equipo;
  - Organizaciones;
  - Comunidades;
  - Actividades;
  - Alcance (personas, horas y comunidades alcanzadas);
  - Documentos;
  - Origen;
  - Historial.
- **Crear:** Proyectos → **«+ Nuevo proyecto»**. Solo el nombre es obligatorio. También se crea desde una solicitud, con «Crear proyecto».
- **Agregarle actividades** de tres formas:
  1. en el proyecto, pestaña Actividades → **«+ Nueva actividad»** (queda ligada sola);
  2. en una actividad existente → Editar → campo **Proyecto**;
  3. una solicitud convertida en proyecto y luego en actividad.
- Para probarlo con datos de demostración, abre «Proyecto Demo de alfabetización».

## 8. Documentos: cómo se suben, se ven y se revisan

| Acción | Cómo | Qué pasa |
|---|---|---|
| **Subir** | En la ficha (actividad, persona, organización, solicitud o proyecto) → pestaña Documentos → **«Subir nuevo»** | Se guarda el archivo en la carpeta de documentos y sus datos en la base. Tipos permitidos: PDF, Word, Excel, PowerPoint, texto, CSV, imágenes (JPG y PNG), audio y video. Máximo 25 MB. Un tipo no permitido o un archivo vacío se rechaza con un mensaje. |
| **Asociar uno existente** | Pestaña Documentos → **«Asociar existente»** | El mismo archivo queda disponible en otra ficha **sin copiarlo**. |
| **Ver y descargar** | Clic en el nombre (ficha del documento) o en «Descargar» | El archivo **pasa por una vista que revisa el permiso** y deja registro en la auditoría. No se puede abrir pegando una dirección. |
| **Restringido** 🔒 | Marcar «restringido» al subir o editar | Solo lo ven quienes tienen el permiso «ver restringido». No aparece en búsquedas ni listados de quien no lo tiene. |
| **Transcribir** | Ficha del documento → **«Transcribir»** | El documento a un lado y un formulario al otro, para copiar datos a una persona u organización. Cada dato queda marcado «salió de este documento» (pestaña Origen). |
| **Vencimiento** | Campo «vence el» | Los certificados vencidos se marcan en rojo, y el listado filtra por vencidos. |
| **Reemplazar el archivo** | Editar → nuevo archivo | La versión anterior se conserva. |
| **Archivar** | Ficha → Archivar (pide motivo) | No se borra: deja de aparecer en las listas normales. |
| **Buscar** | Menú → **Documentos** (`/documentos`) | Filtros por tipo, fecha, ficha asociada, restringidos y vencidos |

Los documentos son **evidencia**: no se convierten en tablas. Lo que importa de ellos se transcribe como dato y queda enlazado al original.

## 9. Cómo entra la información (ingesta)

Todo lo digita Claudio. Hay cinco puertas de entrada:

1. **Ficha rápida o completa** (Personas → «+ Nueva persona»): solo el nombre es obligatorio; el resto se completa después.
2. **Desde la actividad** (Participantes → «Créala aquí mismo»): la persona nace ya vinculada.
3. **Carga de listado** (Participantes → «Cargar listado», o Menú → Importaciones):
   - se sube o se pega la planilla de la institución;
   - el sistema muestra cuatro grupos: nuevos, ya existentes, posibles duplicados y errores;
   - **nada se guarda hasta confirmar**, y la carga se puede **revertir**.
4. **Transcribir un documento** (ver la sección 8).
5. **Solicitud → actividad** (Solicitudes → «Crear actividad»): los datos pasan sin reescribirlos.

Cada dato guarda su **fuente** (pestaña Origen) y cada cambio queda en el **Historial**.

## 10. Cómo se visualiza

| Para ver… | Ir a… |
|---|---|
| Qué hay que hacer hoy | **Inicio** (Panel): actividades incompletas, solicitudes sin respuesta, personas por completar, próximas acciones e invitaciones sin respuesta |
| Algo sin saber dónde está | El **buscador** de arriba (encuentra sin tildes) |
| Una lista con filtros | Cada opción del menú (búsqueda, filtros, orden, páginas y «Exportar») |
| Todo de una persona, organización, actividad, lugar o comunidad | Su **ficha**, con pestañas |
| Qué se hizo en un lugar del mapa | **Territorio** → la comuna o el sector |
| Las fechas | **Calendario** (mes, semana o lista; un clic abre la actividad) |
| Qué cambió | La pestaña **Historial** de cada ficha |

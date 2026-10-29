# Cumplimiento de los requerimientos

Auditoría del 14-10-2026 sobre la rama `auditoria/documentacion`, que parte de `main` en el commit `bb8307d`. Fuente de las historias: `docs/Requerimientos_por_modulo_FCHE.md`.

**Cómo leer la tabla**
- **Estado**: Cumple, Parcial, No cumple o No aplica. Ninguna historia se marca «Cumple» sin una evidencia concreta.
- **Evidencia**: archivo y línea del código, o la prueba automática que lo demuestra. Las pruebas viven en `apps/<app>/tests.py` o `apps/<app>/test_*.py`; la ruta se da sin el prefijo `apps/`.
- **Cómo probarlo**: los pasos en pantalla, entrando como Gestor salvo que se indique otra cosa.
- **[V]**: depende de una decisión pendiente con Claudio o Manuel.

Todas las pruebas citadas pasaron el 14-10-2026: **546 pruebas, 0 fallas**.

## Resumen

| | Historias (HU) | Reglas transversales (NF) |
|---|---|---|
| Cumple | 109 | 5 |
| Parcial | 4 | 3 |
| No cumple | 0 | 0 |
| No aplica | 1 | 1 |
| **Total** | **114** | **9** |

**Parciales:**
- HU-TE-06: falta el archivo oficial de comunas.
- HU-PE-10: falta decidir qué se guarda de los menores [V#2].
- HU-VA-04: la búsqueda de candidatos no filtra por perfil de persona.
- HU-DA-04: crear una persona o un lugar «sin salir» abre una página dentro de la actividad, no una ventana emergente.
- NF-03, NF-04 y NF-06.

**No aplica:**
- HU-DA-06 (celular): tu documento lo deja fuera de alcance.
- NF-08: no se puede comprobar con una prueba.

---

## Módulo 1 · Acceso y sesión (AC)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-AC-01 | Ingresar con correo y contraseña | Cumple | `cuentas/tests.py:11` test_ingresa_con_usuario_o_correo; `nucleo/tests.py:37` | En `/login`, escribir el correo (o el usuario) y la contraseña: llega al Panel. |
| HU-AC-02 | Cuenta desactivada explicada | Cumple | `cuentas/tests.py:175` y `:184` (con la clave mala no revela nada); `config/settings/base.py:123` `CONTACTO_ADMINISTRADOR` | Como Administrador, desactivar al Gestor. Ingresar como Gestor con la clave correcta: explica que la cuenta está desactivada y a quién consultar. |
| HU-AC-03 | La sesión se cierra sola [P] | Cumple | `config/settings/base.py:134-135`: 60 minutos sin uso (`SESION_SEGUNDOS`). Sin prueba automática. | Cambiar `SESION_SEGUNDOS=60` en `.env`, reiniciar, esperar 1 minuto y hacer clic: pide ingresar de nuevo. |
| HU-AC-04 | Cambiar la contraseña en Mi cuenta | Cumple | `cuentas/tests.py:154` test_mi_cuenta_y_cambio_de_clave | Menú del nombre → Mi cuenta → Cambiar contraseña. |
| HU-AC-05 | Pantalla clara de «sin permiso» y «no existe» | Cumple | `nucleo/tests.py:51` (403 propio), `:71` (404 propio); `templates/errores/` | Como Gestor abrir `/administracion/usuarios` (403) y `/no-existe` (404). Ambas tienen «Volver al inicio». |
| HU-AC-06 | El Administrador restablece una contraseña | Cumple | `cuentas/tests.py:119` test_restablecer_clave_solo_admin | Como Administrador: Administración → Usuarios → la cuenta → Restablecer contraseña. La recuperación sin el Administrador sigue [V#9]. |
| HU-AC-07 | Toda pantalla privada pide ingresar | Cumple | `config/settings/base.py:49` `LoginRequiredMiddleware`; `nucleo/tests.py:28` | Sin sesión, abrir `/personas`: lleva al ingreso y, al entrar, vuelve a `/personas`. |

## Módulo 2 · Usuarios, roles y permisos (US)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-US-01 | Cuenta solo para una persona ya registrada | Cumple | `cuentas/tests.py:191` test_crear_cuenta_exige_persona; `:88` (una persona, una cuenta) | Administración → Usuarios → «+ Nuevo usuario»: obliga a elegir una persona. *Ojo:* el comando de consola `crear_usuario` puede crear la primera cuenta sin persona. |
| HU-US-02 | Dos roles, Gestor y Administrador | Cumple | `cuentas/tests.py:45`, `:57`, `:62`; `apps/cuentas/roles.py` | Ingresar con cada cuenta: el Gestor no ve «Administración». |
| HU-US-03 | Desactivar o reactivar sin borrar | Cumple | `cuentas/tests.py:102`, `:31` (cierra la sesión abierta) | Usuarios → la cuenta → Desactivar. La persona sigue en Personas. |
| HU-US-04 | Queda quién creó la cuenta y quién cambió el rol | Cumple | `apps/cuentas/views_admin.py:75` (`usuario_creado`), `:96` (`rol_cambiado`); `cuentas/tests.py:206` | Crear una cuenta y luego abrir Administración → Auditoría. |
| HU-US-05 | Los permisos se revisan en el servidor | Cumple | `cuentas/tests.py:66`; `nucleo/test_escenarios.py:180`; `personas/tests.py:223` | Como Administrador, escribir a mano `/personas/nueva`: da 403 aunque el botón no se vea. |

## Módulo 3 · Territorio (TE)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-TE-01 | Dirección en cascada región → comuna → sector | Cumple | `territorio/tests.py:148`, `:156`; `templates/territorio/_ubicacion.html` y `templates/territorio/_direccion_form.html` | Nueva organización → Dirección: al elegir la región se filtran las comunas, y luego los sectores. |
| HU-TE-02 | Sectores dentro de sectores | Cumple | `territorio/tests.py:12`, `:114`; `apps/territorio/models.py:68` `sector_padre` | Territorio → una comuna → Sectores → crear «Etapa 1» con sector padre. |
| HU-TE-03 | Ver todo lo de una comuna o sector | Cumple | `territorio/tests.py:93`; `territorio/test_contenedor.py:76`, `:217` | Territorio → la comuna: Resumen con cifras clicables y pestañas con contador. |
| HU-TE-04 | Crear un sector sin salir y reconocer nombres escritos distinto | Cumple | `territorio/tests.py:167`, `:133`, `:142`; `apps/territorio/models.py:102` `SectorAlias` | En una dirección, «+ Crear sector». Escribir «Pobl. Las Flores» y luego «Población Las Flores»: avisa que se parece. |
| HU-TE-05 | Municipalidad ligada a su comuna | Cumple | `organizaciones/tests.py:78`; `apps/organizaciones/models.py:21` | Nueva organización de tipo Municipalidad → elegir su comuna. La comuna la muestra en su cabecera. |
| HU-TE-06 | Cargar regiones y comunas desde la fuente oficial | **Parcial** | El comando existe y está probado: `territorio/tests.py:63`, `apps/territorio/management/commands/cargar_territorio.py`. **Falta el archivo CUT.** La base de prueba solo tiene «Región Demo / Comuna Demo». | `python manage.py cargar_territorio comunas.csv` cuando tengas el archivo. |

## Módulo 4 · Personas (PE)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-PE-01 | Registrar solo con el nombre | Cumple | `personas/tests.py:20` test_ficha_rapida_solo_con_nombre | Personas → «+ Nueva persona» → escribir solo el nombre → Guardar. |
| HU-PE-02 | Ver coincidencias antes de crear y decidir | Cumple | `personas/tests.py:59`, `:71`, `:78`, `:250`; `nucleo/test_escenarios.py:69` | Crear «Voluntario1 Demo» otra vez: muestra la ficha parecida con [Usar existente] y [Crear de todos modos]. |
| HU-PE-03 | RUT con o sin puntos, validado; seguir sin RUT | Cumple | `nucleo/test_utilidades.py:14`, `:18`; `personas/tests.py:36`, `:41`, `:47`, `:53` | Escribir un RUT inventado con el dígito verificador malo: avisa. Con puntos o sin ellos se guarda igual. |
| HU-PE-04 | Anotar de dónde llegó la persona | Cumple | `apps/personas/models.py:66` (catálogo «origen de persona») | Ficha completa → campo Origen. |
| HU-PE-05 | Varios contactos; teléfono en formato único | Cumple | `personas/tests.py:28`, `:93`, `:104`; `nucleo/test_utilidades.py:49` | Ficha → Contactos → «+ Agregar»: escribir «9 1234 5678» y queda «+56 9 1234 5678». |
| HU-PE-06 | Relacionar con instituciones, carreras y cargos con fechas | Cumple | `personas/tests.py:116`, `:129`, `:138`, `:275` | Ficha → Formación, y Organizaciones y cargos → «+ Agregar». |
| HU-PE-07 | Acumular roles sin otra ficha | Cumple | `actividades/tests.py:304`; `nucleo/test_escenarios_catalogo.py:344` | Agregar a la misma persona a dos actividades con roles distintos: la ficha muestra ambas. |
| HU-PE-08 | Estado del registro (activo, incompleto…) | Cumple | `personas/tests.py:230` | Editar la persona → Estado del registro. |
| HU-PE-09 | Ficha con todo en un solo lugar | Cumple | `personas/tests.py:178` | Abrir una persona: pestañas Datos, Contactos, Formación, Organizaciones y cargos, Participaciones, Documentos, Historial y otras. *Nota:* son hasta 18 pestañas; ver la propuesta 6 del inventario. |
| HU-PE-10 | Datos sensibles y de menores, solo cuando hacen falta y restringidos | **Parcial** | Permiso propio y consentimiento: `personas/tests.py:159`; `nucleo/test_f22.py:58`, `:69`, `:79`, `:92`. **Falta decidir qué se conserva de los menores y por cuánto tiempo [V#2].** | Sin el permiso «ver datos sensibles», las pestañas con 🔒 no aparecen. |
| HU-PE-11 | Desactivar en vez de eliminar | Cumple | `personas/tests.py:190`, `:199` (no existe ruta para eliminar) | Ficha → Desactivar. Sigue en las actividades pasadas. |

## Módulo 5 · Organizaciones y carreras (OR)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-OR-01 | Tipos comunes de organización | Cumple | `organizaciones/tests.py:17`; catálogo «tipos de organización» | Organizaciones → «+ Nueva» → Tipo. |
| HU-OR-02 | Buscar antes de crear, sin duplicar | Cumple | `organizaciones/tests.py:46`; `nucleo/test_escenarios.py:75` | Crear «Universidad Demo» otra vez: avisa del parecido. |
| HU-OR-03 | Varios contactos y personas con cargo y fechas | Cumple | `organizaciones/tests.py:86`, `:101`; `personas/tests.py:138` | Ficha de la organización → Personas relacionadas → «+ Agregar persona con cargo». |
| HU-OR-04 | Carreras de una institución educativa | Cumple | `organizaciones/tests.py:61`, `:72` | Universidad Demo → Carreras → «+ Agregar». En una junta no aparece la pestaña. |
| HU-OR-05 | RUT o personalidad jurídica, opcionales | Cumple | `organizaciones/tests.py:34`; `apps/organizaciones/models.py:14` (RUT), `:16` (otro identificador) | Crear una organización sin RUT: se guarda. |
| HU-OR-06 | La Fundación como organización, con contactos por propósito | Cumple | `organizaciones/tests.py:54` (una sola propia), `:86`; `apps/personas/models.py:178` (propósito) | Crear la organización marcando «es la Fundación» y agregar contactos con propósito «cartas» o «donaciones». |
| HU-OR-07 | Ver las actividades de una organización | Cumple | `nucleo/test_busqueda.py:66`; `templates/organizaciones/pestanas/actividades.html` | Ficha → «Actividades y proyectos». |
| HU-OR-08 | Desactivar sin eliminar | Cumple | `organizaciones/tests.py:106`; `nucleo/test_escenarios_catalogo.py:322` | Ficha → Desactivar. |

## Módulo 6 · Lugares (LU)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-LU-01 | Lugar con dirección, comuna, sector, capacidad y condiciones | Cumple | `territorio/test_contexto.py:80`; `apps/lugares/models.py:13` | Lugares → «+ Nuevo lugar». |
| HU-LU-02 | Reutilizar un lugar y ver su historial de uso | Cumple | `apps/lugares/views.py:151` (pestaña «Uso histórico»); `nucleo/test_escenarios.py:222` | Sede Demo → Uso histórico. |
| HU-LU-03 | Organización dueña del lugar | Cumple | `apps/lugares/models.py:15`; `nucleo/test_escenarios_catalogo.py:502` | Editar lugar → Organización propietaria. |
| HU-LU-04 | Crear un lugar desde la agenda | Cumple | `actividades/tests.py:537` test_crear_lugar_desde_la_agenda | Actividad → Agenda → Programar → «+ Crear lugar». |
| HU-LU-05 | La capacidad cuenta al validar | Cumple | `actividades/tests.py:144`; `nucleo/test_escenarios_catalogo.py:374` | Con más participantes que la capacidad, «Confirmar» lo marca como incompatibilidad. |

## Módulo 7 · Solicitudes y oportunidades (SO)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-SO-01 | Registrar una solicitud casi sin datos | Cumple | `solicitudes/tests.py:12` | Solicitudes → «+ Nueva solicitud» → Guardar sin llenar casi nada. |
| HU-SO-02 | Origen, canal, fecha, motivo y estado | Cumple | `solicitudes/tests.py:18`; `apps/solicitudes/models.py:21-28` | Ver el formulario. |
| HU-SO-03 | Contacto «por identificar» | Cumple | `solicitudes/tests.py:108` | Dejar persona y organización vacías: la ficha dice «Por identificar». |
| HU-SO-04 | Seguir como pendiente, en seguimiento, convertida o descartada con motivo | Cumple | `solicitudes/tests.py:69`; `nucleo/test_escenarios_catalogo.py:636` (reabrir) | Ficha → Cambiar estado → Descartar (pide motivo). |
| HU-SO-05 | Convertir en actividad sin reescribir | Cumple | `solicitudes/tests.py:51`, `:59` | Ficha → «Crear actividad». |
| HU-SO-06 | Puede quedar sin actividad | Cumple | `apps/solicitudes/models.py:31` (`null=True`) | Guardar y no convertir. |

## Módulo 8 · Interacciones y convocatoria (IN)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-IN-01 | Registrar llamado, correo, mensaje o reunión | Cumple | `coordinacion/tests.py:22`, `:38` | En la ficha de una persona: «Registrar interacción». |
| HU-IN-02 | Próxima acción con fecha, visible en pendientes | Cumple | `coordinacion/tests.py:22`; `nucleo/test_fases.py:44` | Poner la próxima acción para mañana: aparece en el Panel. |
| HU-IN-03 | Asociar a persona, organización, solicitud o actividad | Cumple | `coordinacion/tests.py:168` | El botón está en las cuatro fichas. |
| HU-IN-04 | A quién contacté, su interés y disponibilidad | Cumple | `coordinacion/tests.py:104`; `nucleo/test_escenarios_catalogo.py:684` | Participantes → estado «Interesado» o «Disponible». |
| HU-IN-05 | Invitaciones y solicitudes de apoyo con su estado | Cumple | `coordinacion/tests.py:152`, `:125`, `:163` | Actividad → Coordinación → «+ Nueva invitación» y «+ Solicitud de apoyo». |

## Módulo 9 · Actividades (AT)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-AT-01 | Crear con nombre y tipo, completar después | Cumple | `actividades/tests.py:26` | Actividades → «+ Nueva» → nombre y tipo → Guardar. |
| HU-AT-02 | Objetivo, condiciones, estado y zona | Cumple | `actividades/tests.py:26`; la zona es el territorio de la actividad (HU-AT-03) | Editar la actividad. |
| HU-AT-03 | Uno o varios territorios sin lugar | Cumple | `actividades/tests.py:428`; `territorio/test_contexto.py:110` | Desde la Comuna Demo, «+ Actividad»: queda con la comuna como territorio. |
| HU-AT-04 | Presencial, virtual o híbrida | Cumple | `apps/actividades/models.py:33`; `nucleo/test_escenarios_catalogo.py:527` | Editar → Modalidad. |
| HU-AT-05 | Personas con rol, estado y asistencia, sin repetir | Cumple | `actividades/tests.py:291`; `apps/actividades/models.py:154` (restricción única) | Agregar a la misma persona con el mismo rol dos veces: avisa. |
| HU-AT-06 | Organizaciones con cómo intervienen y su contacto | Cumple | `actividades/tests.py:437`; `apps/actividades/models.py:198` | Actividad → Organizaciones → «+ Agregar». |
| HU-AT-07 | Responsable de la Fundación | Cumple | `apps/actividades/models.py:34`; `nucleo/test_escenarios_catalogo.py:329` | Editar → Responsable. |
| HU-AT-08 | Una jornada contiene otras actividades [P] | Cumple | `actividades/tests.py:35`, `:46` | Crear una charla con «actividad padre» = la jornada. |
| HU-AT-09 | Cambiar el estado con motivo | Cumple | `actividades/tests.py:261`, `:282`; `apps/actividades/reglas.py:17` (motivo obligatorio al suspender o cancelar) | Ficha → Cambiar estado → Suspendida: pide motivo. |
| HU-AT-10 | Cargar participantes desde una planilla [P] | Cumple | `actividades/tests.py:557`; `importaciones/tests.py:104`, `:131` | Participantes → «Cargar listado». |
| HU-AT-11 | Proyecto opcional [V] | Cumple | `actividades/tests.py:35`; `proyectos/tests.py:12` | Crear una actividad sin proyecto: se puede. |

## Módulo 10 · Agenda y calendario (AG)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-AG-01 | Fecha, horas, duración, lugar y estado | Cumple | `actividades/tests.py:67`, `:589` | Agenda → Programar. |
| HU-AG-02 | Reprogramar conservando la anterior | Cumple | `actividades/tests.py:73` | Agenda → Reprogramar con motivo: la versión 1 queda como histórica. |
| HU-AG-03 | Una sola programación vigente | Cumple | `actividades/tests.py:90`; `apps/actividades/models.py:359` (restricción en la base) | No hay forma de tener dos vigentes. |
| HU-AG-04 | Motivo, quién y cuándo | Cumple | `actividades/tests.py:82`; `apps/actividades/models.py:347` (motivo), `:350` (creado por) | Ver la versión histórica en la pestaña Agenda. |
| HU-AG-05 | Calendario por mes, semana y lista | Cumple | `actividades/tests.py:452`; `static/js/calendario.js:10` | Menú → Calendario → botones Mes, Semana y Lista. |
| HU-AG-06 | Filtrar por estado, zona, responsable y organización | Cumple | `actividades/tests.py:618` | Calendario → filtros. |
| HU-AG-07 | Serie de actividades repetidas [P] | Cumple | `actividades/tests.py:599`, `:611` | Ficha → «Crear serie» semanal. |

## Módulo 11 · Compatibilidad y búsqueda asistida (VA)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-VA-01 | Revisar capacidad, horario y condiciones antes de confirmar | Cumple | `actividades/tests.py:144`, `:168`, `:218` | Ficha → «Confirmar». |
| HU-VA-02 | Cada problema con su motivo | Cumple | `actividades/tests.py:246`; `apps/actividades/reglas.py:108-154` | La pantalla de confirmar lista ✓, ⚠ y ✕ con el motivo. |
| HU-VA-03 | Choques de horario del lugar y de las personas | Cumple | `actividades/tests.py:168` (lugar), `:192` (persona) | Programar dos actividades en el mismo lugar y hora y confirmar una. |
| HU-VA-04 | Candidatos por tipo de persona, organización, zona, área, disponibilidad, institución, carrera y cantidad | **Parcial** | `apps/actividades/matching.py:28` filtra por texto, área, institución, carrera, comuna y disponibilidad; lugares por cantidad (`:68`); organizaciones por tipo (`apps/actividades/views.py:869`). **No filtra personas por perfil** (estudiante, vecino…). | Participantes → «Buscar candidatos». |
| HU-VA-05 | Razones de cada resultado; decide Claudio | Cumple | `actividades/tests.py:483`, `:503` (no asigna solo) | Cada candidato muestra sus razones y un botón «Agregar». |

## Módulo 12 · Documentos (DO)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-DO-01 | Adjuntar documentos a una actividad | Cumple | `documentos/tests.py:32` | Actividad → Documentos → «Subir nuevo». |
| HU-DO-02 | Tipo, nombre, fecha, descripción y quién lo subió | Cumple | `apps/documentos/models.py:32-55` | Ver la ficha del documento. |
| HU-DO-03 | Mismo documento en varias fichas sin duplicar el archivo [P] | Cumple | `documentos/tests.py:176` | Documentos → «Asociar existente». |
| HU-DO-04 | Documentos restringidos | Cumple | `documentos/tests.py:79`; `nucleo/test_busqueda.py:89` | Marcar «restringido»; sin permiso, su dirección da 403. |
| HU-DO-05 | Avisar tipo o tamaño no permitido | Cumple | `documentos/tests.py:45`, `:51`; `apps/documentos/models.py:14-15` (lista de tipos y 25 MB) | Subir un `.exe` renombrado o un archivo vacío: avisa. |
| HU-DO-06 | Folio, emisor, emisión y vencimiento | Cumple | `apps/documentos/models.py:48-51`; `documentos/tests.py:160` | Documento → Editar. |

## Módulo 13 · Asistencia, resultados y cierre (RE)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-RE-01 | Marcar asistencia | Cumple | `actividades/tests.py:337` | Actividad → Asistencia. |
| HU-RE-02 | Agregar a quien llegó sin estar previsto | Cumple | `actividades/tests.py:563` | Asistencia → «+ Agregar persona que llegó». |
| HU-RE-03 | Observaciones, incidencias, resultado y evidencias | Cumple | `actividades/tests.py:352`, `:365`; las evidencias van en Documentos | Actividad → Resultados. |
| HU-RE-04 | Finalizar con «sin registro» | Cumple | `actividades/tests.py:352`; `apps/actividades/servicios.py:156` | Resultados → marcar «sin registro de asistencia» → Finalizar. |

## Módulo 14 · Historial y trazabilidad (HI)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-HI-01 | Historial de persona, organización, lugar y actividad | Cumple | `personas/tests.py:183`; `organizaciones/tests.py:94`; `proyectos/tests.py:80` | Pestaña Historial de cada ficha. |
| HU-HI-02 | Usuario, fecha, acción y cambios | Cumple | `cuentas/tests.py:38`, `:206`; `documentos/tests.py:66` | Administración → Auditoría. |
| HU-HI-03 | Conservar la versión anterior | Cumple | `personas/tests.py:183`; `apps/personas/models.py:7` (historial automático) | Cambiar un dato y abrir Historial: se ve el antes y el después. |
| HU-HI-04 | Fuente del dato [P] | Cumple | `personas/tests.py:284`; `documentos/tests.py:118`, `:127` | Ficha → pestaña Origen. |
| HU-HI-05 | Pasar de una ficha a otra con un clic | Cumple | `territorio/test_contexto.py:230`; `templates/personas/pestanas/trayectoria.html` | Persona → Participaciones → clic en la actividad. |
| HU-HI-06 | Auditoría completa para el Administrador | Cumple | `cuentas/tests.py:206` (filtra por fecha y acción) | Como Administrador: Administración → Auditoría. |

## Módulo 15 · Búsqueda, consultas y exportación (BU)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-BU-01 | Buscar en todo desde un lugar | Cumple | `nucleo/test_busqueda.py:41`, `:113`, `:181`; `nucleo/test_escenarios_catalogo.py:132` (sin tildes) | Caja de arriba: «vecina» → resultados por tipo. |
| HU-BU-02 | Filtrar actividades por fecha, estado, zona, organización, institución y responsable | Cumple | `actividades/tests.py:51`, `:575`; `nucleo/test_busqueda.py:76` | Actividades → filtros. |
| HU-BU-03 | Búsqueda, orden y paginación en cada módulo | Cumple | `personas/tests.py:206`; `nucleo/test_busqueda.py:105`; `templates/generico/lista.html` | Cualquier listado. |
| HU-BU-04 | Exportar lo que veo, según mis permisos | Cumple | `nucleo/test_busqueda.py:119`, `:137`; `nucleo/test_escenarios_catalogo.py:755` | Listado con filtros → «Exportar». |
| HU-BU-05 | «Qué hicimos con esta organización» y «qué hubo en esta comuna» | Cumple | `nucleo/test_busqueda.py:54`, `:66`; `territorio/test_contenedor.py:76` | Ficha de la organización, o ficha de la comuna. |

## Módulo 16 · Catálogos y configuración (CA)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-CA-01 | El Gestor agrega valores | Cumple | `nucleo/test_catalogos.py:17`, `:71` | Menú → Catálogos → «Tipos de actividad» → «+ Agregar valor». |
| HU-CA-02 | El Administrador desactiva sin borrar | Cumple | `nucleo/test_catalogos.py:28`, `:71` | Como Administrador → Desactivar. Las actividades antiguas lo conservan. |
| HU-CA-03 | No borrar un valor usado | Cumple | `nucleo/test_catalogos.py:55`, `:66` (no hay botón eliminar) | No existe la opción. |

## Módulo 17 · Ingesta de datos (IG)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-IG-01 | Ficha rápida con nombre y un contacto | Cumple | `personas/tests.py:20`, `:235` | «+ Nueva persona» → Ficha rápida. |
| HU-IG-02 | Lista de incompletos, primero los de actividades próximas | Cumple | `nucleo/test_busqueda.py:164` | Panel → «Personas por completar». |
| HU-IG-03 | Cargar un listado con vista previa antes de confirmar | Cumple | `importaciones/tests.py:104`, `:122`, `:131` | Importaciones → Nueva → subir o pegar → revisar los cuatro grupos → Confirmar. |
| HU-IG-04 | Revertir una carga | Cumple | `importaciones/tests.py:202`; `nucleo/test_escenarios_catalogo.py:880` | Importaciones → la carga → Revertir. |
| HU-IG-05 | RUT, teléfonos y nombres se ordenan solos | Cumple | `nucleo/test_utilidades.py:49`, `:66`; `importaciones/tests.py:49`, `:81` | Pegar «Pérez, Ana» y «9 1234 5678». |
| HU-IG-06 | Ver el documento junto al formulario [P] | Cumple | `documentos/tests.py:214`, `:231` | Documento → «Transcribir». |

## Módulo 18 · Panel y navegación (DA)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-DA-01 | Ver lo pendiente al entrar | Cumple | `nucleo/test_busqueda.py:149`; `nucleo/test_vacios.py:16` | Ingresar: el Panel muestra lo pendiente. |
| HU-DA-02 | Menú simple | Cumple | `templates/base.html:31`; `nucleo/test_fases.py:16` | Menú lateral. |
| HU-DA-03 | Volver, migas de pan y aviso de cambios sin guardar | Cumple | `static/js/fche.js:105-109`; `nucleo/test_escenarios_catalogo.py:117` | Escribir en un formulario y pulsar «← Volver»: pregunta. |
| HU-DA-04 | Buscar, elegir o crear sin salir de la actividad | **Parcial** | Crear persona y lugar desde la actividad: `actividades/tests.py:311`, `:537`. La creación abre **una página dentro de la actividad** (`actividades/participante_rapido.html`) y vuelve sola, **no una ventana emergente** como dice docs/CONTEXTO.md §10. | Participantes → «+ Agregar» → «Créala aquí mismo». |
| HU-DA-05 | Cargando, vacío, sin resultados, error, sin permiso | Cumple | `nucleo/test_escenarios_catalogo.py:123`; `nucleo/test_busqueda.py:37`; `templates/base.html` (aviso de error de conexión) | Listado vacío, búsqueda sin resultados, URL sin permiso. |
| HU-DA-06 | Consultar desde el celular [V] | No aplica | Tu documento lo deja **fuera de alcance**. El servidor solo escucha en el propio equipo (`iniciar.bat:33`, `127.0.0.1`). Las pantallas sí se adaptan a pantallas chicas (`templates/base.html:5`). | — |

## Módulo 19 · Proyecto o campaña, opcional (PR)

| HU | Qué pide | Estado | Evidencia | Cómo probarlo |
|---|---|---|---|---|
| HU-PR-01 | Agrupar actividades bajo un proyecto, sin exigirlo [V] | Cumple | `proyectos/tests.py:12`, `:25`; `actividades/tests.py:35` | Proyectos → «+ Nuevo» → pestaña Actividades → «+ Nueva actividad». |
| HU-PR-02 | Ver equipo, organizaciones y actividades del proyecto [V] | Cumple | `proyectos/tests.py:35`, `:61`; `apps/proyectos/views.py:88-99` | Abrir «Proyecto Demo de alfabetización». |

## Reglas transversales (NF)

| Regla | Estado | Evidencia | Nota |
|---|---|---|---|
| NF-01 Crear nunca se bloquea | Cumple | `personas/tests.py:20`; `actividades/tests.py:26`; `solicitudes/tests.py:12` | Solo se exige algo al **confirmar** y al **finalizar**. |
| NF-02 Validación en el servidor | Cumple | `cuentas/tests.py:66`; `documentos/tests.py:45`; `territorio/tests.py:35` | |
| NF-03 Datos generales, restringidos y sensibles | **Parcial** | `personas/tests.py:159`, `:270`; `territorio/test_exportar.py:217`, `:236` | Pendientes: menores [V#2] y los nombres de residentes en el Excel territorial (`specs/f23/spec.md`, pendientes [V]). |
| NF-04 Respaldo diario | **Parcial** | `nucleo/test_comandos.py:34`; `respaldar.bat` | El comando funciona, pero **«a diario» depende de programarlo** en el Programador de tareas de Windows. Eso se hace al instalar. |
| NF-05 Nunca se elimina con historia | Cumple | `personas/tests.py:199`; `nucleo/test_catalogos.py:66`; `cuentas/tests.py:149` | |
| NF-06 Ágil y puede crecer | **Parcial** | Topes de consultas en Territorio: `territorio/test_contenedor.py:349`; `territorio/test_indice.py:142` | No hay prueba de carga ni topes en los otros módulos. |
| NF-07 Funciona sin internet | Cumple | `nucleo/tests.py:85` test_sin_recursos_externos | Bootstrap, HTMX y FullCalendar están en `static/vendor/`. |
| NF-08 No cerrar la puerta a integraciones | No aplica | — | Es una cualidad del diseño; no hay una prueba que la demuestre. |
| NF-09 Aviso de duplicados | Cumple | `personas/tests.py:59`; `organizaciones/tests.py:46` | |

## Diferencias con `Procesos_y_pruebas_de_Claudio.md`

El código **no** sigue en algunos puntos lo que dice ese documento. No se corrigió nada.

| El documento dice | El sistema hace | Dónde |
|---|---|---|
| §6: confirmar sin responsable, fecha o lugar solo avisa | **Impide confirmar** hasta tener esos tres datos. Es lo que dice docs/CONTEXTO.md §10. | `apps/actividades/reglas.py:108-113` |
| §6: superar la capacidad solo avisa | **Impide confirmar** (incompatibilidad crítica), salvo que se active `CONFIRMAR_CON_CONFLICTO_CRITICO` [V#3]. | `apps/actividades/reglas.py:123`; `actividades/tests.py:229` |
| P5: un choque de horario no bloquea | Al **programar** no bloquea. Al **confirmar**, un lugar ocupado es incompatibilidad crítica; una persona ocupada solo avisa. | `apps/actividades/reglas.py:134`, `:152` |
| §5: estados de participación «inscrito, confirmado, asistió, no asistió, canceló» | Hay 10: invitado, interesado, disponible, confirmado, asistió, no asistió, rechazó, canceló, en lista de espera y registro erróneo. | Catálogo «estados de participación» |
| §5: papel de la organización «colaboró, puso el lugar, trajo alumnos, donó, solicitó» | Se llama «tipo de intervención»: solicita, articula, coordina, facilita espacio, aporta personas, aporta recursos. **Donar = «aporta recursos», sin monto.** | Catálogo «tipos de intervención» |
| §5: tipo de lugar «sede vecinal, biblioteca, colegio, espacio abierto, virtual» | Sede, sala, salón comunitario, establecimiento educacional, espacio público, otro. | Catálogo «tipos de lugar» |
| §5: «Grupo» no está modelado | Existe **Comunidad** (grupo de vecinos, curso, comité, agrupación) con integrantes. Se agregó en F22. | `apps/comunidades/` |
| P13: «hacer un respaldo y restaurarlo» desde la pantalla | El respaldo es un comando (`respaldar.bat`). No hay botón en pantalla. | `docs/entrega.md` |
| Estados: «Pendiente → Planificada → Confirmada» | Desde **pendiente** solo se puede pasar a planificada o cancelada. **Cancelada** no se puede reabrir. **Realizada** solo se reabre con un permiso especial que nadie tiene [V#4]. | `apps/actividades/reglas.py:7-15` |

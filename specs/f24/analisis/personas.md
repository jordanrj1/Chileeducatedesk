# personas

## Resumen
Hoy la persona se registra con un único formulario estático: PersonaNuevaForm tiene unos 20 campos en 5 secciones fijas (apps/personas/forms.py:28-37 y 103-117). El catálogo de perfiles (estudiante, vecino…) se marca como casillas, pero no cambia nada del formulario (apps/nucleo/models.py:72; apps/personas/models.py:89). Lo propio de cada tipo de persona ya vive en tablas separadas, pero se llega a ellas después de crear la persona y por pestañas distintas, entre 18 (apps/personas/views.py:203-222):
- estudiante: PersonaFormacion, con la sede como texto libre y la carrera sin cascada;
- vecino: PersonaDireccion, ComunidadMiembro y el bloque «Hogar» dentro de PerfilSensible;
- dirigente y contacto institucional: PersonaOrganizacion y Contacto.cargo;
- voluntario: Experiencia, DisponibilidadPersona y ContactoEmergencia.

Propuesta normalizada:
1) Persona sigue siendo la identidad única. El «tipo de registro» ES el catálogo PerfilPersona, ampliado con un campo `ficha` editable desde Catálogos. Ese campo dice qué sección muestra cada perfil. Los perfiles se mantienen porque Territorio (F23), los filtros y las exportaciones dependen de ellos.
2) Tablas 1 a 0..1 nuevas solo donde hay datos que hoy no tienen tabla:
- FichaVecino: hogar y familia, restringida 🔒 con consentimiento; absorbe el bloque Hogar de PerfilSensible.
- IntegranteHogar: conteos por parentesco y tramo de edad, sin nombres de menores.
- FichaVoluntario.
- FichaProfesional (tallerista).
- FichaInvitado [V].
3) Sin tablas duplicadas para estudiante, dirigente y contacto institucional:
- estudiante: su tabla ES PersonaFormacion (1:N con historia). Se normaliza la sede como FK a Lugar de la institución (tipo «sede» o «casa matriz»).
- dirigente y contacto institucional: su tabla ES PersonaOrganizacion, más ComunidadMiembro o Contacto.cargo.
4) Género y edad: el género sigue en PerfilSensible hasta resolver el [V] de F22. Se unifica su vocabulario con los conteos de las sesiones. La edad sale de fecha_nacimiento, con una marca de «aproximada» cuando solo se conoce la edad.
5) Flujo de pantalla:
- arriba, una fila de botones de selección con los perfiles (varios a la vez);
- debajo, una sección por ficha, armada desde un registro en `apps/personas/fichas.py`;
- con JavaScript, las secciones se muestran y ocultan sin recargar;
- sin JavaScript, un botón «Mostrar secciones» vuelve a dibujar el formulario sin guardar;
- dentro de cada sección hay listas en cascada con HTMX: institución → sede/carrera y comuna → sector → comunidad.
6) La ficha de la persona no suma pestañas: cada tipo aparece como una tarjeta en «Datos» con su botón Editar.
7) Las migraciones son aditivas: se copian datos y las columnas antiguas se retiran después, con permiso.
8) Hay que adaptar la fusión (hoy no fusiona las relaciones 1 a 1), la exportación de datos personales (hoy armada a mano hoja por hoja), la importación (la columna «perfil» que promete la spec F22 no existe) y ParticipanteRapido (crea la persona sin perfil).

Todo amplía la sección 7 de docs/CONTEXTO.md y cambia una decisión de F22. Antes de construir hace falta la autorización expresa del usuario y una spec (F24 o una nueva). Además, el plan F24 con JSONB `datos_extra` choca con el pedido de tablas relacionales normalizadas, y eso hay que decidirlo.

## Hallazgos

### Formulario de persona único y estático
- Evidencia: apps/personas/forms.py:28-37 (SECCIONES_PERSONA fijas), :103-117 (PersonaNuevaForm), :120-129 (PersonaRapidaForm); apps/personas/views.py:118-126 (solo modo rápida/completa); templates/personas/nueva.html:5-11
- Hoy: Rápida (nombre y contacto) o completa: 5 secciones iguales para todos (Identificación, Contacto, Perfil y ocupación, Intereses, Registro). Elegir un perfil no muestra ni oculta nada.
- Problema: Para registrar a un alumno de Duoc UC o a una vecina, crea la persona, entra a la ficha, abre otra pestaña (Formación, Direcciones, Comunidades, Datos sensibles) y llena cada formulario por separado. Ve campos que no le sirven (sitio web o idiomas para una vecina) y no ve los que sí necesita (sede, carrera, número de casa, hijos).
- Propuesta: Formulario compuesto `RegistroPersona` en un archivo nuevo, `apps/personas/fichas.py`:
- formulario base PersonaNuevaForm sin prefijo, para no romper los POST actuales;
- un formulario por ficha con prefijo (`est-`, `vec-`, `vol-`, `pro-`, `inv-`, `dir-`, `ci-`);
- un registro `SECCIONES_TIPO = {codigo_ficha: SeccionTipo(titulo, ayuda, formularios, plantilla, permiso, guardar)}`.
Una sección se valida y se guarda solo si su perfil está marcado o si trae datos; si trae datos, marca el perfil sola. Todo en transaction.atomic, con registrar_origen y auditoría para lo sensible. PersonaNueva, PersonaEditar y documentos.Transcribir usan esta misma clase.

### El catálogo de perfiles no gobierna nada
- Evidencia: apps/nucleo/models.py:72 (PerfilPersona = _catalogo(...), sin atributos); apps/nucleo/migrations/0011_semillas_f22.py:4-7; apps/personas/models.py:89 (M2M sin tabla intermedia ni historial); apps/personas/views.py:83 y :88 (dos filtros de «tipo»: rol y perfil)
- Hoy: Los perfiles son etiquetas para filtrar y para Territorio (apps/territorio/exportar.py:162-173, apps/territorio/views.py:184-192). No se sabe qué datos le corresponden a cada perfil y su cambio no queda en el historial.
- Problema: El tipo de persona no le ahorra trabajo ni ordena el formulario. La lista muestra dos filtros parecidos («Tipo de relación» y «Perfil»).
- Propuesta: Que el tipo de registro alimente los perfiles, no que los reemplace:
- PerfilPersona pasa a ser una clase explícita (como RolParticipacion) con `ficha = CharField(choices=FICHAS, blank=True)` y `campos_extra = ['ficha']`, editable en Catálogos;
- carga inicial: estudiante→estudiante, vecino_o_vecina_de_la_comunidad→vecino, voluntario_o_voluntaria→voluntario, tallerista_o_profesional→profesional, dirigente_social→dirigente, docente_o_academico y funcionario_institucional→contacto_institucional, beneficiario_o_beneficiaria→vecino [P], apoderado_o_apoderada→'' y uno nuevo, invitado_o_invitada→invitado;
- Claudio podrá crear perfiles nuevos y asignarles una sección existente sin programar;
- opcional: `HistoricalRecords(m2m_fields=[perfiles, areas_interes])` (simple_history 3.13 lo admite);
- en la lista, renombrar los filtros a «Perfil (tipo de registro)» y «Rol en actividades».

### Estudiante: la sede es texto libre y la carrera no va en cascada
- Evidencia: apps/personas/models.py:233-266 (PersonaFormacion, sede CharField :242); apps/personas/forms.py:180-182 (la carrera ofrece TODAS las carreras activas de todas las instituciones); apps/organizaciones/urls.py:21-22 (no hay endpoint de opciones de carreras ni sedes); apps/lugares/models.py:11-20 (Lugar con organizacion_propietaria; TipoLugar ya trae «sede»)
- Hoy: PersonaFormacion ya guarda institución, carrera, estado, sede (texto), jornada, nivel, años, asignatura, docente y horas, pero se llena en otra pestaña después de crear la persona. «Duoc UC San Andrés», «Sede San Andrés» y «SAN ANDRES» quedan como tres sedes distintas.
- Problema: No puede filtrar ni contar estudiantes por sede o casa matriz. Elige la carrera entre todas las del banco. Registrar un alumno le toma dos pantallas.
- Propuesta: No crear FichaEstudiante: la tabla del estudiante ES PersonaFormacion. La sección «Estudiante» del registro la envuelve.
- Agregar `PersonaFormacion.sede_institucion = FK(lugares.Lugar, null, PROTECT, related_name='estudiantes')` y validar en clean() que lugar.organizacion_propietaria == organizacion.
- La sede o casa matriz es un Lugar de la institución (TipoLugar «sede» y un valor nuevo «casa matriz» en el catálogo). Así sirve también para hacer actividades allí y da la comuna para Territorio.
- `sede` (texto) queda como respaldo hasta revisar.
- Endpoints HTMX nuevos: `organizaciones/<pk>/sedes/opciones` y `organizaciones/<pk>/carreras/opciones`.
- FormacionForm con hx-get en `organizacion` hacia `carrera` y `sede_institucion`.

### Vecino: sus datos están en 4 tablas y en 4 pantallas, sin hijos ni nietos
- Evidencia: apps/personas/views.py:512-532 (la dirección se agrega en otra página); apps/personas/urls.py:35 (comunidad en otra pestaña); apps/personas/models.py:399-402 (jefatura, integrantes y tramo RSH dentro de PerfilSensible, junto a salud y origen); apps/territorio/test_exportar.py:86-92 (una «vecina» se arma con perfil + PersonaDireccion + ComunidadMiembro + PerfilSensible); la guía interna de protección de datos (hogar y datos de menores = sensibles)
- Hoy: El número de casa está en territorio.Direccion (numero, block, depto) y la comunidad y su rol en ComunidadMiembro. PerfilSensible mezcla tres temas: identidad, salud y hogar socioeconómico. No hay dónde anotar hijos, nietos u otros familiares.
- Problema: Registrar a un vecino le exige recorrer Direcciones, Comunidades y Datos sensibles. Lo que más pide (familia, hijos, nietos) no existe.
- Propuesta: Sección «Vecino/a» del registro, compuesta por:
(a) dirección de residencia en cascada comuna → sector, con calle, número, block y depto (PersonaDireccionForm con prefijo);
(b) comunidad filtrada por la comuna o el sector elegidos, con su rol (ComunidadMiembro);
(c) 🔒 «Hogar y familia», que escribe en la tabla nueva FichaVecino (jefatura_hogar, tramo_rsh e integrantes_hogar, traspasados desde PerfilSensible) y en IntegranteHogar (filas parentesco × tramo × cantidad).
La parte 🔒 exige `ver_sensibles`, consentimiento vigente de «sensibles» y DATOS_SENSIBLES=True, con la casilla de consentimiento en línea, igual que en PerfilSensibleForm (forms.py:244-282). Sin consentimiento, el vecino queda registrado igual, con su dirección, comunidad y perfil.

### Composición familiar y menores (Ley 21.719, [V#2])
- Evidencia: apps/personas/models.py:455-475 (Apoderado: persona↔persona); :136-154 (es_menor y avisos); specs/f22/spec.md:24 y :127 (conservación de datos de menores [V#2]); apps/actividades/models.py:252-258 (las sesiones ya cuentan por tramos 0–17, 18–29, 30–59 y 60+)
- Hoy: No hay dónde registrar a la familia. La única relación entre personas es Apoderado, que es legal y exige que el menor sea una Persona.
- Problema: Si se crea una Persona por cada hijo o nieto solo para contarlo, se guardan nombres y fechas de nacimiento de menores sin necesidad ni autorización del apoderado.
- Propuesta: Por defecto, CONTEOS y no personas: IntegranteHogar(ficha FK FichaVecino, parentesco FK al catálogo nuevo Parentesco, tramo_edad con choices alineados a las sesiones [0_17, 18_29, 30_59, 60_mas], cantidad ≥1, vive_en_hogar Bool para separar el hogar de la familia extendida, como los nietos que no viven con él).
- Sin nombres, RUT ni fechas.
- Vincular persona con persona solo si el familiar ya es Persona por sí mismo (participa en actividades): para menores, la tabla Apoderado que ya existe, con su consentimiento de apoderado; para adultos, un VinculoFamiliar opcional [P], fuera de esta etapa.
- Nunca se crea una Persona para contar a un niño.
- Si hay detalle, integrantes_hogar se recalcula como 1 + la suma de los integrantes con vive_en_hogar.

### Género o sexo: es un dato sensible y su vocabulario no coincide entre tablas
- Evidencia: apps/personas/models.py:385-386 (GENEROS femenino/masculino/no_binario/otro/no_responde en PerfilSensible); apps/actividades/models.py:257-259 (conteo_mujeres/hombres/otros); apps/territorio/test_exportar.py:92 (genero='mujer', que no es una opción válida); specs/f22/spec.md:46 y :126 ([V] general o sensible)
- Hoy: El género solo se registra en la pestaña de datos sensibles, con consentimiento. Las sesiones y los informes usan otra clasificación (mujeres, hombres, otro).
- Problema: Pide «sexo» para el vecino, pero no lo ve en el formulario de registro. Los informes por género no cruzan con lo registrado por persona.
- Propuesta: Mantenerlo en PerfilSensible hasta que el tutor resuelva el [V] de F22. Mientras tanto:
- en el registro (todos los tipos), un campo 🔒 «Género» dentro de Identificación, visible solo con ver_sensibles y DATOS_SENSIBLES, con el consentimiento en línea;
- una función `genero_para_informe()` que traduzca femenino→mujeres, masculino→hombres y el resto→«otro o no informado»;
- corregir el dato de prueba «mujer» por «femenino».
Si el tutor declara general el sexo registral: agregar `Persona.sexo_registral` (femenino, masculino, no informado), separado de la identidad de género, que sigue siendo sensible.

### Edad: los vecinos la declaran, pero el sistema solo acepta fecha
- Evidencia: apps/personas/models.py:75 y :127-137 (edad y es_menor desde fecha_nacimiento); apps/personas/views.py:38-56 (filtro de edad por fecha)
- Hoy: Sin fecha de nacimiento no hay edad, ni tramo, ni aviso de menor.
- Problema: En terreno la vecina dice «tengo 67 años», no su fecha de nacimiento.
- Propuesta: Agregar `Persona.fecha_nacimiento_aproximada = BooleanField(default=False)` [P]. El formulario ofrece «Edad (si no sabes la fecha)». Ese campo no se guarda: el servidor calcula fecha_nacimiento = 01-01-(año actual − edad) y marca aproximada=True. La ficha muestra «≈ 67 años». Si la edad aproximada es 17 o 18, avisa «posible menor». El filtro de edad no cambia.

### Dirigente y contacto institucional: ya tienen tabla, pero el cargo es texto libre
- Evidencia: apps/personas/models.py:269-294 (PersonaOrganizacion: cargo CharField :275, tipo_cargo directorio/funcional/autoridad :272); :184 (Contacto.cargo: contactos que pertenecen al cargo); apps/comunidades/models.py:59 (ComunidadMiembro.ROLES incluye dirigente)
- Hoy: El dirigente es un PersonaOrganizacion (directorio de la junta de vecinos) o un ComunidadMiembro con rol dirigente. El contacto institucional es un PersonaOrganizacion con sus Contacto(cargo=...). Todo se llena por pestañas separadas.
- Problema: No puede filtrar «presidentas de juntas de vecinos de Hualpén» porque el cargo es texto libre. Crear un dirigente le toma tres pantallas.
- Propuesta: No crear FichaDirigente ni FichaContactoInstitucional: duplicarían PersonaOrganizacion. Las secciones del registro las envuelven:
- «Dirigente»: VinculoForm con tipo_cargo='directorio' y la organización con hx-get filtrada a juntas de vecinos o comités, más la comunidad con rol dirigente;
- «Contacto institucional»: VinculoForm más un ContactoForm que guarda Contacto(cargo=vínculo), para que el correo institucional termine cuando termina el cargo.
Opcional [P]: un catálogo `Cargo` (presidente/a, secretario/a, tesorero/a, director/a, socio/a, docente…) que reemplace el texto, con migración que convierta los valores existentes, y agregar 'socio' a TIPOS_CARGO.

### Invitado: no existe como perfil y su invitación ya vive en la actividad
- Evidencia: apps/nucleo/migrations/0011_semillas_f22.py:4-7 (no hay perfil «invitado»); apps/coordinacion/models.py:166-175 (Invitacion por actividad con rol propuesto)
- Hoy: La invitación a una actividad ya se registra en coordinacion.Invitacion. No hay ningún dato propio de la persona invitada.
- Problema: Para cartas y protocolo (autoridades, expositores) no tiene dónde anotar el tratamiento ni el tipo de invitado.
- Propuesta: Tabla FichaInvitado 1:0..1, mínima y [V]: tipo FK al catálogo nuevo TipoInvitado (autoridad, expositor/a, invitado/a especial, prensa, aliado, otro), tratamiento CharField(40) con lista de sugerencias (Sr., Sra., Dr., Alcalde/sa, Concejal/a…), requiere_protocolo Bool e invitado_por FK Persona null. La institución y el cargo siguen en PersonaOrganizacion y la invitación a cada actividad en Invitacion. Si Claudio confirma que «invitado» es solo un rol en la actividad, basta el perfil y no se crea la tabla.

### Voluntario y tallerista: datos repartidos, sin estado ni áreas que imparte
- Evidencia: apps/personas/models.py:91-92 (habilidades e idiomas en Persona), :297-334 (Experiencia, DisponibilidadPersona), :336-356 (ContactoEmergencia); apps/actividades/matching.py:32-38 (el emparejamiento busca por texto en profesión, carrera o experiencia)
- Hoy: Cada dato del voluntario va en su propia pestaña. No hay estado del voluntariado, fecha de ingreso, ni temas o formatos que el tallerista imparte.
- Problema: No puede listar «voluntarios activos que pueden ir a Coronel» ni «talleristas que dan talleres de educación financiera en modalidad virtual».
- Propuesta: FichaVoluntario: estado FK al catálogo EstadoVoluntario (postulante, activo, en pausa, retirado), fecha_ingreso, fecha_induccion, motivacion, comunas_preferidas M2M Comuna, y compromiso FK Documento (carta compromiso). La sección «Voluntario/a» incluye además la disponibilidad (formset de DisponibilidadPersona) y el contacto de emergencia 🔒.
FichaProfesional: areas_que_imparte M2M AreaTematica, formatos M2M TipoActividad, modalidades M2M Modalidad, colaboracion (ad honorem, a través de su institución u otra; sin montos) [V] y necesidades_tecnicas.
El emparejamiento (matching.py) puede luego usar areas_que_imparte y formatos en vez de buscar por texto.

### Importación: la columna «perfil» prometida no existe y la sede no se normaliza
- Evidencia: specs/f22/spec.md:111 («nivel educacional y perfil»); apps/importaciones/lectura.py:11-41 (SINONIMOS sin 'perfil'); apps/importaciones/procesar.py:370-387 (_persona no asigna perfiles), :320-336 (_formacion guarda la sede como texto), :492-493 (revertir: diccionario `modelos` cerrado, KeyError si aparece un tipo_objeto nuevo)
- Hoy: Una planilla de alumnos o de vecinos crea personas sin perfil. La sede queda como texto.
- Problema: Después de cargar 40 alumnos tiene que marcar el perfil uno por uno. Además, el estado de la trazabilidad F22 dice «✅» en un punto que no está hecho.
- Propuesta: - Sinónimo 'perfil' (perfil, tipo, tipo de persona), resuelto contra PerfilPersona por nombre sin tildes, con aviso si no existe.
- Campos nuevos opcionales del lote: `Lote.perfil` (FK PerfilPersona) y `Lote.comunidad` (FK), para que toda la planilla quede «estudiantes» o «vecinos de X».
- `RolParticipacion.perfil` asigna el perfil en un listado de actividad.
- La sede se resuelve contra los Lugar de la institución; si no calza, queda en `sede` (texto) con aviso.
- LoteItem nuevos: 'perfil_persona' (pk de la tabla intermedia), 'membresia' y 'ficha_*', agregados al diccionario `modelos` de revertir().
- Los datos sensibles (género, hogar) no se importan por planilla.

### Crear desde el contexto: la persona nace sin tipo
- Evidencia: apps/actividades/forms.py:164-170 y apps/actividades/views.py:675-678 (ParticipanteRapido crea la Persona sin perfil); apps/comunidades/forms.py:44-54 (IntegranteForm solo elige personas existentes); apps/comunidades/views.py:83-92 (ComunidadOpciones no filtra por comuna ni sector); templates/territorio/pestanas/personas.html:16 («+ Persona» sin comuna precargada)
- Hoy: Agregar un estudiante a una actividad o un vecino a una comunidad crea personas «en blanco».
- Problema: Después tiene que buscar a cada una y marcarle el perfil y los datos de su tipo.
- Propuesta: - Campo nuevo `RolParticipacion.perfil = FK(PerfilPersona, null)` (en campos_extra). ParticipanteRapido agrega ese perfil al crear y, si el perfil lleva a la sección estudiante, ofrece un selector «Institución» limitado a las organizaciones educativas de la actividad, que crea la PersonaFormacion mínima (Participacion.completar_procedencia ya la usa).
- Enlaces con datos precargados: `/personas/nueva?perfil=vecino_o_vecina_de_la_comunidad&comunidad=<pk>` desde la ficha de la comunidad (al guardar crea la membresía y vuelve a la comunidad), `?perfil=estudiante&institucion=<pk>` desde una organización educativa y `?comuna=<pk>` desde Territorio.
- ComunidadOpciones acepta `comuna` y `sector`.

### Fusión de duplicados: no une las relaciones 1 a 1
- Evidencia: apps/nucleo/fusion.py:20-26 (relaciones incluye one_to_one), :45-53 (IntegrityError → el registro queda en el origen), :13-17 (COMPLETAR solo campos de Persona), :76-78 (solo suma las M2M de Persona)
- Hoy: Si las dos fichas tienen PerfilSensible, el del origen se queda en la ficha desactivada. Con las tablas nuevas pasaría lo mismo con FichaVecino, FichaVoluntario, etc.
- Problema: Al unir duplicados, los datos de hogar o del voluntariado de la ficha que se desactiva no pasan a la que se conserva.
- Propuesta: Una función nueva `_fusionar_uno_a_uno(origen, destino)` en fusion.py, que corre antes del ciclo general para cada OneToOne hacia Persona:
- si el destino no tiene la ficha, la mueve;
- si la tiene, completa los campos vacíos y suma las M2M (modalidades, áreas, formatos, comunas);
- mueve los IntegranteHogar solo si no chocan con la restricción única; si chocan, prevalecen los del destino y se informan como conservados.
Con esto se corrige también el caso que ya existe con PerfilSensible. Requiere una prueba nueva.

### Exportación de datos personales armada a mano
- Evidencia: apps/personas/views.py:393-427 (cada hoja escrita a mano; los sensibles dependen de ver_sensibles :415)
- Hoy: Cada tabla nueva obliga a editar la vista. Si se olvida, el derecho de acceso queda incompleto.
- Problema: Si la persona pide sus datos, el Excel no traería su ficha de vecino, de voluntario, etc.
- Propuesta: Cada SeccionTipo del registro aporta `filas_exportacion(persona, usuario)` y PersonaDatosPersonales recorre el registro: «Ficha voluntario», «Ficha profesional», «Ficha invitado», y «Hogar y familia» solo con ver_sensibles. La hoja «Formación» agrega la sede normalizada.

### Ruido visual de la ficha
- Evidencia: apps/personas/views.py:203-222 (18 pestañas); templates/personas/pestanas/datos.html:3-23
- Hoy: Cada tabla hija tiene su propia pestaña.
- Problema: Mucho clic y mucho ruido. Si cada tipo nuevo sumara una pestaña, sería peor.
- Propuesta: Las fichas por tipo NO suman pestañas. En «Datos» aparece una tarjeta plegable (`<details open>`) por cada perfil con sección: Estudiante (institución · sede · carrera · año · jornada), Vecino/a (dirección, comunidad y rol, 🔒 hogar), etc. Cada tarjeta tiene «Editar» hacia la ruta nueva `/personas/<pk>/tipo/<ficha>/editar`. Opcional: reunir Formación, Experiencia, Cargos y Comunidades en una pestaña «Trayectoria».

### El plan F24 (JSONB) choca con el pedido de tablas normalizadas
- Evidencia: docs/rediseno_integral.md:11 (escalabilidad mixta) y :40 (F24: `CampoPersonalizado` + `datos_extra` JSONB con índice GIN); :28 (anti-meta «Excel dentro del sistema»); :33 (migraciones solo aditivas)
- Hoy: F24 propone campos configurables guardados en JSONB, pensados para organizaciones.
- Problema: Hoy pide «datos estructurados en tablas relacionales normalizadas». Un JSONB no se puede relacionar ni validar con llaves foráneas, y deja que se pidan datos sin un «para qué» (RNF-02).
- Propuesta: Los datos clave de cada tipo van en tablas tipadas (esta propuesta). Si de verdad se necesitan campos propios definidos por Claudio, modelarlos de forma relacional y acotada: CampoPersonalizado(perfil FK, nombre, tipo_dato, catalogo_opciones, orden, activo) y ValorCampo(campo FK, persona FK, valor_texto, valor_numero, valor_fecha, valor_opcion FK, con único (campo, persona)), sin campos sensibles. Lo mejor es postergarlos hasta tener un caso real.

## Cambios de modelo
- **nucleo.PerfilPersona**: Pasa de _catalogo() a una clase explícita (patrón de RolParticipacion) con `ficha = CharField(max_length=24, choices=FICHAS, blank=True)` (FICHAS = '', estudiante, vecino, voluntario, profesional, invitado, dirigente, contacto_institucional) y `campos_extra = ['ficha']`. Valor nuevo en el catálogo: «Invitado o invitada». | Migración: nucleo/0012: AddField `ficha`; mismo db_table y mismos permisos (desactivar_perfilpersona). nucleo/0013 RunPython: carga la relación perfil→ficha por código y crea el perfil invitado_o_invitada. Reversa: noop. | Riesgo: Bajo. Si el catálogo se reescribe como clase, el estado de la migración debe quedar solo como AddField (revisar con makemigrations --dry-run).
- **nucleo.RolParticipacion**: `perfil = ForeignKey(PerfilPersona, null=True, blank=True, on_delete=PROTECT, related_name='+')`; `campos_extra = ['grupo', 'perfil']`. | Migración: AddField. RunPython: estudiante, practicante y ayudante→estudiante; voluntario→voluntario_o_voluntaria; tutor→docente_o_academico; tallerista→tallerista_o_profesional; beneficiario→beneficiario_o_beneficiaria; contacto_institucional→funcionario_institucional. | Riesgo: Bajo. vistas_catalogos.py:43 ya dibuja los campos de campos_extra.
- **nucleo.Parentesco, nucleo.TipoInvitado, nucleo.EstadoVoluntario (nuevos)**: Catálogos con _catalogo(). Se agregan a CATALOGOS y a cuentas/roles.py:CATALOGOS_MODELOS. | Migración: CreateModel y carga inicial: Parentesco (hijo/a, nieto/a, pareja, padre/madre, hermano/a, abuelo/a, otro familiar, sin parentesco); TipoInvitado (autoridad, expositor/a, invitado/a especial, prensa, aliado o patrocinador, otro); EstadoVoluntario (postulante, activo, en pausa, retirado). | Riesgo: Bajo. Los permisos del Gestor se cargan solos (roles.py:55-68, post_migrate).
- **lugares (datos) TipoLugar**: Valor nuevo «casa matriz» en el catálogo TipoLugar (el valor «sede» ya existe). | Migración: RunPython get_or_create. | Riesgo: Nulo.
- **personas.Persona**: `fecha_nacimiento_aproximada = BooleanField(default=False)` [P]. Opcional: `history = HistoricalRecords(m2m_fields=[perfiles, areas_interes])`. | Migración: AddField (también en HistoricalPersona). El historial de M2M crea tablas históricas nuevas. | Riesgo: Bajo. Revisar `fusion.COMPLETAR` (fusion.py:14-15) para incluir el campo nuevo.
- **personas.PersonaFormacion**: `sede_institucion = ForeignKey('lugares.Lugar', null=True, blank=True, on_delete=PROTECT, related_name='estudiantes', verbose_name='sede o casa matriz')`. clean() valida que sede_institucion.organizacion_propietaria_id == organizacion_id. `sede` (texto) cambia su etiqueta a «sede (texto por revisar)» y se oculta del formulario si hay sede_institucion. | Migración: AddField. RunPython: busca un Lugar con tipo sede o casa matriz y organizacion_propietaria = organizacion cuyo nombre coincida sin tildes y, si lo encuentra, lo enlaza. No crea Lugar porque Lugar.direccion es obligatoria y el texto no trae comuna. | Riesgo: Medio-bajo. test_f22.py:115-124 sigue pasando si se conserva `sede` como texto. Para que la cascada sea útil hay que cargar las sedes de cada institución.
- **personas.FichaVecino (nueva, 🔒)**: `persona = OneToOneField(Persona, PROTECT, related_name='ficha_vecino')`; `jefatura_hogar = BooleanField(null=True)`; `tramo_rsh = CharField(choices=TRAMOS_RSH, blank=True)`; `integrantes_hogar = PositiveSmallIntegerField(null=True)` (total declarado; se recalcula si hay detalle); `actualizado_en = DateTimeField(auto_now=True)`; `history = HistoricalRecords()`. Se ve y se edita solo con ver_sensibles, consentimiento vigente de «sensibles» y DATOS_SENSIBLES. | Migración: CreateModel. RunPython: por cada PerfilSensible con algún dato de hogar, crea la FichaVecino y copia los valores. Las 3 columnas de PerfilSensible se conservan pero dejan de usarse (formulario, plantilla sensibles.html:16-18 y exportación). Se eliminarán en una migración posterior, con permiso. | Riesgo: Medio: cambia una decisión de F22 (el bloque Hogar en PerfilSensible) y habrá dos copias mientras no se eliminen las columnas. Se mitiga dejando las antiguas como solo lectura.
- **personas.IntegranteHogar (nueva, 🔒)**: `ficha = ForeignKey(FichaVecino, PROTECT, related_name='integrantes')`; `parentesco = ForeignKey('nucleo.Parentesco', PROTECT)`; `tramo_edad = CharField(choices=[('0_17','0 a 17'),('18_29','18 a 29'),('30_59','30 a 59'),('60_mas','60 o más')])`; `cantidad = PositiveSmallIntegerField()` con CheckConstraint cantidad ≥ 1; `vive_en_hogar = BooleanField(default=True)`; UniqueConstraint(ficha, parentesco, tramo_edad, vive_en_hogar); history. Sin nombres, RUT ni fechas. | Migración: CreateModel. No hay datos previos. | Riesgo: Bajo. Al fusionar, los choques con la restricción única se resuelven a favor del destino.
- **personas.FichaVoluntario (nueva)**: `persona = OneToOneField(Persona, PROTECT, related_name='ficha_voluntario')`; `estado = FK(nucleo.EstadoVoluntario, null, PROTECT)`; `fecha_ingreso`, `fecha_induccion = DateField(null)`; `motivacion = TextField(blank)`; `comunas_preferidas = ManyToManyField('territorio.Comuna', blank)`; `compromiso = FK('documentos.Documento', null, PROTECT, related_name='+')`; `actualizado_en`; history. | Migración: CreateModel. No se crean fichas vacías para quienes ya tienen el perfil. | Riesgo: Bajo.
- **personas.FichaProfesional (nueva)**: `persona = OneToOneField(Persona, PROTECT, related_name='ficha_profesional')`; `areas_que_imparte = M2M(AreaTematica)`; `formatos = M2M(TipoActividad)`; `modalidades = M2M(Modalidad)`; `colaboracion = CharField(choices=[ad_honorem, institucional, otra], blank)` [V]; `necesidades_tecnicas = TextField(blank)`; `actualizado_en`; history. | Migración: CreateModel. | Riesgo: Bajo. La fusión debe sumar sus M2M.
- **personas.FichaInvitado (nueva, [V])**: `persona = OneToOneField(Persona, PROTECT, related_name='ficha_invitado')`; `tipo = FK(nucleo.TipoInvitado, null, PROTECT)`; `tratamiento = CharField(40, blank)`; `requiere_protocolo = BooleanField(default=False)`; `invitado_por = FK(Persona, null, PROTECT, related_name='invitados_referidos')`; history. | Migración: CreateModel. | Riesgo: Bajo. Podría no hacer falta si «invitado» resulta ser solo un rol en la actividad.
- **personas.PerfilSensible**: El formulario y la plantilla dejan de usar jefatura_hogar, integrantes_hogar y tramo_rsh (pasan a FichaVecino). Quedan género, pueblo y salud. GENEROS se mantiene y se agrega un mapeo para informes. | Migración: Sin cambio de esquema ahora (migraciones aditivas). La eliminación de las columnas viene después, con autorización. | Riesgo: Medio por las pruebas y plantillas que muestran el bloque Hogar (sensibles.html:16-18, views.py:425-426).
- **importaciones.Lote / LoteItem**: `Lote.perfil = FK(PerfilPersona, null)`, `Lote.comunidad = FK(comunidades.Comunidad, null)` [P]. Valores nuevos de LoteItem.tipo_objeto: 'perfil_persona', 'membresia', 'ficha_vecino', 'ficha_voluntario'. | Migración: AddField ×2. revertir() agrega esos tipos al diccionario `modelos`. | Riesgo: Medio: un tipo_objeto que falte en `modelos` hace fallar la reversión (procesar.py:514).

## Archivos
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/specs/f24/spec.md (o una spec nueva para personas: ampliación de la sección 7 y cambio de decisión F22, primero la spec)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/specs/f24/plan.md
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/specs/f24/tasks.md
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/specs/f22/spec.md (bloque Hogar movido a FichaVecino; perfil en planillas)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/specs/trazabilidad_requerimientos.md (la columna perfil hoy figura como hecha)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/models.py (PerfilPersona.ficha, RolParticipacion.perfil, catálogos Parentesco, TipoInvitado y EstadoVoluntario, CATALOGOS)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/migrations/0012_fichas_por_tipo.py (nueva)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/migrations/0013_semillas_fichas.py (nueva)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/cuentas/roles.py (CATALOGOS_MODELOS)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/personas/models.py (FichaVecino, IntegranteHogar, FichaVoluntario, FichaProfesional, FichaInvitado, PersonaFormacion.sede_institucion, Persona.fecha_nacimiento_aproximada)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/personas/migrations/0004_fichas_por_tipo.py (nueva)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/personas/migrations/0005_datos_fichas.py (nueva: copia el hogar y enlaza sedes)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/personas/fichas.py (nuevo: registro SECCIONES_TIPO y RegistroPersona)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/personas/forms.py (PerfilesWidget con data-ficha, FichaVecinoForm, IntegranteHogarFormSet, FichaVoluntarioForm, FichaProfesionalForm, FichaInvitadoForm, FormacionForm con cascada y sede_institucion, PerfilSensibleForm sin Hogar, campo edad aproximada)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/personas/views.py (PersonaNueva y PersonaEditar con RegistroPersona, PersonaSeccionEditar nueva, ctx de la pestaña Datos con tarjetas, PersonaDatosPersonales por registro, filtros Sede y Sector)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/personas/urls.py (personas/<pk>/tipo/<ficha>/editar)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/organizaciones/views.py (SedesOpciones, CarrerasOpciones)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/organizaciones/urls.py
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/comunidades/views.py (ComunidadOpciones filtra por comuna y sector)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/comunidades/ficha.html (+ Registrar vecino/a)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/fusion.py (_fusionar_uno_a_uno, M2M de las fichas)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/importaciones/lectura.py (sinónimo perfil)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/importaciones/procesar.py (perfil, sede→Lugar, Lote.perfil y comunidad, LoteItem nuevos, revertir)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/importaciones/models.py (Lote.perfil, Lote.comunidad)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/importaciones/forms.py
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/actividades/forms.py (PersonaRapidaForm: institución opcional)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/actividades/views.py (ParticipanteRapido asigna el perfil del rol)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/documentos/views.py (Transcribir usa RegistroPersona)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/personas/nueva.html (botones de tipo, secciones, botón sin JS)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/personas/secciones/_estudiante.html (nueva; y _vecino, _voluntario, _profesional, _invitado, _dirigente, _contacto_institucional)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/personas/secciones/_ver_estudiante.html (nueva; tarjetas de solo lectura por tipo)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/personas/pestanas/datos.html
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/personas/pestanas/sensibles.html
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/documentos/transcribir.html
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/static/js/fche.js (mostrar u ocultar y habilitar o deshabilitar las secciones según data-ficha)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/static/css/fche.css (botones de tipo .fche-chip y secciones plegables)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/management/commands/cargar_demo.py (fichas de demostración ficticias)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/docs/manual_de_uso.md
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/docs/CONTEXTO.md (sección 7.2, después de la aprobación)

## Pruebas afectadas
- apps/nucleo/test_f22.py:26-40 (test_ficha_completa_guarda_identificacion_perfil_e_intereses): POST a /personas/nueva con 'perfiles' sin prefijo. Sigue pasando si el formulario base queda sin prefijo; con el perfil estudiante marcado y sin datos de sección no debe exigir nada.
- apps/nucleo/test_f22.py:42-49 (secciones de la ficha completa: verifica los títulos de los bloques). Cambia si se reordenan las secciones o se agregan las de tipo.
- apps/nucleo/test_f22.py:59-66 (test_datos_sensibles_exigen_consentimiento): sigue vigente. Hay que agregar una variante para el bloque 🔒 Hogar de FichaVecino.
- apps/nucleo/test_f22.py:115-124 (test_formacion_ampliada_del_estudiante): espera f.sede == 'Campus Ficticio'. Pasa si se conserva `sede` como texto; hay que agregar un caso con sede_institucion.
- apps/nucleo/test_f22.py:307-315 (test_fusion_suma_perfiles_y_completa_fecha): agregar la fusión de las fichas 1 a 1.
- apps/nucleo/test_f22.py:318-326 (test_exportar_datos_personales_incluye_lo_nuevo): agregar las hojas nuevas y comprobar que «Hogar y familia» solo sale con ver_sensibles.
- apps/personas/tests.py:116-137 (la carrera pertenece a la institución; formación solo en institución educativa): siguen pasando. Agregar la validación de sede ↔ institución.
- apps/personas/tests.py:236-249 (ficha rápida y completa; guardar y completar después): verifican 'name="rut"' y 'name="origen"'. Se mantienen si el formulario base no cambia de nombres.
- apps/personas/tests.py:252-254 y apps/nucleo/test_escenarios_catalogo.py:186 (aviso de duplicado): sin cambio si los duplicados se revisan antes de guardar las secciones.
- apps/nucleo/test_escenarios_catalogo.py:105-113 (fche.js presente; alta rápida una vez): fche.js crece con el manejo de secciones.
- apps/nucleo/test_escenarios_catalogo.py:172-178 (documento extranjero en la ficha completa): sin cambio.
- apps/nucleo/test_escenarios_catalogo.py:213-251 (fusionar personas: 403/200/400): agregar un caso con FichaVecino en ambas fichas.
- apps/nucleo/test_escenarios_catalogo.py:762 y apps/nucleo/test_vacios.py:68-90 (Excel de datos personales): las hojas nuevas no deben aparecer sin permiso.
- apps/nucleo/test_escenarios_catalogo.py:840-856 (test_IG_E9_carrera_inexistente con revertir): agregar la sede, el perfil y la reversión con los LoteItem nuevos.
- apps/nucleo/test_escenarios.py:24, :71-72, :185-194 y apps/documentos/tests.py:121 (POST mínimos a /personas/nueva): deben seguir funcionando sin 'modo' ni secciones.
- apps/territorio/test_exportar.py:84-92 y apps/territorio/test_contenedor.py:137-141 y :326-330: usan perfiles (se conservan) y PerfilSensible con genero='mujer' (dato inválido que hay que corregir a 'femenino'). Si el bloque Hogar sale de PerfilSensible, revisar que ninguna exportación de Territorio lo muestre.
- apps/actividades/tests.py:528-531 (PersonaFormacion sin sede para completar_procedencia): sin cambio. Agregar una prueba de ParticipanteRapido que asigna el perfil del rol.

## Decisiones abiertas
- Autorización expresa del usuario para ampliar la sección 7 de docs/CONTEXTO.md (§15 «no ampliar el modelo sin preguntarme») y para cambiar una decisión de F22 (el bloque Hogar sale de PerfilSensible y pasa a FichaVecino). ¿Es una feature nueva o se amplía F24?
- F24 en docs/rediseno_integral.md:40 propone `CampoPersonalizado` + `datos_extra` JSONB. ¿Se reemplaza por tablas tipadas (esta propuesta) más campos propios relacionales y acotados, o se posterga? El pedido actual es de «tablas relacionales normalizadas».
- [V F22] Género o sexo: ¿el sexo registral es un dato general (Persona.sexo_registral) o todo sigue como sensible en PerfilSensible.genero? ¿Se adopta el vocabulario de informes mujeres, hombres y otro o no informado?
- [V#2] Composición familiar: ¿bastan conteos por parentesco y tramo, sin nombres? ¿Los tramos son los 4 de las sesiones (0–17, 18–29, 30–59, 60+) o se necesita primera infancia (0–5)? ¿Interesa la familia que no vive en el hogar (nietos no convivientes) o se registra solo el hogar? ¿Por cuánto tiempo se conservan esos datos?
- ¿Estos datos del hogar son sensibles (requieren consentimiento de «sensibles»), como dice la skill fche-ley-datos, o basta el consentimiento general de datos? Validar con el tutor.
- Invitado: ¿es un tipo de persona con ficha propia (tratamiento y protocolo) o solo un rol en una actividad (Invitacion o Participacion)?
- Estudiante: confirmar que no habrá una tabla FichaEstudiante y que PersonaFormacion es la tabla del estudiante. ¿La sede o casa matriz se modela como Lugar de la institución (recomendado) o como una tabla propia SedeInstitucion? ¿Las carreras se ofrecen por sede (M2M Carrera↔Lugar) o por institución?
- ¿El cargo pasa a ser catálogo (presidente/a, secretario/a, tesorero/a, socio/a…) para dirigentes y contactos institucionales, con migración del texto actual?
- ¿El perfil «beneficiario/a» abre la sección Vecino/a (dirección, comunidad y hogar) o ninguna?
- Edad aproximada: ¿se acepta guardar 01-01-(año actual − edad) marcada como aproximada, o se prefiere una columna aparte con el año de nacimiento?
- Retirar las columnas que quedan en desuso (PerfilSensible: jefatura_hogar, integrantes_hogar y tramo_rsh; PersonaFormacion.sede como texto): las migraciones son solo aditivas, así que su eliminación necesita permiso aparte (docs/CONTEXTO.md §0.4).
- ¿Se simplifican las 18 pestañas de la ficha de persona (por ejemplo, Formación, Experiencia, Cargos y Comunidades en una sola «Trayectoria»), o solo se agregan las tarjetas por tipo en «Datos»?

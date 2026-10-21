# Manual de uso — Plataforma FCHE

Para Claudio (Gestor) y quien administre el sistema. Todos los datos de los ejemplos son ficticios.

## 1. Ingresar
1. Abre la dirección del sistema (por defecto `http://127.0.0.1:8000`).
2. Escribe tu **usuario o correo** y tu contraseña → **Ingresar**.
3. Para salir: tu nombre (arriba a la derecha) → **Cerrar sesión**. La sesión se cierra sola tras 60 minutos sin actividad.
4. Cambiar tu contraseña: tu nombre (arriba) → **Cambiar contraseña**. Si la olvidas, el Administrador la restablece.

## 1b. Seguridad
- Tras 5 intentos fallidos el acceso se bloquea 15 minutos; el Administrador puede desbloquearlo antes.
- Si la sesión vence mientras escribes, al volver a ingresar se recupera lo escrito («Se recuperó lo que habías escrito»).
- Si otra pestaña cambió el registro mientras lo editabas, el sistema avisa en vez de pisar los cambios.

## 2. Cómo está organizado
- **Inicio**: qué tienes que hacer hoy (actividades incompletas, solicitudes sin respuesta, personas por completar, tareas por vencer).
- **Buscador** (arriba, siempre visible; atajo: tecla `/`): busca en personas, organizaciones, comunidades, proyectos, actividades, **minutas de sesiones**, lugares, reuniones y documentos. En **/buscar** puedes combinar filtros (tipo, estado, zona, fechas).
- **Menú lateral**, agrupado: *Operación* (Solicitudes, Proyectos, Actividades, Calendario), *Registro* (Personas, Organizaciones, Comunidades, Lugares, Territorio, Documentos), *Gestión* (Importaciones) y *Configuración* (Catálogos, Administración, Ayuda), según tu rol. En el celular se abre con el botón ☰.
- **Nuevo** (botón azul, arriba): crea una solicitud, actividad, persona, organización, comunidad, lugar o documento desde cualquier pantalla.
- Cada registro tiene una **ficha con pestañas**. Arriba están **Editar**, las acciones de la ficha y **Volver**.
- Nada se elimina. Lo que ya no se usa se **desactiva** o se **archiva**, y su historial se conserva.

## 2b. Elegir con clics (desde F24)
- **Campos de búsqueda** (persona, organización, responsable…): al hacer clic se despliegan los registrados; escribe para filtrar. Si no está, usa «+ Crear persona» o «+ Crear organización»: se abre una ventana, avisa si ya existe alguien parecido y lo creado queda elegido.
- **Responsable:** primero aparece el «Equipo de la Fundación». Para que alguien salga ahí, regístralo en Organizaciones → la Fundación (marcada «es la Fundación») → Personas relacionadas.
- **Varias opciones** (temas de interés, perfiles, tramos de edad): pulsa «Elegir…», busca y marca. Lo elegido queda como etiquetas con ×.
- **Ubicación:** región → comuna → sector. Si el sector no existe, escríbelo y pulsa «+ Crear sector» (antes debes elegir la comuna).
- **Listados:** buscador y tres filtros a la vista; el resto en «Más filtros». Los filtros aplicados se ven como etiquetas; la × quita cada uno.
- **Persona por tipo:** al registrar a alguien, marca si es estudiante, vecino o vecina, invitado o invitada, o voluntario o voluntaria; aparecen solo sus datos. Sin marcar nada, se registra con los datos básicos.

## 2c. Personas: relaciones, cargos y experiencia (desde F25)
- **Al registrar** (Nueva persona → «Relaciones»): agrega con «+ Agregar relación» una fila por cada vínculo. Las filas pueden ser de cuatro tipos:
  - organización con rol (estudiante, docente, funcionaria, dirigente, socia, practicante y de dónde viene);
  - comunidad con su rol;
  - proyecto o tarea;
  - actividad.
  
  Nada es obligatorio.
- **Cargos y vínculos** (pestaña de la persona): reúne todo lo que la une a organizaciones, estudios, lugares, comunidades, proyectos y actividades o tareas, marcado «Vigente» o «Terminado», con enlaces.
- **Experiencia**: se arma sola con los cargos y roles que ya terminaron. A mano se agrega solo la «Experiencia fuera de la Fundación».
- **Lugares**: «+ Vincular a un lugar» (estudia, trabaja o participa ahí); el lugar muestra a sus personas.

## 5b. Tareas de un proyecto (desde F25)
- **Dónde están:** en el proyecto, pestaña «Tareas» → «+ Nueva tarea», con nombre, propósito, fecha y horas, lugar o comunidad, grupo objetivo y responsable.
- **Cómo funcionan:** una tarea es como una actividad, con participantes, asistencia y sesiones, pero vive dentro del proyecto.
  - En el calendario aparece como «Tarea · proyecto».
  - En /actividades aparece solo con «Incluir tareas de proyectos».
- **Participantes en terreno:** «+ Agregar participante» busca a la persona; si no está, «Créala aquí mismo» pide los datos básicos (RUT, nacionalidad, sexo, comuna), su rol y de qué grupo viene (organización con cargo, o comunidad). Todo queda vinculado a su ficha, a la organización, a la comunidad y a la comuna.
- **Si sigue otro día:** se agrega una sesión en «Sesiones y minutas», con su propia lista de asistencia.

## 3. Registrar una persona (una sola vez)
1. **Personas → + Nueva persona**. Elige **Ficha rápida** (nombre y un contacto) o **Ficha completa**. Solo el nombre es obligatorio. «Guardar y completar después» la deja en la cola de incompletos.
2. Al guardar, el sistema **busca coincidencias** (mismo RUT, correo, teléfono o nombre parecido). Si aparece un posible duplicado, elige **Usar existente** o **Crear de todos modos**. Nunca se fusiona nada automáticamente.
3. La **ficha completa** se llena por secciones:
   - **Identificación:** nombre social, fecha de nacimiento (calcula la edad y avisa si es menor) y nacionalidad.
   - **Contacto** y canal preferido.
   - **Perfil y ocupación:** estudiante, vecino/a, voluntario/a, tallerista, dirigente, docente…; nivel educacional y situación ocupacional.
   - **Intereses y habilidades:** áreas de interés, habilidades e idiomas. Sirven para encontrar a quién invitar.
4. En la ficha: Datos, Contactos, Direcciones, Formación, Experiencia, Disponibilidad, Organizaciones y cargos, Participaciones (con horas acumuladas), Documentos, Interacciones, Contacto de emergencia, Verificaciones, **Datos sensibles**, **Apoderados**, **Consentimientos**, **Comunidades**, Origen e Historial. Las pestañas marcadas con 🔒 solo las ve quien tiene permiso de datos sensibles.
   - **Formación del estudiante:** institución, carrera, sede, jornada, año que cursa, asignatura o práctica vinculada, docente a cargo y horas comprometidas.
   - **Datos sensibles 🔒** (salud y accesibilidad, alergias, previsión, pueblo originario, género, hogar y tramo del Registro Social de Hogares): se guardan **solo con el consentimiento explícito** de la persona o de su apoderado, registrado ahí mismo (fecha y medio). Si el Administrador pone `DATOS_SENSIBLES=False` en `.env`, la sección desaparece.
   - **Consentimientos:** tratamiento de datos, datos sensibles, uso de imagen, contacto para futuras actividades y autorización del apoderado. No se borran: se **revocan** con fecha. Sin consentimiento la persona no se excluye; la ficha muestra qué falta.
   - **Menores de edad:** la ficha avisa si falta el apoderado o su autorización. El apoderado se registra como otra persona en la pestaña **Apoderados 🔒**.
5. El listado de **Personas** tiene un buscador (nombre, RUT, correo o teléfono) y se filtra por perfil, comuna y comunidad a la vista; el tipo de relación, la organización, el interés, el tramo de edad y el estado del registro están en **Más filtros**. Así se arma el banco de personas para cada actividad.
6. Una persona **no necesita cuenta** para existir ni participar.
7. Personas extranjeras: en la ficha completa se registra el pasaporte u otro documento.
8. Si una persona fallece: estado «Fallecida/o»; no se elimina y ya no aparece como candidata.
9. Fichas duplicadas descubiertas tarde: el Administrador usa «Fusionar con otra ficha»; todo pasa a la que queda (también perfiles e intereses).
10. «Exportar sus datos personales» entrega todo lo que el sistema guarda de esa persona (los datos sensibles, solo a quien tiene permiso).
11. Al desactivar una persona, organización o lugar con actividades futuras, el sistema las muestra antes de confirmar. «Reasignar sus actividades» pasa las de un responsable que se va a otra persona.

## 3b. Comunidades
Una **comunidad** es un grupo de personas que vive en un sector o comparte un espacio: vecinos de una villa, una comunidad escolar, un club de adulto mayor, una comunidad indígena.
1. **Comunidades → + Nueva comunidad** (o desde la pestaña *Comunidades* de una comuna):
   - nombre, tipo, comuna y sector;
   - organización que la representa (p. ej., la junta de vecinos) y referente;
   - población estimada, rango etario, áreas de interés, y diagnóstico y necesidades.
2. Pestaña **Integrantes**: el padrón de la comunidad (integrante, dirigente/a, referente, vocero/a), con fechas. Una persona también se suma a una comunidad desde su ficha.
3. **+ Actividad para esta comunidad** crea una actividad ya dirigida a ella.
4. Pestaña **Alcance**: cuántas personas de la comunidad se alcanzaron, con qué equipo y cuántas horas.

## 4. Organizaciones y lugares
- **Organizaciones → + Nueva organización**: tipo, RUT (opcional), dirección, contactos (varios, con propósito), carreras (si es institución educativa), personas y cargos.
- **Lugares → + Nuevo lugar**: dirección, **capacidad** y condiciones. En su ficha: **Uso histórico** y **Disponibilidad** por fecha. También se crea desde **Programar** («+ Crear lugar»).
- **Direcciones**: se eligen región → provincia → comuna → sector. Si el sector no existe, «+ Crear sector» lo crea ahí mismo; si se escribe distinto («Pobl.», «Vla.») lo reconoce.
- **Territorio**: la comuna y el sector reúnen todo lo que hay en ellos (ver sección 4b).

## 4b. Territorio: dónde trabajamos
La comuna (y cada sector, villa o población) es un **contenedor**: reúne sus comunidades, organizaciones, lugares, personas y actividades, para responder «¿qué hacemos en Hualpén?» sin abrir cinco pantallas.

**Entrar**
1. **Territorio** (menú lateral) abre **Dónde trabajamos**: primero las comunas donde ya hay trabajo registrado, con sus comunidades, organizaciones, personas residentes y actividades de los últimos 12 meses. Van primero las de más actividad reciente.
2. Más abajo, **Todas las regiones**. Una región también muestra primero sus comunas con presencia. El buscador encuentra una comuna por nombre.
3. Si aún no hay nada registrado, la pantalla lo explica y ofrece **+ Comunidad** y **+ Organización**.

**La ficha de una comuna** abre en **Resumen**:
1. Arriba, los **indicadores**: comunidades, organizaciones, residentes, lugares, actividades de los últimos 12 meses y total alcanzado. Cada uno es un botón que lleva a su pestaña. Cuentan solo lo que está activo. Tres no calzan uno a uno con la lista de su pestaña: **Actividades** muestra las de los últimos 12 meses (la pestaña las lista todas; el total va en la nota del indicador), **Residentes** cuenta a quienes tienen residencia vigente aquí (la pestaña Personas suma además a los integrantes de comunidades que viven en otra parte) y **Total alcanzado** suma asistentes registrados y sin registro.
2. **Organizaciones por tipo**: junta de vecinos, institución educativa, municipalidad, empresa, fundación u ONG y otras, con la cantidad y hasta cinco nombres. «ver las n» abre la lista completa de ese tipo.
3. **Por sector**: una tabla con comunidades, organizaciones, lugares, residentes y actividades de cada sector; cada fila lleva a la ficha del sector. «Sin sector» reúne lo que no lo tiene en su dirección y las actividades dirigidas a toda la comuna.
4. **Próximas actividades** (los siguientes 30 días) y **Últimas minutas** (las 5 sesiones más recientes que ya ocurrieron; las planificadas a futuro no cuentan).
5. Las otras pestañas, cada una con su cantidad: **Sectores** (para crearlos y editarlos), **Comunidades**, **Organizaciones**, **Personas**, **Lugares**, **Actividades** y **Alcance**.
   - **Organizaciones** va agrupada por tipo. Al final, un grupo atenuado reúne las **inactivas**: no se cuentan en los indicadores, pero siguen a la vista porque tienen historia. Lo mismo vale para los lugares.
   - **Personas** separa a los **residentes** (dirección de residencia vigente en la comuna) de los **integrantes de comunidades de la comuna que viven en otra parte**. Solo se ven nombre, perfiles y comunidad; el RUT, los contactos y los datos sensibles están en la ficha de cada persona. «Ver personas de la comuna en el listado» abre el listado de Personas filtrado por la comuna: trae a quien tiene una dirección vigente allí, de residencia o de procedencia, así que puede mostrar más gente que los residentes. En la ficha de un sector el filtro sigue siendo la comuna entera. Solo la ve quien puede ver personas.
   - **Alcance** suma a las personas alcanzadas en todas las actividades de la comuna, como el Alcance de una actividad.
6. Arriba, junto a la región y la provincia, aparece la **municipalidad** de la comuna. Si no está registrada, **+ Registrar municipalidad** abre el formulario ya con la comuna y el tipo elegidos. Si la municipalidad fue desactivada, igual se enlaza y se marca «Inactiva».
7. La **ficha de un sector** tiene las mismas pestañas, calculadas sobre el sector y los sectores que contiene. Cambia en cuatro cosas: no muestra la municipalidad (es de la comuna), «Por sector» lista solo los sectores que contiene (sin la fila «Sin sector»), la pestaña de sectores se llama **Sectores dentro** y suma **Nombres alternativos**.

**Crear desde la comuna o el sector**
1. En la cabecera: **+ Comunidad**, **+ Organización**, **+ Lugar** y **+ Actividad**.
2. El formulario llega con la comuna ya elegida (en la dirección, en cascada); si lo abres desde la ficha de un sector, llega también con ese sector. En una actividad nueva, la comuna (o el sector, si la creaste desde su ficha) queda registrada como su territorio, aunque todavía no tenga lugar.
3. Cuando una sección está vacía, también ofrece su botón (por ejemplo, **+ Actividad** si no hay nada en los próximos 30 días).

**Exportar el resumen** (para la Dirección o un fondo)
1. En la cabecera de la comuna o del sector: **Exportar resumen**. Descarga un Excel. Solo lo ve quien tiene el permiso para exportar resúmenes territoriales, y cada descarga queda en la auditoría.
2. Las hojas son siete: *Resumen*, *Sectores*, *Comunidades*, *Organizaciones* (con el correo o teléfono principal), *Personas residentes*, *Actividades* y *Alcance*, más una hoja final *Aviso* con la advertencia de confidencialidad. Una hoja falta si quien exporta no podría ver ese dato en la ficha.
3. Privacidad:
   - **RUT, correo y teléfono** de las personas residentes salen solo con el permiso de exportar personas; sin él, esas columnas no existen.
   - Los **menores de edad** no se listan por nombre: una fila final dice cuántos son. Quien no tiene fecha de nacimiento sí se lista, porque no se sabe su edad.
   - La **pertenencia a una comunidad indígena** no aparece junto a la persona (revela pueblo originario): una fila final dice cuántas se omitieron.
   - Nunca salen datos sensibles, apoderados, contactos de emergencia ni el desglose por género.
   - El archivo trae un aviso de confidencialidad. Revisa qué compartes antes de enviarlo fuera de la Fundación.

**«En esta comuna»**: en la cabecera de la ficha de una persona (su comuna de residencia vigente), organización, lugar y actividad (la comuna del lugar programado o del territorio indicado) aparece la comuna como enlace. Un clic lleva a todo lo demás que hay allí.

## 5. De la solicitud a la actividad
1. **Solicitudes → + Nueva solicitud** (o **+ Nueva oportunidad** si la buscó la Fundación): se puede guardar con lo poco que se sabe; sin contacto queda «Por identificar».
2. Registra cada llamada o correo en **Seguimiento → Registrar interacción** (con próxima acción y fecha).
3. Cuando está clara, usa **Crear proyecto** o **Crear actividad**: la solicitud queda «convertida».
4. En una **actividad** completa: participantes, beneficiarios, organizaciones, sesiones, agenda y coordinación.
   - **Agregar participante**: busca a la persona; si no existe, **Crear persona nueva** desde ahí mismo.
   - **Buscar candidatos**: el sistema sugiere personas, lugares y organizaciones y explica conflictos. Tú decides; nunca asigna solo.

## 6. Programar, reprogramar y confirmar
- **Programar** fija fecha, hora (o duración) y lugar (versión 1). **Crear serie** repite la actividad (por ejemplo, cada semana). **Reprogramar** crea una versión nueva y pide el **motivo**; la anterior queda en la pestaña *Agenda*.
- **Confirmar** revisa la compatibilidad: falta de responsable/fecha/lugar, capacidad del lugar, lugar ocupado, personas con otra actividad al mismo tiempo y disponibilidad declarada. Los faltantes y conflictos graves impiden confirmar; las advertencias se pueden aceptar marcando «Confirmar de todos modos».
- **Estado**: suspender o cancelar exige un motivo. Una actividad cancelada o finalizada (realizada) ya no se modifica.
- **Calendario**: vista mensual/semanal/lista; filtra por estado, zona, responsable y organización, y puede mostrar programaciones anteriores.

## 6b. Más acciones de la actividad
- **Duplicar**: copia una actividad del año pasado, sin participantes ni fechas.
- **Quitar** (en Participantes): si alguien se agregó por error; queda como «registro erróneo» con el motivo.
- **En lista de espera**: estado para quien no alcanza cupo; no ocupa capacidad.
- La capacidad cuenta personas: quien tiene dos roles cuenta una vez.

## 6c. A quién va dirigida y quién la ejecuta
- Al crear o editar la actividad: **línea o área temática**, **público objetivo**, rango etario y beneficiarios estimados.
- Pestaña **Público y comunidades**: agrega las **comunidades destinatarias** (una o varias).
- Pestaña **Participantes**: se separa el **equipo ejecutor** (estudiantes, voluntarios, talleristas, coordinación) de los **asistentes**. Para cada persona se guardan su **institución de procedencia** y su **comunidad**, que se completan solas con su formación y su padrón, y las **horas**.

## 6d. Sesiones y minutas
Cada encuentro de una actividad se registra en la pestaña **Sesiones y minutas** → **Nueva sesión**:
- **Datos:** fecha, horario, lugar y **facilitadores**.
- **Minuta:** objetivo, desarrollo, avances, acuerdos, incidencias y próximos pasos.
- **Asistentes sin registro individual:** solo cifras, por tramo de edad y género. Úsalo cuando asiste gente que no se registra una por una.
- En **Ver minuta** se marca la **asistencia de esa sesión** y se suben las **evidencias** (fotos, listas firmadas, presentaciones).
- Las minutas se encuentran con el buscador.

## 7. Ejecutar y finalizar
1. Después de la actividad, pestaña **Asistencia**: marca quién asistió (o «no hay registro de asistencia»). Si llegó alguien no previsto: **+ Agregar persona que llegó**.
2. Pestaña **Resultados**: resultado, observaciones, incidencias, indicadores. Sube fotos/minutas en **Documentos** o como evidencia de cada sesión.
3. Pestaña **Alcance** (también en el proyecto y la comunidad): total alcanzado, equipo ejecutor y sus horas, asistentes, instituciones de procedencia, comunidades, edades y sesiones.
4. **Finalizar actividad**: exige asistencia (o «sin registro») y resultado. Queda **Realizada**, de solo lectura y consultable en el historial.

## 8. Documentos
- **Documentos → + Nuevo documento** (o desde una actividad, proyecto, persona u organización). Formatos: PDF, Word, Excel, imágenes, etc. (máx. 25 MB).
- Marca **Restringido** para documentos sensibles: solo los ven quienes tienen ese permiso. Los archivos se descargan siempre a través del sistema.
- Un documento no se borra: se **archiva**. Puede tener **fecha de vencimiento**.
- **Asociar existente**: usa un documento ya subido en otra ficha, sin copiar el archivo.
- **Transcribir datos de este documento**: el documento a un lado y el formulario al otro; lo registrado queda con ese documento como origen.
- **Origen del dato**: en la pestaña *Origen* de cada ficha queda de dónde salió la información, quién la registró y si está verificada.

## 8b. Más sobre documentos
- Si subes un archivo que ya existe, el sistema avisa y ofrece usar el existente.
- **Reemplazar archivo** guarda una versión nueva (por ejemplo, un escaneo mejor); la anterior queda archivada.
- Archivar pide un motivo. Si un archivo desaparece del disco, la ficha lo indica.

## 9. Cargar un listado (planilla que manda una institución)
1. **Importaciones → + Nueva importación** → «Listado de participantes de una actividad» → elige actividad y rol → sube el archivo (CSV, TXT o XLSX) o pega las filas.
2. **Revisa**: el sistema muestra *nuevos*, *ya existen*, *posibles duplicados* y *errores*. Corrige los datos en la misma tabla y pulsa «Revisar de nuevo». Para cada duplicado elige: usar la existente, crear nueva u omitir.
3. **Confirmar carga**: solo se habilita cuando no queda nada pendiente. La planilla original se guarda como documento restringido.
4. Si una columna no se reconoce, indícala en «Columnas de la planilla» y pulsa «Aplicar columnas».
5. Si la persona ya existe con datos distintos, elige: conservar, agregar solo el contacto nuevo o actualizar la ficha.
6. Si te equivocas: abre el lote y **Revertir lote** (se conservan las personas que ya tienen otra historia o que alguien editó después).
7. Columnas que se reconocen además del nombre, RUT, correo y teléfono:
   - **fecha de nacimiento** (dd-mm-aaaa o dd/mm/aa), **nacionalidad** y **nivel educacional**;
   - **comuna** y **dirección**: crean la dirección de residencia;
   - **institución**, **carrera**, **sede**, **jornada**, **año que cursa** y **asignatura**: completan la formación.

## 10. Filtrar y exportar
- **Filtros de los listados:** arriba se ven el buscador y los 2 o 3 filtros más usados; el resto está en **Más filtros** (el número al lado dice cuántos de ellos están aplicados). Elige y pulsa **Filtrar**.
- Bajo la barra aparecen cuántos resultados hay y cada filtro aplicado como una etiqueta: la **×** quita solo ese filtro y **Limpiar filtros** los quita todos, pero conserva el orden.
- Por comuna, una actividad aparece si su lugar está en la comuna o si va dirigida a la comuna o a uno de sus sectores (listado, calendario y buscador).
- Los listados con botón **Exportar** generan un Excel con los filtros aplicados. Cada exportación queda en la auditoría.

## 11. Segunda fase
Reuniones con asistentes, tareas, beneficiarios, verificaciones y finanzas están construidas pero ocultas (las **sesiones y minutas** ya están siempre visibles). Para mostrarlas, el Administrador pone `SEGUNDA_FASE=True` en `.env` y reinicia.

## 11b. Finanzas (solo usuarios autorizados, segunda fase)
Presupuesto por proyecto (ítems), gastos, aportes y donaciones. Los movimientos no se borran: se **anulan** con motivo. No registres cuentas bancarias.

## 12. Administración (rol Administrador)
- **Usuarios**: crear cuenta (vinculada a una persona, opcional), asignar rol, desactivar, restablecer contraseña.
- **Roles y permisos**: qué puede hacer cada rol. El sistema no ofrece «eliminar».
- **Catálogos**: el Gestor agrega y edita valores; solo el Administrador desactiva. Desactivar no borra el historial.
- **Auditoría**: ingresos, cambios de rol, exportaciones, confirmaciones, importaciones, respaldos.

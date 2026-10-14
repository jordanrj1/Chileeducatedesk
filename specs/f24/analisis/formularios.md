# formularios

## Resumen
Revisé solo en modo lectura los 13 forms.py, BootstrapMixin/secciones (apps/nucleo/formularios.py), generico/formulario.html, _campos.html, _campo.html y personas/nueva.html. También dibujé los formularios con el cliente de pruebas, dentro de una transacción que se deshizo; verifiqué que no quedó rastro y el repositorio sigue limpio. Mediciones: /organizaciones/nueva muestra 22 campos en una sola columna, sin secciones y con 1 sola ayuda. /comunidades/nueva muestra 13 casillas de «Áreas de interés». /personas/nueva?modo=completa muestra 22 casillas (9 perfiles + 13 áreas). /actividades/<id>/editar tiene 13 campos y 1 sola ayuda. Causas principales: (1) las etiquetas salen del verbose_name del modelo, sin ayuda ni ejemplo; algunas salen sin tilde («Region», «Organizacion», «Titulo», «Categoria») y algunas ayudas traen códigos internos («PE-E4», «F22», «DO-06», «LU-E8»). (2) OrganizacionForm no declara `secciones`. Los datos legales quedan sueltos y se duplica la dirección: «Domicilio legal» es texto y «Dirección» es estructurada. (3) Toda selección múltiple es CheckboxSelectMultiple a la vista, y BootstrapMixin la excluye (formularios.py:14). (4) Hay datos que deberían ser catálogo o tabla y hoy son texto libre: rango_etario en Actividad y Comunidad, zona del Proyecto, naturaleza_juridica, nacionalidad (con un datalist fijo en la plantilla), idiomas, propósito del contacto, parentesco y cargo. (5) Faltan cascadas: comuna→sector en Comunidad, institución→carrera en Formación, y TerritorioForm tiene 4 listas sueltas. (6) La casilla «Vigente» aparece en unos 19 formularios hijos y duplica el botón «Marcar no vigente». Propongo cuatro cosas: un widget SelectorMultiple propio, sin librerías, hecho con casillas nativas y CSS `:has()`, que funciona sin JS y que JS mejora con un filtro; secciones plegables declaradas en `secciones`; etiquetas en forma de pregunta y ayudas con ejemplo, puestas en Meta.labels/help_texts de cada form, para no tocar fichas ni historial; y catálogos nuevos con migraciones aditivas que conservan el texto antiguo. Los cambios de modelo requieren permiso (docs/CONTEXTO.md §0.4 y §15) y spec previa; encajan en la F24 de docs/rediseno_integral.md:40.

## Hallazgos

### (a) Organización: qué significan «Naturaleza jurídica» y «Domicilio legal», y cómo encuadrar los campos
- Evidencia: apps/organizaciones/forms.py:11-19 (sin `secciones`: _campos.html:11 dibuja todo en una columna, sin fche-form__rejilla); apps/organizaciones/models.py:18-31 (ningún help_text); :27 comentario «certificados de directorio/vigencia»; templates/organizaciones/formulario.html:5-7 (bloque «Dirección» estructurada aparte); apps/nucleo/tablero.py:111,137-138 (vigencia_hasta genera en el Inicio el aviso «Vigencia legal de X», 30 días antes); docs/Requerimientos_por_modulo_FCHE.md:127 (HU-OR-05: RUT o personalidad jurídica). Medido: 22 campos, 0 secciones, 1 ayuda.
- Hoy: campo | etiqueta actual | ayuda actual:
- tipo | «Tipo» | —
- rut | «RUT» | «Opcional. Ej.: 12.345.678-5» (ejemplo de persona)
- otro_identificador | «Otro identificador» | —
- estado_registro | «Estado» (forms.py:27) | — (ofrece «Fallecida/o» y «Fusionada en otra ficha»)
- descripcion | «Descripción» | —
- sitio_web | «Sitio web» | —
- comuna_municipal | «Comuna (si es municipalidad)» | — (visible para cualquier tipo)
- naturaleza_juridica | «Naturaleza jurídica» | — (texto libre, 120)
- domicilio_legal | «Domicilio legal» | — (texto libre, 200; además está «Dirección» estructurada debajo)
- vigencia_desde / vigencia_hasta | «Vigencia desde» / «Vigencia hasta» | — (no dice de qué es la vigencia)
- es_propia | «Es la Fundación» | —
- Problema: No sabe qué escribir ni de dónde sacarlo. Ve dos direcciones y no sabe cuál usar. «Vigencia» no dice de qué, aunque alimenta un aviso del Inicio. Todo aparece en una lista larga sin marcos, mezclando lo básico con lo legal y con datos internos de la ficha.
- Propuesta: QUÉ SIGNIFICAN (texto para la ayuda de la sección):
- Naturaleza jurídica: la forma legal con que se constituyó la organización. Figura en su certificado de vigencia (Registro Civil o municipalidad) o en sus estatutos. Ejemplos: una junta de vecinos es «Organización comunitaria territorial»; un club deportivo o una agrupación cultural, «Organización comunitaria funcional»; FCHE, «Fundación»; una empresa, «Sociedad (SpA, Ltda., S.A.)»; la municipalidad, «Organismo público». Debe guardarse como valor de catálogo (ver cambios de modelo), no como texto.
- Domicilio legal: la dirección o comuna que la organización declaró en sus estatutos y que aparece en el certificado. Puede ser distinta de la sede donde se reúne (eso es la «Dirección»). Solo se registra si es distinta.

ETIQUETAS Y AYUDAS NUEVAS (en OrganizacionForm.Meta.labels/help_texts):
- tipo → «Tipo de organización». Ayuda: «Elige la que mejor la describe. Ej.: Junta de vecinos o comité.»
- rut → «RUT de la organización». Ayuda: «Opcional. Aparece en sus certificados, cartas o facturas.»
- otro_identificador → «N.º de personalidad jurídica u otro registro». Ayuda: «Si no tiene RUT o además del RUT. Ej.: N.º de inscripción del Registro Civil, o el RBD si es un liceo.»
- estado_registro → «Estado de la ficha». Ayuda: «Qué tan completa y confiable es esta información (no si la organización funciona). Ej.: Por verificar, si vino de una planilla.»
- descripcion → «¿Qué hace?». Ayuda: «Una o dos frases. Ej.: Junta de vecinos de la Etapa 2; organiza ferias y talleres para personas mayores.»
- sitio_web → «Sitio web o red social». Ayuda: «Ej.: https://www.ejemplo.cl»
- comuna_municipal → «Comuna que administra». Ayuda: «Solo para municipalidades. Ej.: Municipalidad de Hualpén → Hualpén.»
- naturaleza_juridica (pasa a catálogo) → «Tipo de persona jurídica (según su certificado)». Ayuda: «Cómo fue constituida legalmente. Ej.: Organización comunitaria territorial (junta de vecinos).»
- domicilio_legal → «Domicilio que figura en el certificado». Ayuda: «Solo si es distinto de la dirección donde funciona. Ej.: comuna de Hualpén, aunque se reúna en la sede de la villa.»
- vigencia_desde/hasta → «Directorio vigente desde» / «Directorio vigente hasta» [V]. Ayuda: «Fechas del período del directorio que indica el certificado. El Inicio te avisa 30 días antes de que venza. Ej.: 15-04-2025 a 15-04-2028.»
- es_propia → «Esta ficha es la de FCHE». Ayuda: «Márcalo solo en la ficha de la propia Fundación (hay una sola).» Mostrarla solo si todavía no existe la organización propia o si se está editando esa misma ficha.

MARCOS (declarar `secciones`):
1) «Identificación»: nombre, tipo, rut, otro_identificador.
2) «Qué hace»: descripcion, sitio_web.
3) «Municipalidad»: comuna_municipal, visible solo si tipo = municipalidad (data-mostrar-si; la validación de servidor ya existe en models.py:64-66).
4) «Datos legales (según certificado)», plegada. Ayuda: «Complétala con el certificado de vigencia a la vista. Si no lo tienes, déjala vacía: el resto se guarda igual.»
5) «Dirección», plegada, abierta si ya tiene datos.
6) «Ficha», plegada: estado_registro, es_propia.
En el selector de estado excluir «fallecida» y «fusionada».

### (a) Actividad: «Para qué y para quién» necesita contexto; «Rango etario» como texto
- Evidencia: apps/actividades/forms.py:27-32 (ayuda de sección genérica); apps/actividades/models.py:32-44 (solo publico_objetivo tiene help_text, en :42; rango_etario en :43 es CharField(100) sin ayuda); templates/actividades/pestanas/publico.html:3-15 (las comunidades destinatarias y el territorio están en otra pestaña, sin vínculo desde el formulario); apps/actividades/views.py:285-292 (ya arma `destinos` y `territorios_publico`). Medido en /actividades/2/editar: 13 campos y 1 ayuda.
- Hoy: campo | etiqueta actual | ayuda actual:
- tipo | «Tipo» | —
- area_tematica | «Línea o área temática» | —
- proyecto | «Proyecto» | —
- actividad_padre | «Actividad padre (jornada)» | —
- responsable | «Responsable» (generada) | —
- objetivo | «Objetivo» | —
- publico_objetivo | «Público objetivo» | «A quién va dirigida: por ejemplo, vecinos del sector, estudiantes de 3.º medio, personas mayores.»
- rango_etario | «Rango etario» | — (texto libre: no se puede filtrar ni sumar)
- beneficiarios_estimados | «Beneficiarios estimados» | — (se confunde con el de cada comunidad, en ActividadComunidad)
- descripcion | «Descripción» | —
- condiciones | «Condiciones» | —
- Problema: Al editar no ve a qué comunidades ni a qué territorio ya está dirigida la actividad, ni la población objetivo del proyecto, así que escribe a ciegas y repite datos. «Rango etario» admite cualquier texto, no permite marcar varios tramos y no se cruza con los tramos del informe de alcance (alcance.py:8).
- Propuesta: ETIQUETAS Y AYUDAS (ActividadForm.Meta.labels/help_texts):
- objetivo → «¿Qué se quiere lograr?». Ayuda: «El cambio esperado en quienes participan, en una frase. Ej.: Que 20 personas mayores aprendan a hacer videollamadas.»
- publico_objetivo → «¿A quién va dirigida?». Ayuda: «Descríbelo con tus palabras; las comunidades concretas se eligen en «Público y comunidades». Ej.: vecinas y vecinos de la Etapa 2 que no terminaron la enseñanza media.»
- rango_etario → reemplazarlo por `tramos_etarios` (catálogo, varios), etiqueta «Tramos de edad». Ayuda: «Marca uno o más. Ej.: Adultos (30 a 59) y Personas mayores (60 o más).»
- beneficiarios_estimados → «¿Cuántas personas esperas?». Ayuda: «Total aproximado de asistentes, sin contar al equipo. Ej.: 25. Por comunidad se indica en «Público y comunidades».»
- tipo → «Tipo de actividad». Ayuda: «Ej.: Taller (práctico, una o varias sesiones) o Charla (una exposición).»
- area_tematica → «Tema principal». Ayuda: «Sirve para buscar e informar por línea de trabajo. Ej.: Educación financiera.»
- proyecto → «¿Es parte de un proyecto?». Ayuda: «Opcional. Así la actividad aparece en la ficha del proyecto.»
- actividad_padre → «¿Es parte de una jornada?». Ayuda: «Solo si esta charla o taller ocurre dentro de un evento mayor. Ej.: Feria de salud del sábado.»
- responsable → Ayuda: «Quien la coordina. Se exige al confirmarla.»
- descripcion → «Contenido o programa». Ayuda: «Ej.: 3 módulos: presupuesto familiar, ahorro y deudas.»
- condiciones → «Requisitos y necesidades». Ayuda: «Lo que hace falta para realizarla. Ej.: proyector, sala accesible, inscripción previa.»

CONTEXTO EN LA SECCIÓN:
(1) Nueva ayuda de sección: «Tres preguntas para el informe: qué se quiere lograr, a quién va dirigida y cuántas personas se esperan. Abajo ves lo que ya está indicado en la ficha.»
(2) Agregar a la tupla de la sección un 4.º elemento opcional {"plantilla": "actividades/_contexto_publico.html"}. Esa plantilla muestra, en solo lectura: las comunidades destinatarias vigentes (con su territorio, población y tramos), los territorios vigentes y la población objetivo del proyecto, si tiene. Lleva el enlace «Cambiar en Público y comunidades». ActividadEditar.get_context_data reutiliza la consulta de views.py:285-292.
(3) [P] Mostrar como sugerencia (sin marcar nada solo) la unión de los tramos de las comunidades destinatarias.
(4) Sacar proyecto y actividad_padre de «Qué es» a una sección plegada «¿Es parte de algo mayor?».

### (a) Comunidad: etiquetas y ayudas
- Evidencia: apps/comunidades/forms.py:19-33; apps/comunidades/models.py:12-29 (tipo con lista fija en :12-15; rango_etario CharField en :27; areas_interes M2M en :28).
- Hoy: campo | etiqueta actual | ayuda actual:
- tipo | «Tipo» | —
- descripcion | «Descripción» | —
- sector | «Sector» | «Sector, villa o población, si corresponde. Debe ser de la comuna.» (la lista trae los sectores de todas las comunas)
- referente | «Referente o dirigente principal» | —
- poblacion_estimada | «Población estimada (personas)» | —
- rango_etario | «Rango etario predominante» | «Ej.: familias con niños, personas mayores, jóvenes de 15 a 29 años.» (texto libre)
- areas_interes | «Áreas de interés» | — (13 casillas a la vista)
- diagnostico | «Diagnóstico y necesidades» | «Qué necesita esta comunidad, según lo levantado en terreno.»
- Problema: Las 13 casillas abiertas son ruido. El rango etario no se puede comparar con el de la actividad. El sector obliga a buscar entre los sectores de todo el país.
- Propuesta: - tipo → «Tipo de comunidad». Ayuda: «Ej.: Vecinal o barrial, para los vecinos de una villa.»
- descripcion → «¿Quiénes la forman?». Ayuda: «Ej.: familias de la Etapa 3 que se organizan en torno a la sede vecinal.»
- sector → «Sector, villa o población». Ayuda: «Se carga al elegir la comuna. Si no está, créalo con «+ Crear sector».» (cascada, ver hallazgo de cascadas).
- referente → Ayuda: «Persona con quien se coordina. Ej.: la presidenta de la junta de vecinos.»
- poblacion_estimada → «¿Cuántas personas son, aprox.?». Ayuda: «Personas, no familias. Ej.: 120.»
- rango_etario → `tramos_etarios` (catálogo, varios), etiqueta «Edades principales». Ayuda: «Marca uno o más tramos. Ej.: Adultos (30 a 59) y Personas mayores (60 o más).»
- areas_interes → «Temas que le interesan», con SelectorMultiple desplegable. Ayuda: «Sirven para proponerle actividades. Ej.: Salud y bienestar.»
- diagnostico → agregar ejemplo: «Ej.: no hay plaza; muchas personas mayores viven solas; interés en usar el celular para trámites.»
La sección «Caracterización» queda plegada al crear (se completa después del levantamiento en terreno) y abierta al editar si tiene datos.

### (a) Proyecto: etiquetas y ayudas
- Evidencia: apps/proyectos/forms.py:17-30; apps/proyectos/models.py:18-26 (zona en :22 es CharField(200) con «Comuna, sector o territorio donde se desarrolla.»; inicio y término en :24-25).
- Hoy: campo | etiqueta actual | ayuda actual:
- estado | «Estado» | —
- objetivo_general | «Objetivo general» | —
- objetivos_especificos | «Objetivos específicos» | —
- diagnostico | «Diagnóstico» | —
- poblacion_objetivo | «Población objetivo» | —
- zona | «Zona» | «Comuna, sector o territorio donde se desarrolla.» (texto libre)
- fecha_inicio / fecha_termino | «Inicio» / «Término» | —
- Problema: «Zona» como texto no queda enlazada a la comuna: el contenedor Territorio (F23) no puede listar los proyectos de una comuna, y la búsqueda depende de cómo se escribió (busqueda.py:75-81). Las etiquetas cortas no dicen qué se espera.
- Propuesta: - estado → «Etapa del proyecto». Ayuda: «Ej.: Postulado, mientras se espera el resultado del fondo.»
- objetivo_general → Ayuda: «El gran propósito, en una frase. Ej.: Reducir la brecha digital de las personas mayores de la comuna.»
- objetivos_especificos → Ayuda: «Uno por línea. Ej.: Realizar 8 talleres; formar 10 monitores.»
- diagnostico → «¿Qué problema atiende?». Ayuda: «La situación que motivó el proyecto, con datos si los hay.»
- poblacion_objetivo → «¿A quién va dirigido?». Ayuda: «Ej.: personas mayores socias de las juntas de vecinos de la comuna.»
- zona → selector territorial en cascada (tabla ProyectoTerritorio), etiqueta «¿Dónde se desarrolla?». Ayuda: «Agrega una o más comunas o sectores. Ej.: comuna de Hualpén.»
- fecha_inicio / fecha_termino → «Fecha de inicio» / «Fecha de término».
Secciones: «Identificación» abierta; «Propósito» (objetivo_general, poblacion_objetivo, territorio) abierta; «Formulación detallada» (descripcion, objetivos_especificos, diagnostico) plegada.

### (a) Persona (ficha completa y edición): etiquetas y ayudas
- Evidencia: apps/personas/forms.py:25-37 (SECCIONES_PERSONA), :51 (widgets), :107 (label «teléfono» en minúscula); apps/personas/models.py:66-71, :76, :89-93; templates/generico/_campos.html:12 (datalist fijo de nacionalidades); templates/personas/nueva.html:4-11.
- Hoy: campo | etiqueta actual | ayuda actual:
- tipo_documento | «Otro documento (tipo)» | «Para quien no tiene RUT, por ejemplo personas extranjeras (PE-E4).»
- numero_documento | «Otro documento (número)» | —
- nacionalidad | «Nacionalidad» | — (texto con datalist fijo)
- correo | «Correo» (generada) | —
- telefono (PersonaNuevaForm) | «teléfono» | —
- perfiles | «Perfiles» | «Qué es esta persona para la Fundación. Puede tener varios.» (9 casillas)
- areas_interes | «Áreas de interés» | — (13 casillas)
- idiomas | «Idiomas» | — (texto libre)
- origen | «Origen» | —
- estado_registro | «Estado del registro» | — (ofrece «Fusionada en otra ficha», que solo pone el sistema)
- Problema: El código «(PE-E4)» y la palabra «Origen» no le dicen nada. Los 22 chips abiertos alargan la ficha completa. La nacionalidad y los idiomas quedan escritos de formas distintas («ingles», «Inglés básico»), así que no sirven para filtrar.
- Propuesta: - tipo_documento → «Documento (si no tiene RUT)». Ayuda: «Ej.: Pasaporte.» (sin el código interno)
- numero_documento → «N.º del documento». Ayuda: «Ej.: AB123456.»
- nacionalidad → catálogo; etiqueta igual. Ayuda: «Ej.: Venezolana.»
- correo → «Correo electrónico». Ayuda: «Ej.: nombre@ejemplo.cl»
- telefono → «Teléfono». Ayuda: «Ej.: +56 9 1234 5678.»
- perfiles → «¿Qué es para la Fundación?». Ayuda: «Marca uno o más. Ej.: Estudiante y Voluntaria.» (SelectorMultiple)
- areas_interes → «Temas que le interesan». Ayuda: «Sirven para invitarla a actividades. Ej.: Medioambiente.» (SelectorMultiple)
- idiomas → catálogo, varios: «Idiomas que habla». Ayuda: «Ej.: Español y Creole haitiano.»
- origen → «¿Cómo llegó a la Fundación?». Ayuda: «Ej.: Derivación (la envió la municipalidad).»
- estado_registro → «Estado de la ficha». Ayuda: «Ej.: Incompleto, si falta el apellido o un contacto.» Excluir «fusionada» del selector.
- canal_preferido → «¿Cómo prefiere que la contacten?»

### (a) Formularios hijos de persona y organización: Contacto, Cargo/vínculo, Formación, Experiencia, Emergencia y Apoderado
- Evidencia: apps/personas/models.py:177-181 (valor, principal, proposito), :274-276 (organizacion sin verbose_name → «Organizacion»; cargo texto; tipo_cargo), :238 (estado de la formación), :299 (descripcion «experiencia»), :342 y :460 (parentesco texto); apps/personas/forms.py:180-182 (carrera sin filtrar).
- Hoy: campo | etiqueta actual | ayuda actual:
- Contacto.valor | «Valor» | —
- Contacto.proposito | «Propósito» | «Ej.: institucional, cartas, donaciones.» (texto libre)
- Contacto.principal | «Principal» | —
- Vínculo.organizacion | «Organizacion» (sin tilde) | —
- Vínculo.cargo | «Cargo» | — (texto libre)
- Vínculo.tipo_cargo | «Tipo de cargo» | — (Directorio/Funcional/Autoridad sin explicar)
- Vínculo.fecha_inicio / fecha_termino | «Desde» / «Hasta» | —
- Formación.estado | «Estado» | —
- Formación.carrera | «Carrera» | — (todas las carreras de todas las instituciones)
- Experiencia.descripcion | «Experiencia» | —
- Emergencia/Apoderado.parentesco | «Parentesco» | — (texto libre)
- Problema: «Valor» y «Tipo de cargo» no se entienden. El cargo y el parentesco quedan escritos de mil formas («pdta.», «Presidenta») y no permiten saber quién es la presidenta vigente de cada junta.
- Propuesta: - Contacto.valor → «Número, correo o enlace». Ayuda: «Ej.: +56 9 1234 5678 o nombre@ejemplo.cl.»
- Contacto.proposito → catálogo PropositoContacto, etiqueta «¿Para qué se usa?». Ayuda: «Ej.: Cartas y oficios.»
- Contacto.principal → «Usar como contacto principal».
- Vínculo.organizacion → «Organización» (corregir verbose_name).
- Vínculo.cargo → catálogo Cargo (opcional) + texto «Detalle del cargo». Ayuda: «Ej.: Presidenta; Encargado de vinculación con el medio.»
- Vínculo.tipo_cargo → Ayuda: «Directorio: presidencia, secretaría o tesorería. Funcional: quien trabaja o coordina. Autoridad: alcalde, director de liceo.» (si el catálogo Cargo trae el tipo, se deduce solo).
- Vínculo.fecha_termino → «Hasta (si ya dejó el cargo)».
- Formación.estado → «Situación». Ayuda: «Estudiante, egresado o titulado.»
- Formación.carrera → Ayuda: «Se cargan las de la institución elegida.» (cascada)
- Experiencia.descripcion → «¿Qué hizo?». Ayuda: «Ej.: Monitora de taller de lectura.»
- parentesco → catálogo Parentesco. Ayuda: «Ej.: Madre.»

### (a) Formularios de la actividad: Resultados, Sesión, Territorio, Participación, Organización y Programar
- Evidencia: apps/actividades/forms.py:294-298 (ResultadoForm sin ayudas), :219-237 (SesionForm), :275-291 (TerritorioForm), :109-161 (participación), :173-183 (organización), :53-61 (ProgramarForm, «o duración (minutos)»); apps/actividades/models.py:46-50, :106 (region sin verbose_name → «Region»), :238 («n.º»), :241-242 («desde» y «hasta»), :201.
- Hoy: campo | etiqueta actual | ayuda actual:
- resultado | «Resultado» | —
- indicadores | «Indicadores» | —
- incidencias | «Incidencias» | —
- observaciones | «Observaciones» | —
- asistencia_sin_registro | «Asistencia sin registro (explícito)» | —
- Sesión.numero | «N.º» | —
- Sesión.hora_inicio / hora_fin | «Desde» / «Hasta» | —
- Territorio.region | «Region» | «Elige un único nivel: región, provincia, comuna o sector.» (4 listas sueltas)
- Participación.estado | «Estado» | —
- ActividadOrganizacion.tipo_intervencion | «Tipo de intervención» | —
- Programar.duracion | «o duración (minutos)» | «Si indicas la duración, se calcula la hora de término.»
- Problema: No distingue Resultado de Indicadores ni de Observaciones. La frase «(explícito)» es jerga. En Territorio debe adivinar que solo puede elegir una de las 4 listas.
- Propuesta: - resultado → «¿Qué se logró?». Ayuda: «Resumen para el informe. Ej.: Se realizaron las 4 sesiones; 18 de 20 personas terminaron el taller.»
- indicadores → «Cifras logradas». Ayuda: «Números que muestran el resultado. Ej.: 18 constancias entregadas.»
- incidencias → «Imprevistos». Ayuda: «Ej.: corte de luz; se empezó 30 minutos tarde.»
- observaciones → «Otras observaciones». Ayuda: «Lo que convenga recordar para la próxima vez.»
- asistencia_sin_registro → «No se tomó asistencia persona por persona». Ayuda: «Márcalo si no hubo lista; así igual se puede finalizar.» Orden: resultado, indicadores, incidencias, observaciones.
- Sesión.numero → «N.º de sesión»; hora_inicio/hora_fin → «Hora de inicio» / «Hora de término».
- Territorio → una sola cascada «Territorio». Ayuda: «Elige la región y baja hasta donde sepas: se guarda el último nivel elegido. Ej.: Biobío › Concepción › Hualpén.»
- Participación.estado → «Estado de la participación». Ayuda: «Ej.: Invitado → Confirmado → Asistió.»
- tipo_intervencion → «¿Qué aporta esta organización?». Ayuda: «Ej.: Facilita espacio (presta la sede).» (igual en ProyectoOrganizacionForm).
- duracion → «Duración (minutos)». Ayuda: «En vez de la hora de término. Ej.: 90.»

### (a) Otros formularios: Solicitud, Documento, Lugar y segunda fase (etiquetas sin tilde)
- Evidencia: apps/solicitudes/models.py:22-23; apps/documentos/models.py:50-54; apps/lugares/models.py:17-19; apps/coordinacion/models.py:63 y :117 (titulo → «Titulo»), :174 (fecha_respuesta → «Fecha respuesta»); apps/finanzas/models.py:15 (categoria → «Categoria»).
- Hoy: campo | etiqueta actual | ayuda actual:
- Solicitud.origen | «Origen» | —
- Documento.folio | «Folio» | —
- Documento.emisor | «Emisor» | —
- Documento.restringido | «Restringido» | «Solo lo ven quienes tienen permiso para documentos restringidos.»
- Lugar.organizacion_propietaria | «Organización propietaria» | — (select con todas las organizaciones)
- Reunión/Tarea.titulo | «Titulo» | —
- Invitación.fecha_respuesta | «Fecha respuesta» | —
- Ítem.categoria | «Categoria» | —
- Problema: Hay faltas de ortografía en pantalla y palabras de oficina sin ejemplo.
- Propuesta: - Solicitud.origen → «¿Cómo surgió?». Ayuda: «Solicitud externa: alguien pidió algo. Búsqueda activa: la Fundación detectó la oportunidad. Ej.: un liceo pide una charla.»
- Documento.folio → «N.º o folio». Ayuda: «Si el documento lo trae. Ej.: 2026-0345.»
- Documento.emisor → «¿Quién lo emitió?». Ayuda: «Ej.: Registro Civil; Municipalidad de Hualpén.»
- Documento.restringido → «Documento confidencial». Ayuda: «Solo lo ve quien tiene permiso. Ej.: certificado de antecedentes.»
- Lugar.organizacion_propietaria → «¿De quién es el lugar?». Ayuda: «Opcional. Ej.: la junta de vecinos dueña de la sede.» (con SelectorField buscable).
- Agregar verbose_name con tilde: «título», «fecha de la respuesta», «categoría», «región» (ActividadTerritorio) y «organización» (PersonaOrganizacion). Son migraciones solo de estado (AlterField), sin cambio en la base.

### Códigos internos de requisitos en las ayudas
- Evidencia: apps/personas/models.py:67 «(PE-E4)»; apps/documentos/models.py:45 «(F22)» y :54 «(DO-06)»; apps/actividades/models.py:352 «(LU-E8)».
- Hoy: Las ayudas que ve Claudio incluyen IDs de historias de usuario y de features.
- Problema: Son ruido: no significan nada para él y hacen pensar que el sistema está a medio terminar.
- Propuesta: Quitar los códigos de help_text (la trazabilidad ya vive en specs/trazabilidad_requerimientos.md) y dejar el ID en un comentario de código si se quiere conservar. Agregar una prueba que recorra todos los forms y falle si un help_text o label coincide con r"\b[A-Z]{2}-E?\d+\b|\bF\d{2}\b".

### Casilla «Vigente» repetida en los formularios hijos
- Evidencia: apps/nucleo/hijos.py:130-133 (todo hijo con campo `vigente` recibe la ruta «alternar»); templates/generico/_hijos.html:20 (botón «Marcar no vigente/Marcar vigente»); la casilla aparece en IntegranteForm, MembresiaDesdePersonaForm, ActividadComunidadForm, ActividadOrganizacionForm, TerritorioForm, SesionForm, ProyectoComunidadForm, EquipoForm, BeneficiarioForm, ProyectoOrganizacionForm, PostulacionForm, ContactoForm, FormacionForm, ExperienciaForm, DisponibilidadForm, EmergenciaForm, ApoderadoForm, VerificacionForm, AsistenteForm, ResponsableForm e ItemForm.
- Hoy: Al crear un registro hijo aparece una casilla «Vigente», ya marcada y sin explicación. El mismo dato se cambia también con el botón de la lista.
- Problema: No sabe si debe tocarla. Crear algo «no vigente» no tiene sentido, y son dos caminos para lo mismo.
- Propuesta: En BootstrapMixin.__init__: si el form es un ModelForm y la instancia es nueva (`self.instance._state.adding`), quitar `vigente` de `self.fields`; el modelo ya tiene default=True. Al editar, quitarla también donde exista la ruta «alternar», o como mínimo rotularla «Vigente (desmárcala para darla de baja sin borrarla)». Las pruebas que envían "vigente": "on" siguen pasando, porque Django ignora los datos que no corresponden a un campo del formulario.

### «Estado» de la ficha ofrece valores que no corresponden
- Evidencia: apps/organizaciones/forms.py:26-27 y apps/personas/forms.py:59-60 filtran solo activo=True; en el catálogo estado-registro están «Fallecida/o» y «Fusionada en otra ficha» (migraciones 0008 y 0009 de nucleo).
- Hoy: Una organización puede quedar «Fallecida/o». «Fusionada» se puede elegir a mano, aunque debería ponerla solo el proceso de fusión.
- Problema: Son opciones absurdas o peligrosas en la lista.
- Propuesta: OrganizacionForm: excluir codigo__in=["fallecida", "fusionada"]. PersonaForm: excluir "fusionada" (salvo que sea el valor actual de la instancia). [P] Agregar al catálogo EstadoRegistro un campo extra `aplica_a` (persona/organización/ambas) en campos_extra (vistas_catalogos.py:43), para que no quede fijo en el código.

### (b) Inventario de los campos de selección múltiple
- Evidencia: Búsqueda en apps/*.py y templates: no hay forms.SelectMultiple en uso. Hay CheckboxSelectMultiple en: apps/personas/forms.py:51 (perfiles, areas_interes), apps/comunidades/forms.py:33 (areas_interes), apps/actividades/forms.py:222 (facilitadores) y apps/personas/views.py:471 (actividades a reasignar). Casillas escritas a mano en templates/administracion/rol_editar.html:12-18. Conteo en la base: perfil-persona 9 y area-tematica 13 (semillas en nucleo/migrations/0011_semillas_f22.py:4-12); permisos editables 250, en 15 grupos.
- Hoy: 1) PersonaForm, PersonaNuevaForm y Transcribir → perfiles: 9 opciones (PerfilPersona). 2) Las mismas → areas_interes: 13 (AreaTematica). 3) ComunidadForm.areas_interes: 13. 4) SesionForm.facilitadores: variable (equipo ejecutor + responsable de la actividad). 5) PersonaReasignar.actividades: variable, todas marcadas por defecto (es una lista de confirmación). 6) RolEditar.permisos: 250 casillas en 15 fieldsets abiertos (administración). Previstos: tramos_etarios en Actividad y Comunidad (6), idiomas de persona (unos 8). Hoy todos se dibujan como fichas abiertas (_campo.html:13, .fche-opciones en fche.css:640-645).
- Problema: Todas las opciones se ven siempre: /personas/nueva?modo=completa tiene 22 casillas a la vista y /comunidades/nueva, 13.
- Propuesta: Regla en BootstrapMixin: con 6 opciones o menos, se mantienen las fichas en línea actuales (compactas: tramos de edad, roles de comunidad). Con más de 6, o si el número es variable, se usa el «selector múltiple desplegable» (siguiente hallazgo): perfiles, ambas áreas_interes, facilitadores, idiomas. PersonaReasignar queda como lista, porque es una confirmación. En RolEditar, cada grupo de permisos pasa a <details> plegado, con el resumen «n de m marcados» y un filtro de texto.

### (b) Diseño del «selector múltiple desplegable» sin librerías y que funciona sin JavaScript
- Evidencia: apps/nucleo/formularios.py:14-15 (hoy salta los CheckboxSelectMultiple); templates/generico/_campo.html:3,7,13; static/css/fche.css:640-645 y 664 (ya se usa :has()); static/js/fche.js:12-58 (los borradores ignoran inputs sin name, y `marcar` reacciona a cualquier change) y :129 (sinTildes); config/settings/base.py no define FORM_RENDERER, así que una plantilla de widget en templates/ no se encontraría: la solución debe dibujarse desde _campo.html.
- Hoy: Las casillas se dibujan como fichas abiertas. No hay filtro, no hay contador y no se puede plegar.
- Problema: Mucho ruido visual y desplazamiento. Con 13 o más opciones no encuentra rápido la que busca.
- Propuesta: 1) PYTHON (apps/nucleo/formularios.py): `class SelectorMultiple(forms.CheckboxSelectMultiple): pass` y `UMBRAL_DESPLEGABLE = 6`. En BootstrapMixin.__init__, todo CheckboxSelectMultiple o SelectMultiple con len(campo.choices) > UMBRAL se cambia a SelectorMultiple(attrs=w.attrs). El POST no cambia (`areas_interes=3&areas_interes=7`), así que las vistas y pruebas siguen igual. widget_type queda como 'selectormultiple'.
2) PLANTILLA (_campo.html): si widget_type == 'selectormultiple', la etiqueta del campo se dibuja como <span class="form-label" id="{{campo.auto_id}}_etiqueta"> (id_for_label viene vacío en casillas múltiples) y se incluye la nueva generico/_selector_multiple.html:
<div class="fche-multi" data-fche-multi>
  <input type="checkbox" class="fche-multi__abrir visually-hidden" id="{{campo.auto_id}}_abrir" aria-controls="{{campo.auto_id}}_lista">  (sin name: no se envía)
  <label class="form-select fche-multi__boton" for="{{campo.auto_id}}_abrir"><span data-resumen>{{ campo|elegidas_resumen }}</span></label>  («Elegir…» o «3 elegidas»)
  <input type="search" class="form-control form-control-sm fche-multi__filtro" placeholder="Filtrar…" aria-label="Filtrar opciones de {{campo.label}}" hidden>
  <ul class="fche-multi__lista" id="{{campo.auto_id}}_lista" role="group" aria-labelledby="{{campo.auto_id}}_etiqueta">
    {% for opcion in campo %}<li><label for="{{opcion.id_for_label}}">{{ opcion.tag }}<span>{{ opcion.choice_label }}</span><span class="fche-multi__quitar" aria-hidden="true">×</span><span class="visually-hidden">(quitar)</span></label></li>{% endfor %}
  </ul>
</div>
3) CSS (fche.css), con todo funcionando sin JS:
- Cerrado: `.fche-multi__abrir:not(:checked) ~ .fche-multi__lista > li:not(:has(input:checked)){display:none}`. Solo quedan las marcadas, como fichas (border-radius 2rem; fondo --fche-primario-suave), con su casilla visualmente oculta pero enfocable (position:absolute; opacity:0) y una «×». Un clic en la ficha (es un <label for>) desmarca la casilla y la ficha desaparece: «quitar con un clic» sin JS.
- Abierto: `.fche-multi__abrir:checked ~ .fche-multi__lista{display:block; max-height:16rem; overflow:auto; border:1px solid var(--fche-borde-fuerte); border-radius:var(--fche-radio); padding:.35rem}`. Lista vertical con casillas visibles.
- `.fche-multi__abrir:focus-visible + .fche-multi__boton{box-shadow:var(--fche-anillo)}`.
- El filtro se oculta mientras está cerrado.
- Sin soporte de :has() se ven todas las opciones, como hoy (degradación aceptable).
4) JS (fche.js, unas 35 líneas, con eventos delegados para que también funcione en contenido cargado por HTMX):
- Al cargar (y en htmx:afterSwap) quitar `hidden` al filtro y dar al botón role="button" con aria-expanded sincronizado.
- input en el filtro: ocultar los <li> cuyo texto sinTildes no contenga lo escrito.
- change en una opción: actualizar el resumen («3 elegidas: Educación, Salud y 1 más»).
- Escape o clic fuera: cerrar y limpiar el filtro.
- Opcional: botones «Marcar todas» y «Quitar todas».
- Corregir `marcar()` para ignorar inputs sin name, de modo que abrir el desplegable no active «cambios sin guardar».
5) TEMPLATETAG (apps/nucleo/templatetags/fche.py): filtro `elegidas_resumen(campo)` que lee campo.value() y los choices.
6) PRUEBAS: un form con 13 opciones genera class="fche-multi"; uno con 6, class="fche-opciones"; el POST con varias opciones guarda el M2M; no aparece ningún <script src> externo.

### Faltan cascadas y campos que dependan del tipo elegido (formularios dinámicos)
- Evidencia: apps/comunidades/forms.py:37-39 (comuna: todas; sector: los de todas las comunas, con «(comuna)» en la etiqueta); apps/personas/forms.py:180-182 (carrera: todas las carreras activas); apps/actividades/forms.py:275-291 (TerritorioForm con 4 select independientes y la regla «exactamente uno»); apps/organizaciones/models.py:23-25 y :64-66 (comuna_municipal solo vale para municipalidad, pero se muestra siempre); la cascada ya existe en apps/territorio/forms.py:51-89, con los endpoints /territorio/provincias, /comunas y /sectores (territorio/urls.py:18-20).
- Hoy: Solo la dirección es cascada. Comunidad, Territorio de actividad y Formación usan listas planas. Los campos que dependen del tipo se muestran siempre.
- Problema: Con el CUT completo cargado, «Comuna» tendría 346 opciones y «Sector» todos los sectores del país. Además ve campos que no aplican.
- Propuesta: 1) Extraer de DireccionForm.__init__ (territorio/forms.py:64-89) un `CascadaTerritorialMixin` (región y provincia sin guardar → comuna → sector, con los mismos atributos hx-get) y usarlo en ComunidadForm, TerritorioForm y el nuevo ProyectoTerritorioForm. En TerritorioForm.clean(), guardar solo el nivel más profundo elegido; la CheckConstraint actividad_territorio_un_nivel se mantiene.
2) Formación: endpoint nuevo `organizaciones/<pk>/carreras/opciones` (o `/organizaciones/carreras?organizacion=`) y hx-get en «organizacion» con destino #id_carrera. La validación ya existe en PersonaFormacion.clean (personas/models.py:261-262).
3) Atributo genérico `data-mostrar-si="tipo:municipalidad"` sobre .fche-campo, puesto desde el form, y unas 15 líneas en fche.js que alternan `hidden` según el select que lo controla. Sin JS se ve todo, como hoy. Usos: comuna_municipal (tipo=municipalidad), datos legales (tipos con personalidad jurídica, ligado a F24), enlace de Programar (modalidad virtual o híbrida), «Carrera» y «Año que cursa» de Formación (estado=estudiante).
4) DocumentoForm: abierto desde una ficha, mostrar solo la asociación de esa ficha y plegar las otras tres.

### (c) Texto libre que debería ser catálogo o tabla (resumen; el detalle está en cambios_de_modelo)
- Evidencia: apps/actividades/models.py:43 y apps/comunidades/models.py:27 (rango_etario CharField); apps/proyectos/models.py:22 (zona CharField); apps/organizaciones/models.py:28-29; apps/personas/models.py:76, :92, :181, :275, :342, :362, :460. Datos actuales en la base local (lectura): solo Comunidad.rango_etario = «Personas adultas y mayores» (1 fila), Proyecto.zona = «Comuna Demo» (1), Persona.nacionalidad = «Chilena» (1), Persona.idiomas = «ingles» (1); el resto vacío. Restricción «migraciones solo aditivas» en docs/rediseno_integral.md:31.
- Hoy: Son campos de texto sin normalizar. No se pueden filtrar ni cruzar con alcance ni con territorio, y cada uno se escribe distinto.
- Problema: No puede preguntar «actividades para personas mayores en Hualpén», ni contar por tramo, ni listar a las presidentas vigentes.
- Propuesta: Prioridad 1 (lo pidió el usuario): TramoEtario como M2M en Actividad y Comunidad, y ProyectoTerritorio. Prioridad 2: catálogo NaturalezaJuridica (FK en Organización) y domicilio legal [V]. Prioridad 3: Nacionalidad (FK) e Idioma (M2M) en Persona, PropositoContacto, Parentesco y Cargo. Prioridad 4 (2.ª fase): TipoVerificacion. Patrón común de migración: 1) CreateModel del catálogo con semillas (RunPython, como nucleo/0011); 2) AddField con la FK o el M2M nuevo; 3) RunPython que normaliza el texto antiguo (sin tildes y en minúsculas, igual que territorio/reconocer.py:13) y lo asigna; el texto que no calce se conserva en el campo antiguo; 4) el campo antiguo sale del formulario, se renombra en pantalla «(texto anterior)» y la ficha lo muestra solo si tiene contenido, con el aviso «revisar»; 5) quitar la columna antigua es un paso aparte que necesita permiso. Usar Catalogo + campos_extra (vistas_catalogos.py:43), para que el Gestor agregue valores desde Catálogos sin programar.

### Listas fijas en código y plantillas (lo «hardcodeado»)
- Evidencia: templates/generico/_campos.html:12 (datalist de 8 nacionalidades escrito en la plantilla); templates/territorio/_direccion.html:13 (tipos de sector repetidos a mano, distintos de la fuente apps/territorio/models.py:67); apps/actividades/alcance.py:8 (TRAMOS de edad fijos); apps/comunidades/models.py:12-15 (tipos de comunidad) y :59 (roles en la comunidad); apps/personas/models.py:65, :77-88, :234, :243 (documento, nivel educacional, situación ocupacional, estado y jornada de la formación).
- Hoy: Estas listas solo cambian con un programador. Dos de ellas están repetidas en plantillas y pueden desincronizarse.
- Problema: No puede agregar una nacionalidad, un tipo de comunidad ni un tramo sin pedirlo.
- Propuesta: 1) Inmediato y sin cambio de modelo: generar las opciones de _direccion.html:13 con Sector.TIPOS desde el contexto o un templatetag.
2) Con el catálogo Nacionalidad, eliminar el datalist de _campos.html:12.
3) alcance.TRAMOS se lee de TramoEtario (edad_min y edad_max), con el valor actual como respaldo.
4) [P] Pasar a catálogo, en F24: Comunidad.tipo (TipoComunidad) y ComunidadMiembro.rol. Las listas con lógica de negocio (Proyecto.ESTADOS, usado en actividades/forms.py:41; Consentimiento.TIPOS; los estados de Tarea, Invitación y Colaboración) y las listas legales (pueblos originarios, tramos del RSH, previsión) quedan en el código.

### (d) Mecanismo para plegar secciones («Más datos»)
- Evidencia: apps/nucleo/formularios.py:32-47 (secciones = (título, ayuda, campos); el resto cae en «Otros datos», siempre abierto); templates/generico/_campos.html:3-11 (<fieldset><legend>); static/css/fche.css:435-436 (ya hay estilo para details>summary) y :633-637; apps/nucleo/test_f22.py:43-46 (comprueba el <legend> exacto).
- Hoy: Todas las secciones están siempre abiertas, y los formularios sin `secciones` no tienen marcos.
- Problema: Lo opcional pesa tanto como lo obligatorio.
- Propuesta: 1) Admitir un 4.º elemento opcional en cada sección: {"plegada": True, "plantilla": "..."}. secciones_ui() devuelve dicts {titulo, ayuda, campos, plegada, abierta, con_datos, plantilla}, donde `abierta` = tiene errores, o (se está editando y con_datos > 0), y con_datos = campos cuyo value() no está vacío.
2) _campos.html: las secciones normales siguen como <fieldset><legend class="fche-bloque__titulo"> (la prueba test_f22 se mantiene para ellas); las plegadas se dibujan como <fieldset class="fche-bloque"><details {% if s.abierta %}open{% endif %}><summary class="fche-bloque__titulo">{{titulo}} <span class="fche-bloque__resumen">{{ con_datos }} con datos | opcional</span></summary>…</details></fieldset>.
3) «Otros datos» pasa a plegada por defecto.
4) Un error de servidor dentro de una sección plegada la abre siempre; fche.js no necesita cambios, porque los borradores recorren form.elements aunque <details> esté cerrado.

### (d) Qué plegar en cada formulario
- Evidencia: Secciones actuales: personas/forms.py:28-37, actividades/forms.py:27-32 y :224-231, comunidades/forms.py:23-28, proyectos/forms.py:19-23, personas/forms.py:169-172 y :250-256, actividades/forms.py:136-139; sin secciones: Organización, Lugar, Solicitud, Documento, Interacción, Consentimiento, Programar y Resultado.
- Hoy: Ningún formulario tiene partes plegadas.
- Problema: Las fichas completas obligan a recorrer campos que casi nunca se llenan.
- Propuesta: - Organización: abiertas «Identificación» y «Qué hace»; condicional «Municipalidad»; plegadas «Datos legales (según certificado)», «Dirección» y «Ficha».
- Comunidad: abiertas «Identificación» y «Territorio»; «Caracterización» plegada al crear (abierta al editar si tiene datos).
- Actividad: abiertas «Qué es» y «Para qué y para quién» (con el panel de contexto); plegadas «¿Es parte de algo mayor?» (proyecto, actividad_padre) y «Detalle» (descripción, condiciones).
- Proyecto: abiertas «Identificación» y «Propósito»; plegada «Formulación detallada» (descripción, objetivos específicos, diagnóstico).
- Persona, ficha completa y edición: separar «Identificación» en «Nombre y RUT» (abierta: nombres, apellidos, rut, fecha_nacimiento) y «Otros datos de identidad» (plegada: nombre_social, documento, nacionalidad); «Contacto» y «Perfil y ocupación» abiertas; plegadas «Intereses y habilidades» y «Registro» (ajustar test_f22:46).
- Formación: «Estudios» abierta con institución, carrera y estado; plegada «Detalle» (sede, jornada, nivel, años); «Vínculo con la Fundación» abierta si estado = estudiante.
- Sesión: abiertas «Sesión» y «Minuta»; plegadas «Asistentes sin registro individual» (8 cifras) y «Otros».
- Participación (editar): «Procedencia y horas» plegada (se completa sola).
- Datos sensibles: cada bloque plegado, con consentimiento abierto.
- Documento: abiertas «Archivo» y «¿A qué ficha pertenece?» (solo la del contexto); plegadas «Datos del certificado» (folio, emisor, emisión, vencimiento) y «Acceso».
- Interacción: abierta «Contacto»; «Próximo paso» abierta si tiene fecha.
- Consentimiento: plegadas «Respaldo» (otorgado_por, documento) y «Revocación» (solo al editar).
- Programar: «Enlace» solo para modalidad virtual o híbrida; «Duración» como alternativa plegada.
- Resultado: «Otras observaciones» plegada.
- Rol (administración): cada grupo de permisos plegado, con «n de m».

## Cambios de modelo
- **nucleo.TramoEtario (catálogo nuevo)**: Catalogo + edad_min (PositiveSmallInteger) + edad_max (PositiveSmallInteger, null = sin tope); campos_extra = ["edad_min", "edad_max"]; registrar en CATALOGOS como "tramo-etario". Semillas: Primera infancia (0 a 5), Niñez (6 a 13), Adolescencia (14 a 17), Jóvenes (18 a 29), Adultos (30 a 59), Personas mayores (60 o más). Calzan dentro de los 4 tramos de informes (0–17, 18–29, 30–59, 60+) de alcance.py:8 y specs/f22/spec.md:128. | Migración: nucleo/0012: CreateModel + RunPython con las semillas (mismo patrón que 0011_semillas_f22). Aditiva. | Riesgo: Bajo. [V] Los tramos definitivos se validan con Claudio y Manuel (¿jóvenes 15–29 según INJUV o 18–29?). alcance.py debería leer los tramos del catálogo.
- **actividades.Actividad**: + tramos_etarios = ManyToManyField(TramoEtario, blank=True, related_name="+", verbose_name="tramos de edad"). rango_etario (models.py:43) se conserva con verbose_name «rango etario (texto anterior)» y sale de ActividadForm. HistoricalRecords(m2m_fields=[tramos_etarios]) para que el historial muestre los cambios. | Migración: AddField M2M + RunPython que normaliza rango_etario y asigna tramos: por palabras clave (mayor→Personas mayores; adult→Adultos; joven|juvenil→Jóvenes; adolesc→Adolescencia; niñ|infan→Niñez y Primera infancia) y por rangos «N a M» o «N-M» (asigna todos los tramos que se superponen). Lo que no calza queda en rango_etario y la pestaña Público lo muestra con el aviso «revisar». Hoy hay 0 filas con texto. Aditiva; la tabla histórica del M2M es nueva. | Riesgo: Bajo. Hay que actualizar templates/actividades/pestanas/publico.html:5, cargar_demo.py y duplicar.html:11 (si se copian los tramos al duplicar).
- **comunidades.Comunidad**: + tramos_etarios = ManyToManyField(TramoEtario, blank=True, verbose_name="edades principales"). rango_etario (models.py:27) se conserva como «(texto anterior)». m2m_fields en el historial. [P] Comunidad.tipo pasa a catálogo TipoComunidad (FK) en F24. | Migración: AddField + el mismo RunPython. La fila existente «Personas adultas y mayores» queda en Adultos + Personas mayores. Actualizar cargar_demo.py:80. | Riesgo: Bajo. Actualizar templates/comunidades/pestanas/info.html:10 y la exportación de comunidades si incluye la columna.
- **proyectos.ProyectoTerritorio (tabla nueva) y proyectos.Proyecto.zona**: Tabla nueva igual a ActividadTerritorio (actividades/models.py:102-134): proyecto FK PROTECT related_name="territorios"; region, provincia, comuna y sector FK nulos; vigente; CheckConstraint de un solo nivel; HistoricalRecords. Se gestiona como hijo con urls_hijo y CascadaTerritorialMixin. Proyecto.zona se conserva como «zona (texto anterior)» y sale de ProyectoForm. | Migración: CreateModel + RunPython: normalizar(zona) contra Comuna.nombre sin tildes; si no calza, contra Sector y SectorAlias; si hay coincidencia única, crear la fila; si no, el texto queda en zona. Hoy hay 1 fila («Comuna Demo», datos de demostración). Aditiva. | Riesgo: Medio: hay que adaptar apps/nucleo/busqueda.py:75-83 (filtrar por territorios y, mientras exista, por el texto de zona), proyectos/views.py:23-25 (búsqueda y exportación), templates/proyectos/ficha.html:8 y pestanas/resumen.html:5. Así el contenedor de comuna (F23) puede listar sus proyectos. [V] ¿un proyecto puede tener varios territorios? (propuesta: sí).
- **nucleo.NaturalezaJuridica (catálogo nuevo) y organizaciones.Organizacion**: Catálogo con semillas: Organización comunitaria territorial (junta de vecinos); Organización comunitaria funcional (club, centro de madres, agrupación); Corporación o asociación sin fines de lucro; Fundación; Comunidad o asociación indígena; Cooperativa; Sindicato o asociación gremial; Entidad religiosa; Empresa o sociedad (SpA, Ltda., S.A., EIRL); Organismo público (municipalidad, servicio, liceo municipal o SLEP); Universidad, instituto profesional o CFT; Sin personalidad jurídica; Otra. Organizacion + tipo_persona_juridica = FK(NaturalezaJuridica, null, PROTECT, verbose_name="tipo de persona jurídica"). naturaleza_juridica (models.py:28) se conserva como «(texto anterior)». [P] Valor sugerido según TipoOrganizacion. | Migración: CreateModel + semillas + AddField + RunPython (coincidencia sin tildes y sin mayúsculas, o por contenido). El texto que no calce queda como estaba. Hoy hay 0 filas con texto. Aditiva. | Riesgo: Bajo. Afecta apps/documentos/tests.py:240 (busca name="naturaleza_juridica" en Transcribir), apps/nucleo/fusion.py:16 (agregar el campo nuevo) y templates/organizaciones/pestanas/info.html:11-12. [V] La lista de valores se valida con los certificados reales de docs/reales/.
- **organizaciones.Organizacion.domicilio_legal / vigencia_desde / vigencia_hasta**: Opción A (preferida, sin cambio de modelo): solo etiquetas y ayudas nuevas, sección plegada, y domicilio_legal solo si es distinto de la dirección. Opción B: + domicilio_legal_direccion = FK(territorio.Direccion, null, PROTECT) con cascada, y el texto pasa a «(texto anterior)». vigencia_* se reetiquetan «Directorio vigente desde/hasta» (AlterField solo de verbose_name) y el aviso de tablero.py:138 dice «Directorio de X vence el…». | Migración: A: AlterField solo de estado (verbose_name/help_text). B: AddField; el texto antiguo se conserva. | Riesgo: Bajo. Si cambia el texto del aviso, se ajusta apps/nucleo/test_vacios.py:31. [V] ¿La vigencia es del directorio o de la personalidad jurídica? ¿Hace falta el domicilio legal aparte de la dirección?
- **nucleo.Nacionalidad (catálogo nuevo) y personas.Persona.nacionalidad**: Catálogo con semillas: Chilena, Venezolana, Peruana, Colombiana, Haitiana, Boliviana, Argentina, Ecuatoriana y Otra (las mismas del datalist _campos.html:12, que se elimina). Persona + nacionalidad_ref = FK(Nacionalidad, null, PROTECT, verbose_name="nacionalidad"); el CharField se conserva como «(texto anterior)». | Migración: CreateModel + semillas + AddField + RunPython (sin tildes y sin mayúsculas; un texto que no calce se agrega como valor nuevo del catálogo, para no perder datos). Hoy hay 1 fila («Chilena»). Aditiva. | Riesgo: Medio: apps/importaciones/procesar.py:380 y lectura.py:35 deben convertir el texto de la planilla en FK; también personas/views.py:395 (exportación) y las pruebas test_f22.py:31-37 y :276.
- **nucleo.Idioma (catálogo nuevo) y personas.Persona.idiomas**: Semillas: Español, Inglés, Creole haitiano, Portugués, Francés, Mapudungun, Lengua de señas chilena y Otro. Persona + idiomas_ref = M2M(Idioma, blank); el CharField (models.py:92) se conserva como «(texto anterior)». Usa el SelectorMultiple. | Migración: AddField + RunPython que separa por «,», «/» e « y » y busca coincidencias; lo que no calce queda en el texto. Hoy hay 1 fila («ingles» → Inglés). Aditiva. | Riesgo: Bajo. test_f22.py:33 envía idiomas como texto y habría que adaptarlo; personas/views.py:398 (exportación).
- **nucleo.PropositoContacto (catálogo nuevo) y personas.Contacto.proposito**: Semillas [D, docs/CONTEXTO.md §7.3]: Institucional, Cartas y oficios, Donaciones, Personal y Laboral. Contacto + proposito_ref = FK(null); el CharField (models.py:181) se conserva como «(texto anterior)». | Migración: AddField + RunPython de normalización. Hoy hay 0 filas. Aditiva. | Riesgo: Bajo. apps/organizaciones/tests.py:88-93 envía proposito como texto («cartas», «donaciones»).
- **nucleo.Parentesco (catálogo nuevo); personas.ContactoEmergencia y personas.Apoderado**: Semillas: Madre, Padre, Abuela/o, Tía/o, Hermana/o, Pareja o cónyuge, Hija/o, Tutor/a legal, Vecina/o o amiga/o y Otro. + parentesco_ref = FK(null) en ambos modelos; los textos (models.py:342 y :460) se conservan. | Migración: AddField ×2 + RunPython. Hoy hay 0 filas. Aditiva; Apoderado tiene historial. | Riesgo: Bajo. apps/personas/tests.py:176 envía parentesco «madre» como texto. Son datos restringidos o sensibles: no cambia el permiso ver_sensibles.
- **nucleo.Cargo (catálogo nuevo) y personas.PersonaOrganizacion**: [P] Catálogo con campo extra tipo_cargo (directorio, funcional o autoridad). Semillas: Presidente/a, Vicepresidente/a, Secretario/a, Tesorero/a, Director/a (directorio); Coordinador/a, Encargado/a de vinculación con el medio, Docente, Profesional (funcional); Alcalde/sa, Concejal/a, Director/a de establecimiento (autoridad). PersonaOrganizacion + cargo_ref = FK(null); el CharField cargo se conserva como «detalle del cargo»; tipo_cargo se deduce del catálogo si viene vacío. | Migración: AddField + RunPython (coincidencia normalizada). Hoy hay 0 filas. Aditiva. | Riesgo: Bajo. Ayuda a CerrarCargosAutoridad y al contenedor Organización (F25).
- **nucleo.TipoVerificacion (catálogo nuevo; 2.ª fase) y personas.VerificacionPersona.tipo**: [V#10] Catálogo con vigencia sugerida en días (campo extra). Ejemplos: Certificado de antecedentes; Inhabilidades para trabajar con menores. + tipo_ref = FK(null); el texto se conserva. | Migración: AddField + RunPython. Hoy hay 0 filas. Aditiva. | Riesgo: Bajo; el módulo está oculto con SEGUNDA_FASE=False.
- **Etiquetas sin tilde (solo verbose_name)**: verbose_name «región» en ActividadTerritorio.region (actividades/models.py:106), «organización» en PersonaOrganizacion.organizacion (personas/models.py:274), «título» en Reunion y Tarea (coordinacion/models.py:63 y :117), «fecha de la respuesta» (:174), «categoría» (finanzas/models.py:15). Además, quitar de los help_text los códigos PE-E4, F22, DO-06 y LU-E8. | Migración: AlterField solo de estado, una migración por app. No toca datos. | Riesgo: Nulo en datos. Cambia el texto del historial (vistas_base.py usa verbose_name). Las etiquetas en forma de pregunta van en Meta.labels de cada form, no en el modelo, para que las fichas y el historial sigan con sustantivos cortos.

## Archivos
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/specs/f24/spec.md (o una spec nueva «claridad de formularios»; primero la spec, docs/CONTEXTO.md §0.3)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/specs/f24/plan.md
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/specs/f24/tasks.md
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/formularios.py (SelectorMultiple, UMBRAL_DESPLEGABLE, secciones plegables, quitar «vigente» al crear, data-mostrar-si)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/generico/_campos.html (secciones plegables con <details>, plantilla de contexto, quitar el datalist de la línea 12)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/generico/_campo.html (rama selectormultiple, data-mostrar-si)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/generico/_selector_multiple.html (nuevo)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/static/css/fche.css (.fche-multi, .fche-bloque--plegable, .fche-bloque__resumen)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/static/js/fche.js (filtro y resumen del selector, aria-expanded, Escape, mostrar-si; que marcar() ignore inputs sin name)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/templatetags/fche.py (filtro elegidas_resumen)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/models.py (TramoEtario, NaturalezaJuridica, Nacionalidad, Idioma, PropositoContacto, Parentesco, Cargo y su registro en CATALOGOS)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/migrations/0012_catalogos_formularios.py (nuevo, con semillas)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/organizaciones/forms.py (secciones, Meta.labels/help_texts, filtro de estado, es_propia condicional)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/organizaciones/models.py (tipo_persona_juridica, verbose_name de vigencia)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/organizaciones/formulario.html (dirección plegada)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/organizaciones/pestanas/info.html
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/tablero.py (texto del aviso de vigencia, línea 138)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/fusion.py (línea 16: campos nuevos)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/comunidades/forms.py (cascada, tramos, etiquetas, sección plegada)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/comunidades/models.py (tramos_etarios, m2m en historial)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/comunidades/pestanas/info.html
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/actividades/forms.py (ActividadForm, ResultadoForm, SesionForm, TerritorioForm en cascada, etiquetas)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/actividades/models.py (tramos_etarios, verbose_name de región)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/actividades/views.py (contexto de público en ActividadEditar)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/actividades/_contexto_publico.html (nuevo)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/actividades/pestanas/publico.html
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/actividades/alcance.py (TRAMOS desde el catálogo)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/proyectos/models.py (ProyectoTerritorio)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/proyectos/forms.py (secciones, ProyectoTerritorioForm)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/proyectos/views.py (búsqueda y exportación por territorio)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/proyectos/urls.py (hijo territorios)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/proyectos/ficha.html
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/proyectos/pestanas/resumen.html
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/busqueda.py (líneas 75-83: zona → territorios)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/personas/forms.py (etiquetas, secciones, FormacionForm en cascada, filtro de estado)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/personas/models.py (FK y M2M a catálogos, quitar PE-E4, verbose_name de organización)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/personas/views.py (exportación, líneas 395-398)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/organizaciones/views.py y urls.py (endpoint de carreras por institución)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/territorio/forms.py (extraer CascadaTerritorialMixin)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/territorio/_direccion.html (línea 13: tipos de sector desde Sector.TIPOS)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/documentos/models.py (quitar F22 y DO-06; etiquetas)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/documentos/forms.py (secciones)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/solicitudes/forms.py y apps/lugares/forms.py (Meta.labels y help_texts)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/coordinacion/models.py y apps/finanzas/models.py (verbose_name con tilde)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/importaciones/procesar.py (línea 380: nacionalidad como FK) y lectura.py
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/apps/nucleo/management/commands/cargar_demo.py (líneas 55 y 76-80: usar tramos y territorio)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/templates/administracion/rol_editar.html (grupos plegables)
- /Users/jordanrj1997/Desktop/ChileDesk/Chileeducatedesk/docs/manual_de_uso.md

## Pruebas afectadas
- apps/nucleo/test_f22.py:43-46: exige <legend class="fche-bloque__titulo"> para «Identificación», «Perfil y ocupación» e «Intereses y habilidades». Si «Intereses y habilidades» se pliega en <details>, hay que ajustar la aserción, o mantener legend en las secciones no plegadas.
- apps/documentos/tests.py:240: busca name="naturaleza_juridica" en /documentos/<id>/transcribir?registro=organizacion. Se rompe si el formulario pasa a la FK tipo_persona_juridica.
- apps/organizaciones/tests.py:88-93: envía proposito como texto («cartas», «donaciones»). Se rompe si ContactoForm usa la FK PropositoContacto.
- apps/personas/tests.py:176: envía parentesco «madre» como texto en EmergenciaForm.
- apps/nucleo/test_f22.py:31-37: envía nacionalidad «Chilena» e idiomas «Inglés básico» como texto y comprueba p.nacionalidad.
- apps/nucleo/test_f22.py:276: la importación con nacionalidad «Peruana» comprueba el texto (importaciones/procesar.py:380).
- apps/nucleo/test_busqueda.py:20 y :45: crea Proyecto(zona="Comuna Ficticia") y busca proyectos. Sigue pasando si se conserva el campo zona y busqueda.py filtra también por texto.
- apps/nucleo/test_vacios.py:27-31: espera el texto «Vigencia legal de Universidad Ficticia» en el Inicio. Se rompe si cambia el texto de tablero.py:138.
- apps/nucleo/test_comandos.py:15-18: ejecuta cargar_demo, que hoy asigna rango_etario y zona (cargar_demo.py:55 y :80). Hay que actualizar el comando si se deja de leer esos campos.
- apps/organizaciones/tests.py:80-85: valida comuna_municipal solo para municipalidad. No se rompe si la regla de servidor (organizaciones/models.py:64-66) se mantiene; el ocultamiento por JS es solo visual.
- apps/actividades/tests.py:431-433: TerritorioForm con comuna y región a la vez (espera un rechazo). Con la cascada que guarda el nivel más profundo, esa combinación pasaría a ser válida: hay que redefinir la prueba.
- Pruebas que envían "vigente": "on" al crear hijos (actividades/tests.py:431-445; proyectos/tests.py:41-75; personas/tests.py:97-176; coordinacion/tests.py:54-79; finanzas/tests.py:92; nucleo/test_f22.py:119-254): siguen pasando si se quita «vigente» del formulario al crear (Django ignora el dato y el modelo usa default=True), pero conviene correrlas.
- apps/nucleo/test_f22.py:181-193: SesionForm con facilitadores=[pk]. Sigue pasando con SelectorMultiple, porque el formato del POST no cambia.

## Decisiones abiertas
- Permiso del usuario para ampliar el modelo (docs/CONTEXTO.md §0.4 y §15): catálogos nuevos (TramoEtario, NaturalezaJuridica, Nacionalidad, Idioma, PropositoContacto, Parentesco, Cargo), la tabla ProyectoTerritorio y los campos FK/M2M nuevos. ¿Va en F24 (docs/rediseno_integral.md:40) o en una feature propia de claridad de formularios?
- [V] Tramos de edad definitivos (specs/f22/spec.md:128): ¿6 tramos dentro de los 4 de informe (0–17, 18–29, 30–59, 60+), o jóvenes 15–29 como usa INJUV? Afecta a alcance.py y a los conteos de SesionActividad.
- [V] «Vigencia desde/hasta» de Organización: ¿es el período del directorio o la vigencia de la personalidad jurídica? Alimenta el aviso del Inicio (tablero.py:137-138).
- [V] Domicilio legal: ¿Claudio lo necesita aparte de la dirección? ¿Como texto, como comuna o como dirección estructurada? (opciones A y B)
- [V] Valores iniciales de NaturalezaJuridica, revisados contra los certificados de vigencia reales (docs/reales/) con Claudio o Manuel.
- Proyecto: ¿varios territorios (tabla ProyectoTerritorio, la propuesta) o una sola comuna (FK simple)?
- [P] Umbral del selector desplegable: 6 opciones o menos como fichas en línea, más de 6 como desplegable con filtro.
- [P] Quitar «Vigente» de los formularios hijos al crear y también al editar, cuando ya existe el botón «Marcar no vigente».
- [P] Las secciones plegadas, ¿cerradas al crear y abiertas al editar si tienen datos, o siempre cerradas salvo error?
- Borrar más adelante las columnas de texto antiguas (rango_etario, zona, naturaleza_juridica, nacionalidad, idiomas, proposito, parentesco y cargo) requiere permiso explícito (borrado de datos y migraciones no aditivas).
- ¿Activar el historial de M2M (HistoricalRecords m2m_fields) para perfiles, áreas de interés y tramos? Crea tablas históricas nuevas; hoy esos cambios no quedan en el historial.
- Prioridad de catálogos dentro de las ~7 semanas que quedan: ¿solo tramos, territorio del proyecto y naturaleza jurídica (lo que pidió el usuario), o también nacionalidad, idiomas, propósito, parentesco y cargo?
- [P] ¿EstadoRegistro con campo extra «aplica a» (persona, organización o ambas), o basta excluir por código en cada formulario?

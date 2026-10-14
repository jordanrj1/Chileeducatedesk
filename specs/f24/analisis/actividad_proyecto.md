# actividad_proyecto

## Resumen
Revisé ActividadForm y TerritorioForm, las vistas de alta y edición de actividad con sus pestañas Información y Público, ProyectoForm con Proyecto, ComunidadForm con Comunidad, y las plantillas genéricas que dibujan los formularios. Las verificaciones las hice con el cliente de pruebas dentro de transacciones que deshice al final. No modifiqué archivos ni la base.

Hallazgos principales:
(a) El rango etario es texto libre de un solo valor en Actividad y en Comunidad. En cambio, el código tiene tres listas fijas de tramos de edad: alcance, filtro de personas y conteos de sesión.
(b) El territorio de la actividad no se puede elegir al crear ni al editar. Solo llega por la URL o desde otra pantalla, con 4 listas planas sin cascada que además exigen un único nivel.
(c) Error confirmado: una actividad con territorio en un sector no aparece en el filtro por comuna de /actividades, del calendario ni de /buscar, aunque sí aparece en la ficha de la comuna.
(d) La zona del proyecto es texto libre.
(e) El «Responsable vacío» no es un error de datos: el selector solo trae personas cuando se escribe en el buscador que tiene encima, y nada lo explica.
(f) En comunidad, las áreas de interés son 13 casillas que no se usan en ningún filtro. La comuna y el sector son listas planas de todo el país.

Propuestas:
- **Tramo etario:** catálogo con edad mínima y máxima. Los 6 valores sugeridos caben dentro de los 4 tramos que ya usan los informes. Se usa como selección múltiple en Actividad y Comunidad. El texto actual se convierte con un intérprete y el original se conserva como «texto anterior».
- **«¿Dónde?» reutilizable:** región → comuna → sector, con varias filas. Guarda el nivel más preciso en ActividadTerritorio o en un nuevo ProyectoTerritorio. Parte prellenado según de dónde se viene: la comuna o el sector de la URL, la comunidad o la jornada.
- **Formulario de actividad:** secciones plegables con `<details>` del navegador, sin JS. Lo opcional queda plegado.
- **Textos de ayuda:** en Meta de cada formulario, para no generar migraciones.

Todo cambio de modelo amplía la sección 7: requiere la autorización del usuario y la spec F24 antes de escribir código.

## Hallazgos

### Rango etario en texto libre (Actividad y Comunidad) y tramos repetidos en el código
- Evidencia: apps/actividades/models.py:43 rango_etario CharField(100); apps/comunidades/models.py:27 rango_etario CharField(100); apps/actividades/forms.py:30,36; apps/comunidades/forms.py:27,32; templates/actividades/pestanas/publico.html:5; templates/comunidades/pestanas/info.html:10; dato demo apps/nucleo/management/commands/cargar_demo.py:80 «Personas adultas y mayores». Tramos fijos en el código: apps/actividades/alcance.py:8 TRAMOS; apps/personas/views.py:51 (limites) y :92 (opciones del filtro Edad); apps/actividades/models.py:253-256 (conteo_menores/jovenes/adultos/mayores). Pendiente [V] en specs/f22/spec.md:128 y specs/f22/tasks.md:12 (tramos de edad de los informes).
- Hoy: Un campo de texto de una línea por registro. No hay catálogo ni varios valores, y nada se puede filtrar ni sumar. La edad también vive en 3 listas fijas distintas en el código.
- Problema: Escribe cada vez algo distinto («jóvenes de 15 a 29», «familias con niños»), no puede marcar varios grupos de forma clara, ni filtrar actividades o comunidades por edad del público.
- Propuesta: Catálogo nucleo.TramoEtario editable en Catálogos (/administracion/catalogos/tramo-etario/), con edad_min y edad_max. Valores iniciales: Primera infancia (0 a 5), Niñez (6 a 12), Adolescencia (13 a 17), Jóvenes (18 a 29), Adultos (30 a 59), Personas mayores (60 o más). Los tres primeros caben en el tramo 0-17 de los informes, así que alcance.py y los conteos de sesión no se rompen. Se agrega el campo M2M tramos_etarios en Actividad y en Comunidad, dibujado como CheckboxSelectMultiple: son 6 casillas en una fila con el estilo .fche-opciones que ya existe en static/css/fche.css:640-645. Se suma un botón «Todas las edades» que las marca todas (fche.js). Vacío significa «sin indicar». Se agregan filtros «Edad del público» en ActividadLista (apps/actividades/views.py:81-93) y en ComunidadLista (apps/comunidades/views.py:28-32). Conversión del texto actual: un intérprete apps/nucleo/tramos.py, con una copia congelada dentro de la migración. Lee primero los números («15 a 29», «60+», «mayores de 60», «menores de 18») y marca los tramos que se cruzan; luego busca palabras clave (adult→Adultos salvo «adulto mayor», mayor/tercera edad→Personas mayores, joven/juvent/universit→Jóvenes, adolesc/liceo/media→Adolescencia, niñ/escolar/básica→Niñez, párvul/jardín/primera infancia→Primera infancia). Ejemplo: «Personas adultas y mayores» queda como {Adultos, Personas mayores}. La columna de texto no se borra. Se muestra en la ficha y en el formulario como «Antes decía: «…»», con la casilla «Ya lo revisé». Al marcarla se vacía el texto y simple_history lo conserva. Más adelante, el filtro de personas (personas/views.py:51,92) puede leer los límites del catálogo; queda como decisión.

### Cómo enganchar el catálogo nuevo sin dejar cabos sueltos
- Evidencia: apps/nucleo/models.py:29-41 (_catalogo), :49-59 (RolParticipacion con campos_extra como modelo a seguir), :75-92 (CATALOGOS); apps/cuentas/roles.py:5-9 (CATALOGOS_MODELOS da add/change al Administrador); apps/nucleo/vistas_catalogos.py:39-45 (el formulario incluye campos_extra), :15-24 (dependencias). Verifiqué en el shell que una M2M automática aparece en «En uso» como «relaciones comunidad-areatematica». templates/administracion/catalogo.html:14-18 no muestra los campos extra. apps/nucleo/test_catalogos.py:16 exige que todo catálogo tenga filas.
- Hoy: Los catálogos simples se crean con _catalogo. Los que llevan campos propios son subclases con campos_extra.
- Problema: Si solo se agrega el modelo, el catálogo queda sin semillas (la prueba falla). La columna «En uso» muestra una etiqueta técnica, y la tabla no deja ver el rango de edades de cada valor.
- Propuesta: class TramoEtario(Catalogo) con edad_min y edad_max (PositiveSmallIntegerField null=True, blank=True), campos_extra=['edad_min','edad_max'], clean() que exige edad_max >= edad_min, y Meta con su permiso desactivar_tramoetario. Registrarlo como CATALOGOS['tramo-etario']. Agregar 'tramoetario' a CATALOGOS_MODELOS. Sembrar los valores en la migración nucleo/0012. Para que «En uso» se lea bien, usar through explícito con verbose_name_plural «actividades» y «comunidades» (ActividadTramoEtario y ComunidadTramoEtario, con UniqueConstraint), o al menos dar verbose_name al through. Agregar en catalogo.html una columna «Edades» que aparezca solo si el modelo tiene edad_min.

### Territorio de la actividad: no está en el formulario y la pantalla aparte no tiene cascada
- Evidencia: TerritorioForm apps/actividades/forms.py:275-291: cuatro listas planas (todas las regiones, provincias, comunas y sectores). Comprobé al renderizar /actividades/<id>/territorios/nuevo que no tienen hx-get. Si se elige región y comuna da el error «Elige exactamente un nivel» (forms.py:289-290). El alta solo crea territorio desde ?comuna=&sector= (apps/actividades/views.py:173-177). La pestaña Información lo agrega en otra pantalla (templates/actividades/pestanas/info.html:10-12). Sector.__str__ no muestra la comuna (apps/territorio/models.py:82-83), así que sectores con el mismo nombre se confunden. ComunasOpciones solo filtra por provincia (apps/territorio/views.py:453-459). Patrón de cascada ya resuelto en DireccionForm (apps/territorio/forms.py:86-89) y en templates/territorio/_direccion.html.
- Hoy: Para decir «es en Hualpén», Claudio guarda la actividad, entra a Información, pulsa «+ Territorio» y busca en una lista de todas las comunas del país. Si además elige la región, se rechaza.
- Problema: Son muchos clics, hay una lista enorme y un error poco intuitivo. La zona queda fuera del flujo de crear y editar.
- Propuesta: Nueva sección «¿Dónde?» dentro de crear y editar actividad, opcional:
(1) TerritorioCascadaForm (ModelForm de ActividadTerritorio) con región (solo de interfaz; parte con la región de la dirección de la Organización es_propia), comuna (llega por HTMX según la región, agrupada por provincia en optgroup, con un primer grupo «Donde ya trabajamos» desde territorio/resumen.presencia_por_comuna) y sector (HTMX según la comuna, más «+ Crear sector»). En clean() guarda solo el nivel más específico elegido (sector > comuna > región). Valida que el sector sea de la comuna. Si la fila queda vacía, no guarda nada.
(2) inlineformset_factory(Actividad, ActividadTerritorio, form=TerritorioCascadaForm, extra=1, can_delete=False) con prefijo 'donde' y botón «+ Otro territorio» que clona la fila desde un <template> (fche.js). Los territorios vigentes se muestran como chips con casilla «Quitar», que deja vigente=False; no se editan en el sitio, para no perder qué decían. clean() del formset rechaza el mismo territorio repetido.
(3) Prellenado sin duplicar: ?comuna/?sector (ComunaInicialMixin), ?comunidad (su sector o su comuna) y ?padre (los territorios de la jornada).
(4) Un ConTerritoriosMixin en apps/nucleo/direccion_mixin.py, análogo a ConDireccionMixin (líneas 30-44). Guarda dentro del mismo transaction.atomic de views.py:164. Si el POST no trae 'donde-TOTAL_FORMS', usa la URL como hoy (de eso dependen las pruebas de test_contexto).
(5) ComunasOpciones acepta un parámetro cuyo nombre termine en 'region' y filtra por provincia__region_id. Ojo: _valor() (territorio/views.py:38-39) toma el primer número que encuentre en la URL. SectorCrearRapido usa hx-include «[name$='comuna']» y el id fijo #aviso-sector (territorio/views.py:507, _direccion.html:15-17): con varias filas hay que acotarlo a la fila («closest .fche-territorio-fila») y pasar un aviso_id por fila.
(6) La misma cascada reemplaza a TerritorioForm en /territorios/nuevo.

### Error: los filtros por comuna ignoran actividades dirigidas a un sector
- Evidencia: apps/actividades/views.py:45-48 (_filtro_comuna del listado), apps/actividades/views.py:831 (calendario) y apps/nucleo/busqueda.py:98 (buscador global) usan solo territorios__comuna_id. En cambio apps/territorio/consultas.py:31-32 y apps/territorio/resumen.py:81 sí consideran sector__comuna. Reproducido en una transacción deshecha: una actividad con territorio en un sector aparece en la ficha de la comuna, pero no en /actividades?comuna=<id> ni en /buscar?tipo=actividad&zona=<id>.
- Hoy: Dos criterios distintos para la misma pregunta: «¿esta actividad es de esta comuna?».
- Problema: Si empieza a elegir el sector en «¿Dónde?», esas actividades desaparecen del filtro de comuna del listado, del calendario y del buscador.
- Propuesta: Una sola condición en apps/territorio/consultas.py, por ejemplo dirigida_a_comuna(prefijo, comuna_id) = Q(territorios__vigente=True, territorios__comuna_id=c) | Q(territorios__vigente=True, territorios__sector__comuna_id=c). Usarla en los 3 lugares y agregar una prueba con territorio de nivel sector. Opcional: que el filtro «Zona (comuna)» del listado (views.py:85) ofrezca primero las comunas con presencia, en vez de todas.

### Zona del proyecto en texto libre
- Evidencia: apps/proyectos/models.py:22 zona CharField(200); apps/proyectos/forms.py:22,29; apps/proyectos/views.py:23 (búsqueda) y :25 (columna Zona, también en el Excel); apps/nucleo/busqueda.py:75 y :80-83 (busca por coincidencia parcial con el nombre de la comuna); templates/proyectos/pestanas/resumen.html:5; templates/proyectos/ficha.html:8; demo «Comuna Demo». Pregunta abierta en docs/cuestionario_manuel.md:41 («Zona» ¿equivale a comuna y sector?).
- Hoy: Texto escrito a mano. No se enlaza con la comuna, no se filtra, y el contenedor Territorio (F23) no puede contar proyectos por comuna.
- Problema: «Hualpen» y «Hualpén» o «San Pedro» y «SPC» quedan como cosas distintas. No puede listar los proyectos de una comuna con un clic.
- Propuesta: Tabla proyectos.ProyectoTerritorio con el mismo diseño que ActividadTerritorio (un nivel por fila, CheckConstraint, vigente) y la misma sección «¿Dónde?» y ConTerritoriosMixin en ProyectoNuevo y ProyectoEditar. Se agrega la propiedad Proyecto.zona_resumen: territorios vigentes unidos por « · », o el texto anterior si no hay ninguno. La columna «Zona» del listado y del Excel pasa a ser lambda p: p.zona_resumen, con prefetch_related('territorios__comuna', 'territorios__sector'). Nuevo Filtro('comuna', 'Comuna', …) en ProyectoLista. busqueda._proyectos filtra por territorios (comuna o sector de la comuna) y, como respaldo, por el texto anterior. La migración convierte zona→comuna o sector cuando hay una sola coincidencia con el nombre normalizado (normalizar de apps/territorio/reconocer.py:13, más nombres alternativos). Lo que no calza se conserva y se muestra «Antes decía: «…» (por revisar)». zona sale del formulario.

### «Responsable sale vacío» en /proyectos/nuevo (y también en actividad)
- Evidencia: apps/nucleo/formularios.py:50-60: _IteradorLimitado solo entrega la opción vacía y la ya elegida. templates/generico/_campo.html:9-11: el buscador carga opciones solo al escribir (hx-trigger «input changed delay:300ms»). apps/personas/views.py:535-546: la respuesta siempre empieza con «---------». Comprobado al renderizar: el select «responsable» tiene 1 sola opción en /proyectos/nuevo y en /actividades/nueva. Lo mismo pasa con actividad_padre (apps/actividades/forms.py:25).
- Hoy: Está hecho así a propósito, para no cargar listas largas, pero nada lo explica. Después de buscar, la primera opción sigue siendo «---------» y hay que abrir el desplegable: dos pasos.
- Problema: Parece que no hay personas cargadas.
- Propuesta: (a) SelectorField(..., sugerencias=callable): _IteradorLimitado agrega un <optgroup label=«Sugeridas»> con hasta 15 personas: las que tienen vínculo vigente con la organización propia (PersonaOrganizacion + Organizacion.es_propia), los responsables recientes de actividades y proyectos, y la persona del usuario conectado (PerfilCuenta.persona, apps/cuentas/models.py:23). Solo se sugieren; nunca quedan elegidas solas. Para «Jornada a la que pertenece» se sugieren las actividades de tipo jornada del mismo proyecto.
(b) Etiqueta vacía «— Escribe arriba para buscar o elige una sugerida —».
(c) En PersonaOpciones y ActividadOpciones, si la búsqueda devuelve una sola coincidencia, se envía con selected.
(d) Junto al selector, un enlace «¿No está? Regístrala» hacia la ficha rápida, según el patrón «crear desde el contexto» de docs/CONTEXTO.md §10.

### Formulario de actividad: orden, ruido y falta de contexto
- Evidencia: apps/actividades/forms.py:27-32: «Qué es» tiene 7 campos mezclados (nombre, tipo, área, proyecto, jornada, modalidad, responsable). apps/nucleo/formularios.py:34-47: secciones_ui no permite plegar. templates/generico/_campos.html:3-11: todas las secciones se dibujan abiertas. ActividadEditar (apps/actividades/views.py:183-194) no muestra estado, proyecto ni fecha. Hay modalidad en la actividad (models.py:37) y otra en cada programación (models.py:349; ProgramarForm forms.py:59), sin explicar la diferencia. Las comunidades se agregan en otra pestaña (forms.py:29).
- Hoy: Tres secciones siempre abiertas. Lo opcional (jornada, proyecto, condiciones) pesa lo mismo que lo esencial.
- Problema: Se ve «Actividad padre (jornada)» sin saber para qué sirve, y la edición no dice en qué estado ni en qué proyecto está la actividad.
- Propuesta: Orden propuesto:
1) «Qué es» (abierta): nombre*, tipo, tema (area_tematica), responsable con la marca «para confirmar».
2) «Para qué y para quién» (abierta): objetivo, tramos_etarios, publico_objetivo (Textarea de 2 filas), beneficiarios_estimados, y un aviso con enlace a la pestaña de comunidades, o la comunidad fija si se llegó con ?comunidad.
3) «¿Dónde?» (abierta, opcional): modalidad y filas de territorio.
4) «Proyecto y jornada» (plegada): proyecto y actividad_padre con la etiqueta «Jornada a la que pertenece». Se abre sola si viene ?proyecto o ?padre, o si ya tiene valor; el título resume lo elegido («Proyecto: X · Jornada: Y»).
5) «Más detalles» (plegada): descripcion y condiciones.
Cómo hacerlo: secciones acepta un 4.º elemento opcional {'plegada': True, 'incluir': 'territorio/_territorios_formset.html'}. secciones_ui devuelve diccionarios con abierta = not plegada or algún campo con valor o error. _campos.html dibuja <details class='fche-bloque fche-bloque--plegable' open?><summary class='fche-bloque__titulo'> para las plegadas y mantiene <fieldset><legend> en las abiertas (de eso depende test_f22.py:46). Es HTML nativo, sin JS y sin CDN. La marca «para confirmar» sale de un atributo para_confirmar = ['responsable'] que lee _campo.html, sin volver obligatorio el campo. En Editar, la bajada sería: «Estado: Planificada · Proyecto: X · Programada el 20-10-2026 en Sala Y. La fecha y el lugar se cambian en Programar.»

### Comunidad: áreas de interés hacen ruido y la comuna no está en cascada
- Evidencia: apps/comunidades/forms.py:27,33,40: 13 casillas de AreaTematica, con semillas en apps/nucleo/migrations/0011_semillas_f22.py:8-12. En /comunidades/nueva se dibujan 13 casillas. Comunidad.areas_interes no se usa en filtros ni en la búsqueda de candidatos: solo se muestra en templates/comunidades/pestanas/info.html:11 y se suma al fusionar (apps/nucleo/fusion.py:76). La comuna y el sector son listas planas de todo el país (apps/comunidades/forms.py:37-39). Comunidad.TIPOS está escrito en el código e incluye tipos por edad («personas_mayores», «juventud»; apps/comunidades/models.py:12-16) que se cruzan con el tramo etario.
- Hoy: «Caracterización» mezcla población, rango en texto, 13 casillas y diagnóstico. La comuna se elige de una lista larga y el sector muestra los de todas las comunas.
- Problema: Mucho ruido visual en un dato que no se usa, y elegir la comuna cuesta.
- Propuesta: Secciones:
- «Quiénes son»: nombre*, tipo, descripción.
- «Dónde»: región (solo de interfaz) → comuna* → sector, más «+ Crear sector». Usa los mismos atributos hx que DireccionForm, el sector se filtra por la comuna y se respeta el prellenado ?comuna/&sector.
- «Cómo es»: tramos_etarios (6 casillas) y población estimada.
- «Contacto» (plegada): organización y referente.
- «Más detalles» (plegada): diagnóstico y áreas de interés. Las áreas se plegarían como SelectMultiple compacto o se quitarían, según lo que decida Claudio.
Como mejora aparte, convertir TipoComunidad en catálogo para no tenerlo escrito en el código.

### Duplicar actividad no copia los datos de público
- Evidencia: apps/actividades/servicios.py:171-191: copia tipo, objetivo, descripción, modalidad, responsable, condiciones, territorios y organizaciones. No copia area_tematica, publico_objetivo, rango_etario, beneficiarios_estimados ni las comunidades destino. Prueba: apps/nucleo/test_escenarios_catalogo.py:435-450.
- Hoy: La copia sale sin tema ni público.
- Problema: Debe volver a escribir a quién va dirigida cada vez que repite una actividad.
- Propuesta: Copiar también area_tematica, publico_objetivo y beneficiarios_estimados, más nueva.tramos_etarios.set(actividad.tramos_etarios.all()), y agregar las aserciones en test AT-E1.

### Territorio sin historial y editable en el sitio
- Evidencia: ActividadTerritorio no tiene HistoricalRecords (apps/actividades/models.py:102-134), pero la ruta territorios_editar (apps/actividades/urls.py:44, que usa HijoEditar en apps/nucleo/hijos.py:73-102) permite cambiar la comuna de una fila. No hay restricción contra territorios repetidos.
- Hoy: Cambiar la zona de una actividad borra qué decía antes.
- Problema: No puede reconstruir dónde iba dirigida una actividad antes de un cambio.
- Propuesta: En «¿Dónde?» las filas existentes no se editan: se quitan (vigente=False) y se agrega otra. Opcional: history = HistoricalRecords() en ActividadTerritorio y ProyectoTerritorio. Validar repetidos en el formset, y no con una restricción en la base, para no fallar con datos existentes.

### Textos de ayuda propuestos (en simple), en Meta.labels y Meta.help_texts de cada formulario
- Evidencia: Hoy las ayudas están repartidas entre modelos y formularios (apps/actividades/models.py:42; apps/comunidades/models.py:24-27; apps/proyectos/models.py:22; apps/comunidades/forms.py:21; apps/actividades/forms.py:28-31). Cambiar help_text o verbose_name en un modelo genera una migración AlterField.
- Hoy: Muchos campos no tienen ayuda: Actividad padre, Modalidad, Responsable, Condiciones, Estado del proyecto, Diagnóstico.
- Problema: No sabe qué poner ni si un campo es necesario.
- Propuesta: ACTIVIDAD.
- Nombre: «Cómo la reconocerás en listas y calendario. Ej.: «Taller de huertos · Villa Los Aromos».»
- Tipo: «Taller, charla, jornada… Si falta uno, se agrega en Catálogos.»
- Tema: «El tema principal. Sirve para agrupar actividades y encontrar personas interesadas.»
- Responsable: «Quién de la Fundación la coordina. Escribe parte del nombre y elige. Se necesita para confirmarla, no para guardarla.»
- Objetivo: «Qué se quiere lograr, en una o dos frases.»
- Edades del público: «Marca uno o varios grupos. Si aún no lo sabes, déjalo vacío.»
- ¿Quiénes?, en palabras: «Solo si hace falta precisar. Ej.: «apoderados de 1.º básico», «dirigentes de juntas de vecinos».»
- Personas esperadas: «Cuántas personas crees que asistirán en total. Un número aproximado basta.»
- Modalidad: «Presencial, virtual o híbrida. Al programar una fecha puedes cambiarla solo para esa vez.»
- ¿Dónde?: «La comuna o el sector donde se hará o al que va dirigida, aunque aún no haya lugar. La sala o sede se elige al programar.»
- Región: «Parte con la de la Fundación; cámbiala si es otra.»
- Comuna: «Si es para toda la región, déjala vacía.»
- Sector: «Si va a un sector puntual. ¿No está? Escríbelo y pulsa «+ Crear sector».»
- + Otro territorio: «Si llega a más de una comuna o sector.»
- Quitar: «Deja de mostrarse como zona; queda en el historial.»
- Proyecto: «Si es parte de un proyecto, elígelo; si no, déjalo vacío.»
- Jornada a la que pertenece: «Solo si esta charla o taller ocurre dentro de una jornada ya registrada (por ejemplo, una feria con varios talleres).»
- Cómo se hará (descripción): «Contenidos, dinámica y materiales.»
- Requisitos y cuidados (condiciones): «Accesibilidad, materiales que deben traer, autorización de apoderados, etc.»
PROYECTO.
- Nombre: «Ej.: «Alfabetización digital 2026».»
- Etapa (estado): «En qué etapa está; cámbiala cuando avance.»
- Tema: «El tema principal del proyecto.»
- Responsable: «Quién lo lidera. Escribe parte del nombre y elige; si no aparece, regístrala en Personas.»
- Inicio y Término: «Aproximadas está bien; el término puede quedar vacío.»
- ¿Dónde?: «Comunas o sectores donde se desarrolla; puedes agregar varios.»
- Objetivo general: «El cambio grande que busca, en una frase.»
- ¿Para quiénes? (población objetivo): «Quiénes se benefician. Ej.: «personas mayores de la comuna».»
- Plegados: Descripción («Resumen breve: qué es y por qué existe.»), Objetivos específicos («Los pasos para lograr el objetivo general; uno por línea.»), Diagnóstico («Qué necesidad se detectó y cómo se sabe: encuesta, reunión, diagnóstico municipal…»).
COMUNIDAD.
- Nombre: «Cómo la conocen. Ej.: «Vecinos de Villa Los Aromos», «Club de adulto mayor Renacer».»
- Tipo: «Qué la une: el barrio, un colegio, un interés…»
- Descripción breve: «Una o dos frases para quien no la conoce.»
- Comuna*: «Dónde vive o se reúne.»
- Sector: «Villa, población o etapa, si corresponde; si no está, créalo aquí.»
- Edades que predominan: «Marca uno o varios grupos.»
- Cuántas personas son: «Número aproximado.»
- Organización que la representa: «La junta de vecinos, el colegio u otra, si existe.»
- Persona de contacto (referente): «Con quién se coordina.»
- Qué necesita (diagnóstico): «Lo conversado en terreno: necesidades, intereses, problemas.»
- Temas que le interesan: «Opcional. Sirve para proponerle actividades.»

## Cambios de modelo
- **nucleo.TramoEtario (nuevo)**: Subclase de Catalogo con edad_min y edad_max (PositiveSmallIntegerField null/blank), campos_extra=['edad_min','edad_max'], clean() con edad_max >= edad_min y permiso desactivar_tramoetario. Se registra en CATALOGOS como 'tramo-etario' y se agrega 'tramoetario' a cuentas/roles.py CATALOGOS_MODELOS. | Migración: apps/nucleo/migrations/0012_tramo_etario.py: CreateModel más RunPython que siembra primera_infancia (0-5), ninez (6-12), adolescencia (13-17), jovenes (18-29), adultos (30-59) y personas_mayores (60 o más), en orden 1 a 6. Reversa: noop. | Riesgo: Bajo. Sin semillas falla test_catalogos.py:16. Los permisos del Gestor y del Administrador se siembran solos con post_migrate (cuentas/apps.py:29).
- **actividades.Actividad**: Nuevo campo tramos_etarios = ManyToManyField('nucleo.TramoEtario', blank=True, related_name='actividades'). Se recomienda through ActividadTramoEtario con UniqueConstraint y verbose_name para que «En uso» se lea bien. rango_etario se conserva en la base, pero sale del formulario y se muestra como «Antes decía», con «Ya lo revisé». Opcional: HistoricalRecords(m2m_fields=[...]) (simple_history 3.13 lo admite) para que el cambio de edades aparezca en el Historial. | Migración: apps/actividades/migrations/0008_tramos_etarios.py: AddField (y CreateModel del through) más RunPython que convierte rango_etario en tramos con el intérprete congelado dentro de la migración. No borra el texto. Reversa: noop. | Riesgo: Medio-bajo. Una conversión ambigua deja el registro sin tramos y con el texto «por revisar». La base local solo tiene datos demo (0 actividades con rango), pero el equipo de Claudio puede tener datos reales: probar con una copia de respaldo.
- **comunidades.Comunidad**: Nuevo campo tramos_etarios M2M (through ComunidadTramoEtario recomendado). rango_etario queda como texto anterior. areas_interes se conserva en la base y se pliega en el formulario (o se quita si Claudio lo decide). | Migración: apps/comunidades/migrations/0002_tramos_etarios.py: AddField más RunPython de conversión. La demo «Personas adultas y mayores» queda como Adultos + Personas mayores. | Riesgo: Bajo. Hay que actualizar cargar_demo.py:79-81.
- **actividades.ActividadTerritorio**: El esquema no cambia necesariamente: se reemplaza TerritorioForm por TerritorioCascadaForm y se usa en un formset. Opcional: history = HistoricalRecords(). Opcional: base abstracta territorio.TerritorioObjetivo (region, provincia, comuna, sector, vigente, nivel, __str__) compartida con ProyectoTerritorio, manteniendo en el hijo el nombre de restricción 'actividad_territorio_un_nivel' para que no haya migración. | Migración: Ninguna si solo cambia el formulario. Si se agrega historial: AddModel HistoricalActividadTerritorio. | Riesgo: Bajo. Los filtros de comuna deben incluir sector__comuna (views.py:47 y :831; busqueda.py:98) antes de que se empiece a elegir sectores.
- **proyectos.ProyectoTerritorio (nuevo)**: proyecto FK PROTECT con related_name='territorios'; region, provincia, comuna y sector como FK PROTECT null con related_name='+'; vigente; CheckConstraint 'proyecto_territorio_un_nivel' igual a la de la actividad; propiedad nivel. En Proyecto, propiedad zona_resumen. | Migración: apps/proyectos/migrations/0003_proyecto_territorio.py: CreateModel más RunPython. Convierte el texto de zona en una fila de comuna o sector solo cuando hay una coincidencia única con el nombre normalizado (incluye nombres alternativos de sector). El texto se mantiene. | Riesgo: Medio-bajo. Si zona se renombra o se borra, falla test_busqueda.py:20 (Proyecto.objects.create(zona=...)): por eso se recomienda conservar la columna. El buscador debe mantener el respaldo por texto.
- **proyectos.Proyecto**: zona sale de ProyectoForm. Se muestra como «Antes decía: «…» (por revisar)» con la casilla «Ya lo revisé». La etiqueta se cambia en el formulario, no en el modelo, para evitar una migración AlterField. Opcional: tramos_etarios también en Proyecto, si se decide. | Migración: Ninguna para ocultarlo. Borrar la columna más adelante requiere permiso (docs/CONTEXTO.md §0 regla 4). | Riesgo: Bajo.

## Archivos
- specs/f24/spec.md, specs/f24/plan.md, specs/f24/tasks.md (nuevos: tramo etario, «¿Dónde?» en cascada y secciones plegables; lo [V] queda listado)
- apps/nucleo/models.py (TramoEtario, CATALOGOS['tramo-etario'])
- apps/nucleo/migrations/0012_tramo_etario.py (nuevo, con semillas)
- apps/nucleo/tramos.py (nuevo: intérprete texto→tramos, con pruebas propias)
- apps/cuentas/roles.py (CATALOGOS_MODELOS += 'tramoetario')
- apps/nucleo/formularios.py (secciones_ui con plegada/abierta/incluir; SelectorField con sugerencias y etiqueta vacía)
- apps/nucleo/direccion_mixin.py (ConTerritoriosMixin con respaldo a la URL cuando falta el management form)
- templates/generico/_campos.html (<details>/<summary> para plegadas, include por sección; mantener <legend> en las abiertas)
- templates/generico/_campo.html (marca «para confirmar», optgroup de sugeridas)
- static/css/fche.css (.fche-bloque--plegable, .fche-territorio-fila)
- static/js/fche.js (agregar fila del formset desde <template>, «Todas las edades»)
- templates/administracion/catalogo.html (columna Edades cuando hay edad_min)
- apps/actividades/models.py (tramos_etarios con through; opcional HistoricalRecords en ActividadTerritorio)
- apps/actividades/migrations/0008_tramos_etarios.py (nuevo, con conversión de rango_etario)
- apps/actividades/forms.py (ActividadForm: secciones, labels, help_texts, tramos; TerritorioCascadaForm reemplaza TerritorioForm; TerritorioFormSet)
- apps/actividades/views.py (ActividadNueva/ActividadEditar con formset y bajada de contexto; _filtro_comuna y calendario con sector__comuna; filtro de edad en ActividadLista; ctx_publico con tramos)
- apps/actividades/urls.py (territorios_* con el formulario nuevo; quitar edición en el sitio si se decide)
- apps/actividades/servicios.py (duplicar copia tema, público y tramos)
- templates/actividades/pestanas/publico.html y templates/actividades/pestanas/info.html (tramos como chips, texto anterior, enlace a ¿Dónde?)
- templates/territorio/_territorios_formset.html y templates/territorio/_cascada.html (nuevos; región→comuna→sector con «+ Crear sector» por fila)
- apps/territorio/views.py (ComunasOpciones con región y optgroups por provincia y «Donde ya trabajamos»; SectorCrearRapido con aviso por fila)
- apps/territorio/consultas.py (condición común dirigida_a_comuna)
- templates/territorio/_direccion.html (aviso-sector parametrizable)
- apps/proyectos/models.py (ProyectoTerritorio, zona_resumen)
- apps/proyectos/migrations/0003_proyecto_territorio.py (nuevo, con conversión de zona)
- apps/proyectos/forms.py (secciones nuevas, sin zona, help_texts)
- apps/proyectos/views.py (formset en Nuevo/Editar, columna Zona, filtro comuna, prefetch)
- templates/proyectos/pestanas/resumen.html y templates/proyectos/ficha.html (zona desde territorios)
- apps/nucleo/busqueda.py (proyectos por territorio con respaldo de texto; actividades con sector→comuna)
- apps/comunidades/models.py (tramos_etarios)
- apps/comunidades/migrations/0002_tramos_etarios.py (nuevo)
- apps/comunidades/forms.py (secciones, cascada región→comuna→sector, áreas plegadas, help_texts)
- apps/comunidades/views.py (filtro por edad)
- templates/comunidades/pestanas/info.html (tramos, texto anterior)
- apps/personas/views.py (PersonaOpciones: selected si hay 1 resultado)
- apps/nucleo/management/commands/cargar_demo.py (tramos en lugar de texto; ProyectoTerritorio en lugar de zona)
- docs/manual_de_uso.md (líneas 50 y 119), docs/modelo/diagrama_er.md, specs/trazabilidad_requerimientos.md, docs/escenarios_estado.md

## Pruebas afectadas
- apps/actividades/tests.py:430-436 test_territorio_de_la_actividad_un_solo_nivel: hoy espera 200 cuando se envían región y comuna. Con la cascada debe guardar solo la comuna y responder 302. Se ajusta la aserción; la parte de IntegrityError del modelo sigue igual.
- apps/actividades/tests.py:28-33 test_crear_actividad_con_informacion_parcial: envía solo el nombre. El formset debe ser opcional: sin 'donde-TOTAL_FORMS' no puede fallar.
- apps/actividades/tests.py:37-45 y :48-50 (proyecto y jornada; una actividad no puede ser su propia padre): envían proyecto y actividad_padre. No cambian si se mantienen los nombres de campo, aunque la sección quede plegada.
- apps/actividades/tests.py:53-65 test_listado_filtros (filtro ?comuna= por lugar): debe seguir pasando al agregar sector__comuna. Conviene una prueba nueva con territorio de nivel sector.
- apps/actividades/tests.py:620-634 test_calendario_filtra_por_zona…: debe seguir pasando con el filtro ampliado.
- apps/actividades/tests.py:405 (editar una actividad realizada no cambia): no le afecta.
- apps/territorio/test_contexto.py:110-126, :140-157, :160-175 y :215-225: crean la actividad por URL (?comuna/&sector) enviando solo el nombre. Dependen de que se use la URL cuando el POST no trae el formset, o hay que reescribirlas con campos donde-*.
- apps/territorio/test_contexto.py:129-137 test_nueva_actividad_con_comuna_y_comunidad_conserva_ambas: usa ActividadTerritorio.objects.get(). Si ?comunidad también prellena la comuna, hay que deduplicar o la consulta devuelve 2 filas.
- apps/territorio/test_contexto.py:105-107 y :205-213: initial['comuna'] y initial['sector'] de ComunidadForm. La cascada debe mantener esos initial y sumar la región.
- apps/nucleo/test_f22.py:43-46 test_formulario_por_secciones…: busca <legend class="fche-bloque__titulo">. Las secciones abiertas deben seguir con <fieldset><legend>.
- apps/nucleo/test_f22.py:128-139 y :142-148 (crear comunidad, sector de otra comuna rechazado): envían comuna y sector. La región debe ser solo de interfaz y opcional, y la validación sigue en Comunidad.clean().
- apps/nucleo/test_f22.py:158-172 test_actividad_para_una_comunidad…: envía publico_objetivo y beneficiarios_estimados. No le afecta, salvo que la comunidad prellenada cree un territorio, cosa que esa prueba no revisa.
- apps/nucleo/test_catalogos.py:12-16 test_catalogos_iniciales_cargados: exige filas en cada catálogo, así que TramoEtario debe sembrarse en la migración.
- apps/cuentas/tests.py:142-147 (sembrar_roles): debe incluir los permisos de tramoetario.
- apps/proyectos/tests.py:10-11, :22-24 y :85: crean y editan proyectos sin zona. El formset debe ser opcional.
- apps/nucleo/test_busqueda.py:16-31 (fixture mundo con Proyecto(zona='Comuna Ficticia')) y :134-136 (exportar /proyectos): conservar la columna zona y el respaldo de texto en búsqueda y exportación.
- apps/nucleo/test_escenarios.py:21-40 test_recorrido_completo_normal (proyecto con responsable y actividad nueva) y :223-250 test_todas_las_pantallas_principales_responden (GET de /actividades/nueva, /actividades/<pk>/editar, /actividades/<pk>/territorios/nuevo, /proyectos/nuevo, /proyectos/<pk>/editar): deben seguir respondiendo 200.
- apps/nucleo/test_escenarios_catalogo.py:435-450 test_AT_E1_duplicar_actividad: si duplicar copia los tramos, agregar la aserción.
- apps/territorio/test_resumen.py, apps/territorio/test_contenedor.py, apps/territorio/tests.py:99-107 y apps/nucleo/test_escenarios_catalogo.py:958-966: crean ActividadTerritorio directamente. No les afecta mientras el modelo y el nombre de su restricción no cambien.

## Decisiones abiertas
- Autorización del usuario para ampliar la sección 7 del modelo (docs/CONTEXTO.md §15 «No ampliar el modelo… sin preguntarme»): TramoEtario, tramos_etarios en Actividad y Comunidad, y ProyectoTerritorio. Se abre la spec F24 antes del código.
- Valores y nombres finales de los tramos (¿Jóvenes 18-29 según INJUV? ¿Personas mayores 60+ según la Ley 19.828?) y si los informes siguen con 4 tramos (0-17, 18-29, 30-59, 60+): pendiente [V] en specs/f22/spec.md:128.
- Significado de no marcar ningún tramo: «sin indicar» o «todas las edades». Se propone vacío = sin indicar, más un botón «Todas las edades».
- ¿El tramo etario también va en Proyecto (población objetivo)?
- «Zona» = comuna y sector (docs/cuestionario_manuel.md:41). ¿Se permite el nivel provincia en la cascada o basta región → comuna → sector?
- Región por defecto en la cascada: la de la dirección de la organización propia o un ajuste en .env.
- Áreas de interés de la comunidad: plegarlas en «Más detalles» o quitarlas, ya que hoy no se usan en filtros ni en la búsqueda de candidatos.
- Borrar más adelante las columnas de texto anterior (Actividad.rango_etario, Comunidad.rango_etario, Proyecto.zona): es borrar datos y requiere permiso.
- ¿Las comunidades destinatarias se eligen dentro del formulario de la actividad o siguen en la pestaña «Público y comunidades»?
- Historial: agregar HistoricalRecords a ActividadTerritorio y ProyectoTerritorio, y m2m_fields para tramos, o solo impedir la edición en el sitio.
- Responsable: ¿basta con sugerir al equipo de la Fundación y a los responsables recientes, o prellenar con la persona del usuario conectado? Se recomienda solo sugerir.
- Fuera de este alcance, pero pedido por «nada hardcodeado»: Comunidad.TIPOS (comunidades/models.py:12-16), Proyecto.ESTADOS (proyectos/models.py:15) y los tramos fijos en alcance.py:8 y personas/views.py:51 podrían pasar a catálogos.

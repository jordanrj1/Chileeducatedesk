# territorio

## Resumen
Revisé el código y reproduje los casos con el cliente de pruebas, dentro de transacciones que se deshicieron. No quedaron filas guardadas; solo avanzaron las secuencias de ids de PostgreSQL. La base de desarrollo tiene 1 región («Región Demo», código 99), 1 provincia, 1 comuna, 0 sectores, 0 territorios de actividad y un proyecto con zona = «Comuna Demo». Por eso /territorio muestra «un solo territorio»: falta el archivo oficial CUT (docs/CONTEXTO.md §0.5 y §7.1), y la pantalla no lo dice porque el aviso solo aparece cuando no hay ninguna región (templates/territorio/indice.html:20-21).

«+ Crear sector» sí funciona cuando hay comuna. Con htmx 2.0.4, un POST incluye siempre el formulario completo, así que el sector se crea y queda elegido en lugar, organización y dirección de persona. El problema es de diseño:
- el botón está activo antes de elegir la comuna;
- el mismo mensaje «Elige la comuna y escribe el nombre del sector» sale en dos casos distintos, y con el nombre vacío además se pierde el sector que ya estaba elegido;
- Enter en ese campo envía todo el formulario y el nombre escrito se descarta sin aviso;
- `hx-include="[name$='comuna']"` es un selector de toda la página y sobra, y el servidor adivina la comuna tomando «la primera clave que termina en comuna»;
- la Comunidad y el territorio de la actividad no tienen cascada ni «crear sector».

El territorio de la actividad es una página aparte con 4 listas planas. Rechaza la elección natural en cascada (región + comuna da «Elige exactamente un nivel territorial») y acepta la misma comuna dos veces. Los filtros por zona del listado, del buscador y del calendario no incluyen las actividades dirigidas a un sector de la comuna; la ficha de la comuna sí las incluye. Proyecto.zona es texto libre y el buscador lo compara como texto.

Propuestas:
1. Un componente único de ubicación en cascada (`UbicacionMixin` + `_ubicacion.html` + un endpoint que vuelve a dibujar el bloque). La provincia es opcional y la región filtra comunas directamente. «Crear sector» queda deshabilitado con explicación hasta elegir comuna, recibe la comuna explícita y conserva lo elegido. Con modo «destino», actividad y proyecto guardan solo el nivel más fino. En el formulario de lugar, un panel «En Hualpén ya hay…» muestra sectores, comunidades, lugares y organizaciones de esa comuna.
2. Tabla ProyectoTerritorio (misma forma que ActividadTerritorio, con una base abstracta común). Se conserva el texto de `zona` como «texto anterior» y se vincula de forma automática e idempotente solo cuando hay una coincidencia única.
3. Bloque «Qué reúne este territorio y de dónde sale» en la ficha de comuna y sector, con qué se crea, edita o desactiva. Sector con `activo` e historial [V].
4. Un CSV CUT guardado en el repositorio + un cargador común con ceros a la izquierda y validación de jerarquía y totales (16/56/346) + `cargar_territorio` con archivo por defecto y `--si-falta`/`--simular`. Recomiendo el comando y no una migración de datos. La Región Demo (99/990/99001) no choca con los códigos oficiales (01–16) y nunca se borra.

## Hallazgos

### «+ Crear sector»: reproducción en cada formulario
- Evidencia: templates/territorio/_direccion.html:8-18 (bloque solo si perms.territorio.add_sector; botón :15 con hx-include="closest .crear-sector, [name$='comuna']" y hx-target=#{{campo.id_for_label}}); apps/territorio/views.py:472-508 (SectorCrearRapido; :482 comuna_id = primera clave del POST que termina en 'comuna'); static/vendor/htmx/htmx.min.js versión 2.0.4, función cn(): if(t!=="get"){on(...g(e,"form")...)} → en un POST siempre incluye el formulario que lo contiene. Reproducción (cliente de pruebas, transacción deshecha): /lugares/nuevo y /organizaciones/nueva → select name=dir-comuna, target id_dir-sector; /personas/<id>/direcciones/nuevo → name=comuna, target id_sector; /comunidades/nueva y /actividades/<id>/territorios/nuevo → NO tienen «+ Crear sector». POST con comuna → 200 «Sector «Villa Ficticia Uno» creado y seleccionado» (option selected). POST sin comuna → «Elige la comuna y escribe el nombre del sector.» POST con comuna, sin nombre y con un sector ya elegido → el mismo mensaje y la lista vuelve sin ningún sector seleccionado. Organización con comuna_municipal y la dirección sin comuna → «Elige la comuna…» (correcto: comuna_municipal no termina en 'comuna'). Después de crear el sector, guardar el lugar → 302.
- Hoy: Cuando hay comuna, el endpoint funciona en lugar, organización y dirección de persona. `[name$='comuna']` es un selector de toda la página y no hace falta, porque htmx ya manda el formulario. El aviso usa un id fijo `aviso-sector` (_direccion.html:17 y views.py:507). Comunidad y territorio de la actividad no ofrecen crear sector.
- Problema: La casilla «¿No está? Escribe el sector» y el botón están activos antes de elegir comuna. Si Claudio pulsa, recibe un rechazo que no dice qué falta. Si la comuna ya estaba elegida pero el nombre quedó vacío, el mensaje le pide «elegir la comuna» igual y además pierde el sector que tenía elegido. Así parece que el sistema ofrece crear y después lo impide.
- Propuesta: En SectorCrearRapido:
- leer la comuna de un parámetro explícito `comuna` enviado con hx-vals desde el bloque (mantener por compatibilidad la lectura de `*comuna`);
- separar los mensajes: «Primero elige la comuna: cada sector pertenece a una comuna» y «Escribe el nombre del sector nuevo»;
- ante un error, devolver la lista con el sector que venía en `<prefijo>-sector` todavía seleccionado;
- usar un id de aviso por prefijo (`aviso-sector-dir`).

En la plantilla: quitar `[name$='comuna']` y mostrar el bloque deshabilitado, con la explicación, mientras no haya comuna (lo dibuja el servidor; ver el componente en la propuesta 1).

### Enter en «¿No está? Escribe el sector» guarda el formulario y descarta el nombre
- Evidencia: templates/territorio/_direccion.html:11 (el input nuevo_sector_nombre está dentro del <form> principal de generico/formulario.html:15); apps/nucleo/direccion_mixin.py:30-44 (el post no lee nuevo_sector_nombre); static/js/fche.js:117-126 (el único manejador de keydown es el atajo del buscador).
- Hoy: Si Claudio escribe el sector y pulsa Enter, se envía todo el lugar, la organización o la dirección, sin sector. El nombre escrito se ignora sin ningún aviso.
- Problema: Cree que creó el sector y la dirección queda sin él.
- Propuesta: En el componente nuevo, dar al input `data-enter-dispara="#btn-crear-sector-<prefijo>"` y agregar a static/js/fche.js un manejador que haga preventDefault y llame a click(). Si al guardar viene `nuevo_sector_nombre` con texto y no hay sector elegido, DireccionForm.clean() lo informa: «Escribiste un sector nuevo pero no lo creaste: pulsa «Crear sector» o borra el texto».

### La cascada de la dirección está incompleta: región no filtra comunas y nada se reinicia
- Evidencia: apps/territorio/forms.py:87-89 (región → solo provincias; provincia → comunas; comuna → sectores); apps/territorio/views.py:453-459 (ComunasOpciones solo filtra por provincia; sin provincia devuelve todas); forms.py:81-84 (sin provincia la lista de comunas trae todas); views.py:38-39 (_valor toma el primer valor numérico del GET, sin nombre).
- Hoy: Si Claudio elige la región y salta la provincia, sigue viendo todas las comunas (serán 346 con el CUT). Cambiar región o provincia no limpia la comuna ni la lista de sectores, que puede quedar con los de otra comuna; el error aparece recién al guardar («El sector debe pertenecer a la comuna…»).
- Problema: Más clics y listas largas. La provincia actúa como un paso obligatorio que nadie usa en el día a día («es en Hualpén»).
- Propuesta: Lo resuelve el componente de la propuesta 1:
- la región filtra las comunas directamente;
- la provincia es opcional y queda plegada en «Filtrar por provincia»;
- cada cambio de región, provincia o comuna vuelve a dibujar el bloque completo en el servidor (`hx-get=/territorio/ubicacion`, `hx-target=closest .fche-ubicacion`, `hx-swap=outerHTML`), así una elección incoherente nunca queda en pantalla.

Opcional [P]: `REGION_POR_DEFECTO` en .env para que la cascada parta en la región de trabajo, y dentro de la lista de comunas un grupo «Donde trabajamos» primero (presencia_por_comuna, apps/territorio/resumen.py:168).

### Propuesta (1): componente reutilizable de ubicación en cascada
- Evidencia: Hoy hay cuatro implementaciones distintas:
- DireccionForm (apps/territorio/forms.py:51-96), con cascada;
- ComunidadForm (apps/comunidades/forms.py:25,37-39): comuna plana y sector plano de TODAS las comunas («nombre (comuna)»);
- TerritorioForm (apps/actividades/forms.py:275-291): 4 listas planas;
- Proyecto.zona (apps/proyectos/models.py:22): texto libre.
- Hoy: Cada formulario resuelve la ubicación a su manera. Solo la dirección tiene cascada y crear sector.
- Problema: La misma decisión («es en Hualpén, villa X») se toma de formas distintas según la pantalla. En comunidad y actividad hay que recorrer listas largas.
- Propuesta: Archivos nuevos:
- `apps/territorio/ubicacion.py` con `UbicacionMixin` para formularios. Agrega `region`, `provincia` (opcional, plegada), `comuna` y `sector` como campos y arma sus listas desde los datos enviados, la instancia o `initial` (sale de DireccionForm.__init__, forms.py:64-89). Atributos:
  - `ubicacion_modo`: 'direccion' o 'comunidad' (comuna obligatoria, guarda comuna y sector) o 'destino' (región mínima, guarda solo el nivel más fino, compatible con la restricción de un solo nivel);
  - `ubicacion_crear_sector=True`;
  - `ubicacion_contexto`: None o 'lugar'.
  - `clean_ubicacion()` valida la coherencia: la comuna pertenece a la región o provincia y el sector a la comuna.
- `templates/territorio/_ubicacion.html`:
  - una fila con Región | Comuna | Sector;
  - debajo del sector, un `<details>` «¿No está? Crear sector en {{comuna}}» (input, tipo, «dentro de» opcional y botón con hx-vals {comuna, prefijo});
  - sin comuna: el sector queda `disabled` y el texto dice «Elige la comuna para ver o crear sus sectores».
- Vista `UbicacionBloque` en `GET /territorio/ubicacion?prefijo=&modo=&contexto=`: dibuja el bloque. SectorCrearRapido, si recibe `formato=bloque`, devuelve el bloque con el sector nuevo elegido y el mensaje.

Uso:
- DireccionForm hereda el mixin y `_direccion.html` incluye `_ubicacion.html`;
- ComunidadForm usa modo 'comunidad';
- TerritorioForm y el formulario nuevo ProyectoTerritorioForm usan modo 'destino'.

Mantener las rutas /territorio/provincias, /comunas y /sectores, que tienen pruebas.

### Territorio de la actividad: poco visible, formulario plano y contradictorio
- Evidencia: templates/actividades/pestanas/info.html:10-12 («Zona de la actividad» + enlace «+ Territorio» a otra página); apps/actividades/forms.py:275-291 (help «Elige un único nivel»; clean exige un solo nivel); apps/actividades/models.py:102-125 (CheckConstraint de un nivel; sin unicidad); apps/actividades/forms.py:27-37 (ActividadForm no tiene zona). Reproducción: POST región+provincia+comuna → 200 «Elige exactamente un nivel territorial»; misma comuna dos veces → 2 filas.
- Hoy: La zona solo se agrega desde una página aparte, con listas planas de región, provincia, todas las comunas y todos los sectores. Una elección en cascada (región y comuna) se rechaza. La zona tampoco se puede indicar al crear la actividad, salvo que se llegue con ?comuna (apps/actividades/views.py:171-176).
- Problema: En /actividades/<id> no ve una zona que se elija con pocos clics. Cuando lo intenta como haría en una dirección, el sistema se lo rechaza.
- Propuesta: - En la pestaña Información, reemplazar el enlace por un formulario en línea (htmx) con `_ubicacion.html` en modo 'destino' y el botón «Agregar zona». Se guarda el nivel más fino elegido.
- Agregar una sección «Dónde» a ActividadForm con el mismo componente (campos que no son del modelo); ActividadNueva y ActividadEditar crean o activan la fila de ActividadTerritorio.
- En el formulario, una zona repetida reactiva la existente en vez de duplicarla, y cuatro UniqueConstraint condicionales (actividad + nivel, por cada nivel) lo aseguran en la base.
- En la cabecera (templates/actividades/ficha.html:10-14), una píldora «Zona: Hualpén › Villa X» que lleva a la ficha del territorio.

### Filtros «zona» inconsistentes con la ficha de comuna
- Evidencia: apps/actividades/views.py:45-48 (_filtro_comuna) y :829-831 (calendario); apps/nucleo/busqueda.py:98 — solo `territorios__comuna_id`. apps/territorio/consultas.py:22-34 (actividades_de) incluye `territorios__sector__comuna`. Reproducción: una actividad dirigida solo a un sector de la comuna aparece en la pestaña Actividades de la comuna (True), pero no en /actividades?comuna= (False) ni en /buscar?tipo=actividad&zona= (False).
- Hoy: Hay tres consultas distintas para responder «qué hay en esta comuna».
- Problema: El listado, el calendario y la ficha de la comuna dan números distintos para la misma comuna.
- Propuesta: Centralizar en `apps/territorio/consultas.py`: `filtro_actividades_en(comuna)` devuelve el Q que ya usa actividades_de; lo usan _filtro_comuna, busqueda._actividades y el calendario (versión sobre AgendaActividad con el prefijo `actividad__`). Agregar una prueba con una actividad dirigida a un sector.

### Propuesta (2): Proyecto.zona en texto libre
- Evidencia: apps/proyectos/models.py:22; apps/proyectos/forms.py:22,29; apps/proyectos/views.py:23,25 (búsqueda y columna «Zona»); templates/proyectos/ficha.html:8; templates/proyectos/pestanas/resumen.html:5; apps/nucleo/busqueda.py:75,80-83 (filtro por zona = icontains del nombre de la comuna); apps/nucleo/management/commands/cargar_demo.py:55 (zona="Comuna Demo"). En la base de desarrollo: 1 proyecto con zona «Comuna Demo».
- Hoy: Claudio escribe la zona a mano. «Hualpen», «Hualpén» y «Hualpén, San Pedro» quedan como textos distintos. Filtrar proyectos por comuna depende de coincidencias de texto, y la ficha de la comuna no muestra proyectos.
- Problema: No tiene el desplegable región → comuna → sector que pide, y los proyectos no aparecen en el contenedor territorial.
- Propuesta: Modelo:
- `ProyectoTerritorio` con la misma forma que ActividadTerritorio (heredan de una base abstracta `territorio.DestinoTerritorial`: region, provincia, comuna y sector con related_name '+', vigente, CheckConstraint de un nivel, `nivel`, `comuna_efectiva`). Es una relación N:M porque un proyecto puede abarcar varias comunas.
- Conservar la columna `zona`, sin renombrarla para no tocar HistoricalProyecto. Cambiar su verbose_name a «zona (texto anterior)» y sacarla de ProyectoForm.

Migración y vinculación:
- Migración 0003: CreateModel.
- Migración 0004: RunPython que divide `zona` por , ; / « y ». Cada parte se busca sin tildes ni mayúsculas entre las comunas, y luego entre sectores y nombres alternativos con `reconocer.normalizar`. Solo se vincula una coincidencia ÚNICA; el texto nunca se borra. Al revertir, no hace nada.
- Comando idempotente `vincular_zonas_proyectos [--simular]` para repetirlo después de cargar el CUT, porque en producción las migraciones corren antes que la carga del CUT.

Pantallas:
- Ficha del proyecto: «Zona del proyecto» con `urls_hijo("proyectos","territorios",...)` y el componente en modo 'destino'. Si queda texto sin vincular, «Zona anotada antes: «…» · Elegir territorio».
- ProyectoLista: la columna Zona usa los territorios (con prefetch).
- busqueda._proyectos filtra por `territorios__comuna`/`territorios__sector__comuna`, y por el texto anterior solo como respaldo.
- cargar_demo crea un ProyectoTerritorio.

### /territorio no explica cómo se alimenta ni avisa que falta la lista oficial
- Evidencia: templates/territorio/indice.html:9-21 (el aviso «El territorio aún no se ha cargado… cargar_territorio» solo aparece cuando no hay regiones); apps/territorio/urls.py:8-22 (no hay rutas para crear o editar región o comuna, por diseño); docs/Requerimientos_por_modulo_FCHE.md:13,69 (el Administrador carga el territorio oficial; el Gestor crea los sectores que falten); apps/cuentas/roles.py:19-29 (el Gestor recibe add/change de region/provincia/comuna sin que exista pantalla para usarlos).
- Hoy: Con la «Región Demo» cargada, el índice muestra 1 región y 1 comuna sin explicar que regiones, provincias y comunas vienen de una lista oficial que no se crea a mano.
- Problema: «Solo hay un territorio y no hay opción de crear otro». No sabe que lo que él crea son los sectores (villas, poblaciones, etapas) ni dónde se hace.
- Propuesta: - En indice.html, un aviso cuando hay menos de 346 comunas oficiales (código `^(0[1-9]|1[0-6])\d{3}$`): «Falta la lista oficial (16 regiones, 56 provincias, 346 comunas). Hoy hay N comuna(s), de demostración. La carga el Administrador con cargar_territorio».
- Un `<details>` «Cómo funciona el territorio»: lista oficial → sectores creados por el Gestor → qué se liga por dirección, comunidad o zona.
- Una línea «¿Falta una villa o población? Busca la comuna → pestaña Sectores → Crear sector».
- Pastilla «Demostración» para los códigos que no son oficiales (calculada, sin campo nuevo).
- [P] Quitar al Gestor add/change de region/provincia/comuna en roles.py.

### Propuesta (3): ficha de comuna o sector como explicación del contenedor
- Evidencia: apps/territorio/views.py:78-341 (_FichaTerritorio, ComunaFicha, SectorFicha); templates/territorio/ficha.html:5-26 (la cabecera no muestra el código CUT ni el origen; las acciones no incluyen «+ Sector»); templates/territorio/pestanas/sectores.html:14-21 (crear sector solo dentro de esa pestaña); templates/territorio/pestanas/resumen.html:93-114; apps/territorio/models.py:64-102 (Sector sin `activo` ni historial); templates/territorio/pestanas/nombres.html (un nombre alternativo no se puede quitar). Reproducción: la ficha de la comuna no tiene «Editar» ni «Desactivar»; la del sector tiene «Editar» pero no «Desactivar».
- Hoy: Los indicadores tienen una nota breve, pero no hay un lugar que diga de dónde sale cada número ni qué se puede crear, editar o desactivar. Un sector no se puede desactivar ni fusionar con otro, y sus cambios no quedan en el historial. Los proyectos no aparecen.
- Problema: No entiende cómo se ingresa, edita o actualiza el territorio, ni qué relaciones pasan por él.
- Propuesta: - Partial nuevo `templates/territorio/_como_se_nutre.html`, incluido plegado en Resumen y desplegado cuando el resumen está vacío. Es una tabla Qué | Cómo llega aquí | Dónde se crea o edita:
  - región, provincia y comuna = lista oficial CUT, no se editan;
  - sectores = los crea el Gestor (pestaña Sectores o «Crear sector» en una dirección); se editan, se les agregan nombres alternativos y se desactivan [V];
  - personas = dirección de residencia vigente;
  - organizaciones = dirección o municipalidad;
  - lugares = dirección;
  - comunidades = su comuna y sector;
  - actividades = lugar programado o zona destino;
  - proyectos = su zona o sus actividades.
  - Pie: «Nada se borra: se desactiva».
- contexto_ficha (views.py:151-155) suma `codigo_cut` y `es_oficial`; la cabecera muestra «Código CUT 08112 · lista oficial» o, en un sector, «Sector creado por el Gestor · Villa · dentro de X».
- Acción «+ Sector» en la cabecera (permiso add_sector) que lleva a ?tab=sectores#crear.
- En la pestaña Sectores, cada fila con «Editar · Desactivar» y cuántas direcciones, comunidades y actividades usan ese sector.
- Pestaña «Proyectos» con `consultas.proyectos_de()` = zonas declaradas ∪ proyectos de las actividades del territorio.
- [V] Sector.activo + HistoricalRecords + «Fusionar sectores» (permiso fusionar_sector, del Administrador, como en personas y organizaciones; el nombre absorbido queda como nombre alternativo).

### /lugares/nuevo: al elegir la comuna no aparece su contexto
- Evidencia: apps/lugares/forms.py:11-19 (organizacion_propietaria = todas las organizaciones activas, sin filtro); apps/lugares/views.py:49-93 (ConDireccionMixin + ComunaInicialMixin); templates/lugares/formulario.html:4-7; apps/lugares/views.py:110,124 y templates/actividades/programar.html:15 (crear lugar rápido: comuna en lista plana y sin sector); apps/territorio/consultas.py:6-19 (lugares_de y organizaciones_de ya existen); Lugar no tiene relación con Comunidad (apps/lugares/models.py:11-23).
- Hoy: Al elegir Hualpén solo se cargan sus sectores. Ni las comunidades, ni los lugares o sedes ya registrados, ni las organizaciones de la comuna aparecen para elegir.
- Problema: Puede crear la misma sede dos veces. Tiene que buscar a la junta dueña en una lista de todas las organizaciones y no ve qué comunidades hay en ese sector.
- Propuesta: Componente con `ubicacion_contexto='lugar'`. Al elegir la comuna, bajo la cascada aparece un `<details open>` «En Hualpén ya hay: N lugares · N comunidades · N organizaciones», con tres listas:
- Lugares (consultas.lugares_de) agrupados por tipo, con enlace y el aviso «¿Es uno de estos? No lo crees de nuevo».
- Comunidades, cada una con el botón «Ubicar aquí»: pone el sector de la comunidad y, con hx-swap-oob, propone su `organizacion` como organización propietaria.
- La lista organizacion_propietaria se dibuja de nuevo (OOB) con un grupo «De Hualpén» primero (organizaciones_de) y «Otras» después.

Si falta el sector, se crea en línea. Si falta la organización, se usa el patrón de crear desde el contexto. LugarCrearRapido usa el mismo componente, con sector.

[V] Una relación Lugar→Comunidad no está en la sección 7: propongo no agregarla y deducir la relación a través del sector y la organización.

### Propuesta (4): carga de la lista oficial CUT
- Evidencia: apps/territorio/management/commands/cargar_territorio.py:13 (COLUMNAS), :20 (`archivo` obligatorio), :25 (utf-8-sig), :35-37 (update_or_create por código, solo .strip(): sin ceros a la izquierda ni validación de jerarquía o totales; nunca borra); apps/territorio/tests.py:65-77 (las pruebas esperan el CSV con esas 6 columnas, carga idempotente y CommandError si faltan columnas; códigos de prueba 98/981/98101); conftest.py:51-56 y apps/nucleo/management/commands/cargar_demo.py:39-41 (Prueba y Demo usan 99/990/99001-99003); docs/COMO_LEVANTAR.md:84-87, docs/entrega.md:9, README.md:21; models.py:9,28,42 (max_length 3/3/5).
- Hoy: El comando está listo pero no hay archivo. Un CUT exportado desde Excel pierde el cero inicial («1101» en vez de «01101»): con el código actual, una segunda carga con los ceros correctos crearía comunas duplicadas.
- Problema: Sin la lista oficial, la cascada no sirve en uso real y el índice parece estar «vacío de territorios».
- Propuesta: Archivos:
- `apps/territorio/datos/cut_2018.csv`, guardado en el repositorio (son datos públicos, sin datos personales). Cabecera = COLUMNAS, códigos con ceros ("08", "081", "08112"), 346 filas. [V] Debe salir del archivo oficial de SUBDERE que entregue o confirme el usuario; no se escribe de memoria.
- `apps/territorio/cut.py`:
  - `leer_cut(ruta)`: rellena con ceros a 2, 3 y 5 dígitos; valida que la comuna empiece con el código de su provincia y la provincia con el de su región; rechaza códigos repetidos.
  - `cargar_cut(filas, Region, Provincia, Comuna)`: recibe las clases para servir también en migraciones; informa nuevas, renombradas y sin cambio; avisa si los totales no son 16/56/346.

Comando:
- `archivo` pasa a ser opcional (nargs='?', por defecto el CSV del repositorio);
- `--simular` deshace la carga y muestra las diferencias;
- `--si-falta` no hace nada si ya hay 346 comunas oficiales.
- Llamarlo con `--si-falta` desde iniciar.bat e iniciar.sh después de migrate.

Por qué comando y no migración de datos: el CUT se actualiza sin crear migraciones nuevas, las pruebas siguen con su comuna ficticia y la carga queda como tarea del Administrador, como dicen los requerimientos.

La Región Demo no se rompe: 99/990/99001 están fuera del rango oficial y el cargador nunca borra. Las pruebas actuales siguen pasando (98/981/98101 ya tienen los dígitos completos). Pruebas nuevas: «8»→«08», una jerarquía incoherente da CommandError, el CSV del repositorio tiene 16/56/346 sin repetidos, y la Demo sobrevive a una carga.

### Listas de comuna planas en filtros y formularios
- Evidencia: apps/actividades/views.py:85 (Filtro comuna con opciones_modelo(Comuna)), :397 (programar: comunas=Comuna.objects.all()), :806 (calendario), :877 (candidatos); apps/lugares/views.py:34; apps/personas/views.py:86; apps/nucleo/vistas_busqueda.py:39; apps/comunidades/forms.py:37.
- Hoy: Hoy hay 1 comuna. Con el CUT cargado, cada filtro mostrará 346 opciones planas.
- Problema: Ruido visual y muchos clics para encontrar Hualpén.
- Propuesta: Un helper `territorio.opciones.comunas_agrupadas()` que devuelva optgroups «Donde trabajamos» (presencia_por_comuna) y «Todas, por región». Usarlo en opciones_modelo de los filtros y en los selects de calendario, buscador, programar y candidatos. Opcional: el buscador `fche-campo__buscar` que ya existe (templates/generico/_campo.html:8-12), con un endpoint de comunas por nombre sin tildes.

### Aviso de sectores parecidos con falsos positivos
- Evidencia: apps/territorio/reconocer.py:10 (UMBRAL_PARECIDO=0.45), :34-39 (TrigramSimilarity sobre el nombre crudo). Reproducción: «Villa Ficticia Tres» frente a «Villa Ficticia Uno» → «Hay sectores parecidos… pulsa «Crear igual»».
- Hoy: Las palabras de tipo (villa, población, sector) inflan la similitud entre nombres distintos.
- Problema: Un clic extra casi cada vez que crea una villa.
- Propuesta: Comparar `normalizar(nombre)` sin las palabras de tipo (villa, población, sector, etapa, barrio) o subir el umbral, y mostrar los parecidos como botones: «Usar «Villa Los Aromos»» / «Es otro: crear».

### Importación de planillas: la comuna se busca por nombre exacto
- Evidencia: apps/importaciones/procesar.py:124-127 (`nombre__iexact`), :146-147, :181-184, :292-293.
- Hoy: «Hualpen» o «Concepcion» sin tilde no coinciden con el nombre oficial y la dirección no se guarda.
- Problema: Con el CUT cargado, muchas filas darán «Comuna desconocida».
- Propuesta: Usar `nombre__unaccent__iexact`, aceptar también el código CUT y, para las que no coincidan, sugerir la comuna más parecida (pg_trgm) en la vista previa.

## Cambios de modelo
- **territorio.DestinoTerritorial (abstracto, nuevo)**: Base abstracta con region, provincia, comuna, sector (FK PROTECT, related_name '+'), vigente, CheckConstraint de un solo nivel, propiedades `nivel` y `comuna_efectiva`, y `clean()`. ActividadTerritorio pasa a heredar de ella manteniendo en su Meta el nombre de restricción `actividad_territorio_un_nivel`. | Migración: Ninguna para ActividadTerritorio si los campos y el nombre de la restricción no cambian. Verificar con `makemigrations --check`. | Riesgo: Bajo. Si se usa el nombre automático `%(class)s`, Django genera RemoveConstraint/AddConstraint.
- **actividades.ActividadTerritorio**: Cuatro UniqueConstraint condicionales: (actividad, region) con region no nula, y lo mismo para provincia, comuna y sector. En el formulario, una zona repetida reactiva la existente. | Migración: actividades/0008: AddConstraint ×4. Antes, un RunPython que desactive o agrupe duplicados (en desarrollo hay 0 filas). | Riesgo: Bajo. Fallaría solo si en producción ya hubiera duplicados.
- **proyectos.ProyectoTerritorio (nuevo)**: proyecto (FK PROTECT, related_name 'territorios') + campos de DestinoTerritorial + observaciones (opcional). Mismas unicidades condicionales que ActividadTerritorio. | Migración: proyectos/0003 CreateModel. proyectos/0004 RunPython que vincula `zona` solo cuando hay una coincidencia única (comuna sin tildes, o sector o nombre alternativo con reconocer.normalizar); al revertir no hace nada. Más el comando idempotente `vincular_zonas_proyectos [--simular]` para repetirlo después de cargar el CUT. | Riesgo: Medio. Amplía la sección 7 y Proyecto es [V#7], así que requiere aprobación. Un nombre ambiguo (p. ej. un sector «Centro» en varias comunas) no se vincula solo.
- **proyectos.Proyecto.zona**: Se conserva la columna, que pasa a verbose_name «zona (texto anterior)» con una ayuda que apunta a «Zona del proyecto». Se quita de ProyectoForm. Se muestra en la ficha solo si tiene texto sin vincular. | Migración: AlterField en Proyecto y HistoricalProyecto (solo etiquetas). Sin pérdida de datos. | Riesgo: Bajo. No se renombra, para no tocar el historial.
- **territorio.Sector**: [V] `activo` BooleanField(default=True) + `history = HistoricalRecords()`. Los desactivados no aparecen en la cascada pero siguen en los registros existentes. Permiso `fusionar_sector`. | Migración: territorio/0004: AddField activo + CreateModel HistoricalSector. | Riesgo: Bajo. Hay que filtrar `activo=True` en SectoresOpciones, en el componente y en reconocer.sectores_parecidos (pero no en mismo_sector, que debe reconocer también los desactivados).
- **territorio.Region / Provincia / Comuna**: Sin cambio de esquema. Los datos vienen de apps/territorio/datos/cut_2018.csv mediante apps/territorio/cut.py y cargar_territorio. El carácter oficial se calcula por el código (01–16), sin campo nuevo. | Migración: Ninguna. Se carga con el comando (`--si-falta` en iniciar.bat/.sh). Alternativa descartada: una migración de datos (congela la versión del CUT y mete 346 comunas en cada base de pruebas). | Riesgo: Bajo. El código actual no rellena con ceros: rellenarlos antes de la primera carga real evita duplicados.

## Archivos
- apps/territorio/ubicacion.py (nuevo: UbicacionMixin)
- templates/territorio/_ubicacion.html (nuevo)
- templates/territorio/_direccion.html
- templates/territorio/_como_se_nutre.html (nuevo)
- templates/territorio/_contexto_lugar.html (nuevo: panel «En Hualpén ya hay…»)
- apps/territorio/forms.py
- apps/territorio/views.py (UbicacionBloque, SectorCrearRapido, ComunasOpciones con region, contexto_ficha, pestaña Proyectos)
- apps/territorio/urls.py (territorio/ubicacion)
- apps/territorio/models.py (DestinoTerritorial; Sector.activo e historial [V])
- apps/territorio/consultas.py (filtro_actividades_en, proyectos_de)
- apps/territorio/reconocer.py
- apps/territorio/cut.py (nuevo)
- apps/territorio/datos/cut_2018.csv (nuevo, del archivo oficial)
- apps/territorio/management/commands/cargar_territorio.py
- apps/territorio/management/commands/vincular_zonas_proyectos.py (nuevo)
- templates/territorio/indice.html
- templates/territorio/ficha.html
- templates/territorio/pestanas/resumen.html
- templates/territorio/pestanas/sectores.html
- templates/territorio/pestanas/proyectos.html (nuevo)
- apps/actividades/models.py
- apps/actividades/forms.py (TerritorioForm, ActividadForm sección «Dónde»)
- apps/actividades/views.py (_filtro_comuna, calendario, ctx_info, ActividadNueva/Editar)
- templates/actividades/pestanas/info.html
- templates/actividades/ficha.html
- apps/proyectos/models.py
- apps/proyectos/forms.py
- apps/proyectos/views.py
- apps/proyectos/urls.py
- templates/proyectos/ficha.html
- templates/proyectos/pestanas/resumen.html
- apps/comunidades/forms.py
- apps/lugares/forms.py
- apps/lugares/views.py (LugarCrearRapido)
- templates/actividades/programar.html
- apps/nucleo/busqueda.py
- apps/nucleo/direccion_mixin.py
- apps/nucleo/management/commands/cargar_demo.py
- apps/importaciones/procesar.py
- apps/cuentas/roles.py ([P] quitar al Gestor add/change de region/provincia/comuna)
- static/js/fche.js (Enter en crear sector)
- static/css/fche.css (.fche-ubicacion)
- iniciar.bat
- iniciar.sh
- docs/COMO_LEVANTAR.md
- docs/entrega.md
- README.md
- docs/manual_de_uso.md
- specs/f24-ubicacion/spec.md, plan.md, tasks.md (nueva feature, primero la spec)
- specs/trazabilidad_requerimientos.md (TE-06 carga oficial, AT-03)

## Pruebas afectadas
- apps/territorio/tests.py::test_crear_sector_sin_salir_del_formulario — envía `dir-comuna`. Mantener la lectura de compatibilidad o pasar a `comuna`; las aserciones de «creado y seleccionado», «Ya existía» y «Crear igual» siguen valiendo.
- apps/territorio/tests.py::test_crear_sector_rapido_exige_comuna_y_permiso — busca el texto «Elige la comuna». El mensaje nuevo debe conservar esa frase o hay que actualizar la prueba.
- apps/territorio/tests.py::test_formularios_de_direccion_muestran_crear_sector — exige «+ Crear sector», «Región» y «Provincia» en el HTML. Si la provincia queda plegada, la etiqueta sigue estando; si cambia el texto del botón, actualizar la prueba.
- apps/territorio/tests.py::test_cascada_de_opciones y test_opciones_de_sector_por_comuna — las rutas /territorio/provincias, /comunas y /sectores deben seguir existiendo.
- apps/territorio/tests.py::test_formulario_de_direccion_con_cascada — depende de initial['region'] e initial['provincia'] y del error «comuna» cuando la provincia no corresponde.
- apps/territorio/tests.py::test_comando_cargar_territorio y test_comando_falla_con_columnas_faltantes — siguen pasando si se mantiene el contrato del CSV (el argumento pasa a ser opcional).
- apps/actividades/tests.py::test_territorio_de_la_actividad_un_solo_nivel (línea 430) — hoy espera que región+comuna se rechacen. Con el modo 'destino', una combinación coherente guarda la comuna: cambiar la prueba para que exija rechazo solo si es incoherente y que se guarde el nivel más fino.
- apps/actividades/tests.py::test_calendario_filtra_por_zona_responsable_y_organizacion (línea 620) — debería seguir pasando al centralizar el filtro.
- apps/nucleo/test_busqueda.py (fixture `mundo`, línea 20: Proyecto(zona='Comuna Ficticia')) — si el filtro de proyectos pasa a usar territorios, crear ProyectoTerritorio en la fixture o mantener el respaldo por texto.
- apps/nucleo/test_f22.py:129,147 — POST /comunidades/nueva con `comuna`/`sector`: mantener esos nombres sin prefijo en ComunidadForm.
- apps/territorio/test_contexto.py:53,90,191; apps/organizaciones/tests.py:26; apps/nucleo/test_escenarios_catalogo.py:97,390 — usan `dir-comuna`/`dir-sector`: mantener el prefijo 'dir'.
- apps/nucleo/test_escenarios.py:243 — GET /actividades/<id>/territorios/nuevo debe seguir respondiendo.
- apps/nucleo/test_comandos.py::test_cargar_demo_* — si cargar_demo crea ProyectoTerritorio, revisar que no se rompa la carga idempotente ni --ampliar.
- apps/territorio/test_indice.py (p. ej. test_indice_busqueda_de_comuna_se_mantiene, test_indice_vacio_ofrece_acciones) — el aviso nuevo de «falta la lista oficial» aparecerá con la región ficticia 99. No debe contener «Todas las regiones» ni romper las aserciones de presencia ni el tope de consultas.

## Decisiones abiertas
- [V] Archivo oficial CUT: el usuario debe entregar o confirmar la fuente (SUBDERE, CUT 2018 con Ñuble: 16/56/346) y autorizar que el CSV quede en el repositorio (son datos públicos).
- [P] Cargar el CUT con el comando (`--si-falta` en iniciar.bat/.sh), que es lo recomendado, o con una migración de datos que deja las 346 comunas también en las bases de prueba.
- [V] Aprobar ProyectoTerritorio, que amplía la sección 7; Proyecto es [V#7]. Alternativa: una sola FK de comuna en Proyecto (más simple, pero un proyecto no podría abarcar varias comunas).
- [V] Agregar Sector.activo + historial y la acción «Fusionar sectores» (¿la hace el Gestor o solo el Administrador?). ¿Se puede quitar un nombre alternativo?
- [V] En el lugar, ¿basta con deducir la comunidad por sector y organización, o Claudio necesita una relación Lugar→Comunidad (campo fuera de la sección 7)?
- [P] Provincia plegada y opcional en la cascada (docs/CONTEXTO.md §7.1 ya la deduce de la comuna).
- [P] `REGION_POR_DEFECTO` en .env y grupo «Donde trabajamos» primero en las listas de comunas.
- [P] Quitar al Gestor los permisos add/change de region/provincia/comuna (son datos oficiales sin pantalla).
- [V] ¿Una actividad dirigida a una región o provincia debe aparecer en la ficha de cada comuna que contiene? Hoy no aparece.
- [P] ¿La zona se indica también en el formulario de nueva actividad o de nuevo proyecto (sección «Dónde»), o solo en la ficha?
- Por regla de docs/CONTEXTO.md, todo esto va como feature nueva (p. ej. F24 Ubicación en cascada) con spec antes del código.

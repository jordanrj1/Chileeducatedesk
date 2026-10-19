# F24 — Cascada, buscadores y fichas por tipo

**Fuente:** comentarios del usuario del 14-10-2026, pantalla por pantalla:
- `/solicitudes/nueva`, `/proyectos/nuevo`, `/actividades/<id>`, `/comunidades/nueva`, `/organizaciones/nueva`, `/lugares/nuevo`, `/territorio`, `/personas` y `/personas/nueva?modo=completa`.

**Análisis previo** (solo lectura, con reproducciones): `specs/f24/analisis/`.

**Reemplaza** la F24 de `docs/rediseno_integral.md`. El usuario pidió **tablas relacionales normalizadas, no campos libres**, así que se descarta `CampoPersonalizado` + `datos_extra` JSONB.

## Qué y por qué

Claudio abre un formulario y:
- no ve a nadie en los desplegables de persona, organización o responsable: solo «---------»;
- no puede elegir región, comuna y sector con clics;
- ve listas largas de casillas y diez filtros a la vista;
- no entiende algunos campos («Naturaleza jurídica», «Domicilio legal»);
- en Territorio ve una sola comuna de demostración.

F24 hace que **todo se elija con clics, en cascada o con desplegables con buscador**, que se pueda **crear en el momento** lo que falta, y que los datos queden en **tablas relacionadas**.

**Etiquetas:** [P] propuesta de diseño, [V] por validar.

---

## Parte A — Se construye ahora

### A1. Buscadores que muestran a los registrados
Hoy: `SelectorField` + `_IteradorLimitado` dibujan solo la opción vacía. La búsqueda es un segundo cuadro que consulta al servidor solo al escribir.

1. **Un solo control** (patrón «combobox» accesible) por cada uno de los 37 campos de búsqueda.
   - Al hacer **clic o enfocar** despliega ya las primeras 25 opciones ordenadas, con el pie «Mostrando 25 de N. Escribe para filtrar».
   - Al **escribir** filtra (espera de 250 ms; gana la última búsqueda).
   - Se usa con teclado: ↑, ↓, Enter, Esc.
   - El `<select>` real sigue oculto y es lo que se envía.
   - **Sin JavaScript** el `<select>` muestra las primeras 25 opciones más el valor actual.
2. **«+ Crear persona “texto”»** y **«+ Crear organización “texto”»** al final de la lista.
   - Abren una ventana (modal de Bootstrap local) con lo mínimo:
     - persona: nombres, apellidos y un contacto opcional;
     - organización: nombre y tipo.
   - Mantienen el **aviso de duplicados** (`personas/duplicados.candidatos`, `organizaciones_parecidas`), con «Usar existente» o «Crear de todos modos».
   - Al crear, el registro queda **seleccionado** sin salir del formulario. Cumple HU-DA-04.
3. **Defectos que se corrigen:**
   - buscar ya no borra el valor elegido;
   - un vínculo desactivado se muestra como «(desactivada)» y no se pierde al guardar;
   - un valor no numérico no provoca un error 500;
   - lo que se ofrece es lo mismo que se valida, con una «fuente» por tipo de registro;
   - sin consultas en bucle (N+1) en las opciones de organizaciones.
4. **Responsable** [P]:
   - el selector muestra primero un grupo **«Equipo de la Fundación»**: personas con vínculo vigente con la organización marcada «es la Fundación», más las personas con cuenta;
   - debajo, el resto;
   - la ayuda dice dónde se registra el equipo (Organizaciones → la Fundación → Personas relacionadas);
   - limitar el responsable solo al equipo es [V] y queda detrás de `RESPONSABLE_SOLO_EQUIPO=False`.
5. **Cómo quedó (T2)** [P]:
   - una «fuente» por tipo de registro (`apps/<app>/selector.py`) sirve para listar y para validar; `apps/nucleo/selector.py` arma la lista con `format_html`;
   - personas en el orden en que se leen (nombre y apellidos), con el RUT o «sin RUT» y el cargo vigente como detalle, igual que antes;
   - organizaciones con tipo y comuna; actividades con estado y fecha, las más recientes primero;
   - si el valor elegido no está entre las primeras 25, se muestra arriba y el pie lo cuenta («Mostrando 26 de N»);
   - «+ Crear persona» exige escribir qué la distingue si hay una parecida, igual que en Personas → Nueva; la organización creada así queda «incompleta» (le faltan dirección y contacto);
   - con `RESPONSABLE_SOLO_EQUIPO=True` el responsable no ofrece «+ Crear» (una persona nueva no sería del equipo);
   - el formulario de cuenta usa el mismo buscador (personas sin cuenta) en vez de su cuadro aparte.

### A2. Selección múltiple desplegable
Afecta a todo campo de selección múltiple que hoy son casillas a la vista (áreas de interés, perfiles…).
- Se convierte en un **botón que despliega la lista con buscador**.
- Lo elegido se muestra como **etiquetas**, cada una con una × para quitarla.
- **Sin JavaScript** siguen siendo casillas nativas, dentro de un bloque plegable (`<details>`).
- **Cómo quedó (T3)** [P]:
  - `BootstrapMixin` cambia **toda** selección múltiple (casillas o lista) por `SelectorMultiple`, sin umbral de cantidad de opciones; también la lista «Actividades a reasignar», que muestra lo marcado como etiquetas;
  - el botón dice «Elegir…» o «3 opciones elegidas»; sin JavaScript agrega los nombres («2 opciones elegidas: Salud y Deporte»);
  - con JavaScript la lista flota como la del buscador de T2, con un cuadro para filtrar sin tildes ni mayúsculas; ↑ y ↓ recorren, Enter marca o desmarca sin enviar el formulario, Esc o un clic fuera cierran;
  - lo que se envía no cambia (`perfiles=3&perfiles=7`); escribir en el cuadro para filtrar no cuenta como cambio sin guardar;
  - la pantalla de permisos de un rol (Administración) sigue con sus casillas: no es un campo de formulario.

### A3. Filtros con menos ruido
Afecta a los 14 listados que usan `ListaBase`.
- `Filtro` gana:
  - `principal` (se ve siempre);
  - `grupo` (subtítulo dentro de «Más filtros»);
  - `todos` (el texto de la opción vacía, con su género: «Todas»);
  - `oculto` (funciona por la dirección pero no se dibuja);
  - el tipo `casilla`.
- La barra muestra:
  - el **buscador** y **2 o 3 filtros principales**;
  - un **«Más filtros (n)»** plegable que funciona sin JavaScript;
  - una línea con **cuántos resultados**, los **filtros aplicados como etiquetas con ×** y **«Limpiar»**, que conserva el orden.
- Los nombres de los parámetros de la dirección no cambian. «← Volver» sigue conservando los filtros.
- **Correcciones:**
  - Personas recupera su buscador;
  - «Estado: todos» aparece una sola vez;
  - los filtros de una sola opción pasan a casilla;
  - Tareas deja de pedir el «id» del responsable;
  - si un filtro tiene más de 300 organizaciones, lo avisa.
- **Filtros principales por listado:** la lista exacta está en `analisis/listados.md`. En Personas son Perfil, Comuna y Comunidad.
- **Cómo quedó (T4):**
  - `?activo=` vacío vale lo predeterminado (activos); «Todos» (`*`) se ve como filtro aplicado;
  - Comuna y Organización ofrecen solo los valores con registros, agrupados por región o por tipo; si se llega con un valor que no está en la lista (desde la ficha de una comuna), igual se muestra;
  - en Actividades, Institución queda dentro de Organización y `?institucion=` sigue funcionando sin dibujarse;
  - en Actividades se agrega el filtro «Cuándo» (`periodo`: próximas, esta semana, este mes, pasadas, sin programar) [P]; Desde y Hasta siguen en «Más filtros»;
  - con JavaScript, la dirección queda sin campos vacíos y «Más filtros» se cierra con Esc o un clic fuera; los filtros se aplican con «Filtrar», no al elegir;
  - el filtro por comuna de `/actividades`, `/calendario` y `/buscar` incluye las actividades dirigidas a sus sectores (y subsectores), igual que la ficha de la comuna (`territorio/consultas.py`).

### A4. Territorio oficial de Chile
- **Datos:**
  - `apps/territorio/datos/cut_chile.csv` con **16 regiones, 56 provincias y 346 comunas**;
  - códigos CUT de la SUBDERE (Decreto Exento 1.115 de 2018) y nombres del INE (Censo 2024);
  - ambas fuentes se compararon código por código: coinciden los 346 códigos y su región y provincia. Las 6 diferencias de escritura se resolvieron con el INE; la provincia queda como «Tamarugal»;
  - las fuentes quedan anotadas en `apps/territorio/datos/LEEME.md`.
- **Carga:**
  - `cargar_territorio` sin argumentos usa ese archivo;
  - antes de escribir revisa todo el archivo: columnas, ceros a la izquierda (un «8112» que dejó Excel se lee como «08112»), que cada comuna sea de su provincia y cada provincia de su región, códigos repetidos y, si el archivo trae códigos oficiales (regiones 01 a 16), los totales 16/56/346. Con cualquier error no carga nada;
  - acepta `--si-falta` (no hace nada si ya están todas las comunas del archivo; si falta alguna, la agrega sin duplicar) y `--simular` (muestra lo que cambiaría y no guarda);
  - no es una migración de datos, para no cambiar las pruebas;
  - `iniciar.bat` e `iniciar.sh` lo ejecutan con `--si-falta`; si falla, el sistema arranca igual;
  - la «Región Demo» (código 99) no choca con los códigos oficiales y nunca se borra.
- **Aviso en `/territorio`:** si faltan comunas oficiales (códigos de las regiones 01 a 16), lo dice aunque exista la Región Demo. Las regiones y comunas que no son oficiales llevan la pastilla «De demostración».
- **Sin servicios externos:** no se usa Google Maps ni ningún servicio de mapas. El sistema funciona sin internet (docs/CONTEXTO.md §15).
- **Sector:**
  - gana `activo` y un historial de cambios (migración aditiva), con la pestaña Historial en su ficha;
  - se crea, se edita y se **desactiva** (lo hace quien puede editar sectores, es decir, el Gestor); nunca se borra;
  - un sector desactivado deja de ofrecerse en las listas para elegir (dirección, comunidad, territorio de la actividad, «dentro de»), no recibe sectores nuevos dentro ni sirve de punto de partida para crear registros; lo registrado en él lo conserva, y al editar ese registro se ve como «(desactivado)»;
  - si alguien intenta crear un sector con el nombre de uno desactivado, el sistema lo avisa y no lo duplica.
- **`/territorio` y las fichas de comuna y sector** explican en un bloque breve:
  - **de dónde sale**: regiones y comunas de la lista oficial; sectores, villas, poblaciones y etapas que crea Claudio;
  - **qué reúne**: personas por su dirección, organizaciones y lugares por su dirección, comunidades, y actividades por su lugar o territorio;
  - **qué se puede hacer**: crear, editar y desactivar sectores y nombres alternativos.

### A5. Ubicación en cascada en todo formulario
- **Un solo componente:** `UbicacionMixin` + `territorio/_ubicacion.html` + un punto que vuelve a dibujar el bloque.
  - **Cascada:** región → comuna → sector. La provincia es opcional y la región filtra las comunas directamente.
  - **«+ Crear sector»:**
    - queda **deshabilitado, con la explicación «Primero elige la comuna»**, hasta que haya comuna;
    - recibe la comuna de forma explícita;
    - conserva lo ya elegido;
    - Enter no envía el formulario completo;
    - avisa si el nombre se parece a uno existente.
  - **Se usa en:** la dirección de persona, organización y lugar; la comunidad; el territorio de la actividad; y el del proyecto.
- **Formulario de lugar:** al elegir la comuna aparece el panel **«En Hualpén ya hay…»** con sus sectores, comunidades, lugares y organizaciones, para reutilizar en vez de duplicar.
- **Corrección:** una actividad dirigida a un **sector** aparece al filtrar por su **comuna** en el listado de actividades, el calendario y el buscador.
- **Cómo quedó (T5)** [P]:
  - `apps/territorio/ubicacion.py` (`UbicacionMixin`, `UbicacionForm`) + `territorio/_ubicacion.html` + `GET /territorio/ubicacion`, que vuelve a dibujar el bloque entero al cambiar región, provincia o comuna (la lista que cambió manda y lo que no calza se suelta);
  - la provincia va plegada en «Filtrar las comunas por provincia (opcional)»; al editar un registro con comuna se muestra abierta con su provincia, y la lista de comunas es la de esa provincia;
  - el sector queda deshabilitado («Primero elige la comuna») hasta elegir la comuna; solo ofrece sectores activos, salvo el que el registro ya tenía («(desactivado)»);
  - «+ Crear sector en Hualpén» va plegado bajo el sector, con nombre, tipo y «Dentro de» (opcional); manda la comuna explícita, responde el bloque con el sector nuevo elegido y el foco en la lista; ante un aviso conserva lo elegido y lo escrito, con mensajes distintos para «falta la comuna» y «falta el nombre». Enter en el nombre crea el sector (no envía el formulario); si se guarda con un nombre escrito y sin crearlo, el formulario lo avisa;
  - sin JavaScript, «Actualizar listas» vuelve a dibujar el formulario sin guardar ni marcar errores; el sector se crea en la ficha de la comuna (enlace en otra pestaña);
  - en `secciones`, el nombre «ubicacion» dibuja el bloque (`BloqueDeSeccion`); la comunidad lo usa en su sección Territorio;
  - el panel «En Hualpén ya hay…» muestra hasta 6 por grupo con enlaces (en otra pestaña), los totales y «Ver … en la ficha de la comuna», con un número fijo de consultas;
  - queda listo para varias filas (prefijo por fila, modo «destino» que guarda el nivel más fino con `ubicacion_elegida()`) y para la comunidad después del sector (`ubicacion_comunidad`);
  - la corrección del filtro por comuna (actividades, calendario y buscador) va con los filtros (T4).

### A6. Actividad y proyecto: «¿Dónde?» con pocos clics
- **Actividad (crear y editar):**
  - una sección **«¿Dónde se realiza o a quién va dirigida?»** con una o más filas de región → comuna → sector;
  - guarda el nivel más preciso en `ActividadTerritorio`;
  - no es obligatoria;
  - parte prellenada si se viene desde una comuna, un sector, una comunidad o una jornada.
- **Formulario de actividad por secciones:**
  - siempre a la vista: qué es (nombre, tipo, estado y modalidad), para qué y para quién, y dónde;
  - plegado: detalles (actividad padre, área temática, condiciones, proyecto);
  - cada campo tiene una ayuda breve con un ejemplo.
- **Proyecto:**
  - nueva tabla **`ProyectoTerritorio`** (misma forma que `ActividadTerritorio`, con base común) y la misma sección «¿Dónde?»;
  - el texto `zona` se conserva como «texto anterior»;
  - se vincula solo si coincide exactamente con una sola comuna o sector, y nunca se borra.

### A7. Tramos de edad catalogados
- **Catálogo nuevo `TramoEtario`:** nombre, edad mínima y edad máxima, orden y activo. Se edita desde Catálogos.
- **Valores iniciales** [P]:
  - Primera infancia (0–5);
  - Niñez (6–12);
  - Adolescencia (13–17);
  - Jóvenes (18–29);
  - Personas adultas (30–59);
  - Personas mayores (60 o más).
- **Selección múltiple** en Actividad (público) y en Comunidad (tramos predominantes).
- El texto libre actual (`rango_etario`) se conserva como «texto anterior», y un intérprete lo convierte cuando reconoce los números o palabras.
- Cómo quedó (T6):
  - el texto anterior se ve en la ficha como «Antes decía: «…» · Por revisar»; en el formulario aparece solo si tiene algo, y se revisa borrándolo (el historial lo conserva);
  - en Catálogos el tramo muestra sus edades y no acepta una edad máxima menor que la mínima;
  - duplicar una actividad copia sus tramos; fusionar comunidades los suma;
  - los informes de alcance siguen con sus cuatro tramos (0–17, 18–29, 30–59, 60 o más): los seis tramos caben dentro de ellos;
  - quedan para después: filtrar listados por tramo y registrar en el historial los cambios de tramos [P].

### A8. Formularios claros
- **Etiquetas y ayudas** en español simple, con ejemplo, en `Meta.labels` y `help_texts` de cada formulario (sin migraciones).
  - Se quitan los códigos internos de las ayudas («PE-E4», «F22», «DO-06»…).
  - Se corrigen las tildes («Región», «Organización»).
  - La tabla completa está en `analisis/formularios.md`.
- **Organización por secciones:**
  - Identificación;
  - Contacto y dirección;
  - **Datos legales**, plegada y con explicación:
    - **Naturaleza jurídica:** qué tipo de entidad es ante la ley;
    - **Domicilio legal:** el que figura en sus estatutos o certificado, si es distinto de donde funciona;
    - **vigencia** de la personalidad jurídica.
- **«Naturaleza jurídica» pasa a catálogo** [P]:
  - valores: organización comunitaria territorial (junta de vecinos), organización comunitaria funcional, corporación, fundación, sociedad o empresa, servicio público, establecimiento educacional, otra;
  - el texto actual se conserva como «texto anterior».
- **Secciones plegables:** `secciones` admite marcar una sección como plegada, para bajar el ruido.

---

## Parte B — Fichas por tipo de persona (decidido por el usuario el 14-10-2026)

**Lo que pidió el usuario:**
- al registrar a alguien, elegir si es:
  - **estudiante**: institución, casa matriz o sede, carrera, año…;
  - **vecino o vecina**: sexo, edad, número de casa, familiares, hijos, nietos…;
  - **invitado o invitada**;
  - **voluntario o voluntaria**;
  - u otra persona sin ficha especial;
- que cada tipo tenga **su propia tabla**;
- que el formulario cambie según el tipo.

**Decisiones del usuario:**
- **Tipos con ficha:** los cuatro (estudiante, vecino, invitado y voluntario).
- **Familia del vecino:** **ambas**:
  - conteos sin nombres por parentesco y tramo de edad;
  - **y** la opción de vincular a un familiar que ya esté registrado como persona.
- **Sexo:** **dato general opcional** de toda persona (mujer, hombre, otro, no informa). La identidad de género sigue en la sección restringida 🔒.
- **Hogar:** **restringido 🔒 sin consentimiento extra**:
  - lo ve quien puede ver la ficha de la persona;
  - el tramo del Registro Social de Hogares sigue siendo dato sensible, con permiso y consentimiento.

### B1. Modelo (migraciones aditivas)
- **`PerfilPersona.ficha`**: estudiante, vecino, invitado, voluntario o ninguna. Se edita en Catálogos, así que un perfil nuevo puede abrir una ficha existente.
  - Asignación inicial: estudiante → estudiante; vecino o vecina de la comunidad → vecino; voluntario o voluntaria → voluntario; perfil nuevo «Invitado o invitada» → invitado.
  - El resto, sin ficha [P].
- **`Persona.sexo`** (opcional) y **`Persona.fecha_nacimiento_aproximada`**: si solo se conoce la edad, se guarda el 1 de enero del año que corresponde, marcado como aproximado.
- **Estudiante:**
  - su tabla es **`PersonaFormacion`**, que ya existe (institución, carrera, estado, año de inicio, año que cursa, jornada);
  - gana **`sede_institucion`** → `Lugar` de esa institución, de tipo «Sede» o «Casa matriz» (valor nuevo del catálogo de tipos de lugar);
  - el texto `sede` actual se conserva como «texto anterior».
- **Vecino:** **`FichaVecino`** (1 a 0..1 con Persona; restringida 🔒):
  - jefatura de hogar e integrantes del hogar, copiados desde `PerfilSensible` (sus columnas se conservan sin uso);
  - **`IntegranteHogar`**: parentesco (catálogo nuevo **Parentesco**), tramo de edad (catálogo **TramoEtario** de A7), cantidad y si vive en el hogar. Sin nombres;
  - **`FamiliarVinculado`**: persona, familiar (otra persona registrada) y parentesco. No se repite, y nadie puede ser su propio familiar;
  - **dirección** (número de casa, comuna y sector) en `PersonaDireccion` de residencia, y **comunidad** en `ComunidadMiembro`. No se duplican.
- **Invitado:** **`FichaInvitado`**:
  - tipo (catálogo nuevo **TipoInvitado**: autoridad, expositor o expositora, invitado o invitada especial, prensa, aliado o patrocinador, otro);
  - invitado por (persona), organización de procedencia, cargo, motivo y actividad (opcional).
- **Voluntario:** **`FichaVoluntario`**:
  - estado (catálogo nuevo **EstadoVoluntario**: postulante, activo, en pausa, retirado);
  - fecha de ingreso y horas disponibles por semana;
  - motivación u observaciones;
  - la disponibilidad, la experiencia y el contacto de emergencia siguen en sus tablas actuales.
- Historial de cambios en las fichas nuevas.
- **Cómo quedó (T9)** [P]:
  - `PerfilPersona` es una clase con `ficha` (opción vacía «Sin ficha propia»); la lista de Catálogos muestra la columna «Ficha que abre». Beneficiario, dirigente y los demás quedan sin ficha;
  - la carga inicial solo crea por código lo que falta y solo asigna la ficha a un perfil que no tiene una: no pisa lo editado en Catálogos;
  - valores iniciales de Parentesco: hijo o hija, nieto o nieta, pareja, padre o madre, hermano o hermana, abuelo o abuela, otro familiar, sin parentesco;
  - `Persona.fijar_edad_aproximada(edad)` guarda el 1 de enero de (año actual − edad); si la fecha se borra, la marca «aproximada» se apaga sola;
  - la sede se valida con `PersonaFormacion.sedes_de(institución)`: lugar de esa institución y de tipo sede o casa matriz (lo mismo que se ofrecerá en el formulario). El texto `sede` sigue igual; su etiqueta «texto anterior» llega con el formulario (T10). La migración enlaza la sede escrita con el lugar de la institución que se llama igual (sin contar tildes, mayúsculas ni espacios de más), solo si hay exactamente uno y la formación aún no tiene sede; no crea lugares, porque un `Lugar` exige dirección y el texto no la trae;
  - `IntegranteHogar.tramo` es **opcional** («si no se sabe la edad»); no se repite la misma fila (parentesco, tramo y si vive en el hogar), tampoco «sin tramo», con dos restricciones parciales que funcionan en cualquier PostgreSQL. Cantidad ≥ 1;
  - `FamiliarVinculado` se lee «el familiar es <parentesco> de la persona»; una sola fila por par y nadie es su propio familiar (restricción en la base y en `clean()`);
  - `FichaInvitado`: tipo, invitado por, organización de procedencia, cargo (texto), motivo y actividad, todo opcional; quien invita no puede ser la misma persona;
  - `FichaVoluntario`: horas por semana hasta 168;
  - la copia del hogar desde `PerfilSensible` solo completa lo vacío y se puede repetir; las columnas antiguas siguen ahí, y la pestaña de datos sensibles las sigue escribiendo hasta que T10 las reemplace por la ficha del vecino;
  - al fusionar duplicados, la persona que queda completa el sexo si lo tiene vacío, y la fecha de nacimiento llega con su marca «aproximada». Las fichas por tipo se completan al fusionar en T11.

### B2. Formulario dinámico y ficha
- **Formulario:**
  - arriba, botones para marcar uno o varios tipos de registro (los perfiles con ficha);
  - debajo aparecen **solo** las secciones de esos tipos;
  - con JavaScript, sin recargar; sin JavaScript, un botón «Mostrar secciones» vuelve a dibujar el formulario sin guardar;
  - se guardan solo las secciones elegidas, en una transacción, y se mantiene el aviso de duplicados.
- **Cascadas dentro de las secciones:**
  - estudiante: institución → sede o casa matriz (con «+ Crear sede», que pide nombre y comuna) y carrera (con «+ Crear carrera»);
  - vecino: comuna → sector → comunidad (con crear en el momento);
  - hogar: filas de «cantidad · parentesco · tramo», y «vincular familiar» con el buscador de personas.
- **Ficha de la persona:**
  - cada tipo es una **tarjeta** en la pestaña Datos, con su resumen y «Editar»;
  - no se suman pestañas;
  - el hogar lleva 🔒.

### B3. Lo que hay que adaptar
- **Fusión de fichas repetidas:**
  - las fichas 1 a 1 se completan desde la otra ficha sin pisar lo que ya está;
  - los conteos y los vínculos familiares se mueven sin duplicar.
- **Exportación de datos personales:** una hoja por ficha.
- **Importación:** una columna opcional «tipo» o «perfil» asigna el perfil.
- **Crear desde la actividad:**
  - `RolParticipacion` gana `perfil`;
  - el rol asigna el perfil (estudiante → estudiante, voluntario → voluntario…).
- **Filtro de Personas por tipo:** usa el filtro de perfil que ya existe.

### Criterios de aceptación (Parte B)
1. En `/personas/nueva`, al marcar «Estudiante» aparece su sección. Al elegir la institución se ofrecen sus sedes y carreras, y se pueden crear en el momento. Al guardar queda la formación con la sede.
2. Al marcar «Vecino o vecina»:
   - se piden dirección con número de casa, comuna, sector y comunidad (en cascada), edad y sexo;
   - el hogar se registra con filas de conteo;
   - se puede vincular un familiar ya registrado;
   - todo queda en sus tablas.
3. «Invitado» y «Voluntario» guardan sus fichas. Una persona puede tener varios tipos a la vez.
4. Sin marcar ningún tipo, la persona se crea solo con sus datos básicos, como hoy. Las pruebas actuales de creación siguen pasando.
5. La ficha muestra una tarjeta por tipo. Fusión, exportación, importación y creación desde la actividad conocen las fichas nuevas.
6. Los datos del hogar no aparecen en resúmenes territoriales, exportaciones territoriales ni opciones del buscador.

---

## Criterios de aceptación (Parte A)
1. En `/solicitudes/nueva`, `/proyectos/nuevo` y `/actividades/<id>/editar`:
   - hacer clic en Persona, Organización, Responsable o Actividad padre despliega nombres registrados sin escribir nada;
   - escribir filtra;
   - «+ Crear…» crea y deja seleccionado sin salir del formulario.
2. Al editar, buscar sin elegir y guardar **no borra** el valor. Un vínculo desactivado se conserva.
3. Ningún campo de selección múltiple se ve como una lista larga de casillas: es un desplegable con buscador y etiquetas.
4. `/personas` muestra un buscador, 3 filtros principales y «Más filtros». Los filtros aplicados se ven como etiquetas con ×.
5. Tras `cargar_territorio`:
   - hay 16 regiones, 56 provincias y 346 comunas;
   - Hualpén es la comuna `08112` de Concepción, Región del Biobío;
   - ejecutarlo de nuevo no duplica nada.
6. En lugar, organización, dirección de persona, comunidad, actividad y proyecto se elige región → comuna → sector con clics. «+ Crear sector» explica que falta la comuna y, con comuna, crea y deja seleccionado.
7. El formulario de lugar muestra lo que ya hay en la comuna elegida.
8. Al crear o editar una actividad o un proyecto se eligen uno o más territorios. El filtro por comuna incluye las actividades dirigidas a sus sectores.
9. Actividad y comunidad tienen tramos de edad de selección múltiple, desde un catálogo. El texto anterior no se pierde.
10. Organización tiene secciones, y Naturaleza jurídica y Domicilio legal se entienden. No quedan códigos internos en las ayudas.
11. `/territorio` y la ficha de comuna explican de dónde salen los datos y qué se puede crear, editar o desactivar.
12. Las pruebas existentes siguen pasando (se ajustan solo las que leen HTML cambiado, sin debilitar lo que comprueban). Hay pruebas nuevas por cada criterio. El recorrido de páginas da 0 errores.

## Restricciones
- Migraciones solo aditivas: nada se borra.
- Sin dependencias nuevas, sin CDN y sin servicios externos.
- Datos de prueba ficticios.
- Commits en español, sin coautoría.
- Lo sensible sigue `fche-ley-datos`.

## Pendiente de validar [V]
- Limitar el responsable al equipo de la Fundación (`RESPONSABLE_SOLO_EQUIPO`).
- Los valores de los catálogos Tramo etario y Naturaleza jurídica.
- Las 6 diferencias de escritura entre la SUBDERE y el INE (se usó el INE).
- Filtro «Cuándo» en Actividades (propuesta: se quita borrando una línea en `ActividadLista.filtros`).
- Parte B: perfiles sin ficha (por ejemplo beneficiario), los valores de Parentesco, TipoInvitado y EstadoVoluntario, el sexo como dato general y el hogar como dato restringido sin consentimiento (decidido por el usuario; validar con el tutor por la Ley 21.719) [V#2].

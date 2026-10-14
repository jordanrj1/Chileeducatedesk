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

### A2. Selección múltiple desplegable
Afecta a todo campo de selección múltiple que hoy son casillas a la vista (áreas de interés, perfiles…).
- Se convierte en un **botón que despliega la lista con buscador**.
- Lo elegido se muestra como **etiquetas**, cada una con una × para quitarla.
- **Sin JavaScript** siguen siendo casillas nativas, dentro de un bloque plegable (`<details>`).

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

### A4. Territorio oficial de Chile
- **Datos:**
  - `apps/territorio/datos/cut_chile.csv` con **16 regiones, 56 provincias y 346 comunas**;
  - códigos CUT de la SUBDERE (Decreto Exento 1.115 de 2018) y nombres del INE (Censo 2024);
  - ambas fuentes se compararon código por código: coinciden los 346 códigos y su región y provincia. Las 6 diferencias de escritura se resolvieron con el INE; la provincia queda como «Tamarugal»;
  - las fuentes quedan anotadas en `apps/territorio/datos/LEEME.md`.
- **Carga:**
  - `cargar_territorio` sin argumentos usa ese archivo;
  - valida la jerarquía y los totales;
  - acepta `--si-falta` (no hace nada si ya hay comunas oficiales) y `--simular`;
  - no es una migración de datos, para no cambiar las pruebas;
  - `iniciar.bat` e `iniciar.sh` lo ejecutan con `--si-falta`;
  - la «Región Demo» (código 99) no choca con los códigos oficiales y nunca se borra.
- **Sin servicios externos:** no se usa Google Maps ni ningún servicio de mapas. El sistema funciona sin internet (docs/CONTEXTO.md §15).
- **Sector:**
  - gana `activo` y un historial de cambios (migración aditiva);
  - se crea, se edita y se **desactiva**; nunca se borra.
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

## Parte B — Fichas por tipo de persona (espera decisiones del usuario)

**Lo que pidió el usuario:** al registrar a alguien, elegir si es **estudiante** (institución, casa matriz o sede, carrera, año…), **vecino o vecina** (sexo, edad, número de casa, familiares, hijos, nietos…), **invitado o invitada**, o una persona sin ficha especial, y que cada tipo tenga **su propia tabla**.

**Diseño base** [P] (detalle en `analisis/personas.md`):
- **Identidad única.** `Persona` sigue siendo la única identidad. El «tipo de registro» es el catálogo `PerfilPersona`, que gana el campo `ficha`, el cual dice qué sección abre cada perfil. Así Claudio puede crear un perfil nuevo que abra una ficha existente.
- **Formulario:**
  - arriba, botones para marcar uno o varios tipos;
  - debajo, solo las secciones de esos tipos, con cascadas (institución → sede o carrera; comuna → sector → comunidad);
  - funciona también sin JavaScript.
- **Estudiante:**
  - su tabla es `PersonaFormacion`, que ya existe: institución, carrera, estado, años, jornada y nivel;
  - la **sede o casa matriz** pasa a ser un `Lugar` de la institución, elegido en cascada y creado en el momento si falta.
- **Vecino o vecina:**
  - dirección de residencia (calle, **número de casa**, comuna y sector) y comunidad;
  - edad (fecha de nacimiento o edad aproximada) y sexo [V];
  - tabla nueva de hogar con **conteos por parentesco y tramo de edad** (por ejemplo, «2 hijos de 6 a 12»), sin nombres de menores [V#2].
- **Invitado o invitada:** tabla nueva con quién invita, de qué organización viene, el motivo y la actividad [V].
- La ficha de la persona muestra cada tipo como una tarjeta en «Datos», sin sumar pestañas.
- **Hay que adaptar:**
  - la fusión de fichas repetidas;
  - la exportación de datos personales;
  - la importación de planillas (columna «perfil»);
  - la creación rápida desde la actividad (asigna el perfil del rol).

**Decisiones pendientes del usuario:**
- qué tipos tienen ficha;
- la familia: ¿conteos o personas vinculadas?;
- el sexo: ¿dato general o restringido?;
- los datos del hogar: ¿restringidos con consentimiento o no?

Se construye después de su respuesta, con su propia sección en este documento.

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
- Toda la Parte B.

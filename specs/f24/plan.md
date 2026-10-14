# F24 — Plan de construcción (Parte A)

**Spec:** `specs/f24/spec.md`. **Análisis con evidencias y propuestas detalladas:** `specs/f24/analisis/` (selectores, territorio, formularios, listados, actividad_proyecto, personas).

## Cómo se construye
- **Una tarea a la vez**, en este orden, porque varias comparten `apps/nucleo/formularios.py`, `templates/generico/_campo.html`, `static/js/fche.js` y `static/css/fche.css`.
- Cada tarea:
  1. escribe primero las pruebas;
  2. implementa;
  3. corre **todas** las pruebas (`.venv/bin/python -m pytest -q`);
  4. hace un commit en español, sin coautoría.
- Después, una revisión independiente y, si hace falta, una ronda de arreglos.
- **No se migra la base de desarrollo** ni se ejecuta `collectstatic` durante las tareas. Al final se respalda la base, se migra, se carga el territorio y se reinicia el servidor.

## Restricciones globales
- Migraciones solo aditivas; nada se borra; `on_delete=PROTECT`.
- Sin dependencias nuevas; sin CDN; JavaScript propio y sin librerías; HTMX local.
- Todo funciona sin JavaScript (mejora progresiva).
- Accesible: etiquetas, teclado, `aria-*`, foco visible y contraste AA.
- Estilos solo con los tokens `--fche-*` de `static/css/fche.css`.
- Español de Chile, simple. Sin códigos internos (HU-…, F22…) en lo que ve Claudio.
- Datos de prueba ficticios.
- Sin consultas en bucle: las opciones y los paneles usan un número fijo de consultas.

## Tareas

### T1 · Territorio oficial y Sector desactivable (spec A4)
- `apps/territorio/datos/cut_chile.csv` ya está hecho.
- **Cargador común** (`apps/territorio/carga.py`):
  - valida 16 regiones, 56 provincias y 346 comunas, la jerarquía de códigos y los códigos repetidos;
  - hace `update_or_create` por código.
- **`cargar_territorio`:**
  - archivo por defecto;
  - `--si-falta` (no hace nada si ya hay comunas con código oficial);
  - `--simular`.
- `iniciar.bat` e `iniciar.sh` lo llaman con `--si-falta` después de migrar.
- `Sector.activo` + `HistoricalSector`, con migración aditiva. Desactivar y reactivar el sector siguen `AlternarActivoBase`. Las opciones en cascada solo ofrecen sectores activos; un formulario de edición conserva un sector desactivado.
- **Bloque «De dónde sale y qué reúne»** en `/territorio` (índice) y en la ficha de comuna y sector. El aviso de «falta el territorio oficial» aparece si no hay comunas oficiales, aunque exista la Región Demo.
- **Pruebas:**
  - carga con conteos y Hualpén `08112`;
  - idempotencia;
  - `--si-falta`;
  - archivo con errores rechazado sin cargar nada;
  - sector desactivado fuera de las opciones;
  - bloque explicativo visible.

### T2 · Buscadores (spec A1)
- `apps/nucleo/selector.py` con una «fuente» por modelo (persona, organización, actividad, comunidad, lugar…), que entrega una sola consulta para listar y validar.
- `SelectorField` usa la fuente:
  - sin JavaScript, el `<select>` trae las primeras 25 opciones más el valor actual;
  - un vínculo desactivado del registro se conserva y se marca «(desactivada)»;
  - un valor no numérico es un error de formulario, no un 500.
- Los endpoints de opciones:
  - aceptan `q`, `actual` y `limite`;
  - devuelven las opciones con la actual primero;
  - incluyen el total («Mostrando 25 de N»);
  - las de organizaciones, sin N+1.
- **Combobox en `static/js/fche.js`** (o en `static/js/selector.js`, enlazado en `base.html`):
  - teclado, `aria-activedescendant`;
  - Enter no envía el formulario;
  - botón «Quitar» si el campo es opcional;
  - HTMX ya está cargado.
- **«+ Crear persona» y «+ Crear organización»:**
  - modal de Bootstrap local;
  - endpoint rápido con aviso de duplicados («Usar existente» o «Crear de todos modos»);
  - devuelve la opción creada y el combobox la selecciona;
  - permisos: `personas.add_persona` y `organizaciones.add_organizacion`.
- **Responsable:**
  - grupo «Equipo de la Fundación» primero;
  - ajuste `RESPONSABLE_SOLO_EQUIPO=False` en base.py y `.env.example`;
  - ayuda que dice dónde se registra el equipo.
- **Pruebas:**
  - GET de los formularios trae opciones sin escribir;
  - buscar conserva el valor;
  - el vínculo desactivado se conserva al guardar;
  - un valor «abc» da 400 y no 500;
  - crear rápido con duplicado avisa;
  - crear rápido deja la opción;
  - el equipo de la Fundación aparece primero;
  - tope de consultas en las opciones de organizaciones.

### T3 · Selección múltiple desplegable (spec A2)
- Widget `SelectorMultiple` (subclase de `CheckboxSelectMultiple`) con su plantilla:
  - `<details>` con el resumen de lo elegido;
  - buscador;
  - casillas nativas.
- JavaScript opcional: etiquetas con ×.
- Se usa por defecto en todo `ModelMultipleChoiceField` y `MultipleChoiceField` de los formularios con `BootstrapMixin`, y en los filtros de selección múltiple si los hubiera.
- **Pruebas:**
  - `/comunidades/nueva` y `/personas/nueva?modo=completa` dibujan el widget;
  - enviar varias opciones sigue guardando igual.

### T4 · Filtros con menos ruido (spec A3)
- `Filtro` gana `principal`, `grupo`, `todos`, `oculto`, el tipo `casilla` y `texto(valor)`.
- `ListaBase` gana `buscable` y `texto_busqueda`, y registra los filtros aplicados.
- Nueva `templates/generico/_filtros.html`: buscador, filtros principales, «Más filtros (n)» en `<details>`, etiquetas de los filtros aplicados con ×, contador y «Limpiar» que conserva el orden.
- Se marcan los principales de los 14 listados según `analisis/listados.md`.
- **Correcciones:**
  - buscador en Personas;
  - «todos» una sola vez y con «Limpiar»;
  - casillas en vez de selects de una opción;
  - Tareas por responsable con nombre;
  - aviso de tope en Organización.
- **Pruebas:**
  - Personas muestra el buscador y 3 principales;
  - las etiquetas de los filtros aplicados quitan solo su filtro;
  - «Limpiar» conserva el orden;
  - los nombres de los parámetros no cambian.
- Se ajustan solo las pruebas que leen HTML cambiado, sin debilitarlas.

### T5 · Ubicación en cascada (spec A5)
- `UbicacionMixin` y `territorio/_ubicacion.html` reemplazan a `_direccion.html` en sus usos, más un endpoint que vuelve a dibujar el bloque. Región → comuna → sector, con la provincia opcional.
- **«+ Crear sector»:**
  - deshabilitado con «Primero elige la comuna»;
  - recibe la comuna explícita;
  - conserva lo elegido;
  - Enter no envía el formulario;
  - avisa de parecidos.
- **Se usa en:** la dirección de persona, organización y lugar, y en la comunidad (comuna y sector).
- **Panel «En <comuna> ya hay…»** en el formulario de lugar: sectores, comunidades, lugares y organizaciones, con enlaces y un número fijo de consultas.
- **Corrección:** una actividad dirigida a un sector aparece al filtrar por su comuna en `/actividades`, `/calendario` y `/buscar`.
- **Pruebas:**
  - cascada filtra comunas por región;
  - crear sector sin comuna explica y con comuna crea y selecciona;
  - el panel del lugar;
  - el filtro por comuna incluye sectores;
  - los formularios existentes de dirección siguen guardando.

### T6 · Tramos de edad (spec A7)
- Catálogo `TramoEtario` (nombre, edad_min, edad_max, orden y activo) en `apps/nucleo/models.py`, agregado a `CATALOGOS` y a los catálogos de `roles.py`.
- Datos iniciales por migración.
- M2M `tramos_etarios` en `Actividad` y `Comunidad`.
- El texto `rango_etario` se queda con la etiqueta «Rango etario (texto anterior)», oculto en los formularios si está vacío.
- Migración de datos con un intérprete conservador: solo asigna cuando reconoce números o palabras sin ambigüedad.
- Se ve en las fichas y en el alcance.
- **Pruebas:**
  - catálogo cargado;
  - selección múltiple guarda;
  - el intérprete reconoce «jóvenes de 15 a 29» → Adolescencia + Jóvenes, y no inventa ante texto ambiguo.

### T7 · «¿Dónde?» en actividad y proyecto (spec A6)
- Base abstracta común de territorio, y nuevo `ProyectoTerritorio` (mismas reglas: un solo nivel por fila; no repetir).
- **Sección «¿Dónde se realiza o a quién va dirigida?»** en crear y editar actividad y proyecto:
  - filas de ubicación, que usan el componente de T5;
  - guardan el nivel más fino;
  - en una transacción;
  - prellenado desde `?comuna=`, `?sector=`, `?comunidad=` o la jornada.
- **Formulario de actividad con secciones:**
  - a la vista: qué es, para qué y para quién, dónde;
  - plegado: detalles;
  - ayudas breves con ejemplo.
- **`Proyecto.zona`:**
  - se conserva como «texto anterior»;
  - migración de datos que vincula solo coincidencias únicas y exactas sin tildes.
- **Pruebas:**
  - crear actividad con dos comunas y un sector;
  - editar sin tocar conserva;
  - proyecto con territorio;
  - migración de zona (coincidencia única sí, ambigua no);
  - pestaña Territorio del proyecto.

### T8 · Formularios claros (spec A8)
- `Meta.labels` y `help_texts` según `analisis/formularios.md`, en todos los formularios:
  - sin códigos internos;
  - con tildes correctas;
  - con ejemplos.
- `secciones` admite plegar («Datos legales», «Más datos»).
- Organización con secciones.
- Catálogo `NaturalezaJuridica` (FK nueva): el texto antiguo pasa a «texto anterior», migrado por coincidencia exacta.
- La casilla «Vigente» sale de los formularios de alta de los hijos; queda en editar.
- **Pruebas:**
  - Organización con 3 secciones y ayuda en Naturaleza jurídica;
  - ninguna ayuda con códigos internos (prueba que recorre los formularios).

### T9 · Modelo de las fichas por tipo (spec B1)
- **Catálogos:**
  - `PerfilPersona.ficha` (campo extra editable en Catálogos, siguiendo el patrón de `RolParticipacion`);
  - catálogos nuevos `Parentesco`, `TipoInvitado` y `EstadoVoluntario`, agregados a `CATALOGOS` y a `roles.py`;
  - «Casa matriz» en tipos de lugar;
  - perfil «Invitado o invitada».
- **Persona y estudiante:**
  - `Persona.sexo` y `Persona.fecha_nacimiento_aproximada`;
  - `PersonaFormacion.sede_institucion` (FK a `Lugar`), con `clean()`: la sede debe pertenecer a la institución.
- **Tablas nuevas, con historial:** `FichaVecino`, `IntegranteHogar`, `FamiliarVinculado`, `FichaInvitado` y `FichaVoluntario`, con sus restricciones (cantidad ≥ 1; no repetir; nadie es su propio familiar).
- **Migraciones de datos:**
  - asigna la ficha de cada perfil;
  - crea el perfil invitado;
  - copia la jefatura y los integrantes del hogar de `PerfilSensible` a `FichaVecino` (las columnas viejas se conservan).
- **Pruebas:** restricciones, migración de datos y el `clean()` de la sede.

### T10 · Formulario dinámico y tarjetas en la ficha (spec B2)
- **Formulario `PersonaNuevaForm` / edición:** fila de tipos (perfiles con ficha) y una sección por ficha.
  - Las secciones las arma un registro, `apps/personas/fichas.py`.
  - Con JavaScript se muestran u ocultan; sin JavaScript, el botón «Mostrar secciones» vuelve a dibujar sin guardar.
  - Se validan y guardan solo las elegidas, en una transacción, y el aviso de duplicados se mantiene.
- **Cascadas**, reutilizando el combobox de T2 y la ubicación de T5:
  - institución → sede (+ crear sede con nombre y comuna) y carrera (+ crear carrera);
  - comuna → sector → comunidad;
  - hogar con filas de conteo (formset) y «vincular familiar» con el buscador de personas.
- **Ficha de la persona:** una tarjeta por tipo en Datos, con «Editar» (vistas de edición por ficha). El hogar va con 🔒.
- **Pruebas:**
  - crear estudiante con sede y carrera;
  - crear vecino con hogar y familiar vinculado;
  - crear invitado y voluntario;
  - persona con dos tipos;
  - sin tipo, igual que hoy;
  - sin JavaScript: «Mostrar secciones».

### T11 · Fusión, exportación, importación y creación desde la actividad (spec B3)
- **Fusión** (`apps/personas/fusion.py` o equivalente):
  - completa las fichas 1 a 1 sin pisar;
  - mueve los conteos y los vínculos sin duplicar, resolviendo la restricción única.
- **Exportación de datos personales:** hojas por ficha.
- **Importación:** columna opcional «tipo» o «perfil».
- **`RolParticipacion.perfil`** (campo extra en Catálogos), con su asignación inicial; `ParticipanteRapido` asigna el perfil del rol.
- **Privacidad:** los datos del hogar no salen en el resumen ni en el Excel territorial ni en las opciones del buscador.
- **Pruebas** de cada punto.

### Cierre
- Revisión final de toda la rama.
- Pruebas completas y recorrido de páginas.
- Detector visual si está disponible.
- Manual de uso (Territorio, buscadores, filtros) y `docs/CONTEXTO.md §0.5` al día.
- Respaldo de la base de desarrollo, migración, carga del territorio y reinicio del servidor.

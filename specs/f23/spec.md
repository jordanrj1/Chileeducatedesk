# F23 — Contenedor Territorio

Fuente: pedido del 13-10-2026 («contenedores que alimenten el proyecto, pocos clics, agrupado por zonas, localidades, instituciones, juntas de vecinos»). El usuario eligió empezar por el territorio. Programa completo en `docs/rediseno_integral.md`; producto en `PRODUCT.md`.

## Qué y por qué
Hoy la ficha de una comuna lista sectores, lugares, organizaciones, comunidades y actividades en pestañas separadas, sin un resumen. Responder «¿qué hacemos en Hualpén?» exige abrir cinco pestañas y contar a mano. F23 convierte la comuna (y el sector) en el **contenedor principal**:
- arriba, un resumen con indicadores clicables;
- debajo, lo agrupado por tipo y por sector;
- las personas que viven ahí y el alcance logrado;
- un Excel listo para la Dirección o un fondo.

El índice de Territorio deja de ser una lista de 16 regiones y muestra primero **dónde trabaja la Fundación**.

## Pantallas

### 1. `/territorio` — «Dónde trabajamos» [P]
- **Comunas con presencia** primero: las que tienen al menos una comunidad, organización, lugar, persona residente o actividad. Cada tarjeta muestra nombre, región y conteos (comunidades, organizaciones, personas residentes, actividades de los últimos 12 meses). Se ordenan por actividades recientes y luego por total.
- Se mantienen el buscador de comuna y, debajo, «Todas las regiones».
- **Vacío:** explica que aún no hay trabajo registrado y ofrece «+ Comunidad» y «+ Organización».

### 2. Ficha de comuna (contenedor)
- **Cabecera:**
  - región › provincia;
  - municipalidad (enlace o «+ Registrar municipalidad»);
  - acciones «+ Comunidad», «+ Organización», «+ Lugar» y «+ Actividad», con la comuna ya elegida;
  - «Exportar resumen».
- **Pestaña Resumen (nueva, por defecto):**
  - **Indicadores clicables:** comunidades, organizaciones, personas residentes, lugares, actividades de los últimos 12 meses y total alcanzado. Cada uno lleva a su pestaña.
  - **Organizaciones por tipo:** junta de vecinos, institución educativa, municipalidad, empresa, fundación u ONG y otra, con contador y hasta 5 nombres más «ver todas».
  - **Sectores:** tabla con comunidades, organizaciones, lugares, personas residentes y actividades por sector, más una fila «Sin sector». Cada fila enlaza a la ficha del sector.
  - **Próximas actividades** (30 días) y **últimas minutas** (5 sesiones con fecha).
- **Pestaña Organizaciones:** agrupadas por tipo, con contador por grupo.
- **Pestaña Personas (nueva):**
  - **residentes:** dirección de residencia vigente en la comuna, con perfiles y comunidad;
  - aparte, **integrantes de comunidades de la comuna que no residen en ella**;
  - nunca datos sensibles; enlace «Ver en el listado de Personas» con el filtro de comuna.
- **Pestaña Alcance (nueva):** el servicio `alcance()` de F22 sobre las actividades de la comuna.
- Se mantienen las pestañas Sectores, Lugares, Comunidades y Actividades, cada una con contador.

### 3. Ficha de sector
Mismas pestañas Resumen, Personas y Alcance, calculadas sobre el sector y sus sectores hijos.

### 4. Ficha de región
Antes de la lista por provincia aparecen las tarjetas de las comunas con presencia de esa región, con el mismo formato que el índice.

### 5. Enlaces «en esta comuna» (hacia arriba)
La comuna aparece como enlace en la cabecera de la ficha de:
- persona (comuna de residencia vigente);
- organización;
- lugar;
- actividad (comuna del lugar programado o del territorio indicado);
- comunidad (ya lo hace).

### 6. Crear desde el contenedor
El parámetro `?comuna=<id>` prellena la comuna en «nueva organización» y «nuevo lugar» (dirección en cascada) y en «nueva comunidad» (ya existe). En «nueva actividad» deja registrada la comuna como territorio de la actividad.

### 7. Exportar resumen territorial (Excel) [V: validar con la Dirección qué hojas usa]
- **Hojas:** Resumen (indicadores), Sectores, Comunidades, Organizaciones (nombre, tipo, sector, correo o teléfono principal), Personas residentes, Actividades (nombre, estado, fecha, lugar) y Alcance.
- **Personas residentes:** nombre, perfiles y comunidad. RUT y contactos solo con `personas.exportar_persona`. Nunca datos sensibles.
- Permiso nuevo `territorio.exportar_territorio`; queda en la auditoría y lleva el aviso de confidencialidad de las demás exportaciones.

### 8. Deuda visual del detector (impeccable, línea base del 13-10-2026)
- Quitar los bordes laterales de acento: alertas, niveles de compatibilidad, cita del manual e índice de ayuda.
- Quitar el texto con degradado en las páginas de error.
- Letra de 10,9 px y espaciado ancho en el día de «Próximas actividades».
- Relleno del icono de candidatos.
- Contraste en el panel de ingreso.
- Meta: detector en 0 hallazgos sobre `templates/` y `static/css/`.

## Reglas de datos
- **Persona residente:** `PersonaDireccion` vigente, tipo «residencia», con dirección en la comuna (o en el sector o sus hijos).
- **Actividades de un territorio:** `territorio.consultas.actividades_de`, es decir, agenda vigente en un lugar del territorio o territorio indicado en la actividad.
- **Últimos 12 meses:** agenda vigente con fecha entre hoy menos 365 días y hoy.
- **Activos e inactivos:** los indicadores y los contadores de las pestañas cuentan solo registros activos, para que el número del indicador coincida con la lista principal de su pestaña. Las pestañas Organizaciones y Lugares muestran los activos y, al final, un grupo atenuado «Organizaciones inactivas (n)» / «Lugares inactivos (n)» con la pastilla «Inactiva»/«Inactivo», para que lo que tiene historia siga a la vista. En la cabecera, una municipalidad desactivada se sigue enlazando, con la pastilla «Inactiva».
- **Integrante no residente:** integrante vigente de una comunidad activa del territorio, sin residencia vigente en él.
- **Rendimiento:** cada pestaña del contenedor usa un número fijo de consultas, independiente de cuántas filas haya. Las pruebas lo verifican con `django_assert_max_num_queries`.

## Criterios de aceptación
1. `/territorio` muestra primero las comunas con presencia, con conteos correctos, ordenadas por actividad reciente. Una comuna sin nada no aparece en esa sección.
2. La ficha de comuna abre en **Resumen**: indicadores correctos y clicables, organizaciones agrupadas por tipo, tabla por sector con fila «Sin sector», próximas actividades y últimas minutas.
3. La pestaña **Personas** separa residentes de integrantes no residentes y no muestra datos sensibles. Quien no tiene `personas.view_persona` no la ve.
4. La pestaña **Alcance** de la comuna coincide con `alcance()` sobre sus actividades.
5. La ficha de sector incluye a sus sectores hijos.
6. Las fichas de persona, organización, lugar y actividad enlazan a su comuna.
7. `?comuna=` prellena la comuna en organización, lugar, comunidad y actividad.
8. La exportación genera las 7 hojas, respeta los permisos (403 sin `exportar_territorio`; sin RUT ni contactos sin `exportar_persona`) y queda en la auditoría.
9. Cada pestaña del contenedor se mantiene bajo un tope fijo de consultas con 1 o 30 registros.
10. El detector de impeccable reporta 0 hallazgos; las 475 pruebas existentes siguen pasando.

## Pendiente de validar [V]
- Hojas y formato del Excel territorial con la Dirección y un fondo de ejemplo.

# listados

## Resumen
Revisé ListaBase y Filtro (apps/nucleo/vistas_base.py), la plantilla común (templates/generico/lista.html), fche.css, fche.js y los 14 listados que heredan de ListaBase. Para medir, rendericé los listados con el cliente de pruebas dentro de una transacción que se deshizo al final, sin escribir nada.

**Por qué hay tanto ruido.** La plantilla pinta todos los filtros del mismo modo, como selects en una fila que se parte en varias líneas (lista.html:23-34). Ningún filtro tiene prioridad y no hay manera de esconder los menos usados. Personas y Actividades tienen 10 filtros cada una. En /personas medí 10 selects, 65 opciones y 5 KB solo en el formulario. La base local tiene 1 comuna; cuando se cargue el archivo CUT, el select Comuna tendrá unas 346 opciones.

**Problemas que encontré:**
- **Personas no tiene buscador en su propio listado.** La causa es `campos_busqueda = ()` (personas/views.py:67) junto con `buscable = bool(campos_busqueda)` (vistas_base.py:146). La búsqueda por `?q=` funciona por URL, pero el cuadro no aparece.
- **Opciones confusas:**
  - Las opciones vacías dicen «Comuna: todos», «Organización: todos», «Vigencia: todos».
  - En el filtro de activos aparece dos veces «todos» («Estado: todos» y «Todos»).
  - Si se elige «Estado: todos» (`activo=` vacío), el listado muestra también los inactivos, pero el sistema cree que no hay filtro: no ofrece «Limpiar» (vistas_base.py:82 y 154-156).
- **Filtros mal resueltos:**
  - Hay selects de una sola opción: «Solo incompletas» y «Solo vencidas».
  - Tareas filtra por «Responsable (id)», donde hay que escribir el número interno de la persona.
  - Organización corta en 300 nombres sin avisar.
  - En Actividades, Organización e Institución filtran la misma relación.
- **El orden no tiene botones.** Las claves de orden llegan a la plantilla, pero esta nunca las usa, y «Limpiar» borra el orden elegido.

**Diseño que propongo:**
- **Filtro gana 4 atributos:**
  - `principal` (bool): se ve siempre en la barra;
  - `grupo`: subtítulo dentro de «Más filtros»;
  - `todos`: el texto de la opción vacía con su género («Todas»);
  - `oculto`: el filtro funciona por URL pero no se pinta (sirve para mantener `?institucion=`).
  
  También gana el tipo de campo `"casilla"` y un método `texto(valor)` que da el texto de la etiqueta del filtro aplicado.
- **ListaBase gana `buscable` y `texto_busqueda`.** Además registra en `filtrar()` qué filtros se aplicaron de verdad. Con eso entrega a la plantilla: los filtros principales, los de «Más filtros», los filtros aplicados (cada uno con su enlace para quitarlo), cuántos aplicados hay dentro de «Más filtros» y un enlace «Limpiar» que conserva el orden.
- **Nueva plantilla `generico/_filtros.html`**, con:
  - el buscador y 2 o 3 filtros a la vista;
  - un `<details>` «Más filtros (n)» que funciona sin JavaScript;
  - una fila con el número de resultados, los filtros aplicados con su × para quitarlos y «Limpiar todo».
- **JavaScript opcional:**
  - los filtros principales se aplican al elegir un valor;
  - al enviar, se arma una URL sin los campos vacíos.
  
  Sin JavaScript todo sigue funcionando, y la URL conserva siempre los parámetros.
- **«← Volver» no cambia.** Las etiquetas de filtros aplicados y «Limpiar» son enlaces comunes que pasan por ListaBase.get, que ya guarda la URL completa en la sesión.

No hay cambios de modelo ni de base de datos. Hay pruebas que leen el HTML de los listados y que podrían romperse: algunas exigen textos fijos («30 registros», «Sin resultados», «Aún no hay registros») y otras exigen que un nombre NO aparezca en la página. Ninguna prueba lee la variable `filtros_ui`. Hay que mantener los nombres de los parámetros: el tablero, la pestaña de territorio y varias pruebas los usan.

## Hallazgos

### Inventario: 14 listados heredan de ListaBase; dos tienen 10 filtros
- Evidencia: apps/personas/views.py:79-94; apps/actividades/views.py:81-93; apps/documentos/views.py:42-50; apps/lugares/views.py:31-36; apps/solicitudes/views.py:36-41; apps/finanzas/views.py:37-42; apps/comunidades/views.py:28-32; apps/coordinacion/views.py:92 y 156-160; apps/cuentas/views_admin.py:243-247 y 36-62; apps/organizaciones/views.py:48; apps/importaciones/views.py:32; apps/proyectos/views.py:31. Medido con el cliente de pruebas (transacción deshecha): /personas tiene 10 selects y 65 <option> (5.076 bytes de formulario); /actividades, 8 selects y 2 fechas; /documentos, 5 selects y 2 fechas.
- Hoy: Filtros por listado:
- **Personas, 10:** activo «Estado», registro, origen, rol «Tipo de relación», organizacion, comuna, perfil, interes, comunidad, edad.
- **Actividades, 10:** estado, tipo, proyecto, comuna «Zona (comuna)», organizacion, responsable, institucion, desde, hasta, incompleta.
- **Documentos, 7:** activo, tipo, desde, hasta, persona, actividad, vencimiento «Vigencia».
- **Lugares, 4:** activo, tipo, comuna, capacidad_min.
- **Solicitudes, 4:** estado, origen, desde, hasta.
- **Finanzas (segunda fase), 4:** proyecto, tipo, desde, hasta.
- **Comunidades, 3:** activo, tipo, comuna.
- **Tareas (segunda fase), 3:** estado, responsable (número), vencidas.
- **Auditoría, 3:** desde, hasta, accion.
- **Organizaciones, 2:** activo, tipo.
- **Importaciones, 2:** tipo, estado.
- **Reuniones (segunda fase), 2:** desde, hasta.
- **Proyectos, 1:** estado.
- **Usuarios, 0:** solo el buscador.

Las vistas de exportación heredan los mismos filtros. Fuera de ListaBase usan la misma clase CSS: /buscar (templates/nucleo/buscar.html:14-23, 6 filtros), /calendario (templates/actividades/calendario.html:13-17, 4 selects que solo funcionan con JavaScript) y candidatos (templates/actividades/candidatos.html:18-30).
- Problema: En Personas y Actividades ve una pared de 10 controles iguales que ocupa 2 o 3 líneas antes de la tabla. No hay nada que le diga cuáles son los habituales.
- Propuesta: Máximo 3 filtros a la vista por listado; el resto va a «Más filtros», agrupado. Abajo, el detalle por listado. Si un listado tiene 3 filtros o menos, se ven todos y no aparece «Más filtros», salvo el de activos, que siempre va adentro.

### Personas no muestra buscador en su propio listado
- Evidencia: apps/personas/views.py:67 `campos_busqueda = ()`; apps/personas/views.py:99-100 `filtrar()` aplica `.buscar(q)`; apps/nucleo/vistas_base.py:146 `buscable=bool(self.campos_busqueda)`; templates/generico/lista.html:22. Renderizado: buscable=False y no hay name="q" en form.fche-filtros. Importaciones tampoco lo tiene (apps/importaciones/views.py:19-32).
- Hoy: La búsqueda por nombre, RUT, correo o teléfono funciona con ?q= (las pruebas la usan), pero el listado /personas no dibuja el cuadro de texto. Solo se ven los 10 selects.
- Problema: Para buscar a una persona en su listado tiene que ir al buscador global. En el listado mismo solo puede filtrar con selects, y eso aumenta la sensación de ruido.
- Propuesta: En ListaBase, agregar `buscable = None` (None significa bool(campos_busqueda)) y `texto_busqueda = ""` para el texto de ayuda del cuadro. En get_context_data: `buscable = self.buscable if self.buscable is not None else bool(self.campos_busqueda)`. En PersonaLista: `buscable = True` y `texto_busqueda = "Nombre, RUT, correo o teléfono…"`. En LoteLista: `campos_busqueda = ("nombre_archivo", "actividad__nombre")`.

### Opción vacía «X: todos», «todos» duplicado y la etiqueta se pierde al elegir
- Evidencia: templates/generico/lista.html:27 `<option value="">{{ f.etiqueta }}: todos</option>` para cada select; apps/nucleo/vistas_base.py:34-39 (filtro_activo ya trae «Todos» con valor «*»). Renderizado de /personas: «Estado: todos» + «Activos / Inactivos / Todos».
- Hoy: Salen frases como «Comuna: todos», «Organización: todos», «Edad: todos», «Vigencia: todos», «Incompletas: todos» y «Zona (comuna): todos». En el filtro de activos hay dos «todos». Cuando se elige un valor, el select muestra solo ese valor («Hualpén», «Incompleto») y no dice de qué filtro se trata.
- Problema: Ruido y concordancia de género mal hecha. Además, después de filtrar, no sabe qué filtros quedaron aplicados sin leer cada select.
- Propuesta: - `Filtro.todos: str = "Todos"`, para escribir `todos="Todas"` en Comuna, Organización, Edad y Vigencia. La plantilla escribe `{{ f.etiqueta }}: {{ f.todos|lower }}` en la fila principal y una etiqueta `<label>` visible dentro del panel.
- No pintar la opción vacía cuando el filtro tiene `por_defecto`, porque sus propias opciones ya incluyen «Todos».
- Mostrar los filtros aplicados como etiquetas («Comuna: Hualpén ×»).

### `activo=` vacío: el listado incluye inactivos, pero no figura como filtro
- Evidencia: apps/nucleo/vistas_base.py:82 `self.request.GET.get(f.param, f.por_defecto)` devuelve "" si el parámetro viene vacío, y la línea 94 entonces no filtra. Las líneas 154-156 tratan "" como «sin filtro». Medido: /personas?activo= da hay_filtros=False.
- Hoy: Al elegir «Estado: todos» se ven activos e inactivos, pero no aparece «Limpiar» ni ninguna señal de filtro aplicado. El formulario envía todos los campos vacíos: /personas?q=&activo=1&registro=&origen=&rol=&…
- Problema: Puede ver fichas desactivadas sin darse cuenta. Además, la URL que se guarda para «← Volver» y la de Exportar quedan llenas de parámetros vacíos.
- Propuesta: - En `valor_filtro`: `v = self.request.GET.get(f.param, ""); return v if v != "" else f.por_defecto`.
- `hay_filtros` pasa a ser `bool(filtros_activos)`, calculado con lo que `filtrar()` aplicó de verdad.
- En fche.js, al enviar `form.fche-filtros`, armar la URL con URLSearchParams sin los vacíos ni los valores iguales a `data-defecto` y navegar con `location.assign`.
- No deshabilitar los campos: el manejador de `pageshow` (static/js/fche.js:84-90) solo rehabilita botones, así que los selects quedarían deshabilitados al volver con «Atrás».

### Filtros de una sola opción y filtro por número interno
- Evidencia: apps/actividades/views.py:92 (select «Incompletas» con una única opción «Solo incompletas»); apps/coordinacion/views.py:159 (lo mismo con «Solo vencidas»); apps/coordinacion/views.py:158 `Filtro("responsable", "Responsable (id)", "asignaciones__persona_id", entrada="number", convertir=int)`.
- Hoy: Un select con una sola opción hace el trabajo de una casilla. En Tareas hay que escribir el número interno de la persona.
- Problema: Claudio no conoce los números internos, así que el filtro de responsable de Tareas no le sirve. Los selects de una sola opción son ruido.
- Propuesta: - Nuevo tipo de campo `entrada="casilla"`: un checkbox con `value="1"` y la etiqueta como texto (por ejemplo, «Solo incompletas»). Hay que mantener el valor «1», porque lo usan apps/nucleo/tablero.py:44 y las pruebas.
- En Tareas: `Filtro("responsable", "Responsable", "asignaciones__persona_id", lambda: [(str(p.pk), p.nombre_completo) for p in Persona.objects.filter(tareas_asignadas__isnull=False).distinct()], todos="Todos")`. La relación se llama `tareas_asignadas` (apps/coordinacion/models.py:154).

### Listas de opciones demasiado largas, recortadas o repetidas
- Evidencia: - `opciones_modelo(Comuna)` trae todas las comunas: apps/personas/views.py:86, apps/actividades/views.py:85, apps/lugares/views.py:34.
- `Organizacion.objects.filter(activo=True)[:300]` está en apps/personas/views.py:84 y apps/actividades/views.py:86; el orden es por nombre (apps/organizaciones/models.py:38).
- Documentos recorta las actividades en `[:300]` (apps/documentos/views.py:48).
- Organización (apps/actividades/views.py:86) e Institución (:88-89) filtran ambos `organizaciones__organizacion_id`.
- Comunidades ya limita a las comunas en uso (apps/comunidades/views.py:31).
- Hoy: Con el archivo CUT cargado, el select Comuna tendrá unas 346 opciones. Las organizaciones que quedan después de la número 300 en orden alfabético desaparecen del filtro sin aviso. En Actividades, Institución repite a Organización.
- Problema: Desplegables interminables. Organizaciones que no aparecen. Dos filtros que hacen lo mismo.
- Propuesta: - Ofrecer solo los valores en uso:
  - Personas: comunas de `PersonaDireccion` vigentes (`Comuna.objects.filter(pk__in=PersonaDireccion.objects.filter(vigente=True).values("direccion__comuna_id"))`).
  - Actividades: comunas de agenda o territorio.
  - Organizaciones: solo las que tienen vínculos o formaciones (Personas) o participación en actividades (Actividades), sin el `[:300]`.
- Permitir que `opciones()` devuelva tríos `(valor, etiqueta, grupo)` y pintarlos con `<optgroup>`: comuna agrupada por región y organización agrupada por tipo. Es una cascada visual sin JavaScript.
- En Actividades, fusionar Institución dentro de Organización con el grupo «Instituciones educativas». Se conserva `Filtro("institucion", …, oculto=True)` porque apps/actividades/tests.py:586 usa `?institucion=`.
- Opcional [P]: un filtro Sector que depende de la comuna, dentro de «Más filtros». Usaría `hx-get="/territorio/sectores"` y `hx-include` sobre el select de comuna; el endpoint ya existe (apps/territorio/views.py:462-470) y toma el primer parámetro numérico (líneas 38-39).

### Filtros aplicados que no se ven al llegar desde el tablero o el territorio
- Evidencia: - apps/nucleo/tablero.py:44 `/actividades?incompleta=1`, :61 `/solicitudes?estado=pendiente`, :69 `/personas?registro=incompleto`, :105 `/documentos?vencimiento=por_vencer`.
- templates/territorio/pestanas/personas.html:5 y :12 `/personas?comuna=`.
- Pruebas que leen esos enlaces: apps/territorio/test_contenedor.py:168 y :432.
- Hoy: Hoy el filtro se reconoce solo porque el select muestra el valor elegido.
- Problema: Si «Registro» o «Vigencia» se van a «Más filtros» cerrado, Claudio llegaría desde el tablero a una lista filtrada sin saber por qué.
- Propuesta: - Fila de filtros aplicados, siempre visible cuando hay alguno: «12 resultados · Registro: Incompleto × · Limpiar todo».
- Un contador en el botón: «Más filtros (1)».
- El panel queda cerrado; las etiquetas bastan.
- Mantener exactamente los nombres de parámetro actuales (comuna, registro, incompleta, vencimiento, estado).

### El orden no tiene botones y «Limpiar» lo borra
- Evidencia: apps/nucleo/vistas_base.py:106-113 (orden por ?orden=) y :147-148 (`orden_actual`, `ordenes` en el contexto). Ninguna plantilla usa `orden_actual` ni `ordenes`. La cabecera de templates/generico/lista.html:1 dice «orden». «Limpiar» es `href="?"` en templates/generico/lista.html:37 y :73.
- Hoy: Solo se puede ordenar escribiendo ?orden= en la URL. «Limpiar» descarta también el orden.
- Problema: La historia BU-03 pide orden, y en pantalla no existe.
- Propuesta: - `url_limpiar` conserva solo `orden`, y el formulario lleva `<input type="hidden" name="orden">` cuando hay uno elegido.
- Opcional: encabezados clicables con un mapa `columnas_orden = {"Nombre": "nombre"}` en ListaBase, que no agregan controles a la barra.

### «← Volver» y la URL: ya funcionan; hay que no romperlos
- Evidencia: apps/nucleo/vistas_base.py:70 guarda `request.get_full_path()` en `session['lista:<ruta>']`; :308-310 FichaBase lo usa si `url_volver` no trae «?». Prueba: apps/nucleo/test_escenarios_catalogo.py:116-119 (UI-E10). Exportar usa la misma consulta: templates/generico/lista.html:14.
- Hoy: Cada GET al listado actualiza la URL que usa «Volver». Exportar respeta los filtros.
- Problema: Ninguno hoy. El riesgo está en el cambio: si se normaliza la URL con una redirección en el servidor, o si «Más filtros» se carga solo por HTMX sin cambiar la URL.
- Propuesta: - Las etiquetas de filtros aplicados, «Limpiar todo» y el envío del formulario son GET comunes, sin redirección; así ListaBase.get sigue guardando la URL.
- No usar `hx-get` en la barra. Si más adelante se usa, tiene que ir con `hx-push-url="true"`.
- `url_quitar` de cada etiqueta = la consulta actual sin `page`, sin ese parámetro y sin vacíos.

### Diseño: atributos nuevos de Filtro y ListaBase (apps/nucleo/vistas_base.py)
- Evidencia: apps/nucleo/vistas_base.py:22-31 (dataclass Filtro), :46-63 (atributos de ListaBase), :85-102 (filtrar), :128-163 (get_context_data).
- Hoy: Filtro solo tiene param, etiqueta, lookup, opciones, convertir, por_defecto, entrada y aplicar. El contexto entrega `filtros_ui` plano.
- Problema: No hay manera de declarar cuáles filtros son principales.
- Propuesta: **Filtro gana:**
- `principal: bool = False`
- `grupo: str = ""`
- `todos: str = "Todos"`
- `oculto: bool = False`
- `entrada`, que además acepta `"casilla"`
- `def texto(self, valor, opciones)`: devuelve dd-mm-aaaa si es fecha, la etiqueta si es casilla, `dict(opciones).get(valor, valor)` si es select y «≥ N» si es número.

`filtro_activo()` pasa a `principal=False, grupo="Registro"`.

**ListaBase gana:**
- `buscable = None`
- `texto_busqueda = ""`
- En `filtrar()`: `self.aplicados = {}` y `self.aplicados[f.param] = v` solo cuando el filtro se aplicó. Los valores mal escritos, como ?desde=no-es-fecha, no generan etiqueta.
- Un ayudante `_consulta_sin(*params)` que copia GET, quita `page` y esos parámetros, y descarta los vacíos.

**get_context_data agrega:**
- `filtros_principales` y `filtros_mas` (los que no son principales ni ocultos);
- `filtros_activos`: una lista de dicts `{etiqueta, texto, url_quitar}`. Incluye el texto buscado como «Texto: «ana»» y deja fuera el filtro cuyo valor es `por_defecto`;
- `n_mas_activos`, `url_limpiar` y `texto_busqueda`;
- `hay_filtros = bool(filtros_activos)`.

Se mantiene `filtros_ui` por compatibilidad: ninguna prueba lo lee y solo lo usa lista.html.

### Diseño: plantilla de la barra (templates/generico/_filtros.html, nueva)
- Evidencia: templates/generico/lista.html:20-40 (formulario actual) y :10 (contador `fche-contador` junto al h1). Los iconos «filtro» y «cerrar» ya existen (apps/nucleo/templatetags/fche.py:42 y :44). La clase `.fche-filtros__etiqueta` existe sin uso en fche.css:368.
- Hoy: El formulario repite el mismo bloque por cada filtro y solo tiene «Filtrar» y «Limpiar».
- Problema: No hay jerarquía visual ni resumen de lo que se aplicó.
- Propuesta: Reemplazar lista.html:20-40 por `{% include "generico/_filtros.html" %}`, con un fragmento `_filtro_campo.html` para un campo. La plantilla lleva la cabecera «Qué es / Dónde se usa», como las demás.

Estructura:
```
<form class="fche-filtros" method="get" role="search" data-filtros>
  hidden orden
  .fche-filtros__busqueda (q)
  {% for f in filtros_principales %} campo .fche-filtros__campo--principal (data-defecto="{{ f.por_defecto }}")
  {% if filtros_mas %}<details class="fche-filtros__mas"><summary class="btn btn-outline-secondary">{% icono "filtro" 16 %}Más filtros {% if n_mas_activos %}<span class="fche-contador">{{ n_mas_activos }}</span>{% endif %}</summary>
    <div class="fche-filtros__panel">{% regroup filtros_mas by grupo as grupos %} un <fieldset class="fche-filtros__grupo"><legend class="fche-filtros__etiqueta"> por grupo, con <label> visible por campo · botón «Aplicar filtros»</div></details>{% endif %}
  <button type="submit">Filtrar</button>
  {% if filtros_activos %}<div class="fche-filtros__activos" aria-live="polite"><span><strong>{{ paginator.count }}</strong> resultado{{ paginator.count|pluralize }}</span>
    {% for a in filtros_activos %}<a class="fche-chip" href="?{{ a.url_quitar }}" aria-label="Quitar filtro {{ a.etiqueta }}: {{ a.texto }}">{{ a.etiqueta }}: <strong>{{ a.texto }}</strong>{% icono "cerrar" 14 %}</a>{% endfor %}
    <a href="?{{ url_limpiar }}">Limpiar todo</a></div>{% endif %}
</form>
```

No cambiar los textos «Sin resultados con estos filtros» (lista.html:71), «Aún no hay registros» ni el texto de paginación «N registros» (_paginacion.html:5). Las pruebas los leen.

### Diseño: CSS y JavaScript (static/css/fche.css, static/js/fche.js)
- Evidencia: static/css/fche.css:360-369 (bloque de filtros); :435-436 (estilo global `details > summary` como enlace subrayado); :311-314 (dropdown de Bootstrap). static/js/fche.js:60-82 (envío único), :84-90 (pageshow). apps/nucleo/test_escenarios_catalogo.py:108-109 lee fche.js y exige «dataset.enviando» y «sessionStorage».
- Hoy: `.fche-filtros` es un flex que se parte en varias líneas. No hay estilos de panel ni de etiqueta. El JavaScript no toca los filtros.
- Problema: Un dropdown de Bootstrap no abre sin JavaScript y se cierra al hacer clic adentro. `<details>` funciona sin JavaScript.
- Propuesta: **CSS (agregar después de la línea 368):**
- `.fche-filtros{position:relative}`
- `.fche-filtros__mas>summary{list-style:none;color:inherit;text-decoration:none}` y `::-webkit-details-marker{display:none}`, para anular las líneas 435-436
- `.fche-filtros__mas[open]>summary{background:var(--fche-primario-suave)}`
- `.fche-filtros__panel{position:absolute;z-index:20;top:calc(100% + .4rem);left:0;right:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(14rem,1fr));gap:1rem;padding:1rem;background:var(--fche-superficie);border:1px solid var(--fche-borde);border-radius:var(--fche-radio-lg);box-shadow:var(--fche-sombra-lg)}`
- `.fche-filtros__grupo{border:0;margin:0;padding:0;display:grid;gap:.5rem}`
- `.fche-filtros__activos{flex:1 0 100%;display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;padding-top:.6rem;border-top:1px solid var(--fche-borde);font-size:.8125rem}`
- `.fche-chip{display:inline-flex;align-items:center;gap:.35rem;padding:.2rem .4rem .2rem .65rem;border-radius:2rem;background:var(--fche-primario-suave);border:1px solid var(--fche-primario-borde);color:var(--fche-primario-oscuro)}`
- En pantallas de menos de 576 px, el panel pasa a `position:static` y ocupa el ancho completo.

**JavaScript (bloque nuevo, opcional):**
1. En `change` de un select o casilla dentro de `.fche-filtros__campo--principal`, llamar a `form.requestSubmit()`.
2. En `submit` de `form[data-filtros]`, ejecutar `preventDefault` y armar la URL con `URLSearchParams(new FormData(form))`, quitando los vacíos y los iguales a `data-defecto`. Luego `location.assign`.
3. Con Escape, o con un clic fuera, se cierra el `<details>` abierto.

Sin JavaScript se usa el botón «Filtrar» y la URL lleva también los vacíos, igual que hoy.

### Qué filtros quedan a la vista en cada listado
- Evidencia: Fuentes para elegir:
- docs/Requerimientos_por_modulo_FCHE.md:93 (Personas: tipo de relación, organización, comuna, estado del registro);
- :204 y :345 (Actividades: fecha, estado, zona, organización, institución, responsable);
- docs/manual_de_uso.md:37 (F22: banco de personas por perfil, interés, comunidad, comuna, organización, edad).
- Hoy: Hoy todos los filtros se ven siempre.
- Problema: Necesita ver solo los 2 o 3 que usa a diario.
- Propuesta: Formato: a la vista → en «Más filtros», con grupos.
- **Personas:** buscador + Perfil, Comuna, Organización [V: ¿Perfil o Tipo de relación?] → «Relación»: Tipo de relación, Comunidad · «Perfil»: Interés, Edad · «Registro»: Estado del registro, Origen, Activos/Inactivos.
- **Actividades:** buscador + Estado, Zona (comuna), Cuándo [P: filtro nuevo `periodo` con Próximas / Esta semana / Este mes / Pasadas / Sin programar; si no se aprueba, Desde–Hasta como un solo rango] → «Qué»: Tipo, Proyecto, Solo incompletas (casilla) · «Con quién»: Organización (con Institución fusionada), Responsable · «Fechas exactas»: Desde, Hasta.
- **Documentos:** buscador + Tipo, Vigencia → «Fecha»: Desde, Hasta · «Asociado a»: Persona, Actividad · «Registro»: Activos/Inactivos.
- **Lugares:** buscador + Tipo, Comuna, Capacidad mínima → Activos/Inactivos.
- **Solicitudes:** buscador + Estado, Origen → Desde, Hasta.
- **Comunidades:** buscador + Tipo, Comuna → Activas/Inactivas.
- **Organizaciones:** buscador + Tipo → Activas/Inactivas.
- **Finanzas:** buscador + Proyecto, Tipo → Desde, Hasta.
- **Sin «Más filtros»:**
  - Tareas: Estado, Responsable (select), Solo vencidas (casilla).
  - Reuniones: Desde–Hasta.
  - Auditoría: Acción, Desde, Hasta.
  - Importaciones: Tipo, Estado.
  - Proyectos: Estado.
  - Usuarios: solo el buscador.

## Cambios de modelo

## Archivos
- specs/f15/spec.md, plan.md y tasks.md (o specs/f24/ si se trata como feature nueva): primero la spec, según la regla 3 de docs/CONTEXTO.md
- apps/nucleo/vistas_base.py (Filtro: principal, grupo, todos, oculto, casilla y texto(); ListaBase: buscable, texto_busqueda, aplicados, _consulta_sin, valor_filtro, nuevo contexto)
- templates/generico/lista.html (líneas 20-40 se reemplazan por el include; «Limpiar» de la línea 73 pasa a url_limpiar)
- templates/generico/_filtros.html (nueva)
- templates/generico/_filtro_campo.html (nueva)
- static/css/fche.css (después de la línea 368: .fche-filtros__mas, __panel, __grupo, __activos, .fche-chip; anular el estilo de details>summary de las líneas 435-436 dentro de la barra)
- static/js/fche.js (aplicar al cambiar, URL sin vacíos con URLSearchParams, cerrar con Escape; mantener «dataset.enviando» y «sessionStorage»)
- apps/personas/views.py (PersonaLista: buscable=True, principal y grupo por filtro, opciones de comuna y organización en uso)
- apps/actividades/views.py (ActividadLista: principales, Institución fusionada como alias oculto, incompleta como casilla, opcional periodo)
- apps/documentos/views.py
- apps/lugares/views.py
- apps/solicitudes/views.py
- apps/comunidades/views.py
- apps/organizaciones/views.py
- apps/importaciones/views.py (campos_busqueda)
- apps/proyectos/views.py
- apps/finanzas/views.py
- apps/coordinacion/views.py (Tareas: Responsable como select; vencidas como casilla)
- apps/cuentas/views_admin.py (Auditoría: principales)
- apps/nucleo/test_listados.py (nueva: buscador en /personas, filtros principales frente a <details>, etiqueta y url_quitar, contador de «Más filtros», activo= vacío, Limpiar conserva orden, fecha inválida sin etiqueta, select de responsable en Tareas)
- docs/manual_de_uso.md (líneas 37 y 245: cómo se usan «Más filtros» y las etiquetas de filtros aplicados)
- docs/auditoria/INVENTARIO_PLANTILLAS.md (agregar los fragmentos _filtros.html y _filtro_campo.html)

## Pruebas afectadas
- apps/nucleo/test_escenarios_catalogo.py:116-119 (UI-E10, «Volver» conserva q=ana&activo=*&page=1): se rompe si se agrega una redirección para normalizar la URL o si ListaBase.get deja de guardar get_full_path
- apps/nucleo/test_escenarios_catalogo.py:105-109 (lee static/js/fche.js y exige «dataset.enviando» y «sessionStorage»): hay que conservar esos textos al editar el JavaScript
- apps/personas/tests.py:209-217 (exige «30 registros», «Siguiente» y «Sin resultados»; además «Nombre01» NO debe estar en /personas): depende de _paginacion.html y del texto del estado vacío con filtros
- apps/personas/tests.py:258-269 (?rol=, ?organizacion=, ?comuna=; '>Otra<' NO debe estar en el HTML): si se agrega a Personas un select «Tipo de organización», el catálogo trae «Otra» (apps/nucleo/migrations/0003_catalogos_iniciales.py:8) y la prueba falla. Un optgroup (label="Otra") no la rompe
- apps/nucleo/test_f22.py:292-304 (?edad=, ?perfil=, ?comunidad=; «Mayor» y «Joven» NO deben estar en el HTML): no usar textos de opciones ni de etiquetas que contengan esas palabras, por ejemplo «Mayor de 60»
- apps/actividades/tests.py:53-65 (?tipo=, ?comuna=, ?desde=, ?hasta=, ?incompleta=1; ?desde=no-es-fecha debe responder 200): la casilla debe enviar «1» y texto() no puede fallar con una fecha inválida
- apps/actividades/tests.py:578-589 (?responsable= y ?institucion=): si Institución se fusiona en Organización, mantener el parámetro institucion como filtro oculto
- apps/documentos/tests.py:162-175 (?vencimiento=vencidos con «por vencer» NO en el HTML; ?persona= y ?actividad=): no cambiar el texto «Vencen en 30 días» por algo que contenga «por vencer»
- apps/documentos/tests.py:113-116 (?q=carta, ?tipo=)
- apps/coordinacion/tests.py:99-104 (/tareas?vencidas=1 con «Al día» NO en el HTML): la casilla debe enviar «1»
- apps/solicitudes/tests.py:31-36 (?q=, ?origen=, ?estado=) y 108-117 («+ Nueva oportunidad» en /solicitudes, de botones_extra)
- apps/cuentas/tests.py:207-215 (Auditoría con ?desde=, ?hasta=, ?accion=; «Sin resultados» con ?hasta=): hay_filtros debe seguir siendo verdadero cuando se aplica una fecha
- apps/finanzas/tests.py:97-98 (/finanzas?proyecto= muestra «Saldo», vía contexto_extra que lee GET['proyecto'])
- apps/nucleo/test_escenarios_catalogo.py:122-125 (UI-E13: /lugares vacío muestra «Aún no hay registros» y «+ Nuevo lugar»)
- apps/nucleo/test_escenarios_catalogo.py:130-175 (búsquedas ?q= en /personas y /organizaciones)
- apps/territorio/test_contenedor.py:168 y 432 (enlace href="/personas?comuna=…"): no renombrar el parámetro comuna
- apps/nucleo/test_f22.py:139 («Club de adulto mayor Ficticio» en /comunidades)

## Decisiones abiertas
- [V con Claudio] Personas: ¿el tercer filtro a la vista es Perfil (F22, docs/manual_de_uso.md:37) o Tipo de relación (docs/Requerimientos_por_modulo_FCHE.md:93)? Comuna y Organización están en ambas fuentes.
- [P] Actividades: ¿se crea un filtro nuevo «Cuándo» (`periodo`: próximas, esta semana, este mes, pasadas, sin programar) o se dejan Desde–Hasta a la vista como un solo rango?
- [P] Actividades: ¿se fusiona Institución dentro de Organización, agrupada por tipo? BU-02 nombra ambas; se conservaría ?institucion= como alias.
- ¿Los filtros a la vista se aplican al elegir un valor (con JavaScript) o se mantiene el botón «Filtrar» como único disparador?
- ¿«Más filtros» queda cerrado aunque tenga filtros aplicados (las etiquetas los muestran) o se abre solo en ese caso?
- Cambio de comportamiento: ¿`activo=` vacío debe significar «Activos», que es lo predeterminado? Hoy muestra todos sin avisar.
- ¿Comuna y Organización ofrecen solo valores que tienen registros, agrupados por región o por tipo? ¿Se agrega el filtro Sector que depende de la comuna (cascada con HTMX)?
- ¿El contador muestra solo «N resultados» o «N de M»? Lo segundo exige una consulta extra y un gancho para listados que restringen por permiso, como Documentos con los restringidos.
- ¿Se agregan encabezados de columna para ordenar (hoy `ordenes` no tiene interfaz) dentro de este mismo cambio o en otro?
- ¿Se aplica después la misma barra a /buscar y /calendario, que hoy tienen sus propios filtros fuera de ListaBase?
- Spec: ¿se actualiza specs/f15 (listados y filtros) o se abre specs/f24 «Barra de filtros»?

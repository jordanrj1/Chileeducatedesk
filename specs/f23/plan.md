# F23 Contenedor Territorio — Plan de implementación

> **Para quien ejecute:** usar superpowers:executing-plans (tarea por tarea, TDD). Los pasos usan casillas `- [ ]`.

**Meta:** convertir comuna y sector en contenedores con resumen, agrupaciones, personas, alcance y exportación, y dejar el detector visual en 0.

**Arquitectura:** un servicio de consultas agregadas (`apps/territorio/resumen.py`) alimenta pestañas nuevas de `ComunaFicha` y `SectorFicha` y el índice. Las plantillas reutilizan los componentes del sistema de diseño (`fche-kpi`, `fche-tarjeta`, `fche-items`, tabla) y el parcial de alcance de F22. La exportación reutiliza `apps/nucleo/exportacion`.

**Stack:** Django 5.2, PostgreSQL 17, Bootstrap 5.3 local, HTMX, pytest-django.

**Spec:** `specs/f23/spec.md` (programa: `docs/rediseno_integral.md`).

## Restricciones globales
- Interfaz, nombres y commits en español; commits **sin** Co-Authored-By ni marcas de herramientas.
- Migraciones solo aditivas; nada se borra; sin dependencias nuevas; sin CDN.
- Datos de prueba ficticios (skill `fche-datos-ficticios`); nada sensible en resúmenes ni exportaciones sin permiso (`fche-ley-datos`).
- Sin consultas en bucle: conteos con `annotate`/`aggregate`/`values().annotate()`.
- Pruebas: `.venv/bin/python -m pytest -q`; las 475 actuales siguen en verde.

## Foco de revisión
1. Comuna sin ningún dato → resumen con ceros y estados vacíos que enseñan (no error).
2. Persona con dos direcciones de residencia vigentes en comunas distintas → cuenta como residente en ambas, una vez por comuna.
3. Sector con hijos y nietos → el resumen del padre suma a todos sus descendientes sin duplicar.
4. Actividad con agenda en un lugar de la comuna **y** territorio de la comuna → cuenta una sola vez.
5. Gestor sin `personas.view_persona` o sin `exportar_persona` → no ve la pestaña Personas; la exportación omite RUT y contactos.

---

### Task 1: Deuda visual del detector
**Archivos:** modificar `static/css/fche.css` (alertas, `.fche-nivel`, `.fche-prosa blockquote`, `.fche-indice a`, `.fche-error__codigo`), `templates/nucleo/dashboard.html` (etiqueta del día), `templates/actividades/candidatos.html` (icono), `templates/cuentas/login.html` (texto del panel).
- [ ] Alertas y niveles: sin `border-left` grueso; fondo tintado, borde de 1 px del mismo tono e icono como marcador.
- [ ] Cita e índice: fondo suave o subrayado del ítem activo, sin barra lateral.
- [ ] Código de error con color sólido.
- [ ] Etiqueta del día de 0.72rem como mínimo y espaciado ≤ 0.05em; icono de candidato con relleno interno; contraste AA en el panel de ingreso.
- [ ] Ejecutar `impeccable detect --json templates static/css/fche.css` → `[]`.
- [ ] Pruebas completas en verde; commit «Detector visual en cero: sin acentos laterales ni texto degradado».

### Task 2: Servicio de resumen territorial
**Archivos:** crear `apps/territorio/resumen.py`; prueba `apps/territorio/test_resumen.py`.
**Interfaces (produce):**
- `personas_residentes(comuna=None, sectores=None) -> QuerySet[Persona]` (distinct, solo activas).
- `resumen_territorio(comuna=None, sectores=None) -> dict` con claves `comunidades`, `organizaciones`, `personas`, `lugares`, `actividades_12m`, `actividades_total`, `organizaciones_por_tipo` (lista de `(TipoOrganizacion, total, [Organizacion…≤5])`), `sectores` (lista de dicts `{"sector", "comunidades", "organizaciones", "lugares", "personas", "actividades"}` + fila `sector=None`), `proximas` (agendas ≤30 días), `minutas` (≤5 `SesionActividad`).
- `presencia_por_comuna(region=None) -> list[dict]` con `{"comuna", "comunidades", "organizaciones", "personas", "actividades_12m", "total"}`, solo total > 0, ordenada por `(-actividades_12m, -total, nombre)`.
- [ ] Pruebas que fallan primero:
  - `test_residentes_por_comuna_y_sector_con_hijos`;
  - `test_resumen_cuenta_una_vez_actividad_con_agenda_y_territorio`;
  - `test_resumen_comuna_vacia_en_cero`;
  - `test_organizaciones_agrupadas_por_tipo_maximo_5_nombres`;
  - `test_tabla_de_sectores_con_fila_sin_sector`;
  - `test_presencia_ordenada_y_sin_comunas_vacias`;
  - `test_resumen_consultas_acotadas` (`django_assert_max_num_queries(20)` con 1 y con 30 registros).
- [ ] Implementar; pruebas en verde; commit.

### Task 3: Ficha de comuna y sector como contenedor
**Archivos:**
- modificar `apps/territorio/views.py` (`_FichaTerritorio`, `ComunaFicha`, `SectorFicha`: pestañas `resumen` (primera), `personas`, `alcance`; organizaciones agrupadas; acciones de cabecera);
- crear `templates/territorio/pestanas/resumen.html`, `templates/territorio/pestanas/personas.html` y `templates/territorio/ficha.html` (cabecera con región › provincia, municipalidad y acciones);
- modificar `templates/territorio/pestanas/organizaciones.html` (grupos por tipo);
- pruebas en `apps/territorio/test_contenedor.py`.

**Consume:** Tarea 2; `apps.actividades.alcance.alcance`; `actividades/pestanas/alcance.html`.
- [ ] Pruebas que fallan primero:
  - `test_comuna_abre_en_resumen_con_indicadores_clicables` (cada indicador enlaza a `?tab=`);
  - `test_pestana_personas_separa_residentes_y_no_muestra_sensibles` (con `PerfilSensible` presente, su contenido no aparece);
  - `test_pestana_personas_oculta_sin_permiso`;
  - `test_alcance_de_la_comuna_coincide_con_servicio`;
  - `test_sector_incluye_hijos`;
  - `test_pestanas_bajo_tope_de_consultas`.
- [ ] Implementar; pruebas en verde; commit.

### Task 4: Índice «Dónde trabajamos» y región
**Archivos:** modificar `apps/territorio/views.py` (`TerritorioIndice`, `RegionDetalle`), `templates/territorio/indice.html`, `templates/territorio/region.html`; crear el parcial `templates/territorio/_comunas_con_presencia.html`.
- [ ] Pruebas: `test_indice_muestra_comunas_con_presencia_primero`, `test_indice_vacio_ofrece_acciones`, `test_region_lista_sus_comunas_con_presencia`.
- [ ] Implementar; pruebas en verde; commit.

### Task 5: Crear en contexto y enlaces «en esta comuna»
**Archivos:**
- modificar `OrganizacionNueva` (`apps/organizaciones/views.py`) y `LugarNuevo` (`apps/lugares/views.py`) (`get_initial`/form de dirección con `comuna`);
- modificar `apps/actividades/views.py` (`ActividadNueva`: crea `ActividadTerritorio(comuna=…)`);
- modificar las cabeceras de `templates/personas/ficha.html`, `organizaciones/ficha.html`, `lugares/ficha.html` y `actividades/ficha.html`;
- contexto nuevo `comuna_residencia` en `PersonaFicha`.
- [ ] Pruebas: `test_nueva_organizacion_con_comuna_prellenada`, `test_nuevo_lugar_con_comuna_prellenada`, `test_nueva_actividad_con_comuna_crea_territorio`, `test_fichas_enlazan_a_su_comuna`.
- [ ] Implementar; pruebas en verde; commit.

### Task 6: Exportar resumen territorial
**Archivos:**
- modificar `apps/territorio/models.py` (`Comuna.Meta.permissions += [("exportar_territorio", "Puede exportar resúmenes territoriales")]`) y crear la migración;
- crear `apps/territorio/exportar.py` con `libro_territorial(usuario, comuna=None, sectores=None, titulo="") -> Workbook`;
- vistas `ComunaExportar` y `SectorExportar`;
- rutas `territorio/comunas/<pk>/exportar` y `territorio/sectores/<pk>/exportar`.
- [ ] Pruebas: `test_exportacion_con_7_hojas`, `test_exportacion_403_sin_permiso`, `test_exportacion_sin_rut_ni_contactos_sin_exportar_persona`, `test_exportacion_queda_en_auditoria`.
- [ ] Implementar (aviso con `agregar_aviso`, auditoría con `registrar`); pruebas en verde; commit.

### Task 7: Cierre
- [ ] `docs/manual_de_uso.md` (sección Territorio como contenedor), docs/CONTEXTO.md §0.5 y `specs/f23/tasks.md` con `[x]`.
- [ ] Skill `fche-revision`: pruebas completas, recorrido de páginas, capturas de escritorio y celular de `/territorio` y de la ficha de comuna, una ronda de correcciones.
- [ ] Detector de impeccable sobre lo cambiado → 0.
- [ ] Merge a `main` (`--no-ff`), reinicio del servidor.

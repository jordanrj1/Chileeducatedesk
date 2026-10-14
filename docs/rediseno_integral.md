# Rediseño integral de FCHE guiado por skills

Diseño del programa (13-10-2026). Contexto de producto: `PRODUCT.md`. Reglas: `docs/CONTEXTO.md`. Cada subproyecto tiene su spec en `specs/fXX/` y se construye solo después de aprobado.

## Intención
Que FCHE funcione como **banco territorial**: cada entidad (comuna, sector, comunidad, organización, persona, proyecto) es un **contenedor** que reúne y enlaza lo que se sabe de ella. Con pocos clics, Claudio opera, la Dirección ve el trabajo por territorio y un informe para un fondo sale sin rearmarlo a mano. Los formularios capturan todo lo útil por secciones y se adaptan al tipo de entidad. El banco crece con nuevas juntas, instituciones, municipalidades y tipos, sin programar lo esencial.

## Decisiones tomadas por el usuario (13-10-2026)
- Uso en **oficina y terreno**: escritorio primero; las pantallas de terreno (asistencia, minuta, llegada) pensadas para celular.
- La información sirve a **Claudio**, a la **Dirección** y a **fondos y aliados**.
- Escalabilidad **mixta**: datos clave de cada tipo fijos y validados, más **campos propios por tipo** definidos por el Gestor en Catálogos.
- Se empieza por el contenedor **Territorio**.

## Metas
1. Contenedores con resumen arriba (indicadores clicables), detalle a una pestaña y enlaces hacia arriba (territorio) y hacia los lados (entidades relacionadas).
2. Formularios catalogados por tipo de entidad: secciones fijas por tipo, más una sección de campos propios configurables, y validación en el servidor.
3. Exportaciones listas para informes (Excel, sin datos sensibles salvo permiso).
4. Base de datos que crece ordenada: diccionario de datos, índices donde se consulta, integridad declarada y plan de crecimiento.

## No metas
- Mapas con teselas o geocodificación: requieren internet y no hay coordenadas confiables.
- Portal público, autoservicio o cuentas para personas registradas.
- Reescribir lo que funciona: se reutilizan ListaBase, FichaBase, `urls_hijo`, el servicio de alcance y el sistema de diseño.

## Anti-metas (sería un fracaso aunque funcione)
- Un contenedor que tarda en cargar porque cuenta todo con consultas en bucle.
- Formularios que obligan a llenar campos para poder guardar.
- Campos configurables que se vuelven un «Excel dentro del sistema»: sin tipo de dato, sin validación ni orden.
- Datos sensibles que se filtran a un resumen, a una exportación o a un contenedor sin permiso.
- Romper las 475 pruebas existentes o una regla de docs/CONTEXTO.md (sin borrado físico, sin CDN, español, datos ficticios).

## Restricciones
Django + PostgreSQL + Bootstrap 5.3 + HTMX locales. Migraciones solo aditivas. Sin dependencias nuevas fuera de docs/CONTEXTO.md §5. Ley 21.719: lo sensible sigue la skill `fche-ley-datos`.

## Subproyectos, en orden, con sus skills

| # | Subproyecto | Qué entrega | Skills que mandan |
|---|---|---|---|
| F23 | **Contenedor Territorio** | Índice «Dónde trabajamos», ficha de comuna y sector como centro (resumen, organizaciones por tipo, sectores, comunidades, personas residentes, actividades, alcance, exportación), enlaces «en esta comuna» desde cada ficha, y corrección de los hallazgos del detector visual | impeccable (shape, layout, critique), ui-ux-pro-max, fche-feature, fche-ley-datos, fche-revision |
| F24 | **Cascada, buscadores y fichas por tipo** (reemplaza la versión con JSONB: el usuario pidió tablas relacionales normalizadas, 14-10-2026) | Buscadores que muestran a los registrados y crean en el momento, selección múltiple desplegable, filtros compactos, territorio oficial de Chile (CUT), ubicación en cascada, tramos de edad catalogados, «¿Dónde?» en actividad y proyecto, formularios claros; fichas por tipo de persona (estudiante, vecino, invitado) en tablas propias. Spec en `specs/f24/` | superpowers (TDD), impeccable (clarify, harden), fche-ley-datos |
| F25 | **Contenedor Organización** | Ficha de junta, institución o municipalidad como centro: personas y cargos, estudiantes por carrera, actividades, comunidades que representa, sedes y lugares, alcance y exportación | impeccable, emil-design-eng |
| F26 | **Contenedores Comunidad y Proyecto, e informes** | Resumen y exportación por comunidad y proyecto (alcance, horas, beneficiarios, sesiones) en el formato que piden fondos y aliados | impeccable, stop-slop (texto de informes) |
| F27 | **Panel de Dirección** | Vista general por territorio, línea temática y período, con tendencias y enlaces a cada contenedor | impeccable (layout, colorize), ui-ux-pro-max |
| F28 | **Base de datos** | Diccionario de datos, diagrama actualizado, índices y restricciones revisados, plan de crecimiento y respaldo; acompaña a cada subproyecto y se consolida aquí | security-guidance, fche-ley-datos |
| F29 | **Terreno, pulido y calidad** | Pantallas de terreno para celular (mobile-native), pulido y auditoría (impeccable polish y audit), revisión de seguridad, pyright, revisión de código, manual y docs/CONTEXTO.md al día | mobile-native, impeccable, pyright-lsp, code-review, stop-slop |

Cada subproyecto pasa por: spec → plan → construcción con pruebas → `fche-revision` (pruebas, recorrido de páginas, capturas) → commit sin marcas de autoría.

## Lo que se deja al constructor
Nombres internos, la forma exacta de cada consulta (siempre sin consultas en bucle), el orden visual dentro de cada resumen, siguiendo `PRODUCT.md` y el sistema de diseño vigente.

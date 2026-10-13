# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Claudio (rol Gestor), usuario principal y único digitador.** Coordina las actividades de la Fundación Chile Edúcate: recibe solicitudes, arma actividades con estudiantes de instituciones educativas, voluntarios y talleristas, y las lleva a comunidades de un sector o comuna. Trabaja **en la oficina** (fichas, planillas de instituciones, documentos, informes) y **en terreno** desde el celular (pasar asistencia, registrar a quien llega, anotar la minuta de la sesión).
- **Administrador** (programador): mantiene usuarios, roles, catálogos y respaldos. Ve los datos solo para mantenimiento.
- **Destinatarios de la información** (no operan el sistema; reciben lo que Claudio extrae): la **Dirección de la Fundación** (visión por territorio, línea temática y período), y **fondos y aliados** (universidades, municipalidades, financistas) que piden informes de alcance, horas y beneficiarios.
- Las personas registradas (estudiantes, vecinos, voluntarios, dirigentes) **no tienen cuenta** ni acceso: existir en el banco no implica cuenta.

## Product Purpose

Centralizar en un solo banco de datos lo que hoy está disperso en Word, PDF, Excel, minutas y mensajes: personas, organizaciones (juntas de vecinos, instituciones educativas, municipalidades, empresas, ONG), comunidades, lugares y territorio, que se registran **una sola vez** y se reutilizan en cada actividad, acumulando historial.

Flujo central: solicitud u oportunidad → actividad (opcionalmente dentro de un proyecto) → coordinación → ejecución por sesiones → resultados → historial → banco enriquecido.

Éxito: con **pocos clics** Claudio sabe a quién invitar, qué falta y qué pasó; la Dirección ve el trabajo por territorio; un informe para un fondo sale del sistema sin reconstruirlo a mano.

## Positioning

No es un CRM genérico ni un gestor de eventos: es el **banco territorial** de una fundación chilena. El territorio (región → comuna → sector) y las comunidades son el eje que conecta personas, organizaciones y actividades; cada actividad deja quién la ejecutó, a quién fue dirigida, quién asistió y qué se acordó, con trazabilidad de la fuente de cada dato.

## Operating Context

- Se instala **local en Windows** (también corre en Mac); funciona **sin internet**; servidor waitress; respaldos diarios con `pg_dump`.
- La información de estudiantes llega como **planillas** de las instituciones: se carga con vista previa, detección de duplicados y reversión.
- Documentos históricos (PDF, Word) son **evidencia**: se adjuntan y se transcribe solo el dato estructurado.
- En terreno la conexión puede ser mala y la pantalla es un celular: las acciones de terreno deben funcionar con una mano y pocas pulsaciones.

## Capabilities and Constraints

- Stack fijo: Django + PostgreSQL + plantillas con Bootstrap 5.3 y HTMX, todo servido localmente (sin CDN ni servicios externos, sin fuentes web externas).
- Interfaz en **español de Chile**; terminología del dominio: ficha, junta de vecinos, unidad vecinal, comuna, sector, RUT, apoderado, minuta, sesión, alcance.
- Nada se elimina físicamente: se desactiva, se archiva, se revoca o se cierra; todo cambio queda en el historial.
- Crear nunca se bloquea por datos faltantes; los mínimos se exigen al confirmar y al finalizar una actividad.
- **Escalabilidad de entidades (decidido 13-10-2026, modelo mixto):** cada tipo de entidad tiene sus datos clave fijos y validados en el código, y además el Gestor puede agregar campos propios por tipo desde Catálogos, sin programar.
- Segunda fase (reuniones con compromisos, tareas, beneficiarios, verificaciones, finanzas) existe pero se oculta por ajuste; las sesiones con minuta están siempre visibles.
- Sin portal público, sin autoservicio, sin WhatsApp, IA, pagos ni automatizaciones.

## Brand Commitments

- Nombre: **Fundación Chile Edúcate (FCHE)**; el sistema se presenta como «FCHE».
- Identidad visual vigente del sistema (azul institucional, estrella blanca como sello): ver `static/css/fche.css`. No hay manual de marca de la Fundación en el repositorio.

## Evidence on Hand

- Requerimientos oficiales y decisiones en `docs/CONTEXTO.md`, `specs/` y `specs/trazabilidad_requerimientos.md`; escenarios en `docs/escenarios_estado.md`.
- Datos de demostración **ficticios** (`cargar_demo`). Documentos reales en `docs/reales/` (fuera de git): no se copian ni se citan.
- No hay testimonios, métricas de uso ni casos publicados: no inventarlos.

## Product Principles

1. **El territorio es el contenedor.** Toda ficha responde «¿dónde?» y enlaza hacia arriba (comuna) y hacia los lados (comunidades, organizaciones, actividades).
2. **Registrar una vez, ver en todas partes.** Un dato se ingresa en un solo lugar y aparece en cada contenedor que lo necesita, con un clic de distancia.
3. **Más contexto, menos clics.** Cada ficha muestra su resumen y alcance arriba; el detalle está a una pestaña, nunca a una búsqueda.
4. **Captura generosa, protección estricta.** Pedir todo lo útil para el banco, por secciones y opcional; lo sensible, restringido y con consentimiento (Ley 21.719).
5. **Crece sin programar lo esencial.** Nuevos tipos y nuevas entidades (juntas, instituciones, municipalidades) se incorporan desde la interfaz.

## Accessibility & Inclusion

- Uso intensivo de teclado en oficina (atajos, foco visible) y uso táctil en terreno (objetivos de toque amplios, una mano).
- Contraste AA, `prefers-reduced-motion` respetado, formularios con etiquetas explícitas y errores en texto.

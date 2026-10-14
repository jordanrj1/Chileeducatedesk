# Revisión de alcance

Auditoría del 14-10-2026. Aquí se lista lo que **no** debería estar según tu documento («fuera del alcance: fotos o galería, acceso desde celular, exportaciones masivas, portal público, mensajería, dinero»), y dónde está. **No se quitó nada.** Cada punto termina con una propuesta y espera tu decisión.

## 1. Fotos, galería o tratamiento de imágenes

| Qué hay | Dónde | Comentario |
|---|---|---|
| Los documentos aceptan `.jpg`, `.jpeg` y `.png` (además de PDF, Word, Excel, PowerPoint, `.mp3` y `.mp4`) | `apps/documentos/models.py:14` | No hay galería, ni miniaturas, ni edición, ni nada especial para imágenes. Una imagen se guarda igual que un PDF: como evidencia adjunta a una ficha. |
| Al transcribir, el documento se muestra al lado del formulario | `templates/documentos/transcribir.html:12` | Si es una imagen, el navegador la muestra. Es la misma vista para cualquier tipo de archivo. |
| Consentimiento «Uso de imagen (fotos y videos)» | `apps/personas/models.py` (modelo `Consentimiento`, campo `tipo`) | Solo registra si la persona autorizó que la fotografíen. No guarda fotos. |
| Una prueba sube «fotos.png» como evidencia | `apps/nucleo/test_escenarios.py:53` | Es solo un nombre de archivo de prueba. |
| **Las capturas PNG que mencioné en mensajes anteriores** | `scripts/revision/capturar.py` | Son fotos de pantalla que yo tomaba para revisar el diseño. Son una herramienta de desarrollo, **no una función del sistema**. Claudio nunca las ve. |

**Propuesta:** decide si los documentos deben aceptar imágenes, audio y video. Hoy la lista de tipos permitidos es una línea de código (`EXTENSIONES_PERMITIDAS`). Si quieres solo documentos (PDF, Word, Excel), se quitan `.jpg`, `.jpeg`, `.png`, `.mp3` y `.mp4` de esa línea.

## 2. Acceso desde celular o exposición fuera del equipo

| Qué hay | Dónde | Comentario |
|---|---|---|
| El servidor **solo escucha en el propio equipo** | `iniciar.bat:33`, `iniciar.sh:28` (`127.0.0.1:8000`); `.env.example:5` | Ningún otro computador ni celular puede entrar. Está bien según tu alcance. |
| Las pantallas se adaptan a anchos chicos | `templates/base.html:5`; 13 reglas `@media` en `static/css/fche.css`; el calendario pasa a lista en pantallas angostas (`static/js/calendario.js:8`) | Es diseño adaptable, el estándar de Bootstrap. **No es una aplicación de celular** ni abre el acceso. Sirve también si la ventana del navegador se achica. |
| Instrucciones para abrir el acceso a la red de la Fundación «[V#5]» | `docs/entrega.md`, sección «Acceso desde otros equipos o celulares»; `.env.example` (`CSRF_TRUSTED_ORIGINS`) | Son solo instrucciones. No se activa nada. |
| **El plan F24–F29 habla de «terreno desde el celular»** | `PRODUCT.md` (Usuarios, Operating Context); `docs/rediseno_integral.md` (decisión «oficina y terreno», F29 «pantallas de terreno para celular») | Esto salió de una respuesta tuya del 13-10 («oficina y terreno»), que yo interpreté como celular. **Contradice tu documento de alcance.** F29 no está construido. |

**Propuesta:** corregir `PRODUCT.md` y `docs/rediseno_integral.md` para quitar el celular y la «pantalla de terreno», y dejar HU-DA-06 como «fuera de alcance». Mantener el diseño adaptable, que no cuesta nada y no abre el acceso.

## 3. Exportaciones, importación de planillas, notificaciones y mensajería

**Exportaciones a Excel (11 rutas).** Todas exigen un permiso propio, quedan en la auditoría y llevan un aviso de confidencialidad:

| Qué exporta | Ruta | Origen |
|---|---|---|
| El listado que estás viendo, con sus filtros: personas, organizaciones, lugares, comunidades, proyectos, actividades, solicitudes y tareas | `/personas/exportar`, `/organizaciones/exportar`, `/lugares/exportar`, `/comunidades/exportar`, `/proyectos/exportar`, `/actividades/exportar`, `/solicitudes/exportar`, `/tareas/exportar` | HU-BU-04 [O] |
| Todos los datos de una persona, para entregárselos si los pide (derecho de acceso de la ley de datos) | `/personas/<id>/datos-personales` | Ley 21.719 |
| Resumen de una comuna o sector (7 hojas) | `/territorio/comuna/<id>/exportar`, `/territorio/sector/<id>/exportar` | F23 (tu pedido del 13-10) |
| Movimientos de dinero | `/finanzas/exportar` | 2.ª fase, oculta |

**Importación de planillas** (`apps/importaciones/`, ruta `/importaciones`):
- **Listado de participantes de una actividad.** Es oficial [O, doc 06] y es HU-AT-10 y HU-IG-03 de tus requerimientos.
- **Personas, organizaciones o lugares sueltos** (banco histórico). Está marcado [V] (IG-06): el tutor pudo dejarlo fuera de esta etapa.

**Notificaciones:** **no hay**. El sistema no envía correos ni avisos (no existe `send_mail` ni configuración de correo). El Panel muestra lo pendiente cuando Claudio entra; eso no es una notificación.

**Mensajería:** **no hay**. Las interacciones solo *registran* que hubo una llamada o un correo (`apps/coordinacion/`).

**Propuesta y pregunta:**
- Tu documento de alcance pone «exportaciones masivas» e «importación de planillas» fuera.
- Pero tus requerimientos (HU-BU-04, HU-AT-10, HU-IG-03) los piden.
- ¿Cuál manda? Mi sugerencia:
  - dejar la exportación del listado filtrado y la carga de participantes por actividad;
  - ocultar la importación de personas, organizaciones y lugares sueltos hasta que Manuel la confirme.

## 4. Módulos de dinero

| Qué hay | Dónde | Visible hoy |
|---|---|---|
| App **finanzas**: movimientos (gasto, aporte, donación) con **monto en pesos** y presupuesto por proyecto | `apps/finanzas/models.py:15`, `:34`; rutas `/finanzas…` | **No.** Está oculta: con `SEGUNDA_FASE=False` la ruta da «no existe» (`apps/nucleo/fases.py:15`). |
| Pestaña «Presupuesto» del proyecto | `apps/proyectos/views.py:97`; `templates/proyectos/pestanas/presupuesto.html` | No (oculta) |
| Postulaciones a fondos (sin montos: fondo, fecha, estado, resultado) | `apps/proyectos/models.py:84` | No (oculta) |
| **Donadores y colaboradores como tipo de vínculo, sin montos** | Catálogo «tipos de intervención»: *aporta recursos*, *aporta personas*, *facilita espacio*… Contactos de la Fundación con propósito «donaciones» (`apps/personas/models.py:178`) | **Sí.** Es lo que pide tu documento. |

**Propuesta:** como el dinero está fuera de alcance, quitar la app `finanzas` y la pestaña Presupuesto, o dejarlas ocultas como están. Quitar una app con tablas exige una migración: es «borrar», así que requiere tu permiso explícito.

## 5. Portal público o cuentas para alumnos o voluntarios

**No hay.**
- Toda pantalla exige ingresar (`config/settings/base.py:49`). Solo se abren sin sesión `/login`, `/salud` (comprueba que la base responde) y las pantallas de error (`apps/nucleo/views.py:14-36`).
- Las cuentas se crean solo desde Administración y solo con los roles Gestor o Administrador (`cuentas/tests.py:45`).

## 6. Dependencias fuera de docs/CONTEXTO.md §5

**Ninguna en el sistema.** `requirements.txt` tiene exactamente las permitidas.

En la Mac de desarrollo se instalaron herramientas **para programar**, con tu permiso del 13-10: Node, Bun, pyright y complementos del editor. **No son parte del sistema** y no se instalan en el computador de la Fundación. La carpeta `scripts/revision/` guarda las herramientas de revisión de pantallas; el sistema no las usa.

## 7. Recursos que se cargan desde internet

**Ninguno.**
- Bootstrap, HTMX y FullCalendar están en `static/vendor/`.
- La prueba `nucleo/tests.py:85` (test_sin_recursos_externos) lo verifica en cada ejecución.
- La única excepción es el «sitio web» de una organización: si Claudio lo escribe, la ficha muestra un enlace que abre esa página afuera.

## 8. Cosas que se agregaron más allá del núcleo

Esto responde a «siento que has idealizado el proyecto». Todo está construido y probado, pero **no es el núcleo** que describes (entrar, crear actividades, agregar personas, organizaciones, lugar y fecha):

| Agregado | Cuándo y por qué | Peso en pantalla |
|---|---|---|
| **Datos sensibles, consentimientos y apoderados** (género, pueblo originario, salud, discapacidad, previsión, Registro Social de Hogares) | F22, tu respuesta «sección restringida» | Pestañas con 🔒 en la ficha de persona (emergencia, datos sensibles, apoderados, verificaciones) y Consentimientos. `DATOS_SENSIBLES=False` oculta la de datos sensibles. |
| **Comunidades** (grupos con integrantes) | F22, tu respuesta «registro propio». Es lo más cercano a tu «grupo». | Menú propio y pestañas en comuna y actividad |
| **Territorio como contenedor** y Excel territorial | F23, aprobado por ti el 13-10 | Ficha de comuna con 9 pestañas |
| **Búsqueda de candidatos** con razones | F16 (matching [V]) | Botón en Participantes |
| **Unir fichas repetidas** | Escenarios PE-E14 y OR-E1 | Solo para el Administrador |
| **Constancia de participación** imprimible | Escenarios | Botón por participante |
| **Serie de actividades** (taller semanal) | HU-AG-07 [P] | Botón en la ficha |
| **Segunda fase**: reuniones, tareas, beneficiarios, verificaciones, postulaciones y finanzas | Requerimientos, «segunda fase» | Oculta |
| **Plan F24–F29** (campos configurables por tipo, panel de Dirección, celular) | `docs/rediseno_integral.md`, `PRODUCT.md` | Solo documentos; **nada construido** |

**Propuesta:** antes de seguir con F24, decide qué de esta tabla se queda visible para Claudio. Lo más simple para el día a día:
- dejar ocultos los datos sensibles y la segunda fase;
- agrupar las pestañas de la ficha de persona.

# F22 — Ingesta ampliada: personas, estudiantes, comunidades, público de la actividad y bitácora de sesiones

Fuente: pedido del 13-10-2026 («reformular las ingestas de datos… que el software actúe como centro y banco de datos de una población»). Decisiones tomadas ese día con el usuario:
- datos sensibles en **sección restringida** con consentimiento registrado y ajuste en `.env`;
- **bitácora de sesiones (minutas y avances) visible desde ya**, fuera de la segunda fase;
- **Comunidad como registro propio**.

## Qué y por qué
La actividad la realizan personas y va dirigida a personas. Hoy el sistema solo guarda nombre, identificador y contacto. Con eso no se puede responder:
- quién **ejecutó** la actividad (equipo de la Fundación, estudiantes y su institución, talleristas);
- quién **asistió** y de qué **comunidad** venía;
- a quién **iba dirigida** (público objetivo, rango etario, comunidades);
- qué se hizo en **cada sesión** (minuta, avances, acuerdos, incidencias, evidencias).

F22 amplía la ingesta para que cada actividad deje un registro completo y reutilizable. El orden es proyecto → actividad → sesiones, con equipo, participantes, comunidad, lugar y fechas.

## Principios
- **Crear nunca se bloquea** (docs/CONTEXTO.md §10): todo campo nuevo es opcional. Los formularios se ordenan por secciones.
- **Minimización [O, RNF-02]:** cada campo tiene un uso concreto (ver la columna «para qué»). No se piden número de matrícula, estado civil, religión, afiliación política ni tallas.
- **Datos sensibles (Ley 21.719, vigente el 01-12-2026):** salud, discapacidad, origen étnico, situación socioeconómica e identidad de género.
  - Van en una sección aparte, visible solo con `personas.ver_sensibles`.
  - Se guardan solo si hay un consentimiento vigente de tipo «datos sensibles».
  - Se apagan con `DATOS_SENSIBLES=False` [V: validar con el tutor].
- **Menores de edad [V#2]:** se calculan desde la fecha de nacimiento. La ficha avisa si falta el apoderado o la autorización del apoderado. No se bloquea el registro.
- Nada se borra: consentimientos, membresías y sesiones se revocan, se cierran o se marcan como no vigentes.

## Formularios de ingesta (catálogo de campos)

### 1. Persona: ficha completa (sección general)
| Sección | Campo | Para qué | Etiqueta |
|---|---|---|---|
| Identificación | nombres, apellidos, RUT u otro documento | identificar sin duplicar | [O] |
| | nombre social | dirigirse a la persona como lo pide | [P] |
| | fecha de nacimiento | edad, menores de edad, rango etario de los informes | [D] |
| | nacionalidad | personas extranjeras (documento distinto del RUT) | [P] |
| Perfil | perfiles (estudiante, vecino/a, voluntario/a, tallerista o profesional, dirigente social, docente, funcionario/a institucional, beneficiario/a, apoderado/a) | filtrar el banco por tipo de persona | [P] |
| | nivel educacional | caracterizar a la comunidad y a los beneficiarios | [P] |
| | situación ocupacional, profesión u oficio | idem; profesión ya existía | [P]/[O] |
| Intereses | áreas de interés (catálogo de áreas temáticas) | invitar a la persona a las actividades que le interesan (matching) | [P] |
| | habilidades y conocimientos, idiomas | buscar talleristas y voluntarios | [D] ficha de voluntario |
| | canal de contacto preferido | contactar por la vía que responde | [P] |
| Registro | origen, estado del registro, observaciones | ya existían | [O] |

### 2. Persona: datos sensibles 🔒 (sección restringida)
Solo con `ver_sensibles` y un consentimiento vigente de tipo «datos sensibles».
- **Género**, para estadísticas desagregadas. Se trata como sensible [V: si el tutor confirma que el sexo registral es dato general, pasa a la sección 1].
- **Pueblo originario** (Ley 19.253 y modificaciones).
- **Discapacidad** y necesidades de apoyo o accesibilidad: para preparar el lugar y la actividad.
- **Condiciones de salud** relevantes para la actividad, alergias y restricciones alimentarias: para actividades con alimentación o esfuerzo físico.
- **Previsión de salud**: para emergencias en terreno.
- **Hogar**: jefatura de hogar, integrantes, tramo del Registro Social de Hogares. Sirve para focalizar beneficiarios y para los informes a fondos [V].

### 3. Consentimientos (por persona)
- **Tipo:** tratamiento de datos personales, datos sensibles, uso de imagen, contacto para futuras actividades, autorización del apoderado.
- **Otorgado o rechazado**, fecha, medio (formulario en papel, formulario digital, correo, verbal registrado) y documento de respaldo.
- **Quién lo otorga** (el apoderado, si es menor). Revocación con fecha.
- La ficha muestra el estado de cada tipo de consentimiento. Sin consentimiento vigente, la persona no se excluye. Solo hay dos efectos: no se guardan sus datos sensibles, y se avisa antes de usar su imagen.

### 4. Apoderados y tutores legales 🔒
Persona (menor) ↔ persona (apoderado), con parentesco y si es tutor legal. Se usa con los consentimientos del tipo «autorización del apoderado».

### 5. Estudiante (formación ampliada)
Ya existían institución, carrera, estado y años. Se agregan:
- sede o campus;
- jornada (diurna, vespertina, en línea);
- año o nivel que cursa;
- asignatura, programa o práctica vinculada (vinculación con el medio, aprendizaje + servicio);
- docente o tutor a cargo (una persona);
- horas comprometidas.

Las **horas realizadas** se calculan con las participaciones con asistencia, y alimentan constancias e informes a la institución.

### 6. Comunidad (registro nuevo) [P]
Grupo de personas que viven en un sector o comparten un espacio: vecinos de un sector, comunidad escolar, club de adulto mayor, comunidad indígena, agrupación.
- **Identificación:** nombre, tipo, comuna (obligatoria) y sector (opcional, debe ser de la comuna), organización que la representa (p. ej., la junta de vecinos).
- **Caracterización:** descripción, población estimada, rango etario predominante, áreas de interés, diagnóstico y necesidades, referente o dirigente principal.
- **Padrón:** personas integrantes con rol (integrante, dirigente/a, referente, vocero/a), desde y hasta.
- **Alcance:** actividades y proyectos dirigidos a ella, personas de la comunidad que asistieron y asistentes sin registro individual.

### 7. Actividad: público y equipo
- **Línea o área temática** del proyecto (catálogo de áreas temáticas). Es el «subconjunto o categoría» del proyecto.
- **Público objetivo** (texto), rango etario y beneficiarios estimados.
- **Comunidades** a las que va dirigida (varias), con beneficiarios estimados por comunidad.
- **Equipo frente a asistentes:** cada rol de participación pertenece a un grupo:
  - **equipo ejecutor:** estudiante, practicante, ayudante, voluntario, tutor, tallerista, coordinador;
  - **asistentes:** participante, beneficiario;
  - **contacto:** contacto institucional.
- **Participación ampliada:**
  - institución de procedencia, que se completa sola con la formación vigente;
  - comunidad de procedencia, que se completa sola con la membresía vigente;
  - horas, que se completan solas con la duración de la programación vigente.

### 8. Proyecto
Área temática, comunidades a las que va dirigido y pestaña **Alcance**: personas únicas, equipo frente a asistentes, instituciones, comunidades, horas y sesiones.

### 9. Bitácora de sesiones: minuta y avances (visible desde ya)
Por cada sesión de una actividad se registra:
- n.º, nombre, fecha, horario y lugar;
- **facilitadores**;
- objetivo de la sesión, **desarrollo** (qué se hizo), **avances**, **acuerdos**, **incidencias** y **próximos pasos**;
- **asistencia por sesión** de los participantes registrados;
- **asistentes sin registro individual** (conteo agregado, sin datos personales): total, por tramo de edad (0–17, 18–29, 30–59, 60+) y por género (mujeres, hombres, otro o no informado);
- **evidencias**: documentos asociados a la sesión;
- quién redactó la minuta y cuándo.

### 10. Carga de planillas (personas y listados de actividad)
Columnas nuevas reconocidas:
- fecha de nacimiento, nacionalidad;
- comuna de residencia y dirección: crean la dirección de residencia;
- sede, jornada, año que cursa y asignatura: completan la formación;
- nivel educacional y perfil.

## Criterios de aceptación
1. La ficha completa de persona se muestra por secciones y guarda los campos nuevos. La edad y «menor de edad» se calculan.
2. Sin consentimiento vigente de datos sensibles no se pueden guardar datos sensibles. Sin `ver_sensibles` la sección no se ve (403 si se entra por URL). Con `DATOS_SENSIBLES=False` desaparece.
3. Un menor sin apoderado o sin autorización del apoderado muestra un aviso en su ficha.
4. Se crea una comunidad con su padrón. Una actividad se dirige a una o más comunidades. La comuna muestra sus comunidades.
5. La participación registra institución, comunidad y horas, y las completa sola cuando hay dato.
6. La bitácora de sesiones está visible sin segunda fase: crear, editar, asistencia por sesión, conteo agregado y evidencias.
7. Proyecto, actividad y comunidad muestran su alcance (personas únicas, equipo y asistentes, instituciones, comunidades, horas).
8. La planilla reconoce las columnas nuevas.
9. Todo nuevo modelo tiene historial y permisos. El Gestor opera y el Administrador ve.

## Pendiente de validar [V]
- Lista final de datos sensibles y su base legal con el tutor (Ley 21.719).
- Género como dato general o sensible.
- Plazo de conservación de los datos de menores [V#2].
- Tramos de edad de los informes: se proponen 0–17 (menores), 18–29 (jóvenes), 30–59 y 60+ (personas mayores, Ley 19.828).

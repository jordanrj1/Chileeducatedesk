# Lo que Claudio hace en el sistema
Procesos, cómo probarlos, qué cubre y qué no. En español simple.

Las rutas son las que define `docs/CONTEXTO.md`. La auditoría del repositorio confirma cuáles son las reales.

---

## 1. El sistema en una página

**Qué es.** Un portal que corre en un computador de la Fundación. Claudio entra, anota actividades y las completa con detalles: personas, organizaciones, lugar, fecha, documentos, contactos y cómo resultó.

**Quién lo usa.** Claudio (rol Gestor), que ingresa todo. El programador (rol Administrador), que cuida el sistema.

**Qué guarda.**
- Actividades.
- Personas: alumnos, participantes, voluntarios, tutores, contactos.
- Organizaciones: instituciones, colaboradores y donadores (ver pendiente en la sección 7).
- Lugares, con su zona y localidad.
- Documentos.
- Los contactos que hizo (llamadas, correos).
- El resultado de cada actividad.

**Dónde se guarda.**
- Los datos, en una base de datos (PostgreSQL) en el mismo computador.
- Los archivos, en una carpeta de documentos fuera del código.

**Idea que manda.** El sistema **avisa y casi nunca bloquea**. Claudio puede anotar una persona con solo el nombre, o una actividad sin fecha, y completarlo después.

**Qué no es.** Un portal para que la gente se inscriba, una aplicación de celular, una galería de fotos, un sistema de dinero, un enviador de mensajes.

---

## 2. Cómo se conectan los datos

```
  PERSONA ──vínculo──┐
                     ├── ACTIVIDAD ── fecha y hora (con versiones anteriores)
  ORGANIZACIÓN ──────┤                └─ lugar ── sector ── comuna ── provincia ── región
                     ├── documentos
  LUGAR ─────────────┤── contactos hechos (llamadas, correos)
                     └── resultado (asistencia, observaciones)
```

- Una **persona** se anota una sola vez. Después se la **vincula** a todas las actividades que haga falta. El vínculo guarda su papel (alumno, voluntario, tutor), si confirmó y si asistió.
- Una **organización** funciona igual. Su vínculo guarda cómo participó: colaboró, puso el lugar, trajo alumnos, donó.
- Un **lugar** también se anota una vez. Su ubicación sale de una cadena: región, provincia, comuna y sector (la localidad o la zona).
- La **actividad** es el centro de todo.
- El **historial** no se escribe aparte: sale de los vínculos. "Qué hizo Juan" es la lista de actividades donde Juan está vinculado.
- En la base de datos, cada vínculo es una tabla intermedia (por ejemplo, la que une persona con actividad). Guarda las dos puntas y los datos propios del vínculo.

---

## 3. Los 13 procesos

### P1 · Entrar y ver el panel
- **Para qué:** que solo entren personas autorizadas y que Claudio vea qué tiene pendiente.
- **Rutas:** `/login` → `/dashboard` → `/mi-cuenta`.
- **Qué guarda:** nada (solo la sesión).
- **Cómo probarlo:**
  1. Abrir la dirección sin haber ingresado: debe llevar al ingreso.
  2. Ingresar con el usuario Gestor: llega al panel.
  3. Poner una clave mala: el mensaje no dice qué dato falló.
  4. Como Administrador, desactivar la cuenta y volver a intentar: no entra.
  5. Cerrar sesión y pulsar Atrás: no debe mostrar datos.
- **Qué no hace:** no recupera la contraseña solo; la restablece el Administrador.

### P2 · Crear una actividad y completarla con el tiempo
- **Para qué:** anotar un evento aunque falten datos y completarlo después.
- **Rutas:** `/dashboard` → `/actividades` → `/actividades/nueva` → ficha `/actividades/<n>`.
- **Qué guarda:** la actividad (nombre, tipo, objetivo, descripción, estado, responsable).
- **Cómo probarlo:**
  1. Crear una actividad solo con nombre y tipo: se guarda.
  2. En la ficha, editar objetivo y descripción: quedan guardados.
  3. Cambiar el estado a "planificada": se ve en la lista.
  4. Intentar guardar sin nombre: avisa.
- **Qué no hace:** no exige fecha, lugar ni personas para crear. Los pide como aviso al confirmar.

### P3 · Agregar personas a la actividad
- **Para qué:** anotar quién participa, aunque todavía no esté registrado.
- **Rutas:** ficha de la actividad → pestaña Participantes → ventana para agregar → `/personas/<n>`.
- **Qué guarda:** la persona (si es nueva) y el vínculo con la actividad (papel y estado).
- **Cómo probarlo:**
  1. Buscar "Ana": si existe, seleccionarla y elegir su papel. Aparece en la lista.
  2. Buscar a alguien que no existe, pulsar [Crear persona], escribir solo el nombre y guardar: queda seleccionada. Asignarle un papel.
  3. Agregar a la misma persona con el mismo papel otra vez: avisa.
  4. Abrir la ficha de esa persona: la actividad aparece en su historial.
- **Qué no hace:** no crea una cuenta de usuario y no exige RUT.

### P4 · Agregar organizaciones, colaboradores y donadores
- **Para qué:** dejar claro quién más participó y cómo.
- **Rutas:** ficha de la actividad → pestaña Organizaciones → `/organizaciones/<n>`.
- **Qué guarda:** la organización (si es nueva) y el vínculo con la actividad (cómo participó).
- **Cómo probarlo:** igual que P3, eligiendo una organización y cómo participó (colaboró, puso el lugar, trajo alumnos, donó).
- **Qué no hace:** no lleva montos de dinero (ver pendiente en la sección 7).

### P5 · Dónde y cuándo
- **Para qué:** programar la actividad y cambiar la fecha sin perder la anterior.
- **Rutas:** ficha → pestaña Agenda → [Programar] → [Reprogramar] → `/calendario`.
- **Qué guarda:** cada programación como una versión (fecha, hora, lugar), con el motivo de los cambios.
- **Cómo probarlo:**
  1. Programar fecha, hora y un lugar existente.
  2. Crear un lugar nuevo desde ahí, con comuna y sector.
  3. Reprogramar con un motivo: la versión anterior queda visible como histórica.
  4. Abrir el calendario y hacer clic en el evento: abre la actividad.
  5. Dejar la actividad sin lugar y marcar solo la zona (por ejemplo "Hualpén"): se puede guardar.
- **Qué no hace:** no bloquea un choque de horario, solo avisa.

### P6 · Registrar contactos y pendientes
- **Para qué:** recordar a quién llamó, qué le dijeron y qué falta.
- **Rutas:** dentro de una actividad, persona u organización → [Registrar contacto].
- **Qué guarda:** fecha, tipo (llamada, correo, mensaje, reunión), con quién, resultado y próxima acción con fecha.
- **Cómo probarlo:**
  1. Registrar una llamada a una organización con una próxima acción para mañana.
  2. En el panel debe aparecer el pendiente.
  3. Abrir la ficha de la organización: se ve la llamada.
- **Qué no hace:** no envía mensajes. Solo registra.

### P7 · Guardar y ver documentos
- **Para qué:** tener a mano las cartas, minutas y certificados.
- **Rutas:** pestaña Documentos de una ficha → [Agregar] → `/documentos`.
- **Qué guarda:** el archivo en la carpeta de documentos, y su nombre, tipo y fecha en la base.
- **Cómo probarlo:**
  1. Subir un PDF a una actividad.
  2. Abrirlo y descargarlo.
  3. Subir un tipo de archivo no permitido: lo rechaza.
  4. Abrir la dirección de un documento sin tener permiso: da error 403.
  5. Asociar el mismo documento a otra actividad sin subirlo de nuevo.
- **Qué no hace:** no tiene galería ni trata imágenes de forma especial. Los tipos permitidos son una lista que se puede cambiar.

### P8 · Resultado y cierre
- **Para qué:** dejar anotado cómo salió.
- **Rutas:** ficha → Asistencia → Resultados → [Finalizar].
- **Qué guarda:** asistencia por persona, observaciones, incidencias, resultado, y el estado "realizada".
- **Cómo probarlo:**
  1. Marcar la asistencia.
  2. Agregar a alguien que llegó y no estaba.
  3. Escribir las observaciones.
  4. Pulsar [Finalizar] con algo sin llenar: avisa y deja marcar "sin registro".
  5. Ver la actividad como realizada en el calendario.

### P9 · Fichas e historial
- **Para qué:** saber todo lo que pasó con una persona, organización o lugar.
- **Rutas:** `/personas/<n>`, `/organizaciones/<n>`, `/lugares/<n>`, pestaña Historial.
- **Cómo probarlo:**
  1. Abrir una persona con dos actividades: aparecen las dos.
  2. Cambiar su teléfono: el historial muestra el cambio, quién y cuándo.
  3. Desde una actividad del historial, hacer clic: llega a esa actividad.
  4. Pulsar [Volver]: regresa a donde estaba.

### P10 · Buscar
- **Para qué:** encontrar algo sin saber en qué sección está.
- **Rutas:** la caja de búsqueda de arriba → `/buscar`, y los filtros de cada lista.
- **Cómo probarlo:**
  1. Buscar "maria": debe encontrar "María".
  2. Filtrar actividades por estado y comuna.
  3. Buscar algo que no existe: mensaje claro.
  4. Una persona desactivada aparece marcada y no se ofrece para actividades nuevas.

### P11 · Ver actividades por proyecto (opcional)
- **Para qué:** agrupar actividades que van juntas. Es una petición del tutor, por validar.
- **Rutas:** `/proyectos` → `/proyectos/<n>`.
- **Cómo probarlo:**
  1. Crear un proyecto.
  2. Asociar dos actividades.
  3. Ver sus actividades dentro del proyecto.
  4. Crear una actividad sin proyecto: debe poder.

### P12 · Mantener las listas de opciones (catálogos)
- **Para qué:** que Claudio pueda agregar un tipo nuevo sin pedírselo al programador.
- **Rutas:** `/administracion/catalogos`.
- **Cómo probarlo:**
  1. Agregar un tipo de actividad nuevo: aparece en el formulario de actividad.
  2. Desactivarlo: ya no aparece para actividades nuevas, y las antiguas lo conservan.
  3. Intentar borrar uno que está en uso: no deja.

### P13 · Administrador: cuentas y respaldos
- **Para qué:** controlar quién entra y no perder los datos.
- **Rutas:** `/administracion/usuarios`, auditoría.
- **Cómo probarlo:**
  1. Crear una cuenta a una persona ya registrada, con el rol Gestor.
  2. Desactivarla.
  3. Verificar que el Gestor no ve el menú de Administración.
  4. Hacer un respaldo y restaurarlo en una copia.

---

## 4. El día a día de Claudio

| Pasa esto | Hace esto | Proceso |
|---|---|---|
| Llama una universidad y quiere hacer una actividad | Crea la actividad con el nombre, anota la organización y el contacto | P2, P4, P6 |
| Llega una persona que no está registrada | La crea en el momento con el dato que tenga | P3 |
| Cambia la fecha | Reprograma con el motivo | P5 |
| Alguien pregunta "¿qué hicimos con esa organización?" | Abre su ficha y mira el historial | P9 |
| Le prometen enviar algo mañana | Registra el contacto con próxima acción | P6 |
| Recibe una carta o un certificado | Lo sube a la actividad o a la persona | P7 |
| Termina la actividad | Marca asistencia, escribe el resultado y finaliza | P8 |
| Quiere ver todo lo de un proyecto | Abre el proyecto | P11 |
| Necesita un tipo de actividad nuevo | Lo agrega en catálogos | P12 |

---

## 5. Catálogos y estados, explicados

Un **catálogo** es una lista de opciones que aparecen en los menús desplegables. Claudio puede agregar opciones nuevas.

**Origen:** *oficial* = está en los documentos 01 a 06 · *propuesta* = la propuse yo y se puede cambiar.

| Catálogo | Para qué sirve | Valores iniciales | Origen |
|---|---|---|---|
| Estado de la actividad | En qué punto está | pendiente, planificada, confirmada, reprogramada, suspendida, cancelada, realizada | Oficial (pendiente viene del doc 05) |
| Tipo de actividad | Qué clase de actividad es | taller, charla, jornada, live, difusión, campaña | Propuesta (sale de los documentos reales) |
| Tipo de organización | Qué clase de organización es | institución educativa, municipalidad, junta de vecinos o comité, empresa, fundación u ONG, otra | Oficial |
| Papel de la persona | Cómo participa | estudiante, practicante, ayudante, voluntario, tutor, contacto institucional | Oficial |
| Papel de la organización | Cómo participó | colaboró, puso el lugar, trajo alumnos, donó, solicitó | Propuesta |
| Estado de participación | Si la persona va a asistir | inscrito, confirmado, asistió, no asistió, canceló | Propuesta |
| Tipo de contacto | Cómo se comunicó | llamada, correo, mensaje, reunión | Oficial |
| Origen de la persona | Cómo llegó a la Fundación | invitación, difusión, interés propio, derivación, búsqueda activa | Oficial |
| Tipo de lugar | Qué clase de lugar es | sede vecinal, biblioteca, colegio, espacio abierto, virtual | Propuesta |

**Los estados de la actividad, en palabras simples**
- **Pendiente:** es una idea o solicitud, todavía sin fecha.
- **Planificada:** ya tiene fecha, falta confirmar.
- **Confirmada:** está todo listo.
- **Reprogramada:** se cambió la fecha o el lugar.
- **Suspendida:** se detuvo y puede volver.
- **Cancelada:** no se hará.
- **Realizada:** se hizo.

**Lugar, zona y localidad.** No son una lista fija: son una cadena de ubicación (región, provincia, comuna y sector). El "sector" cubre las localidades y zonas, y puede tener sectores dentro (por ejemplo, San Pedro de la Costa con sus etapas).

**Grupo.** Lo mencionaste, y **no está modelado todavía**. Ver pendiente en la sección 7.

---

## 6. Qué hace, qué no hace y qué restricciones tiene

**Qué avisa (pero deja seguir)**
- Un participante que supera la capacidad del lugar.
- Un choque de horario con otra actividad.
- Una fecha que ya pasó.
- Confirmar una actividad sin responsable, fecha o lugar.
- Una persona u organización que parece estar repetida (por nombre).
- Una actividad sin personas el día antes.

**Qué sí impide (restricciones fijas)**
1. Entrar sin permiso o con la cuenta desactivada.
2. Guardar un RUT que ya existe en otra persona.
3. Agregar a la misma persona con el mismo papel dos veces en una actividad.
4. Una hora de término anterior a la de inicio.
5. Borrar algo que tiene historial. El botón "Eliminar" no existe: se desactiva.
6. Modificar una programación anterior. Se crea una versión nueva.

**Alcance**
- Registrar y consultar actividades, personas, organizaciones, lugares, documentos, contactos y resultados.
- Dos perfiles: Gestor y Administrador.

**Límites**
- No tiene portal público ni cuentas para alumnos o voluntarios.
- No envía mensajes ni correos.
- No funciona desde celular, porque el sistema es local.
- No maneja dinero ni contabilidad.
- No trata imágenes de forma especial.

**Lo oculto que conviene saber**
- Si desactivas a una persona, sigue apareciendo en las actividades pasadas, pero no se ofrece para nuevas.
- Un documento restringido no se puede abrir pegando su dirección.
- Los cambios importantes quedan con usuario y fecha, aunque no los veas en pantalla.

---

## 7. Preguntas que cambian el alcance

1. **Donadores.** Los nombraste junto con colaboradores. ¿Quieres solo saber quiénes son y en qué actividades participaron, o también llevar los montos? Los documentos oficiales dejan las donaciones fuera de esta etapa.
2. **Grupo.** ¿Es un curso, un comité, un grupo de vecinos o un grupo de alumnos? ¿Tiene nombre y miembros? Hoy no existe en el modelo.
3. **Proyecto.** ¿Lo quieres como agrupador opcional, como pidió el tutor?
4. **Actividad sin solicitud.** El modelo oficial parte de una solicitud. Este documento asume que Claudio puede crear una actividad directamente. ¿Es así?
5. **Estados de participación.** ¿Te sirven los cinco propuestos, o prefieres menos?

---

## 8. Recorrido de prueba de 15 minutos

1. Ingresar como Gestor.
2. Crear una actividad solo con nombre y tipo.
3. Agregar una persona que ya existe.
4. Agregar una persona nueva con solo el nombre.
5. Agregar una organización y marcar cómo participó.
6. Programar una fecha con un lugar nuevo.
7. Reprogramar con un motivo y confirmar que la versión anterior queda visible.
8. Registrar una llamada con próxima acción.
9. Subir un documento.
10. Abrir la ficha de la persona y ver la actividad en su historial.
11. Marcar asistencia.
12. Finalizar la actividad.
13. Buscar a la persona por su nombre sin tilde.
14. Ingresar como Administrador y confirmar que la cuenta de Gestor no ve la Administración.
15. Cerrar sesión y pulsar Atrás.

Si los 15 pasos funcionan, el núcleo del sistema funciona.

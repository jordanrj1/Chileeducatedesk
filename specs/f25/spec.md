# F25 — Pruebas del usuario en la web: relaciones, tareas del proyecto y captura en terreno

**Fuente:** revisión del usuario en el navegador, 20-10-2026. Decisiones tomadas con AskUserQuestion el mismo día. Rama: `feature/f24-cascada-y-fichas`.

## Ya hecho (pasos 1 a 5)
1. **Errores corregidos:**
   - la pestaña Direcciones de la persona fallaba: faltaban las rutas de editar y dar de baja;
   - «Comuna que administra» solo se muestra en municipalidades, con un mensaje claro.
2. **Enlaces y acciones en las listas:**
   - todo nombre en listas y tablas es un enlace a su ficha;
   - cada vínculo tiene «Ver detalle», «Editar» y «Dar de baja» o «Reactivar»;
   - el texto anterior marcado «Por revisar» tiene el botón «Ya lo revisé» (queda en el historial).
3. **Cargos y vínculos:**
   - la pestaña de la persona reúne organizaciones con cargo, estudios, lugares, comunidades, proyectos, y actividades y tareas, marcados «Vigente» o «Terminado»;
   - la organización muestra a sus estudiantes por carrera y a los docentes a cargo.
4. **Formulario de persona:**
   - la edad se calcula sola desde la fecha de nacimiento, y la «edad aproximada» aparece solo sin fecha;
   - «No tiene RUT chileno» cambia el RUT por el documento extranjero.
5. **Sector y lugares:**
   - el sector es opcional y va plegado;
   - el lugar ya no pregunta «¿De quién es?» (el dato antiguo se conserva);
   - la tabla nueva `PersonaLugar` vincula a una persona con un lugar (estudia, trabaja, participa), y el lugar muestra a sus personas y a los estudiantes de esa sede.

## Por hacer

### A. Tareas del proyecto (hecho)
**Decisión:** se renombran y se gestionan dentro del proyecto, y aparecen en el calendario marcadas como tarea.

Por dentro, una tarea es una `Actividad` con `proyecto`. Así reutiliza los participantes con rol, la asistencia, las sesiones con su lista y su minuta, el alcance y el historial de cada persona.

1. **Pestaña «Tareas» del proyecto** (antes «Actividades»):
   - una lista con fecha, lugar o comunidad, estado, cantidad de participantes y asistencia;
   - todo enlazado;
   - botón «+ Nueva tarea».
2. **Formulario «Nueva tarea» en un solo paso:**
   - campos: nombre, propósito, descripción, fecha con hora de inicio y término, lugar (o solo comunidad o territorio), grupo objetivo (tramos de edad y público objetivo) y responsable;
   - crea la actividad, su programación y su destino en una transacción.
3. **En `/actividades`** no aparecen las tareas de proyectos, salvo con el filtro «Incluir tareas de proyectos». En `/calendario` sí aparecen, con la etiqueta «Tarea · <proyecto>».
4. **Ficha de una tarea:**
   - título «Tarea del proyecto <proyecto>», con enlace;
   - migas de pan: Proyectos › proyecto › Tareas › nombre;
   - mismas pestañas que una actividad.
5. **Varias sesiones:** una tarea puede continuar otro día («volvemos en 2 días»). Se usan las sesiones que ya existen; en cada sesión se agregan, editan o quitan participantes y se pasa lista.

### B. Ficha rápida de terreno para participantes (actividades y tareas) (hecho)
**Decisión:** quien no está registrado se crea en la misma tarea o actividad, con pocos datos.

1. **Al agregar un participante:** se busca a la persona; si no está, una ficha rápida pide:
   - nombres y apellidos;
   - RUT, o documento extranjero;
   - nacionalidad;
   - sexo;
   - teléfono o correo;
   - comuna de residencia.
   
   Todo es opcional salvo el nombre. Se mantiene el aviso de duplicados.
2. **Rol** en la tarea o actividad (voluntario, estudiante, practicante, invitado…).
3. **De qué grupo viene**, opcional:
   - organización existente o nueva (junta de vecinos, colegio, municipalidad, panadería…) y su **cargo** («Dirigente», «Dueña»);
   - o comunidad;
   - si se indica, se crea el vínculo `PersonaOrganizacion` (con cargo) o `ComunidadMiembro`, que alimenta esas fichas.
4. **Comuna:** si se indica, se crea la dirección de residencia con solo la comuna. Así la persona aparece en el territorio.
5. Lo mismo vale para «+ Agregar persona que llegó» en la asistencia y en la lista de una sesión.

**Cómo quedó (A y B):** «+ Nueva tarea» en `/proyectos/<id>/tareas/nueva`; `/actividades` excluye las tareas salvo con «Incluir tareas de proyectos» o al filtrar por proyecto; la ficha rápida bloquea un RUT o documento ya registrado (hay que buscar a la persona). La lista de una sesión muestra a todos los participantes de la tarea; las personas se agregan en la tarea, no dentro de la sesión.

### C. Sección «Relaciones» en el formulario de persona (hecho)
**Decisión:** todo en el mismo formulario.

Son filas que se agregan con «+». Hay cuatro tipos:
- **organización** con rol (estudiante, docente, funcionario, dirigente, socio o practicante) y período. Un practicante indica además de dónde viene: actividad, tarea o proyecto;
- **comunidad** con rol;
- **proyecto o tarea**, como equipo con su rol o como beneficiario;
- **actividad** con rol.

Cada fila crea el vínculo que corresponde (`PersonaOrganizacion`, `ComunidadMiembro`, `ProyectoPersona` o `Participacion`). Se ve en «Cargos y vínculos» y en la ficha del otro lado.

### D. Experiencia (hecho)
**Decisión:** se arma sola, más experiencia externa opcional.
- La pestaña muestra automáticamente los cargos y roles ya terminados, con fechas: voluntario, tallerista, dirigente, practicante, equipo de proyecto, participaciones en actividades realizadas.
- La carga a mano queda solo para la «Experiencia fuera de la Fundación».

**Cómo quedó (C y D):** «Relaciones» va en «Nueva persona» (plegada en la ficha rápida). Sin JavaScript se ven dos filas; con «+ Agregar relación» se suman más. Cada fila valida por separado y se guarda en la misma transacción que la persona, después del aviso de duplicados (`apps/personas/relaciones.py`). Organización: estudiante crea su formación (solo en instituciones educativas), dirigente queda como directorio y el resto como cargo funcional («Docente · detalle»); el practicante puede indicar la actividad o tarea, o el proyecto, por el que viene. Proyecto o tarea: en el proyecto como equipo (rol y responsable) o beneficiario; en una tarea, como participante. La pestaña Experiencia muestra los cargos y roles terminados, y aparte la «Experiencia fuera de la Fundación».

## Criterios de aceptación
1. **Tarea completa:** en un proyecto, «+ Nueva tarea» con fecha, lugar o comunidad crea la tarea en un paso. Se ve en la pestaña Tareas y en el calendario como «Tarea · proyecto», y no en `/actividades` sin el filtro.
2. **Participantes en la tarea:**
   - uno ya registrado se agrega con su rol;
   - uno nuevo se crea con la ficha rápida y su organización con cargo, su comunidad y su comuna;
   - el vínculo aparece en la organización, la comunidad, el territorio y su «Cargos y vínculos».
3. **Sesiones:** una segunda sesión de la tarea tiene su propia lista de asistencia.
4. **Relaciones al registrar:** en «Nueva persona», varias filas de relaciones (dos organizaciones con distinto rol, una comunidad y un proyecto) quedan guardadas y visibles en ambos lados.
5. **Experiencia:** muestra los cargos terminados sin cargarlos a mano.
6. **Pruebas:** las existentes siguen pasando y hay pruebas esenciales para cada punto.

## E. Participantes de actividades y tareas (revisión del usuario del 21-10-2026)
Decisiones del usuario: ficha rápida única · cinco estados · la organización del participante se agrega sola · panel lateral sin salir de la tarea.

**E1 · Una ficha rápida igual en todas partes**
- **Campos:** nombres*, apellidos, RUT o documento extranjero, nacionalidad, sexo, fecha de nacimiento, teléfono, correo y comuna de residencia.
- **Dónde se usa:** en «+ Crear persona» del buscador, al agregar participantes y en Personas (modo rápido).
- La ficha completa queda en Personas.
- **Se quita el enlace «Créala aquí mismo»** porque duplica; la ruta se conserva.
- Una ficha incompleta muestra «Completar ficha».

**E2 · Cinco estados para elegir**
- **Estados:** Inscrito (antes «Confirmado»; por defecto en todo alta), Asistió, No asistió, Canceló y En lista de espera.
- «Registro erróneo» queda solo para «Quitar».
- Invitado, interesado, disponible y rechazó siguen solo para las invitaciones.
- Un registro antiguo conserva su estado.

**E3 · Misma persona dos veces:** si ya participa en la actividad con otro rol, se avisa con los roles que tiene y se pide confirmar.

**E4 · Organización del participante:**
- al guardar una participación con institución, la organización queda en la actividad como «Aporta personas» si no estaba;
- la pestaña Organizaciones muestra cuántas personas trajo cada una;
- en Participantes, la procedencia muestra la organización, la sede, la carrera, el cargo y la comunidad, con enlaces.

**E5 · Panel lateral:** al hacer clic en un participante se abre un panel, sin salir de la tarea. Muestra contacto, comuna, organizaciones con cargo, formación (institución, sede, carrera), comunidades, otras actividades, «Completar ficha» y «Abrir ficha completa».

**E6 · Horas:** la ayuda dice el valor por defecto («X h según la programación, HH:MM a HH:MM»).

**E7 · Asistencia en la tabla de Participantes:**
- desde el día de la actividad hay una columna para marcar «Asistió» o «No asistió» y un botón «Guardar asistencia»;
- «Sin registro de asistencia» y «+ Agregar persona que llegó» están en la misma pestaña;
- la pestaña Asistencia deja de mostrarse; `?tab=asistencia` abre Participantes.

**E8 · Pantalla:** las pestañas se muestran todas, en varias líneas si hace falta, y las tablas anchas se desplazan hacia el lado.

**E9 · Grupos:** bajo «Equipo ejecutor» y «Asistentes», una frase explica que se separan por el rol.

**E10 · Cupos:** «Cupos ocupados: 3 de 10 (5 participaciones de 3 personas: quien tiene varios roles ocupa un solo cupo)».

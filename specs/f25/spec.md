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

### C. Sección «Relaciones» en el formulario de persona
**Decisión:** todo en el mismo formulario.

Son filas que se agregan con «+». Hay cuatro tipos:
- **organización** con rol (estudiante, docente, funcionario, dirigente, socio o practicante) y período. Un practicante indica además de dónde viene: actividad, tarea o proyecto;
- **comunidad** con rol;
- **proyecto o tarea**, como equipo con su rol o como beneficiario;
- **actividad** con rol.

Cada fila crea el vínculo que corresponde (`PersonaOrganizacion`, `ComunidadMiembro`, `ProyectoPersona` o `Participacion`). Se ve en «Cargos y vínculos» y en la ficha del otro lado.

### D. Experiencia
**Decisión:** se arma sola, más experiencia externa opcional.
- La pestaña muestra automáticamente los cargos y roles ya terminados, con fechas: voluntario, tallerista, dirigente, practicante, equipo de proyecto, participaciones en actividades realizadas.
- La carga a mano queda solo para la «Experiencia fuera de la Fundación».

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

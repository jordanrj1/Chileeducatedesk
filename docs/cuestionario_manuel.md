# Cuestionario para Manuel (tutor)

Cada pregunta trae por qué importa, las opciones y **qué hace hoy el sistema**. Todo está detrás de un ajuste o un permiso, así que cualquier respuesta se aplica sin rehacer trabajo. Basta con marcar una opción.

## 1. Alcance de esta etapa
1. **¿Qué filas del Excel quedaron en amarillo («no corresponden ahora»)?** Sin ese Excel el alcance se decidió con el tablero y con «Requerimientos por módulo».
   - Hoy: todo lo del MVP está activo; la segunda fase está construida pero oculta.
2. **Segunda fase: ¿qué se muestra ahora?** Reuniones con asistentes y compromisos · tareas · sesiones · beneficiarios · verificaciones · postulaciones · finanzas.
   - ☐ Nada (como hoy) ☐ Solo reuniones y tareas ☐ Todo ☐ Otro: ______
   - Se cambia en `.env` (`SEGUNDA_FASE` o `MODULOS_SEGUNDA_FASE`).
3. **Proyecto o campaña.** ¿Basta como agrupador opcional (equipo, organizaciones, actividades) o el proyecto es el contenedor principal, como sugeriste?
   - Hoy: agrupador opcional; ninguna actividad lo exige.
4. **Importación histórica masiva** (personas, organizaciones y lugares desde planillas). ¿Entra en esta etapa?
   - Hoy: disponible, con vista previa y reversión. La carga de listados por actividad es operación normal.

## 2. Roles y continuidad
5. **¿Quién será Administrador después del 30-11-2026?** ☐ Manuel ☐ Otra persona de la Fundación: ______ ☐ Un proveedor externo.
6. **Recuperación de contraseña:** ☐ Solo la restablece el Administrador (hoy) ☐ Por correo (requiere configurar un servidor de correo).
7. **¿Quién ve Finanzas?** ☐ Solo el Gestor (hoy) ☐ También el Administrador ☐ Otro rol.

## 3. Reglas de la actividad
8. **Incompatibilidad crítica** (por ejemplo, 35 inscritos y lugar para 20): ☐ Impedir confirmar (hoy) ☐ Permitir con motivo escrito, que queda en la auditoría.
9. **Reabrir una actividad finalizada** para corregirla: ☐ Nunca ☐ Solo el Administrador ☐ El Gestor, con motivo. Hoy: nadie tiene el permiso; se asigna en Roles.
10. **Mínimos para finalizar:** asistencia (o «sin registro» explícito) y resultado. ☐ De acuerdo ☐ Agregar: ______
11. **Lista de espera:** cuando no hay cupo, ¿se usa «En lista de espera»? ☐ Sí ☐ No. Hoy: el estado existe y no ocupa cupo.
12. **Series de actividades** (un taller semanal): cada repetición es una actividad propia. ☐ De acuerdo ☐ Prefiero sesiones dentro de una actividad.

## 4. Datos personales (nueva ley)
13. **Menores de edad:** ¿qué datos se guardan, con qué autorización del apoderado y por cuánto tiempo?
14. **Derecho a eliminar sus datos:** el sistema no borra lo que tiene historia. ☐ Anonimizar (borrar nombre, RUT y contactos, y conservar la participación como «persona anónima») ☐ Borrar de verdad con aprobación del Administrador ☐ Consultarlo con un abogado. Hoy: no está implementado.
15. **Derecho de acceso:** hoy se exporta en Excel todo lo de una persona y queda en la auditoría. ¿Basta?
16. **Datos sensibles** (contacto de emergencia, verificaciones): hoy los ven Gestor y Administrador con un permiso aparte. ¿De acuerdo?

## 5. Operación
17. **¿Dónde vivirá el sistema?** ☐ El computador de Claudio ☐ Un equipo de la Fundación en red ☐ Un servidor web. Hoy: solo el equipo local; el celular requiere red.
18. **Respaldo fuera del equipo:** ☐ Disco externo ☐ Nube institucional (¿cuál?) ☐ Otro. La restauración ya se probó.
19. **Notificaciones** (actividades próximas, datos por vencer): ☐ Basta con el panel (hoy) ☐ Correo diario a Claudio.
20. **Constancia de participación:** ¿qué texto, firma y timbre lleva? Hoy hay un formato propuesto.

## 6. Modelo
21. **«Zona»** en los documentos oficiales: ¿equivale a comuna y sector? Hoy: región → provincia → comuna → sector.
22. **Sede y unidad académica de las instituciones:** ¿hacen falta, o basta con institución y carrera (como hoy)?

## 7. Surgidas de los escenarios hipotéticos
23. **Emergencia sin Administrador (AC-E6):** ☐ Sobre cerrado con una clave de respaldo ☐ Segunda cuenta de Administrador ☐ Otro.
24. **RUT con dígito verificador incorrecto (PE-E6):** ☐ Rechazar (hoy) ☐ Advertir y permitir si Claudio confirma.
25. **Mayoría de edad (PE-E9):** ¿se guarda la fecha de nacimiento? Sin ella no se puede saber quién es menor.
26. **Consentimiento (PE-E15, SE-E2):** ¿se registra fecha y origen del consentimiento, y qué pasa si se retira?
27. **Domicilio particular como lugar (LU-E4) y quién ve qué direcciones (LU-E5).**
28. **Una solicitud que genera varias actividades (SO-E2):** ☐ Agruparlas en un proyecto (hoy) ☐ Permitir varias actividades por solicitud.
29. **Actividad sin solicitud (SO-E3):** ☐ Permitida (hoy) ☐ Crear la oportunidad automáticamente.
30. **Dividir o fusionar actividades (AT-E2, AT-E3).**
31. **Actividades de varios días o que cruzan la medianoche (AG-E5, AG-E6):** ☐ Usar series o sesiones ☐ Fecha de término.
32. **Corregir la fecha de una actividad ya realizada (AG-E12).**
33. **Verificaciones vencidas e inhabilidades con menores (VA-E5, SE-E9, SE-E10):** ¿advertencia o bloqueo?
34. **Fotos con menores (DO-E10)** y **borrar archivos subidos por error (DO-E9).**
35. **Asistentes que no dan su nombre (RE-E2):** ¿se registra un conteo?
36. **Exportaciones con datos sensibles o de menores (BU-E6, SE-E6).**
37. **Acciones masivas (UI-E11):** ¿se necesitan?
38. **Reemplazo de Claudio y traspaso del Administrador (CO-E1, CO-E3).**

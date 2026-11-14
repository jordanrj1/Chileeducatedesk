# F27 — Ficha de persona como tarjeta, vínculos flexibles, consentimiento en un documento y contactos compartidos

**Fuente:** pedido del usuario (14-11-2026), tras revisar `/organizaciones/48/personas/nuevo`, `/personas/137/lugares/nuevo`, `/personas/137?tab=consentimientos|resumen|contacto` y `/proyectos/4?tab=tareas`. Lo decidido con el usuario se marca [D-u]; lo [P] es propuesta y lo [V] queda para el tutor.

## 1. Catálogos que se explican solos [D-u]
- Todo catálogo tiene una **descripción** opcional, que se edita en Catálogos.
- En los formularios, bajo la lista, se muestra la descripción del valor elegido y cambia al elegir otro. Sin JavaScript se ven todas las descripciones en una ayuda plegable.
- Migración aditiva: `descripcion` en el catálogo base, que se agrega a cada tabla de catálogo.

## 2. Vínculo con una organización: con o sin cargo [D-u]
- **«Rol en la organización»** se amplía para cubrir a cualquiera que se vincule. Cada valor trae su descripción y dice si admite cargo (`con_cargo`):
  - **admiten cargo:** dirigente, autoridad y representante legal;
  - **pueden tener cargo** (lo indica el usuario): docente o académico, funcionario o funcionaria, socio o socia, voluntario o voluntaria, contacto o enlace;
  - **sin cargo:** estudiante, egresado o egresada, practicante, vecino o vecina, apoderado o apoderada, beneficiario o beneficiaria;
  - **otro**.
- **«Tipo de cargo» deja de ser obligatorio** y ya no viene en «Funcional» por defecto.
  - Solo aparece si el rol admite cargo o si se escribe un cargo.
  - Con un rol sin cargo, el servidor lo deja vacío.
  - Bajo la lista se explica cada tipo:
    - **Directorio:** integra la directiva electa o designada (presidencia, secretaría, tesorería, directores).
    - **Funcional:** trabaja, coordina o tiene una responsabilidad en un área, sin ser parte de la directiva (encargado, coordinadora, profesional).
    - **Autoridad:** es la máxima autoridad de la institución o un cargo público (alcaldesa, director de liceo, rector, seremi).
- **Datos existentes:** los vínculos con rol sin cargo y sin cargo escrito quedan sin tipo de cargo (migración de datos que solo limpia ese caso).

## 3. Persona en un lugar: relación precisa [D-u]
- **«¿Qué hace ahí?»** pasa a ser un catálogo editable (`RelacionLugar`), con descripción y agrupado por ámbito:
  - **Estudio:** estudia ahí, hace su práctica ahí.
  - **Trabajo:** trabaja ahí (contrato o planta), presta servicios u honorarios, dirige o administra el lugar.
  - **Comunidad:** es socia o miembro, hace voluntariado ahí, participa en talleres o actividades, lo usa como punto de reunión.
  - **Residencia:** vive ahí, vive cerca (vecino del lugar).
  - **Otra:** contacto o enlace del lugar, dueño o arrendatario, otra relación (se detalla en observaciones).
- **Dónde se guarda:** en `PersonaLugar` (persona, lugar, relación, desde, hasta, vigente, observaciones).
  - Migración aditiva: nuevo FK `tipo_relacion`, que se rellena desde el texto actual.
  - El campo antiguo `relacion` se conserva sin usarse en pantalla (se mantiene al día según el ámbito).
  - La unicidad pasa a ser persona, lugar y relación del catálogo: «trabaja ahí» y «dirige el lugar» pueden convivir.
- **Lugar:** se elige con el buscador común, del mismo ancho y alto que los demás campos, con «+ Crear lugar» sin salir del formulario.

## 4. Consentimiento en un solo documento [D-u]
- **«Registrar consentimiento firmado»:** se sube un documento, o se elige uno existente, y se marcan las autorizaciones que contiene:
  - tratamiento de datos;
  - datos sensibles;
  - uso de imagen;
  - contacto para futuras actividades.

  Lleva también la fecha, el medio y quién lo otorga (la propia persona o su apoderado).
- **Al guardar:** se crea un consentimiento por autorización marcada, todos con el mismo documento de respaldo. Las no marcadas quedan como «no otorgado».
- **Revocar:** sigue siendo por autorización; se revoca, no se borra.
- **Pestaña:** muestra el documento común y el estado de las 4 autorizaciones.

## 5. Ficha de persona como tarjeta [D-u]
- **Foto opcional (`Persona.foto`):** JPG, PNG o WEBP de hasta 3 MB. Se valida el tipo real del archivo y no hace falta una librería nueva.
  - Se guarda en la carpeta de archivos subidos, fuera del código.
  - Se sirve solo por una vista que exige permiso para ver personas, nunca como archivo estático.
  - **Menores de edad:** solo se puede subir con el consentimiento de imagen otorgado [V].
  - Ayuda: «Solo para reconocer a la persona dentro del sistema; no se publica».
- **Cabecera y Resumen:**
  - una tarjeta de persona con la foto (o sus iniciales), el nombre, el estado, los perfiles y datos con icono (edad, comuna, correo con enlace, teléfono con enlace);
  - en la misma tarjeta, la organización y el cargo vigentes;
  - las acciones a la derecha.
- **«Le falta» arriba:** un aviso con icono al inicio del Resumen, con los datos que faltan y el enlace a completarlos. Reemplaza el «Sin completar (n)» del final.

## 6. Contactos repetidos: cómo se aprueban [D-u]
- **Al agregar o editar un correo o teléfono** que ya tiene otra persona vigente (se compara el valor normalizado), se avisa antes de guardar: «Este contacto ya lo tiene: …», con enlaces. Hay tres salidas:
  1. **«Es la misma persona»:** lleva a su ficha y a «Unir fichas» (herramienta de fusión existente). No se guarda nada.
  2. **«Es otra persona que comparte este contacto»:** se elige el motivo (familiar, apoderado, teléfono de la institución u otro). Se guarda con `compartido=True` y el motivo, y la decisión queda en el historial con usuario y fecha.
  3. **«Cancelar».**
- **En la pestaña Contacto,** cada contacto compartido muestra «Compartido con: …» y su motivo.
- **Mismos apellidos con otros datos** no es duplicado (puede ser familia). El aviso de duplicado al crear la persona (RUT, correo, teléfono, nombre parecido) sigue igual y guarda el motivo cuando se decide crearla igual.

## 7. Tareas del proyecto y tablas de las fichas [D-u]
- **Tareas del proyecto:**
  - tarjetas con el nombre y el estado;
  - fecha y hora, lugar y comunidad con icono, y quién está a cargo;
  - cifras de participantes y asistentes;
  - acciones.

  Alineadas en rejilla y apiladas en el celular.
- **Revisión de UI de las pestañas** de persona, proyecto, actividad u organización: proporciones, alineación y aire, con el sistema de diseño de `static/css/fche.css`.

## Cómo quedó A2 (14-11-2026)
- **Consentimiento firmado:** `personas:consentimientos_firmado`.
  - El documento subido queda con el tipo «Consentimiento firmado» (catálogo; migración de datos), restringido 🔒 y ligado a la persona. También se puede elegir uno existente de la persona, sin copiar el archivo.
  - Con `DATOS_SENSIBLES=False` no se ofrece la autorización de datos sensibles.
  - [P] Si la persona es menor, se agrega la casilla «Autorización del apoderado».
  - La pestaña muestra cada documento común con su enlace protegido (`documentos:archivo`, solo con permiso para abrirlo) y el estado de cada autorización. «+ Una sola autorización» conserva el registro anterior.
- **Contactos compartidos:** `Contacto.compartido`, `motivo_compartido` y `nota_compartido`.
  - Contacto no tiene historial: la decisión queda en la auditoría (`contacto_compartido`, con usuario y fecha).
  - Solo se comparan correos y teléfonos vigentes de personas; los de organizaciones y cargos no.
  - Editar sin cambiar el valor no vuelve a preguntar.
  - «Unir fichas» se ofrece solo a quien tiene `fusionar_persona` (el Administrador); al Gestor se le indica que lo pida.
  - Al crear la persona igual tras el aviso de duplicado, el contacto repetido queda compartido con motivo «otro» y la nota escrita.
  - [P] Reactivar un contacto dado de baja no vuelve a preguntar.
- **Foto:** `Persona.foto` se guarda en `MEDIA_ROOT/personas/fotos/` con un nombre aleatorio (no se conserva el original).
  - Se sube, cambia o quita en «Más acciones → Agregar foto / Cambiar o quitar la foto» (`personas:foto_editar`).
  - Se sirve con `personas:foto` (permiso `view_persona`, tipo real según los bytes, `nosniff`). En la ficha queda `foto_url` para la tarjeta de B.
  - La fusión la conserva y el Excel del derecho de acceso indica si hay foto.
  - [V] Si se revoca el consentimiento de imagen de un menor, la foto no se quita sola: ¿debe quitarse?

## Cómo quedó B (14-11-2026)
- **Tarjeta de identidad** (cabecera común `generico/ficha.html`, para toda ficha):
  - retrato de 72 px a la izquierda: foto de la persona (por la vista protegida) o sus iniciales, en círculo; los demás registros, el icono de su tipo en un cuadrado;
  - nombre grande con su estado, etiquetas (perfiles de la persona) y datos clave con icono: edad, comuna, correo (`mailto:`) y teléfono (`tel:`);
  - en la persona, la organización y el cargo vigentes, uno por línea (los 2 primeros y «y N vínculos más»); por eso ya no se repiten en «De un vistazo»;
  - acciones a la derecha (Editar, Más acciones, Volver); en el celular el retrato queda junto al nombre, lo demás usa todo el ancho y las acciones bajan.
- **Avisos** (`generico/_aviso.html`): un componente con icono, título, texto o lista corta y botón, uno debajo del otro bajo la tarjeta. Lo usan persona (menor de edad, consentimiento pendiente con «Registrar consentimiento»), actividad, solicitud y sector.
- **«Le falta»:** aviso con los mínimos que faltan (`Persona.faltantes()`) y «Completar»; los datos opcionales vacíos van plegados en el mismo aviso. Si no falta ningún mínimo, el aviso es neutro («Tiene lo mínimo»). Se ve en todas las pestañas de la persona, para que la cabecera no cambie de alto al cambiar de pestaña. El «Sin completar (N)» del final del Resumen de la persona se quitó; en organización, comunidad y lugar sigue plegado.
- **Tareas del proyecto:** tarjetas en rejilla (2 por fila en escritorio, 1 en el celular) con nombre y estado, fecha y hora, lugar, comunidades, «A cargo», cifras de participantes y asistentes (enlazadas) y Ver/Editar. Vacío: «+ Nueva tarea». Mismas consultas sin importar cuántas tareas haya.
- **Formularios cortos:** «Vincular persona» desde la organización (antes «Agregar persona con cargo»). En los formularios sin secciones, las fechas y horas seguidas van de a dos en escritorio (Desde | Hasta); el consentimiento firmado ya las tenía en su rejilla.
- **Revisión de pestañas:** secciones en tarjetas suaves en la Información de la actividad o tarea y en el Resumen del proyecto (que ya no repite estado, fechas ni responsable de la cabecera); estados vacíos iguales en Participaciones; las 4 autorizaciones en una fila; sin «—» sueltos («Sin registrar»); en el celular, las acciones de cada registro bajan bajo su texto.

## Criterios
- Migraciones solo aditivas o de datos que no borran. Sin dependencias nuevas.
- Funciona sin JavaScript. Datos sensibles y foto según `docs/CONTEXTO.md §12`.
- Pruebas nuevas por punto. Las existentes siguen pasando y se ajustan solo las que leen pantallas cambiadas a propósito.
- **[V] para el tutor:**
  - foto de menores;
  - motivos de contacto compartido;
  - valores de los catálogos ampliados.

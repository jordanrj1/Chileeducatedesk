# F27 — Plan

**Rama:** `feature/f27-ficha-persona-y-vinculos` (desde `main` = F26).

**Encargos, en orden** (cada uno con sus pruebas y sin romper las existentes):
1. **A1. Catálogos y vínculos:**
   - `descripcion` en el catálogo base, con su ayuda dinámica en formularios y Catálogos;
   - `RolOrganizacion.con_cargo` y valores ampliados;
   - `tipo_cargo` opcional y condicionado al rol;
   - catálogo `RelacionLugar` con un FK en `PersonaLugar` y el selector de lugar común.
2. **A2. Privacidad y contactos:**
   - consentimiento en un solo documento;
   - `Contacto.compartido` y su motivo, con el aviso de contacto repetido;
   - `Persona.foto` con validación y una vista protegida.
3. **B. Interfaz:**
   - tarjeta de persona con foto en la cabecera y el Resumen;
   - aviso «Le falta» arriba;
   - tareas del proyecto en tarjetas;
   - revisión de proporciones y alineación de las pestañas, con la guía de UI de un ERP o CRM profesional.

**Restricciones:**
- Migraciones solo aditivas o de datos.
- Sin dependencias nuevas: la foto se valida por los bytes del archivo, sin librería de imágenes.
- Archivos subidos fuera del código y servidos por una vista con permiso.
- Español de Chile.
- Sin rastro de la herramienta en el repositorio (`docs/CONTEXTO.md`).

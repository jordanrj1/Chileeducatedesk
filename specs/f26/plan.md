# F26 CRM más expedito — Plan de implementación

**Meta:** menos clics en la operación diaria, una sola verdad para los vínculos de cada persona y una ficha 360°, sin perder datos ni funciones.

**Arquitectura:**
- **Operación diaria:** una sola pantalla para pasar lista y otra para agregar personas. Las rutas antiguas redirigen o siguen aceptando su POST.
- **Servicios únicos:** `vincular()` y `vincular_contacto()` en `apps/personas/vinculos.py`, y `recalcular_estado()` en `apps/personas/servicios.py`, disparado por señales (`apps/personas/senales.py`). Responsables y referentes se aseguran con `apps/proyectos/servicios.py`, `apps/comunidades/servicios.py` y `apps/actividades/servicios.py`.
- **Informe de diferencias:** `apps/personas/diferencias.py`, con el comando `diferencias_datos`, que solo lee.
- **Ficha 360°:** reutiliza `cargos_y_vinculos()`, `Persona.faltantes()` y `alcance()`. El informe del proyecto (`apps/proyectos/finalizar.py`) reutiliza la exportación de F23.
- **Plantillas:** se unen los parciales `documentos/pestanas/lista.html`, `coordinacion/_interacciones.html` y `territorio/_direccion_form.html`.

**Stack:** Django 5.2, PostgreSQL 17, Bootstrap 5.3 local, HTMX, pytest-django y openpyxl.

**Spec:** `specs/f26/spec.md`.

## Restricciones globales
- **Commits:** sin commits hasta que el usuario revise. Cuando los haya, sin Co-Authored-By ni marcas de herramientas.
- **Migraciones:** solo aditivas o de datos: `nucleo/0018`, `personas/0007`, `personas/0008` y `proyectos/0004`. `iniciar.sh` respalda antes de aplicarlas.
- **Consultas:** sin consultas en bucle. El Inicio, la ficha de persona y el informe tienen un número fijo de consultas, cubierto por pruebas.
- **Funciona sin JavaScript;** los datos de prueba son ficticios.
- **Pruebas existentes:** se ajustan solo las que leen pantallas cambiadas a propósito.

## Orden de trabajo
1. **P1a:** pasar lista y agregar personas.
2. **P1b:** solicitudes, Inicio y menú.
3. **P2a:** `diferencias_datos`, `vincular()`, catálogo «Rol en la organización» y procedencia calculada.
4. **P2b:** formulario de persona sin datos dobles, completitud calculada, y responsables, referentes y apoderado.
5. **P3a:** resumen 360°, mismas pestañas, «Finalizar proyecto» con informe, e indicadores por período.
6. **P3b:** plantillas sin uso y duplicadas, e inventario.

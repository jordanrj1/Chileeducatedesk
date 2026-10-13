# F22 — Plan

## Modelo (migraciones solo aditivas; nada se borra)
- `nucleo`: catálogos `PerfilPersona` y `AreaTematica` (editables, con semillas).
- `personas`:
  - `Persona` + `nombre_social`, `fecha_nacimiento`, `nacionalidad`, `nivel_educacional`, `situacion_ocupacional`, `habilidades`, `idiomas`, `canal_preferido` (FK Canal), `perfiles` (M2M PerfilPersona), `areas_interes` (M2M AreaTematica). Propiedades `edad` y `es_menor`.
  - `PerfilSensible` (1 a 1 con Persona, con historial).
  - `Consentimiento` (con historial).
  - `Apoderado` (persona ↔ persona).
  - `PersonaFormacion` + `sede`, `jornada`, `nivel_actual`, `asignatura`, `docente` (FK Persona), `horas_comprometidas`.
- `comunidades` (app nueva): `Comunidad`, `ComunidadMiembro` (con historial).
- `actividades`:
  - `Actividad` + `area_tematica`, `publico_objetivo`, `rango_etario`, `beneficiarios_estimados`.
  - `ActividadComunidad`.
  - `Participacion` + `institucion`, `comunidad`, `horas`.
  - `RolParticipacion.grupo` vive en `nucleo` (ejecutor / asistente / contacto), con valor por código.
  - `SesionActividad` + `objetivo`, `desarrollo`, `avances`, `acuerdos`, `incidencias`, `proximos_pasos`, conteos agregados, `redactada_por`, `creado_en`; `facilitadores` (M2M Persona).
  - `SesionAsistencia`.
- `documentos`: `Documento.sesion` (FK opcional, evidencia de la sesión).
- `proyectos`: `Proyecto.area_tematica`, `ProyectoComunidad`.

## Ajustes
- `DATOS_SENSIBLES` (por defecto `True`).
- «sesiones» sale de `MODULOS` de segunda fase (siempre visible).

## Interfaz
- `FormularioMixin` admite `secciones` en el form: [(título, ayuda, [campos])]. `generico/formulario.html` las dibuja como bloques con título.
- **Persona:**
  - pestañas nuevas «Datos sensibles 🔒», «Consentimientos», «Apoderados 🔒» y «Comunidades»;
  - cabecera con edad, «Menor de edad» y avisos de consentimiento;
  - horas acumuladas en Participaciones.
- **Comunidad:** listado, ficha (Información, Integrantes, Actividades, Alcance, Historial), crear y editar, integrantes como registros hijos; menú «Comunidades» (Registro).
- **Actividad:**
  - pestaña «Público y comunidades»;
  - participantes separados en «Equipo» y «Asistentes» por el grupo del rol;
  - pestaña «Sesiones» (bitácora) siempre visible;
  - ficha de sesión con minuta, asistencia y conteos;
  - pestaña «Alcance».
- **Proyecto:** pestaña «Alcance» y comunidades.
- **Comuna:** pestaña «Comunidades».
- **Buscador:** comunidades.

## Servicio de alcance (`actividades/alcance.py`)
Cuenta, sobre un conjunto de actividades:
- personas únicas;
- equipo frente a asistentes;
- instituciones de procedencia;
- comunidades;
- horas;
- sesiones y asistentes sin registro.

## Importación
`lectura.SINONIMOS` y `COLUMNAS_POR_TIPO["personas"]` agregan columnas; `procesar` aplica fecha de nacimiento, nacionalidad, dirección de residencia y datos de formación.

## Pruebas
Una por criterio de aceptación, más permisos (403) de las vistas sensibles.

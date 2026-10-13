# Modelo de datos (generado)

Generado con `python manage.py diagrama_er` a partir de los modelos de Django. Las tablas de historial (`Historical*`) y los catálogos se omiten del dibujo para que se pueda leer; los catálogos aparecen como `FK` a `nucleo`.

## Territorio, personas y organizaciones

```mermaid
erDiagram
    Region {
        numero id PK
        texto codigo
        texto nombre
    }
    Provincia {
        numero id PK
        id region FK
        texto codigo
        texto nombre
    }
    Comuna {
        numero id PK
        id provincia FK
        texto codigo
        texto nombre
    }
    Sector {
        numero id PK
        id comuna FK
        texto nombre
        texto tipo
        id sector_padre FK "opcional"
    }
    SectorAlias {
        numero id PK
        id sector FK
        texto nombre
    }
    Direccion {
        numero id PK
        texto calle "opcional"
        texto numero "opcional"
        texto block "opcional"
        texto depto "opcional"
        texto referencia "opcional"
        id comuna FK
        id sector FK "opcional"
    }
    Persona {
        numero id PK
        texto nombres
        texto apellido_paterno "opcional"
        texto apellido_materno "opcional"
        numero rut_numero "opcional"
        texto rut_dv "opcional"
        id origen FK "opcional"
        id estado_registro FK "opcional"
        texto profesion "opcional"
        texto sitio_web "opcional"
        texto observaciones "opcional"
        bool activo
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    Contacto {
        numero id PK
        id tipo FK
        texto valor
        texto valor_normalizado "opcional"
        bool principal
        bool vigente
        texto proposito "opcional"
        id persona FK "opcional"
        id organizacion FK "opcional"
        id cargo FK "opcional"
    }
    PersonaDireccion {
        numero id PK
        id persona FK
        id direccion FK
        texto tipo
        bool vigente
    }
    PersonaFormacion {
        numero id PK
        id persona FK
        id organizacion FK
        id carrera FK "opcional"
        texto estado
        numero anio_inicio "opcional"
        numero anio_termino "opcional"
        bool vigente
    }
    PersonaOrganizacion {
        numero id PK
        id persona FK
        id organizacion FK
        texto cargo "opcional"
        texto tipo_cargo
        fecha fecha_inicio "opcional"
        fecha fecha_termino "opcional"
    }
    Experiencia {
        numero id PK
        id persona FK
        texto descripcion
        texto lugar "opcional"
        fecha desde "opcional"
        fecha hasta "opcional"
        bool vigente
    }
    DisponibilidadPersona {
        numero id PK
        id persona FK
        numero dia
        hora hora_inicio
        hora hora_fin
        texto comentario "opcional"
        bool vigente
    }
    ContactoEmergencia {
        numero id PK
        id persona FK
        texto nombre
        texto parentesco "opcional"
        texto telefono
        texto telefono_normalizado "opcional"
        bool vigente
    }
    VerificacionPersona {
        numero id PK
        id persona FK
        texto tipo
        fecha fecha
        fecha vigente_hasta "opcional"
        texto observaciones "opcional"
        bool vigente
    }
    Organizacion {
        numero id PK
        texto nombre
        id tipo FK
        numero rut_numero "opcional"
        texto rut_dv "opcional"
        texto otro_identificador "opcional"
        id estado_registro FK "opcional"
        texto descripcion "opcional"
        texto sitio_web "opcional"
        id direccion FK "opcional"
        id comuna_municipal FK "opcional"
        bool es_propia
        texto naturaleza_juridica "opcional"
        texto domicilio_legal "opcional"
        fecha vigencia_desde "opcional"
        fecha vigencia_hasta "opcional"
        bool activo
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    Carrera {
        numero id PK
        id organizacion FK
        texto nombre
        bool activo
    }
    PerfilCuenta {
        numero id PK
        id usuario FK
        id persona FK "opcional"
    }
    Region ||--o{ Provincia : "region"
    Provincia ||--o{ Comuna : "provincia"
    Comuna ||--o{ Sector : "comuna"
    Sector |o--o{ Sector : "sector_padre"
    Sector ||--o{ SectorAlias : "sector"
    Comuna ||--o{ Direccion : "comuna"
    Sector |o--o{ Direccion : "sector"
    Persona |o--o{ Contacto : "persona"
    Organizacion |o--o{ Contacto : "organizacion"
    PersonaOrganizacion |o--o{ Contacto : "cargo"
    Persona ||--o{ PersonaDireccion : "persona"
    Direccion ||--o{ PersonaDireccion : "direccion"
    Persona ||--o{ PersonaFormacion : "persona"
    Organizacion ||--o{ PersonaFormacion : "organizacion"
    Carrera |o--o{ PersonaFormacion : "carrera"
    Persona ||--o{ PersonaOrganizacion : "persona"
    Organizacion ||--o{ PersonaOrganizacion : "organizacion"
    Persona ||--o{ Experiencia : "persona"
    Persona ||--o{ DisponibilidadPersona : "persona"
    Persona ||--o{ ContactoEmergencia : "persona"
    Persona ||--o{ VerificacionPersona : "persona"
    Direccion |o--o{ Organizacion : "direccion"
    Comuna |o--|| Organizacion : "comuna_municipal"
    Organizacion ||--o{ Carrera : "organizacion"
    Persona |o--|| PerfilCuenta : "persona"
```

## Lugares, proyectos y actividades

```mermaid
erDiagram
    Lugar {
        numero id PK
        texto nombre
        id tipo FK
        id direccion FK
        numero capacidad "opcional"
        texto condiciones "opcional"
        id organizacion_propietaria FK "opcional"
        bool activo
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    Proyecto {
        numero id PK
        texto nombre
        texto descripcion "opcional"
        texto objetivo_general "opcional"
        texto objetivos_especificos "opcional"
        texto diagnostico "opcional"
        texto poblacion_objetivo "opcional"
        texto zona "opcional"
        fecha fecha_inicio "opcional"
        fecha fecha_termino "opcional"
        texto estado
        id responsable FK "opcional"
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    ProyectoPersona {
        numero id PK
        id proyecto FK
        id persona FK
        texto tipo
        id rol FK "opcional"
        bool es_responsable
        fecha desde "opcional"
        fecha hasta "opcional"
        bool vigente
    }
    ProyectoOrganizacion {
        numero id PK
        id proyecto FK
        id organizacion FK
        id tipo_intervencion FK "opcional"
        id contacto FK "opcional"
        texto observaciones "opcional"
        bool vigente
    }
    Postulacion {
        numero id PK
        id proyecto FK
        texto fondo
        fecha fecha "opcional"
        texto estado
        texto resultado "opcional"
        texto observaciones "opcional"
        bool vigente
    }
    Actividad {
        numero id PK
        id proyecto FK "opcional"
        id actividad_padre FK "opcional"
        texto nombre
        id tipo FK "opcional"
        texto objetivo "opcional"
        texto descripcion "opcional"
        id estado FK
        texto motivo_estado "opcional"
        id modalidad FK "opcional"
        id responsable FK "opcional"
        texto condiciones "opcional"
        texto observaciones "opcional"
        texto incidencias "opcional"
        texto resultado "opcional"
        texto indicadores "opcional"
        bool asistencia_sin_registro
        fechahora finalizada_en "opcional"
        id finalizada_por FK "opcional"
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    ActividadTerritorio {
        numero id PK
        id actividad FK
        id region FK "opcional"
        id provincia FK "opcional"
        id comuna FK "opcional"
        id sector FK "opcional"
        bool vigente
    }
    Participacion {
        numero id PK
        id actividad FK
        id persona FK
        id rol FK
        id estado FK
        bool asistencia "opcional"
        texto observaciones "opcional"
        fecha fecha "opcional"
        id creado_por FK "opcional"
    }
    ActividadOrganizacion {
        numero id PK
        id actividad FK
        id organizacion FK
        id tipo_intervencion FK "opcional"
        id contacto FK "opcional"
        texto observaciones "opcional"
        bool vigente
    }
    SesionActividad {
        numero id PK
        id actividad FK
        numero numero
        texto nombre "opcional"
        fecha fecha "opcional"
        hora hora_inicio "opcional"
        hora hora_fin "opcional"
        id lugar FK "opcional"
        texto observaciones "opcional"
        bool vigente
    }
    AgendaActividad {
        numero id PK
        id actividad FK
        numero version
        bool vigente
        fecha fecha
        hora hora_inicio "opcional"
        hora hora_fin "opcional"
        id lugar FK "opcional"
        id modalidad FK "opcional"
        id estado FK
        texto motivo_cambio "opcional"
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    Solicitud {
        numero id PK
        texto origen
        id canal FK "opcional"
        fecha fecha
        id persona FK "opcional"
        id organizacion FK "opcional"
        texto motivo "opcional"
        texto descripcion "opcional"
        id estado FK
        texto observaciones "opcional"
        id proyecto FK "opcional"
        id actividad FK "opcional"
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    Proyecto ||--o{ ProyectoPersona : "proyecto"
    Proyecto ||--o{ ProyectoOrganizacion : "proyecto"
    Proyecto ||--o{ Postulacion : "proyecto"
    Proyecto |o--o{ Actividad : "proyecto"
    Actividad |o--o{ Actividad : "actividad_padre"
    Actividad ||--o{ ActividadTerritorio : "actividad"
    Actividad ||--o{ Participacion : "actividad"
    Actividad ||--o{ ActividadOrganizacion : "actividad"
    Actividad ||--o{ SesionActividad : "actividad"
    Lugar |o--o{ SesionActividad : "lugar"
    Actividad ||--o{ AgendaActividad : "actividad"
    Lugar |o--o{ AgendaActividad : "lugar"
    Proyecto |o--o{ Solicitud : "proyecto"
    Actividad |o--|| Solicitud : "actividad"
```

## Coordinación, documentos, importaciones y finanzas

```mermaid
erDiagram
    Interaccion {
        numero id PK
        fechahora fecha
        id canal FK
        id persona FK "opcional"
        id organizacion FK "opcional"
        id solicitud FK "opcional"
        id actividad FK "opcional"
        texto motivo "opcional"
        texto resultado "opcional"
        texto proxima_accion "opcional"
        fecha proxima_fecha "opcional"
        bool accion_cumplida
        id creado_por FK "opcional"
    }
    Reunion {
        numero id PK
        texto titulo
        fecha fecha
        hora hora_inicio "opcional"
        hora hora_fin "opcional"
        id lugar FK "opcional"
        id modalidad FK "opcional"
        texto objetivo "opcional"
        texto temas "opcional"
        texto acuerdos "opcional"
        id actividad FK "opcional"
        id proyecto FK "opcional"
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    ReunionAsistente {
        numero id PK
        id reunion FK
        id persona FK
        bool asistio "opcional"
        texto observaciones "opcional"
        bool vigente
    }
    Tarea {
        numero id PK
        texto titulo
        texto descripcion "opcional"
        texto estado
        fecha fecha_limite "opcional"
        id reunion FK "opcional"
        id actividad FK "opcional"
        id proyecto FK "opcional"
        fechahora hecha_en "opcional"
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    TareaResponsable {
        numero id PK
        id tarea FK
        id persona FK
        bool vigente
    }
    Invitacion {
        numero id PK
        id persona FK
        id actividad FK
        id rol FK
        fecha fecha
        texto estado
        texto respuesta "opcional"
        fecha fecha_respuesta "opcional"
        id creado_por FK "opcional"
    }
    Colaboracion {
        numero id PK
        id organizacion FK
        id actividad FK
        id tipo_apoyo FK
        texto estado
        texto resultado "opcional"
        texto observaciones "opcional"
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    Documento {
        numero id PK
        texto nombre
        archivo archivo
        id tipo FK
        fecha fecha
        texto descripcion "opcional"
        id actividad FK "opcional"
        id proyecto FK "opcional"
        id persona FK "opcional"
        id organizacion FK "opcional"
        bool restringido
        texto folio "opcional"
        texto emisor "opcional"
        fecha fecha_emision "opcional"
        fecha fecha_vencimiento "opcional"
        bool activo
        id subido_por FK "opcional"
        fechahora subido_en "opcional"
    }
    OrigenDato {
        numero id PK
        id content_type FK
        numero object_id
        texto fuente
        id documento FK "opcional"
        numero lote "opcional"
        texto detalle "opcional"
        fecha fecha
        id registrado_por FK "opcional"
        texto estado_verificacion
    }
    Lote {
        numero id PK
        texto tipo
        archivo archivo "opcional"
        texto nombre_archivo "opcional"
        texto fuente "opcional"
        texto estado
        id actividad FK "opcional"
        id rol FK "opcional"
        json filas
        json resumen
        id usuario FK "opcional"
        fechahora creado_en "opcional"
        fechahora confirmado_en "opcional"
        fechahora revertido_en "opcional"
        id revertido_por FK "opcional"
    }
    LoteItem {
        numero id PK
        id lote FK
        texto tipo_objeto
        numero objeto_id
        bool creado
        numero fila
    }
    ItemPresupuesto {
        numero id PK
        id proyecto FK
        texto categoria
        texto concepto
        numero monto_estimado
        bool vigente
    }
    Movimiento {
        numero id PK
        id proyecto FK
        texto tipo
        numero monto
        fecha fecha
        id persona FK "opcional"
        id organizacion FK "opcional"
        texto concepto
        id documento FK "opcional"
        bool anulado
        texto motivo_anulacion "opcional"
        id creado_por FK "opcional"
        fechahora creado_en "opcional"
    }
    Reunion ||--o{ ReunionAsistente : "reunion"
    Reunion |o--o{ Tarea : "reunion"
    Tarea ||--o{ TareaResponsable : "tarea"
    Documento |o--o{ OrigenDato : "documento"
    Lote ||--o{ LoteItem : "lote"
    Documento |o--o{ Movimiento : "documento"
```

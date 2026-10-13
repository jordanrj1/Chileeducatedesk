# Manual de uso — Plataforma FCHE

Para Claudio (Gestor) y quien administre el sistema. Todos los datos de los ejemplos son ficticios.

## 1. Ingresar
1. Abre la dirección del sistema (por defecto `http://127.0.0.1:8000`).
2. Escribe tu **usuario o correo** y tu contraseña → **Ingresar**.
3. Para salir: **Cerrar sesión** (arriba a la derecha). La sesión se cierra sola tras 60 minutos sin actividad.
4. Cambiar tu contraseña: tu nombre (arriba) → **Cambiar contraseña**. Si la olvidas, el Administrador la restablece.

## 1b. Seguridad
- Tras 5 intentos fallidos el acceso se bloquea 15 minutos; el Administrador puede desbloquearlo antes.
- Si la sesión vence mientras escribes, al volver a ingresar se recupera lo escrito («Se recuperó lo que habías escrito»).
- Si otra pestaña cambió el registro mientras lo editabas, el sistema avisa en vez de pisar los cambios.

## 2. Cómo está organizado
- **Inicio**: qué tienes que hacer hoy (actividades incompletas, solicitudes sin respuesta, personas por completar, tareas por vencer).
- **Buscador** (arriba, siempre visible): busca en personas, organizaciones, proyectos, actividades, lugares, reuniones y documentos. En **/buscar** puedes combinar filtros (tipo, estado, zona, fechas).
- **Menú lateral**: Solicitudes, Proyectos, Actividades, Personas, Organizaciones, Lugares, Calendario, Reuniones, Tareas, Documentos, Territorio, Importaciones, Finanzas, Catálogos, Administración (según tu rol).
- Cada registro tiene una **ficha con pestañas**. Arriba están **Editar** y **← Volver**.
- Nada se elimina. Lo que ya no se usa se **desactiva** o se **archiva**, y su historial se conserva.

## 3. Registrar una persona (una sola vez)
1. **Personas → + Nueva persona**. Elige **Ficha rápida** (nombre y un contacto) o **Ficha completa**. Solo el nombre es obligatorio. «Guardar y completar después» la deja en la cola de incompletos.
2. Al guardar, el sistema **busca coincidencias** (mismo RUT, correo, teléfono o nombre parecido). Si aparece un posible duplicado, elige **Usar existente** o **Crear de todos modos**. Nunca se fusiona nada automáticamente.
3. En la ficha: Datos, Contactos, Direcciones, Formación, Experiencia, Disponibilidad, Organizaciones y cargos, Trayectoria, Documentos, Contacto de emergencia y Verificaciones (estas dos son datos sensibles), Origen, Historial.
4. Una persona **no necesita cuenta** para existir ni participar.
5. Personas extranjeras: en la ficha completa se registra el pasaporte u otro documento.
6. Si una persona fallece: estado «Fallecida/o»; no se elimina y ya no aparece como candidata.
7. Fichas duplicadas descubiertas tarde: el Administrador usa «Fusionar con otra ficha»; todo pasa a la que queda.
8. «Exportar sus datos personales» entrega todo lo que el sistema guarda de esa persona.
9. Al desactivar una persona, organización o lugar con actividades futuras, el sistema las muestra antes de confirmar. «Reasignar sus actividades» pasa las de un responsable que se va a otra persona.

## 4. Organizaciones y lugares
- **Organizaciones → + Nueva organización**: tipo, RUT (opcional), dirección, contactos (varios, con propósito), carreras (si es institución educativa), personas y cargos.
- **Lugares → + Nuevo lugar**: dirección, **capacidad** y condiciones. En su ficha: **Uso histórico** y **Disponibilidad** por fecha. También se crea desde **Programar** («+ Crear lugar»).
- **Direcciones**: se eligen región → provincia → comuna → sector. Si el sector no existe, «+ Crear sector» lo crea ahí mismo; si se escribe distinto («Pobl.», «Vla.») lo reconoce.
- **Territorio**: navega por región y abre una comuna para ver sus sectores, lugares, organizaciones y actividades.

## 5. De la solicitud a la actividad
1. **Solicitudes → + Nueva solicitud** (o **+ Nueva oportunidad** si la buscó la Fundación): se puede guardar con lo poco que se sabe; sin contacto queda «Por identificar».
2. Registra cada llamada o correo en **Seguimiento → Registrar interacción** (con próxima acción y fecha).
3. Cuando está clara, usa **Crear proyecto** o **Crear actividad**: la solicitud queda «convertida».
4. En una **actividad** completa: participantes, beneficiarios, organizaciones, sesiones, agenda y coordinación.
   - **Agregar participante**: busca a la persona; si no existe, **Crear persona nueva** desde ahí mismo.
   - **Buscar candidatos**: el sistema sugiere personas, lugares y organizaciones y explica conflictos. Tú decides; nunca asigna solo.

## 6. Programar, reprogramar y confirmar
- **Programar** fija fecha, hora (o duración) y lugar (versión 1). **Crear serie** repite la actividad (por ejemplo, cada semana). **Reprogramar** crea una versión nueva y pide el **motivo**; la anterior queda en la pestaña *Agenda*.
- **Confirmar** revisa la compatibilidad: falta de responsable/fecha/lugar, capacidad del lugar, lugar ocupado, personas con otra actividad al mismo tiempo y disponibilidad declarada. Los faltantes y conflictos graves impiden confirmar; las advertencias se pueden aceptar marcando «Confirmar de todos modos».
- **Estado**: suspender o cancelar exige un motivo. Una actividad cancelada o finalizada (realizada) ya no se modifica.
- **Calendario**: vista mensual/semanal/lista; filtra por estado, zona, responsable y organización, y puede mostrar programaciones anteriores.

## 6b. Más acciones de la actividad
- **Duplicar**: copia una actividad del año pasado, sin participantes ni fechas.
- **Quitar** (en Participantes): si alguien se agregó por error; queda como «registro erróneo» con el motivo.
- **En lista de espera**: estado para quien no alcanza cupo; no ocupa capacidad.
- La capacidad cuenta personas: quien tiene dos roles cuenta una vez.

## 7. Ejecutar y finalizar
1. Después de la actividad, pestaña **Asistencia**: marca quién asistió (o «no hay registro de asistencia»). Si llegó alguien no previsto: **+ Agregar persona que llegó**.
2. Pestaña **Resultados**: resultado, observaciones, incidencias, indicadores. Sube fotos/minutas en **Documentos**.
3. **Finalizar actividad**: exige asistencia (o «sin registro») y resultado. Queda **Realizada**, de solo lectura y consultable en el historial.

## 8. Documentos
- **Documentos → + Nuevo documento** (o desde una actividad, proyecto, persona u organización). Formatos: PDF, Word, Excel, imágenes, etc. (máx. 25 MB).
- Marca **Restringido** para documentos sensibles: solo los ven quienes tienen ese permiso. Los archivos se descargan siempre a través del sistema.
- Un documento no se borra: se **archiva**. Puede tener **fecha de vencimiento**.
- **Asociar existente**: usa un documento ya subido en otra ficha, sin copiar el archivo.
- **Transcribir datos de este documento**: el documento a un lado y el formulario al otro; lo registrado queda con ese documento como origen.
- **Origen del dato**: en la pestaña *Origen* de cada ficha queda de dónde salió la información, quién la registró y si está verificada.

## 8b. Más sobre documentos
- Si subes un archivo que ya existe, el sistema avisa y ofrece usar el existente.
- **Reemplazar archivo** guarda una versión nueva (por ejemplo, un escaneo mejor); la anterior queda archivada.
- Archivar pide un motivo. Si un archivo desaparece del disco, la ficha lo indica.

## 9. Cargar un listado (planilla que manda una institución)
1. **Importaciones → + Nueva importación** → «Listado de participantes de una actividad» → elige actividad y rol → sube el archivo (CSV, TXT o XLSX) o pega las filas.
2. **Revisa**: el sistema muestra *nuevos*, *ya existen*, *posibles duplicados* y *errores*. Corrige los datos en la misma tabla y pulsa «Revisar de nuevo». Para cada duplicado elige: usar la existente, crear nueva u omitir.
3. **Confirmar carga**: solo se habilita cuando no queda nada pendiente. La planilla original se guarda como documento restringido.
4. Si una columna no se reconoce, indícala en «Columnas de la planilla» y pulsa «Aplicar columnas».
5. Si la persona ya existe con datos distintos, elige: conservar, agregar solo el contacto nuevo o actualizar la ficha.
6. Si te equivocas: abre el lote y **Revertir lote** (se conservan las personas que ya tienen otra historia o que alguien editó después).

## 10. Exportar
Los listados con botón **Exportar** generan un Excel con los filtros aplicados. Cada exportación queda en la auditoría.

## 11. Segunda fase
Reuniones con asistentes, tareas, sesiones, beneficiarios, verificaciones y finanzas están construidas pero ocultas. Para mostrarlas, el Administrador pone `SEGUNDA_FASE=True` en `.env` y reinicia.

## 11b. Finanzas (solo usuarios autorizados, segunda fase)
Presupuesto por proyecto (ítems), gastos, aportes y donaciones. Los movimientos no se borran: se **anulan** con motivo. No registres cuentas bancarias.

## 12. Administración (rol Administrador)
- **Usuarios**: crear cuenta (vinculada a una persona, opcional), asignar rol, desactivar, restablecer contraseña.
- **Roles y permisos**: qué puede hacer cada rol. El sistema no ofrece «eliminar».
- **Catálogos**: el Gestor agrega y edita valores; solo el Administrador desactiva. Desactivar no borra el historial.
- **Auditoría**: ingresos, cambios de rol, exportaciones, confirmaciones, importaciones, respaldos.

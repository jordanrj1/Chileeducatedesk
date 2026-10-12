# Manual de uso — Plataforma FCHE

Para Claudio (Gestor) y quien administre el sistema. Todos los datos de los ejemplos son ficticios.

## 1. Ingresar
1. Abre la dirección del sistema (por defecto `http://127.0.0.1:8000`).
2. Escribe tu **usuario o correo** y tu contraseña → **Ingresar**.
3. Para salir: **Cerrar sesión** (arriba a la derecha). La sesión se cierra sola tras 60 minutos sin actividad.
4. Cambiar tu contraseña: tu nombre (arriba) → **Cambiar contraseña**. Si la olvidas, el Administrador la restablece.

## 2. Cómo está organizado
- **Inicio**: qué tienes que hacer hoy (actividades incompletas, solicitudes sin respuesta, personas por completar, tareas por vencer).
- **Buscador** (arriba, siempre visible): busca en personas, organizaciones, proyectos, actividades, lugares, reuniones y documentos. En **/buscar** puedes combinar filtros (tipo, estado, zona, fechas).
- **Menú lateral**: Solicitudes, Proyectos, Actividades, Personas, Organizaciones, Lugares, Calendario, Reuniones, Tareas, Documentos, Territorio, Importaciones, Finanzas, Catálogos, Administración (según tu rol).
- Cada registro tiene una **ficha con pestañas**. Arriba están **Editar** y **← Volver**.
- Nada se elimina. Lo que ya no se usa se **desactiva** o se **archiva**, y su historial se conserva.

## 3. Registrar una persona (una sola vez)
1. **Personas → + Nueva persona**. Solo el nombre es obligatorio; completa lo demás cuando lo tengas.
2. Al guardar, el sistema **busca coincidencias** (mismo RUT, correo, teléfono o nombre parecido). Si aparece un posible duplicado, revisa y decide: abrir la ficha existente o **«Es otra persona: guardar de todos modos»**. Nunca se fusiona nada automáticamente.
3. En la ficha: Datos, Contactos, Direcciones, Formación, Experiencia, Disponibilidad, Organizaciones y cargos, Trayectoria, Documentos, Contacto de emergencia y Verificaciones (estas dos son datos sensibles), Origen, Historial.
4. Una persona **no necesita cuenta** para existir ni participar.

## 4. Organizaciones y lugares
- **Organizaciones → + Nueva organización**: tipo, RUT (opcional), dirección, contactos (varios, con propósito), carreras (si es institución educativa), personas y cargos.
- **Lugares → + Nuevo lugar**: dirección, **capacidad** y condiciones. En su ficha: **Uso histórico** y **Disponibilidad** por fecha.

## 5. De la solicitud a la actividad
1. **Solicitudes → + Nueva solicitud**: se puede guardar con lo poco que se sabe.
2. Registra cada llamada o correo en **Seguimiento → Registrar interacción** (con próxima acción y fecha).
3. Cuando está clara, usa **Crear proyecto** o **Crear actividad**: la solicitud queda «convertida».
4. En una **actividad** completa: participantes, beneficiarios, organizaciones, sesiones, agenda y coordinación.
   - **Agregar participante**: busca a la persona; si no existe, **Crear persona nueva** desde ahí mismo.
   - **Buscar candidatos**: el sistema sugiere personas, lugares y organizaciones y explica conflictos. Tú decides; nunca asigna solo.

## 6. Programar, reprogramar y confirmar
- **Programar** fija fecha, hora y lugar (versión 1). **Reprogramar** crea una versión nueva y pide el **motivo**; la anterior queda en la pestaña *Agenda*.
- **Confirmar** revisa la compatibilidad: falta de responsable/fecha/lugar, capacidad del lugar, lugar ocupado, personas con otra actividad al mismo tiempo y disponibilidad declarada. Los faltantes y conflictos graves impiden confirmar; las advertencias se pueden aceptar marcando «Confirmar de todos modos».
- **Estado**: suspender o cancelar exige un motivo. Una actividad cancelada o finalizada (realizada) ya no se modifica.
- **Calendario**: vista mensual/semanal/lista; filtra por estado y puede mostrar programaciones anteriores.

## 7. Ejecutar y finalizar
1. Después de la actividad, pestaña **Asistencia**: marca quién asistió (o «no hay registro de asistencia»).
2. Pestaña **Resultados**: resultado, observaciones, incidencias, indicadores. Sube fotos/minutas en **Documentos**.
3. **Finalizar actividad**: exige asistencia (o «sin registro») y resultado. Queda **Realizada**, de solo lectura y consultable en el historial.

## 8. Documentos
- **Documentos → + Nuevo documento** (o desde una actividad, proyecto, persona u organización). Formatos: PDF, Word, Excel, imágenes, etc. (máx. 25 MB).
- Marca **Restringido** para documentos sensibles: solo los ven quienes tienen ese permiso. Los archivos se descargan siempre a través del sistema.
- Un documento no se borra: se **archiva**.
- **Origen del dato**: en la pestaña *Origen* de cada ficha queda de dónde salió la información, quién la registró y si está verificada.

## 9. Cargar un listado (planilla que manda una institución)
1. **Importaciones → + Nueva importación** → «Listado de participantes de una actividad» → elige actividad y rol → sube el archivo (CSV, TXT o XLSX) o pega las filas.
2. **Revisa**: el sistema muestra *nuevos*, *ya existen*, *posibles duplicados* y *errores*. Corrige los datos en la misma tabla y pulsa «Revisar de nuevo». Para cada duplicado elige: usar la existente, crear nueva u omitir.
3. **Confirmar carga**: solo se habilita cuando no queda nada pendiente. La planilla original se guarda como documento restringido.
4. Si te equivocas: abre el lote y **Revertir lote** (se conservan las personas que ya tienen otra historia).

## 10. Exportar
Los listados con botón **Exportar** generan un Excel con los filtros aplicados. Cada exportación queda en la auditoría.

## 11. Finanzas (solo usuarios autorizados)
Presupuesto por proyecto (ítems), gastos, aportes y donaciones. Los movimientos no se borran: se **anulan** con motivo. No registres cuentas bancarias.

## 12. Administración (rol Administrador)
- **Usuarios**: crear cuenta (vinculada a una persona, opcional), asignar rol, desactivar, restablecer contraseña.
- **Roles y permisos**: qué puede hacer cada rol. El sistema no ofrece «eliminar».
- **Catálogos**: tipos, estados, roles de participación, canales, etc. Desactivar una opción no borra el historial.
- **Auditoría**: ingresos, cambios de rol, exportaciones, confirmaciones, importaciones, respaldos.

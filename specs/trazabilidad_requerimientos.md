# Trazabilidad — «FCHE · Requerimientos por módulo» → implementación

Estado al 12-10-2026. ✅ hecho y probado · 🟡 hecho con decisión por validar · ⏸ oculto por ajuste (segunda fase) · ⬜ no hecho.

| Módulo | Historia | Estado | Dónde / nota |
|---|---|---|---|
| AC | HU-AC-01 ingresar con correo | ✅ | también con usuario; `cuentas/backends.py` |
| AC | HU-AC-02 cuenta desactivada explicada | ✅ | solo con contraseña correcta; `CONTACTO_ADMINISTRADOR` |
| AC | HU-AC-03 cierre por inactividad | 🟡 | 60 min [P]; `SESION_SEGUNDOS` |
| AC | HU-AC-04 cambiar contraseña | ✅ | Mi cuenta |
| AC | HU-AC-05 pantallas 403/404 con volver | ✅ | |
| AC | HU-AC-06 Administrador restablece contraseña | 🟡 | [V#9] sin recuperación autónoma |
| AC | HU-AC-07 pantallas privadas exigen sesión | ✅ | `LoginRequiredMiddleware` |
| US | HU-US-01 cuenta solo para persona registrada | ✅ | obligatoria en pantalla; `crear_usuario` (consola) permite la primera cuenta sin persona |
| US | HU-US-02 dos roles | ✅ | más pantalla de permisos por rol |
| US | HU-US-03 activar/desactivar sin borrar | ✅ | |
| US | HU-US-04 trazabilidad de cuentas y roles | ✅ | Auditoría |
| US | HU-US-05 permisos en el servidor | ✅ | probado con URL directa |
| TE | HU-TE-01 dirección en cascada | ✅ | región → provincia → comuna → sector |
| TE | HU-TE-02 sectores dentro de sectores | ✅ | |
| TE | HU-TE-03 qué hay en una comuna o sector | ✅ | pestañas con contador, incluye subsectores |
| TE | HU-TE-04 crear sector sin salir y reconocer nombres | ✅ | normalización + nombres alternativos + aviso de parecidos |
| TE | HU-TE-05 municipalidad ligada a comuna | ✅ | una por comuna |
| TE | HU-TE-06 carga oficial | 🟡 | comando listo; falta el archivo CUT |
| PE | HU-PE-01 solo con nombre | ✅ | ficha rápida |
| PE | HU-PE-02 coincidencias, usar existente / crear de todos modos | ✅ | RUT, correo, teléfono, nombre (pg_trgm) |
| PE | HU-PE-03 RUT con o sin puntos | ✅ | módulo 11, único si existe |
| PE | HU-PE-04 origen | ✅ | catálogo |
| PE | HU-PE-05 varios contactos, teléfono normalizado | ✅ | +56… |
| PE | HU-PE-06 instituciones, carreras, cargos con fechas | ✅ | históricos |
| PE | HU-PE-07 acumula roles | ✅ | por participación |
| PE | HU-PE-08 estado del registro | ✅ | |
| PE | HU-PE-09 ficha con pestañas | ✅ | + Interacciones, Origen |
| PE | HU-PE-10 datos sensibles restringidos | 🟡 | permiso `ver_sensibles`; menores [V#2] |
| PE | HU-PE-11 desactivar | ✅ | |
| OR | HU-OR-01…08 | ✅ | incluye «Agregar persona con cargo» y la Fundación como propia |
| LU | HU-LU-01…05 | ✅ | crear desde la agenda; capacidad en compatibilidad |
| SO | HU-SO-01…06 | ✅ | «Nueva oportunidad», «Por identificar»; también «Crear proyecto» |
| IN | HU-IN-01…04 | ✅ | registrar desde persona, organización, actividad y solicitud; próximas acciones en el panel |
| IN | HU-IN-05 invitaciones y solicitudes de apoyo | ✅ | enviada, respondió, aceptó, rechazó, sin respuesta |
| AT | HU-AT-01…10 | ✅ | cargar listado desde la actividad |
| AT | HU-AT-11 proyecto o campaña opcional | 🟡 | módulo Proyecto (tablero F08); actividad nunca lo exige |
| AG | HU-AG-01…06 | ✅ | duración; filtros por estado, zona, responsable, organización |
| AG | HU-AG-07 serie | 🟡 | [P] cada repetición es una actividad dentro de la original |
| VA | HU-VA-01…05 | ✅ | ✓/⚠/✕ con motivo; búsqueda de candidatos; nunca asigna solo |
| VA | confirmar con incompatibilidad crítica | 🟡 | [V#3] apagado: `CONFIRMAR_CON_CONFLICTO_CRITICO` |
| DO | HU-DO-01…06 | ✅ | asociar existente sin duplicar archivo; vencimiento |
| RE | HU-RE-01…04 | ✅ | persona que llegó; «sin registro» |
| RE | mínimos para finalizar / reabrir | 🟡 | asistencia (o sin registro) + resultado; queda *realizada*; reabrir con permiso especial [V#4] |
| HI | HU-HI-01…06 | ✅ | fuente del dato en el historial; auditoría con filtro por fecha |
| BU | HU-BU-01…05 | ✅ | resultados agrupados por tipo; exportación auditada |
| CA | HU-CA-01…03 | ✅ | Gestor agrega/edita; desactivar solo Administrador |
| IG | HU-IG-01…06 | ✅ | ficha rápida, cola de incompletos, carga con vista previa y reversión, transcribir junto al documento |
| IG | importación histórica masiva | 🟡 | [V] disponible (personas, organizaciones, lugares) |
| DA | HU-DA-01…05 | ✅ | aviso de cambios sin guardar, cargando/reintentar, acciones rápidas |
| DA | HU-DA-06 celular | 🟡 | responsive; acceso por red [V#5] |
| PR | HU-PR-01/02 | ✅ | |
| NF | NF-01…09 | ✅ | NF-07 sin internet: estáticos locales |
| 2ª fase | reuniones, tareas, sesiones, beneficiarios, verificaciones, finanzas | ⏸ | construidos; se muestran con `SEGUNDA_FASE=True` |
| 2ª fase | talleres reutilizables, requisitos de fondos, divisiones electorales | ⬜ | no construidos |

## Vacíos detectados en la revisión de dudas
| Vacío | Estado | Dónde |
|---|---|---|
| Cupos y lista de espera | 🟡 | estado «En lista de espera» [P]; no ocupa cupo |
| Constancias de participación | 🟡 | imprimible desde Asistencia [P] |
| Informes a fondos | ⬜ | depende de los requisitos de cada fondo (2ª fase) |
| Avisos de caducidad | ✅ | panel: «Datos por vencer» (documentos, verificaciones, vigencia legal) |
| Derechos sobre los datos | 🟡 | acceso: exportar en Excel ✅ · rectificación: edición ✅ · eliminación: por decidir |
| Continuidad | 🟡 | manual y guía de entrega listos; falta definir el Administrador |

## F22 — Ingesta ampliada (pedido del 13-10-2026)
| Necesidad | Estado | Dónde |
|---|---|---|
| Datos relevantes de la persona (nacimiento, perfil, intereses, habilidades) | ✅ | ficha completa por secciones |
| Datos sensibles con consentimiento (Ley 21.719) | ✅ [V] | pestaña «Datos sensibles 🔒», ajuste `DATOS_SENSIBLES` |
| Consentimientos y apoderados de menores | ✅ [V#2] | pestañas «Consentimientos» y «Apoderados 🔒» |
| Estudiante: sede, jornada, año, asignatura, docente, horas | ✅ | pestaña «Formación» y planillas |
| Comunidad (grupo de personas de un sector) con padrón | ✅ [P] | `/comunidades`, comuna → Comunidades |
| A quién va dirigida la actividad (público, comunidades) | ✅ | pestaña «Público y comunidades» |
| Quién ejecuta frente a quién asiste; procedencia y horas | ✅ | pestaña «Participantes» (grupo del rol) |
| Minutas y avances por sesión, asistencia por sesión, evidencias | ✅ | pestaña «Sesiones y minutas» |
| Alcance de actividad, proyecto y comunidad | ✅ | pestaña «Alcance» |
| Planillas con columnas ampliadas | ✅ | Importaciones |

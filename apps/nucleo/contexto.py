MENU = [
    ("Inicio", "/dashboard", None),
    ("Solicitudes", "/solicitudes", "solicitudes.view_solicitud"),
    ("Proyectos", "/proyectos", "proyectos.view_proyecto"),
    ("Actividades", "/actividades", "actividades.view_actividad"),
    ("Personas", "/personas", "personas.view_persona"),
    ("Organizaciones", "/organizaciones", "organizaciones.view_organizacion"),
    ("Lugares", "/lugares", "lugares.view_lugar"),
    ("Calendario", "/calendario", "actividades.view_agendaactividad"),
    ("Reuniones", "/reuniones", "coordinacion.view_reunion", "reuniones"),
    ("Tareas", "/tareas", "coordinacion.view_tarea", "tareas"),
    ("Documentos", "/documentos", "documentos.view_documento"),
    ("Territorio", "/territorio", "territorio.view_comuna"),
    ("Importaciones", "/importaciones", "importaciones.importar_listado"),
    ("Finanzas", "/finanzas", "finanzas.view_movimiento", "finanzas"),
    ("Catálogos", "/administracion/catalogos/", "nucleo.view_estadoactividad"),
    ("Administración", "/administracion/", "auth.view_user"),
]


def navegacion(request):
    user = getattr(request, "user", None)
    from .fases import modulo_activo, modulos_activos

    modulos = modulos_activos()
    if not user or not user.is_authenticated:
        return {"menu": [], "modulos": modulos}
    ruta = request.path
    visibles = [(e, r) for e, r, perm, *modulo in MENU if (not perm or user.has_perm(perm)) and (not modulo or modulo_activo(modulo[0]))]
    coinciden = [r for _, r in visibles if ruta == r or (r != "/dashboard" and ruta.startswith(r.rstrip("/") + "/"))]
    activa = max(coinciden, key=len) if coinciden else None  # la ruta más específica
    return {"menu": [(e, r, r == activa) for e, r in visibles], "modulos": modulos}

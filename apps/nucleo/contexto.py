MENU = [
    ("Inicio", "/dashboard", None),
    ("Solicitudes", "/solicitudes", "solicitudes.view_solicitud"),
    ("Proyectos", "/proyectos", "proyectos.view_proyecto"),
    ("Actividades", "/actividades", "actividades.view_actividad"),
    ("Personas", "/personas", "personas.view_persona"),
    ("Organizaciones", "/organizaciones", "organizaciones.view_organizacion"),
    ("Lugares", "/lugares", "lugares.view_lugar"),
    ("Calendario", "/calendario", "actividades.view_agendaactividad"),
    ("Reuniones", "/reuniones", "coordinacion.view_reunion"),
    ("Tareas", "/tareas", "coordinacion.view_tarea"),
    ("Documentos", "/documentos", "documentos.view_documento"),
    ("Territorio", "/territorio", "territorio.view_comuna"),
    ("Importaciones", "/importaciones", "actividades.importar_listado"),
    ("Finanzas", "/finanzas", "finanzas.view_movimiento"),
    ("Administración", "/administracion/", "auth.view_user"),
]


def navegacion(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"menu": []}
    ruta = request.path
    return {
        "menu": [
            (e, r, ruta == r or (r != "/dashboard" and ruta.startswith(r.rstrip("/") + "/")))
            for e, r, perm in MENU
            if not perm or user.has_perm(perm)
        ]
    }

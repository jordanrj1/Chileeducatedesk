# (etiqueta, ruta, permiso, icono, grupo[, módulo de segunda fase])
MENU = [
    ("Inicio", "/dashboard", None, "inicio", ""),
    ("Solicitudes", "/solicitudes", "solicitudes.view_solicitud", "solicitudes", "Operación"),
    ("Proyectos", "/proyectos", "proyectos.view_proyecto", "proyectos", "Operación"),
    ("Actividades", "/actividades", "actividades.view_actividad", "actividades", "Operación"),
    ("Calendario", "/calendario", "actividades.view_agendaactividad", "calendario", "Operación"),
    ("Reuniones", "/reuniones", "coordinacion.view_reunion", "reuniones", "Operación", "reuniones"),
    ("Tareas", "/tareas", "coordinacion.view_tarea", "tareas", "Operación", "tareas"),
    ("Personas", "/personas", "personas.view_persona", "personas", "Registro"),
    ("Organizaciones", "/organizaciones", "organizaciones.view_organizacion", "organizaciones", "Registro"),
    ("Comunidades", "/comunidades", "comunidades.view_comunidad", "comunidades", "Registro"),
    ("Lugares", "/lugares", "lugares.view_lugar", "lugares", "Registro"),
    ("Territorio", "/territorio", "territorio.view_comuna", "territorio", "Registro"),
    ("Documentos", "/documentos", "documentos.view_documento", "documentos", "Registro"),
    ("Importaciones", "/importaciones", "importaciones.importar_listado", "importaciones", "Gestión"),
    ("Finanzas", "/finanzas", "finanzas.view_movimiento", "finanzas", "Gestión", "finanzas"),
    ("Catálogos", "/administracion/catalogos/", "nucleo.view_estadoactividad", "catalogos", "Configuración"),
    ("Administración", "/administracion/", "auth.view_user", "administracion", "Configuración"),
    ("Ayuda", "/ayuda", None, "ayuda", "Configuración"),
]

# Creación rápida desde la barra superior: (etiqueta, ruta, permiso, icono[, módulo])
NUEVO = [
    ("+ Solicitud", "/solicitudes/nueva", "solicitudes.add_solicitud", "solicitudes"),
    ("+ Actividad", "/actividades/nueva", "actividades.add_actividad", "actividades"),
    ("+ Persona", "/personas/nueva", "personas.add_persona", "persona_mas"),
    ("+ Organización", "/organizaciones/nueva", "organizaciones.add_organizacion", "organizaciones"),
    ("+ Comunidad", "/comunidades/nueva", "comunidades.add_comunidad", "comunidades"),
    ("+ Lugar", "/lugares/nuevo", "lugares.add_lugar", "lugares"),
    ("+ Documento", "/documentos/nuevo", "documentos.add_documento", "documentos"),
]


def _hubo_guardado(request):
    """Marca la página cuando se acaba de guardar algo: el navegador descarta los borradores enviados (AC-E3)."""
    from django.contrib.messages import get_messages

    return any(m.level_tag == "success" for m in get_messages(request))


def navegacion(request):
    user = getattr(request, "user", None)
    from .fases import modulo_activo, modulos_activos

    modulos = modulos_activos()
    if not user or not user.is_authenticated:
        return {"menu": [], "menu_grupos": [], "menu_nuevo": [], "modulos": modulos, "hubo_guardado": False}
    ruta = request.path
    visibles = [
        (e, r, icono, grupo) for e, r, perm, icono, grupo, *modulo in MENU
        if (not perm or user.has_perm(perm)) and (not modulo or modulo_activo(modulo[0]))
    ]
    coinciden = [r for _, r, _, _ in visibles if ruta == r or (r != "/dashboard" and ruta.startswith(r.rstrip("/") + "/"))]
    activa = max(coinciden, key=len) if coinciden else None  # la ruta más específica
    grupos = []
    for e, r, icono, grupo in visibles:
        if not grupos or grupos[-1][0] != grupo:
            grupos.append((grupo, []))
        grupos[-1][1].append((e, r, r == activa, icono))
    nuevo = [(e, r, icono) for e, r, perm, icono, *modulo in NUEVO if user.has_perm(perm) and (not modulo or modulo_activo(modulo[0]))]
    rol = ", ".join(user.groups.values_list("name", flat=True)) or ("Superusuario" if user.is_superuser else "Sin rol")
    return {
        "menu": [(e, r, r == activa) for e, r, _, _ in visibles],
        "menu_grupos": grupos,
        "menu_nuevo": nuevo,
        "rol_usuario": rol,
        "modulos": modulos,
        "hubo_guardado": _hubo_guardado(request),
    }

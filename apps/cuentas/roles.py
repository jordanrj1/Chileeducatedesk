"""Permisos iniciales de los dos roles (docs/CONTEXTO.md §9). Se pueden ajustar luego desde Administración > Roles."""
from django.contrib.auth.models import Group, Permission

OPERATIVAS = ["nucleo", "territorio", "personas", "organizaciones", "lugares", "proyectos", "actividades", "solicitudes", "coordinacion", "documentos", "importaciones"]
CATALOGOS_MODELOS = {
    "estadoactividad", "estadosolicitud", "estadoparticipacion", "rolparticipacion", "tipoorganizacion", "tipoactividad",
    "tipocontacto", "canal", "modalidad", "origenpersona", "estadoregistro", "tipolugar", "tipodocumento", "tipointervencion",
}


def _accion(codename):
    return codename.split("_", 1)[0]


SOLO_POR_EXCEPCION = {"reabrir_actividad"}  # nadie lo tiene por defecto [V#4]; el Administrador puede asignarlo en Roles


def permisos_gestor(p):
    app, cod = p.content_type.app_label, p.codename
    if cod in SOLO_POR_EXCEPCION:
        return False
    if app == "finanzas":
        return _accion(cod) != "delete"
    if app not in OPERATIVAS:
        return False
    if "auditoria" in cod or "historical" in cod and _accion(cod) != "view":
        return False
    return _accion(cod) != "delete"


def permisos_administrador(p):
    app, cod = p.content_type.app_label, p.codename
    accion = _accion(cod)
    modelo = cod.split("_", 1)[1] if "_" in cod else ""
    if app == "auth":
        return modelo in {"user", "group", "permission"} and accion in {"view", "add", "change"}
    if app == "cuentas":
        return accion in {"view", "add", "change"}
    if app == "finanzas":
        return False
    if app not in OPERATIVAS:
        return False
    if accion == "view":
        return True
    if app == "nucleo" and modelo in CATALOGOS_MODELOS and accion in {"add", "change"}:
        return True
    return accion in {"exportar", "importar", "ver"}


def sembrar_roles():
    from .models import PermisoInicial

    reglas = {"Gestor": permisos_gestor, "Administrador": permisos_administrador}
    permisos = list(Permission.objects.select_related("content_type"))
    for nombre, regla in reglas.items():
        grupo, _ = Group.objects.get_or_create(name=nombre)
        ya = set(PermisoInicial.objects.filter(grupo=grupo).values_list("permiso_id", flat=True))
        nuevos = [p for p in permisos if p.pk not in ya and regla(p)]
        pendientes = [p for p in permisos if p.pk not in ya]
        if nuevos:
            grupo.permissions.add(*nuevos)
        PermisoInicial.objects.bulk_create([PermisoInicial(grupo=grupo, permiso=p) for p in pendientes], ignore_conflicts=True)

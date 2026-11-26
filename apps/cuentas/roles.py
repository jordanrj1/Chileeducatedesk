"""Permisos iniciales de los dos roles, Gestor y Superadministrador (docs/CONTEXTO.md §9). Se pueden ajustar luego desde Administración > Roles.
El Superadministrador tiene todos los permisos del sistema, también los que se agreguen después (F29)."""
from django.contrib.auth.models import Group, Permission

OPERATIVAS = ["nucleo", "territorio", "personas", "organizaciones", "lugares", "proyectos", "actividades", "solicitudes", "coordinacion", "documentos", "importaciones", "comunidades"]
CATALOGOS_MODELOS = {
    "estadoactividad", "estadosolicitud", "estadoparticipacion", "rolparticipacion", "tipoorganizacion", "tipoactividad",
    "tipocontacto", "canal", "modalidad", "origenpersona", "estadoregistro", "tipolugar", "tipodocumento", "tipointervencion",
    "perfilpersona", "areatematica", "tramoetario", "parentesco", "tipoinvitado", "estadovoluntario",
    "naturalezajuridica", "rolorganizacion", "relacionlugar", "categoriagasto",
}


def _accion(codename):
    return codename.split("_", 1)[0]


SOLO_POR_EXCEPCION = {"reabrir_actividad"}  # nadie lo tiene por defecto [V#4]; el Superadministrador lo tiene y puede asignarlo en Roles


def permisos_gestor(p):
    app, cod = p.content_type.app_label, p.codename
    if cod in SOLO_POR_EXCEPCION or cod.startswith("desactivar_") or cod.startswith("fusionar_"):
        return False
    if app == "finanzas":
        return _accion(cod) != "delete"
    if app not in OPERATIVAS:
        return False
    if "auditoria" in cod or "historical" in cod and _accion(cod) != "view":
        return False
    return _accion(cod) != "delete"


GESTOR = "Gestor"
SUPERADMIN = "Superadministrador"


def permisos_superadmin(p):
    """El Superadministrador tiene todos los permisos."""
    return True


REGLAS = {GESTOR: permisos_gestor, SUPERADMIN: permisos_superadmin}


def asegurar_permisos_superadmin():
    """Asigna al Superadministrador cualquier permiso que aún no tenga (también los nuevos). Crea el rol si falta."""
    grupo, _ = Group.objects.get_or_create(name=SUPERADMIN)
    faltan = Permission.objects.exclude(pk__in=grupo.permissions.values_list("pk", flat=True))
    if faltan.exists():
        grupo.permissions.add(*faltan)
    return grupo


def restablecer_rol(grupo):
    """Vuelve los permisos del rol a los iniciales (Gestor: su regla; Superadministrador: todos)."""
    from .models import PermisoInicial

    regla = REGLAS[grupo.name]
    permisos = list(Permission.objects.select_related("content_type"))
    grupo.permissions.set([p for p in permisos if regla(p)])
    PermisoInicial.objects.bulk_create([PermisoInicial(grupo=grupo, permiso=p) for p in permisos], ignore_conflicts=True)


def sembrar_roles():
    from .models import PermisoInicial

    reglas = {GESTOR: permisos_gestor}
    permisos = list(Permission.objects.select_related("content_type"))
    for nombre, regla in reglas.items():
        grupo, _ = Group.objects.get_or_create(name=nombre)
        ya = set(PermisoInicial.objects.filter(grupo=grupo).values_list("permiso_id", flat=True))
        nuevos = [p for p in permisos if p.pk not in ya and regla(p)]
        pendientes = [p for p in permisos if p.pk not in ya]
        if nuevos:
            grupo.permissions.add(*nuevos)
        PermisoInicial.objects.bulk_create([PermisoInicial(grupo=grupo, permiso=p) for p in pendientes], ignore_conflicts=True)
    asegurar_permisos_superadmin()

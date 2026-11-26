"""Pantallas de Administración (solo Superadministrador): usuarios (crear, editar, activar o desactivar, desbloquear,
restablecer contraseña), roles con sus permisos (matriz por módulo y acción), la auditoría con filtros por fecha y acción
y los respaldos (lista y «Respaldar ahora»). Cada cambio de cuenta, rol o permiso queda registrado en la auditoría."""
import io
import os
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.nucleo.auditoria import registrar
from apps.nucleo.models import Auditoria
from apps.nucleo.selector import OpcionesVista
from apps.nucleo.vistas_base import Filtro, ListaBase, Permiso403Mixin
from apps.personas.selector import PERSONAS_SIN_CUENTA

from .forms_admin import ClaveForm, UsuarioForm
from .protecciones import MENSAJE_ULTIMO, es_el_ultimo
from .roles import OPERATIVAS, SUPERADMIN, restablecer_rol

User = get_user_model()
CRUMB = [("Administración", "/administracion/")]


class AdministracionIndice(Permiso403Mixin, TemplateView):
    permission_required = "auth.view_user"
    template_name = "administracion/indice.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["titulo"] = "Administración"
        return ctx


class UsuarioLista(ListaBase):
    model = User
    permission_required = "auth.view_user"
    titulo = "Usuarios"
    descripcion = "Cuentas de acceso del equipo, su rol y último ingreso."
    breadcrumb = CRUMB
    url_crear = "/administracion/usuarios/nuevo"
    permiso_crear = "auth.add_user"
    etiqueta_crear = "+ Nuevo usuario"
    campos_busqueda = ("username", "first_name", "last_name", "email")
    columnas = [
        ("Usuario", "username"),
        ("Nombre", lambda u: u.get_full_name()),
        ("Correo", "email"),
        ("Rol", lambda u: ", ".join(g.name for g in u.groups.all())),
        ("Persona", lambda u: getattr(getattr(u, "perfil", None), "persona", "") or ""),
        ("Estado", lambda u: "Activo" if u.is_active else "Desactivado"),
        ("Último ingreso", lambda u: u.last_login.astimezone().strftime("%d-%m-%Y %H:%M") if u.last_login else "Nunca"),
        ("Acceso", lambda u: "Bloqueado por intentos fallidos" if _bloqueado(u) else ""),
    ]
    orden_defecto = ("username",)

    def get_queryset(self):
        return super().get_queryset().prefetch_related("groups").select_related("perfil__persona")

    def contexto_extra(self):
        return {}


class UsuarioNuevo(Permiso403Mixin, CreateView):
    model = User
    form_class = UsuarioForm
    permission_required = "auth.add_user"
    template_name = "administracion/usuario_form.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nuevo usuario", volver_url="/administracion/usuarios", breadcrumb=CRUMB + [("Usuarios", "/administracion/usuarios")])
        return ctx

    def form_valid(self, form):
        usuario = form.save()
        registrar(self.request.user, "usuario_creado", usuario.username, f"rol={form.cleaned_data['rol']}")
        messages.success(self.request, "Usuario creado.")
        return redirect("cuentas_admin:usuarios")


class UsuarioEditar(Permiso403Mixin, UpdateView):
    model = User
    form_class = UsuarioForm
    permission_required = "auth.change_user"
    template_name = "administracion/usuario_form.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo=f"Editar usuario: {self.object.username}", volver_url="/administracion/usuarios", breadcrumb=CRUMB + [("Usuarios", "/administracion/usuarios")], editando=self.object, bloqueado=_bloqueado(self.object))
        return ctx

    def form_valid(self, form):
        antes = set(form.instance.groups.values_list("name", flat=True))
        usuario = form.save()
        ahora = set(usuario.groups.values_list("name", flat=True))
        if antes != ahora:
            registrar(self.request.user, "rol_cambiado", usuario.username, f"{sorted(antes)} → {sorted(ahora)}")
        messages.success(self.request, "Usuario actualizado.")
        return redirect("cuentas_admin:usuarios")


class UsuarioAlternar(Permiso403Mixin, View):
    permission_required = "auth.change_user"

    def post(self, request, pk):
        usuario = get_object_or_404(User, pk=pk)
        if usuario.pk == request.user.pk:
            messages.error(request, "No puedes desactivar tu propia cuenta.")
            return redirect("cuentas_admin:usuarios")
        if usuario.is_active and es_el_ultimo(usuario):
            messages.error(request, MENSAJE_ULTIMO)
            registrar(request.user, "usuario_desactivacion_rechazada", usuario.username, "último Superadministrador activo")
            return redirect("cuentas_admin:usuarios")
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=["is_active"])
        registrar(request.user, "usuario_activado" if usuario.is_active else "usuario_desactivado", usuario.username)
        messages.success(request, "Cuenta activada." if usuario.is_active else "Cuenta desactivada; la persona conserva su ficha.")
        return redirect("cuentas_admin:usuarios")


def _bloqueado(u):
    from .bloqueo import bloqueado

    return bloqueado(u.username) or bloqueado(u.email)


class UsuarioDesbloquear(Permiso403Mixin, View):
    permission_required = "auth.change_user"

    def post(self, request, pk):
        from .bloqueo import desbloquear

        usuario = get_object_or_404(User, pk=pk)
        desbloquear(request.user, usuario)
        messages.success(request, f"Acceso de {usuario.username} desbloqueado.")
        return redirect("cuentas_admin:usuarios")


class UsuarioClave(Permiso403Mixin, View):
    """Solo el Superadministrador restablece contraseñas [V#9]."""

    permission_required = "auth.change_user"

    def get(self, request, pk):
        usuario = get_object_or_404(User, pk=pk)
        return render(request, "generico/formulario.html", {"form": ClaveForm(usuario), "titulo": f"Nueva contraseña para {usuario.username}", "volver_url": "/administracion/usuarios", "breadcrumb": CRUMB})

    def post(self, request, pk):
        usuario = get_object_or_404(User, pk=pk)
        form = ClaveForm(usuario, request.POST)
        if form.is_valid():
            usuario.set_password(form.cleaned_data["password1"])
            usuario.save()
            registrar(request.user, "clave_restablecida", usuario.username)
            messages.success(request, "Contraseña restablecida.")
            return redirect("cuentas_admin:usuarios")
        return render(request, "generico/formulario.html", {"form": form, "titulo": f"Nueva contraseña para {usuario.username}", "volver_url": "/administracion/usuarios", "breadcrumb": CRUMB}, status=400)


class PersonasLibres(OpcionesVista):
    """Personas sin cuenta, para el buscador del formulario de cuenta (ver apps/personas/selector.py)."""

    fuente = PERSONAS_SIN_CUENTA


# --- Roles y permisos ---------------------------------------------------
ACCIONES = {"view": "Ver", "add": "Crear", "change": "Editar"}
MODULOS = {"auth": "Cuentas y roles", "cuentas": "Respaldos y perfiles", "nucleo": "Núcleo y catálogos", "coordinacion": "Coordinación", "importaciones": "Importaciones", "organizaciones": "Organizaciones"}



def permisos_editables():
    """Permisos que se pueden asignar: sin 'eliminar' (el sistema no borra) ni modelos de historial.
    Devuelve (módulo, modelo, accion, etiqueta, permiso)."""
    res = []
    for p in Permission.objects.select_related("content_type").order_by("content_type__app_label", "content_type__model", "codename"):
        app = p.content_type.app_label
        if app not in OPERATIVAS + ["auth", "cuentas", "finanzas"]:
            continue
        if p.codename.startswith("delete_") or "historical" in p.codename or p.content_type.model in {"permisoinicial", "permission", "contenttype"} and p.codename != "respaldar":
            continue
        if app == "auth" and p.content_type.model not in {"user", "group"}:
            continue
        modelo = p.content_type.model_class()
        nombre_modelo = "respaldos" if p.codename == "respaldar" else str(modelo._meta.verbose_name) if modelo else p.content_type.model
        accion = p.codename.split("_", 1)[0]
        etiqueta = p.name
        res.append((app, nombre_modelo, accion if accion in ACCIONES else "otra", etiqueta, p))
    return res


def matriz(grupo):
    """[(módulo, [(modelo, [ver, crear, editar] como (pk, marcado) o None, [(pk, etiqueta, marcado)])])] para dibujar la matriz de un rol."""
    asignados = set(grupo.permissions.values_list("pk", flat=True))
    modulos = {}
    for app, modelo, accion, etiqueta, p in permisos_editables():
        fila = modulos.setdefault(app, {}).setdefault(modelo, ({}, []))
        if accion == "otra":
            fila[1].append((p.pk, etiqueta, p.pk in asignados))
        else:
            fila[0][accion] = (p.pk, p.pk in asignados)
    return [(MODULOS.get(app, app.capitalize()), [(m, [acc.get(a) for a in ACCIONES], otras) for m, (acc, otras) in sorted(filas.items())]) for app, filas in sorted(modulos.items())]


class RolLista(Permiso403Mixin, TemplateView):
    permission_required = "auth.view_group"
    template_name = "administracion/roles.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["roles"] = [(g, g.user_set.count(), g.permissions.count()) for g in Group.objects.all()]
        ctx.update(titulo="Roles", breadcrumb=CRUMB)
        return ctx


class RolEditar(Permiso403Mixin, View):
    permission_required = "auth.change_group"

    def contexto(self, grupo):
        return {"grupo": grupo, "matriz": matriz(grupo), "fijo": grupo.name == SUPERADMIN, "titulo": f"Permisos del rol {grupo.name}", "breadcrumb": CRUMB + [("Roles", "/administracion/roles")]}

    def get(self, request, pk):
        return render(request, "administracion/rol_editar.html", self.contexto(get_object_or_404(Group, pk=pk)))

    def post(self, request, pk):
        grupo = get_object_or_404(Group, pk=pk)
        if grupo.name == SUPERADMIN:  # tiene todos los permisos y no se recorta: así nunca se pierde el acceso
            messages.info(request, "El Superadministrador tiene todos los permisos; no se pueden quitar.")
            return redirect("cuentas_admin:roles")
        if request.POST.get("restablecer"):
            restablecer_rol(grupo)
            registrar(request.user, "permisos_restablecidos", grupo.name, f"{grupo.permissions.count()} permisos")
            messages.success(request, f"Permisos iniciales restablecidos para {grupo.name}.")
            return redirect("cuentas_admin:rol_editar", pk=grupo.pk)
        ids = {int(i) for i in request.POST.getlist("permisos") if i.isdigit()}
        validos = {p.pk for *_, p in permisos_editables()}
        antes = set(grupo.permissions.values_list("pk", flat=True))
        conservar = antes - validos  # lo que esta pantalla no gestiona (p. ej. permisos de historial)
        grupo.permissions.set(Permission.objects.filter(pk__in=(ids & validos) | conservar))
        nuevos = (ids & validos) - antes
        quitados = (antes & validos) - ids
        registrar(request.user, "permisos_modificados", grupo.name, f"{len(ids & validos)} permisos; agregados {len(nuevos)}, quitados {len(quitados)}")
        messages.success(request, "Permisos guardados.")
        return redirect("cuentas_admin:roles")


# --- Respaldos ----------------------------------------------------------
def carpeta_respaldos():
    from pathlib import Path

    from django.conf import settings

    return Path(os.environ.get("RESPALDO_DIR") or str(settings.BASE_DIR.parent / "fche_respaldos"))


def lista_respaldos():
    """[(nombre, fecha, tamaño en KB, tipo)] de los archivos de respaldo, del más nuevo al más antiguo."""
    carpeta = carpeta_respaldos()
    tipos = {"fche_bd_": "Base de datos", "fche_documentos_": "Documentos", "fche_config_": "Configuración"}
    res = []
    if carpeta.is_dir():
        for f in carpeta.glob("fche_*"):
            if f.is_file():
                tipo = next((t for pre, t in tipos.items() if f.name.startswith(pre)), "Otro")
                st = f.stat()
                res.append((f.name, datetime.fromtimestamp(st.st_mtime), max(1, st.st_size // 1024), tipo))
    return sorted(res, key=lambda r: r[1], reverse=True)


class RespaldoLista(Permiso403Mixin, TemplateView):
    permission_required = "cuentas.respaldar"
    template_name = "administracion/respaldos.html"

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        filas = lista_respaldos()
        ctx.update(titulo="Respaldos", breadcrumb=CRUMB, filas=filas[:60], total=len(filas), carpeta=carpeta_respaldos(), ultimo=filas[0][1] if filas else None)
        return ctx


class RespaldoAhora(Permiso403Mixin, View):
    """Solo POST. Ejecuta el comando `respaldar`; un segundo clic mientras corre no lanza otro."""

    permission_required = "cuentas.respaldar"
    http_method_names = ["post"]

    def post(self, request):
        from django.core.cache import cache
        from django.core.management import call_command
        from django.core.management.base import CommandError

        if not cache.add("fche_respaldando", 1, 600):
            messages.warning(request, "Ya hay un respaldo en curso. Espera a que termine.")
            return redirect("cuentas_admin:respaldos")
        try:
            salida = io.StringIO()
            call_command("respaldar", destino=str(carpeta_respaldos()), stdout=salida)
            registrar(request.user, "respaldo_manual", str(carpeta_respaldos()))
            messages.success(request, "Respaldo listo. " + salida.getvalue().strip())
        except CommandError as e:
            registrar(request.user, "respaldo_fallido", str(carpeta_respaldos()), str(e))
            messages.error(request, f"No se pudo respaldar: {e}")
        finally:
            cache.delete("fche_respaldando")
        return redirect("cuentas_admin:respaldos")


class AuditoriaLista(ListaBase):
    model = Auditoria
    permission_required = "nucleo.view_auditoria"
    titulo = "Auditoría"
    descripcion = "Registro de acciones relevantes: quién hizo qué y cuándo."
    breadcrumb = CRUMB
    campos_busqueda = ("usuario_nombre", "objeto", "detalle", "accion")
    columnas = [("Fecha", lambda a: a.fecha.astimezone().strftime("%d-%m-%Y %H:%M")), ("Usuario", "usuario_nombre"), ("Acción", "accion"), ("Objeto", "objeto"), ("Detalle", "detalle")]
    orden_defecto = ("-fecha", "-id")
    filtros = [
        Filtro("accion", "Acción", "accion", lambda: [(a, a) for a in Auditoria.objects.values_list("accion", flat=True).distinct().order_by("accion")], principal=True, todos="Todas"),
        Filtro("desde", "Desde", "fecha__date__gte", entrada="date", principal=True),
        Filtro("hasta", "Hasta", "fecha__date__lte", entrada="date", principal=True),
    ]
    texto_vacio = "Sin registros de auditoría."
    paginate_by = 50

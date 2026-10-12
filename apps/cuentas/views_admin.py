from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html_join
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.nucleo.auditoria import registrar
from apps.nucleo.models import Auditoria
from apps.nucleo.vistas_base import ListaBase, Permiso403Mixin

from .forms_admin import ClaveForm, UsuarioForm
from .roles import OPERATIVAS

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
        ctx.update(titulo=f"Editar usuario: {self.object.username}", volver_url="/administracion/usuarios", breadcrumb=CRUMB + [("Usuarios", "/administracion/usuarios")], editando=self.object)
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
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=["is_active"])
        registrar(request.user, "usuario_activado" if usuario.is_active else "usuario_desactivado", usuario.username)
        messages.success(request, "Cuenta activada." if usuario.is_active else "Cuenta desactivada; la persona conserva su ficha.")
        return redirect("cuentas_admin:usuarios")


class UsuarioClave(Permiso403Mixin, View):
    """Solo el Administrador restablece contraseñas [V#9]."""

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


class PersonasLibres(Permiso403Mixin, View):
    """Opciones de persona sin cuenta, filtradas por texto (HTMX)."""

    permission_required = "auth.add_user"

    def get(self, request):
        from apps.personas.models import Persona

        q = request.GET.get("q_persona", "")
        qs = Persona.objects.filter(activo=True, cuenta__isnull=True).buscar(q)[:25]
        opciones = [("", "---------")] + [(p.pk, p.nombre_completo) for p in qs]
        return HttpResponse(format_html_join("", '<option value="{}">{}</option>', opciones))


# --- Roles y permisos ---------------------------------------------------
ACCIONES = {"view": "Ver", "add": "Crear", "change": "Editar"}
PROTEGIDOS_ADMIN = {"auth.view_user", "auth.add_user", "auth.change_user", "auth.view_group", "auth.change_group", "auth.view_permission"}


def permisos_editables():
    """Permisos que se pueden asignar: sin 'eliminar' (el sistema no borra) ni modelos de historial."""
    res = []
    for p in Permission.objects.select_related("content_type").order_by("content_type__app_label", "content_type__model", "codename"):
        app = p.content_type.app_label
        if app not in OPERATIVAS + ["auth", "cuentas", "finanzas"]:
            continue
        if p.codename.startswith("delete_") or "historical" in p.codename or p.content_type.model in {"permisoinicial", "permission", "contenttype"}:
            continue
        if app == "auth" and p.content_type.model not in {"user", "group"}:
            continue
        modelo = p.content_type.model_class()
        nombre_modelo = str(modelo._meta.verbose_name) if modelo else p.content_type.model
        accion = p.codename.split("_", 1)[0]
        etiqueta = f"{ACCIONES[accion]} {nombre_modelo}" if accion in ACCIONES else p.name
        res.append((app, etiqueta, p))
    return res


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
        asignados = set(grupo.permissions.values_list("pk", flat=True))
        grupos = {}
        for app, etiqueta, p in permisos_editables():
            grupos.setdefault(app, []).append((p.pk, etiqueta, p.pk in asignados, f"{app}.{p.codename}" in PROTEGIDOS_ADMIN and grupo.name == "Administrador"))
        return {"grupo": grupo, "grupos": sorted(grupos.items()), "titulo": f"Permisos del rol {grupo.name}", "breadcrumb": CRUMB + [("Roles", "/administracion/roles")]}

    def get(self, request, pk):
        return render(request, "administracion/rol_editar.html", self.contexto(get_object_or_404(Group, pk=pk)))

    def post(self, request, pk):
        grupo = get_object_or_404(Group, pk=pk)
        ids = {int(i) for i in request.POST.getlist("permisos") if i.isdigit()}
        validos = {p.pk for _, _, p in permisos_editables()}
        if grupo.name == "Administrador":  # evita quedarse sin acceso a la administración
            ids |= {p.pk for _, _, p in permisos_editables() if f"{p.content_type.app_label}.{p.codename}" in PROTEGIDOS_ADMIN}
        antes = set(grupo.permissions.values_list("pk", flat=True))
        conservar = antes - validos  # lo que esta pantalla no gestiona (p. ej. permisos de historial)
        grupo.permissions.set(Permission.objects.filter(pk__in=(ids & validos) | conservar))
        registrar(request.user, "permisos_modificados", grupo.name, f"{len(ids & validos)} permisos")
        messages.success(request, "Permisos guardados.")
        return redirect("cuentas_admin:roles")


class AuditoriaLista(ListaBase):
    model = Auditoria
    permission_required = "nucleo.view_auditoria"
    titulo = "Auditoría"
    breadcrumb = CRUMB
    campos_busqueda = ("usuario_nombre", "objeto", "detalle", "accion")
    columnas = [("Fecha", lambda a: a.fecha.astimezone().strftime("%d-%m-%Y %H:%M")), ("Usuario", "usuario_nombre"), ("Acción", "accion"), ("Objeto", "objeto"), ("Detalle", "detalle")]
    orden_defecto = ("-fecha", "-id")
    texto_vacio = "Sin registros de auditoría."
    paginate_by = 50

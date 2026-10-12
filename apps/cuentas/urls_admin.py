from django.urls import path

from . import views_admin as v

app_name = "cuentas_admin"
urlpatterns = [
    path("", v.AdministracionIndice.as_view(), name="indice"),
    path("usuarios", v.UsuarioLista.as_view(), name="usuarios"),
    path("usuarios/nuevo", v.UsuarioNuevo.as_view(), name="usuario_nuevo"),
    path("usuarios/personas", v.PersonasLibres.as_view(), name="personas_libres"),
    path("usuarios/<int:pk>/editar", v.UsuarioEditar.as_view(), name="usuario_editar"),
    path("usuarios/<int:pk>/alternar", v.UsuarioAlternar.as_view(), name="usuario_alternar"),
    path("usuarios/<int:pk>/clave", v.UsuarioClave.as_view(), name="usuario_clave"),
    path("roles", v.RolLista.as_view(), name="roles"),
    path("roles/<int:pk>", v.RolEditar.as_view(), name="rol_editar"),
    path("auditoria", v.AuditoriaLista.as_view(), name="auditoria"),
]

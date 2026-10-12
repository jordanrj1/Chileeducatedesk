from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from apps.cuentas.forms import LoginForm
from apps.nucleo import views
from apps.nucleo.vistas_busqueda import Buscar
from apps.nucleo.vistas_inicio import Dashboard

handler403 = "apps.nucleo.views.error_403"
handler404 = "apps.nucleo.views.error_404"
handler500 = "apps.nucleo.views.error_500"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path(
        "login",
        login_not_required(LoginView.as_view(template_name="cuentas/login.html", authentication_form=LoginForm, redirect_authenticated_user=True)),
        name="login",
    ),
    path("logout", LogoutView.as_view(), name="logout"),
    path("dashboard", Dashboard.as_view(), name="dashboard"),
    path("buscar", Buscar.as_view(), name="buscar"),
    path("salud", views.salud, name="salud"),
    path("", include("apps.cuentas.urls")),
    path("administracion/", include("apps.cuentas.urls_admin")),
    path("administracion/", include("apps.nucleo.urls")),
    path("", include("apps.territorio.urls")),
    path("", include("apps.personas.urls")),
    path("", include("apps.organizaciones.urls")),
    path("", include("apps.lugares.urls")),
    path("", include("apps.proyectos.urls")),
    path("", include("apps.actividades.urls")),
    path("", include("apps.solicitudes.urls")),
    path("", include("apps.coordinacion.urls")),
    path("", include("apps.documentos.urls")),
    path("", include("apps.finanzas.urls")),
    path("", include("apps.importaciones.urls")),
]

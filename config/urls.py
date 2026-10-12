from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from apps.nucleo import views

handler403 = "apps.nucleo.views.error_403"
handler404 = "apps.nucleo.views.error_404"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login", login_not_required(LoginView.as_view(template_name="cuentas/login.html", redirect_authenticated_user=True)), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("buscar", views.buscar, name="buscar"),
    path("administracion/", views.administracion, name="administracion"),
    path("salud", views.salud, name="salud"),
]

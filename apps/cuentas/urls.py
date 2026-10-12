from django.urls import path

from . import views

app_name = "cuentas"
urlpatterns = [
    path("mi-cuenta", views.mi_cuenta, name="mi_cuenta"),
    path("mi-cuenta/clave", views.CambiarClave.as_view(), name="cambiar_clave"),
]

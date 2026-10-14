"""Direcciones (rutas) de catálogos, dentro de Administración.
El Gestor agrega y edita valores; desactivar y unir valores repetidos es solo del Administrador."""
from django.urls import path

from . import vistas_catalogos as vc

app_name = "nucleo"
urlpatterns = [
    path("catalogos/", vc.Indice.as_view(), name="catalogos"),
    path("catalogos/<slug:slug>/", vc.Lista.as_view(), name="catalogo"),
    path("catalogos/<slug:slug>/<int:pk>/editar", vc.Editar.as_view(), name="catalogo_editar"),
    path("catalogos/<slug:slug>/<int:pk>/alternar", vc.Alternar.as_view(), name="catalogo_alternar"),
    path("catalogos/<slug:slug>/<int:pk>/unir", vc.Unir.as_view(), name="catalogo_unir"),
]

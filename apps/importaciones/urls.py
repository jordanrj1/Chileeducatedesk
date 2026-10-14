"""Direcciones (rutas) de cargas de listados: listado, nueva, revisar (vista previa), ficha y revertir.
La carga también se abre desde la pestaña Participantes de una actividad."""
from django.urls import path

from . import views

app_name = "importaciones"
urlpatterns = [
    path("importaciones", views.LoteLista.as_view(), name="lista"),
    path("importaciones/nueva", views.LoteNuevo.as_view(), name="nueva"),
    path("importaciones/<int:pk>", views.LoteFicha.as_view(), name="ficha"),
    path("importaciones/<int:pk>/revisar", views.LoteRevisar.as_view(), name="revisar"),
    path("importaciones/<int:pk>/revertir", views.LoteRevertir.as_view(), name="revertir"),
]

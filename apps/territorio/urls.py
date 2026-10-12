from django.urls import path

from . import views

app_name = "territorio"
urlpatterns = [
    path("territorio", views.ComunasLista.as_view(), name="lista"),
    path("territorio/comuna/<int:pk>", views.ComunaDetalle.as_view(), name="comuna"),
    path("territorio/sectores", views.SectoresOpciones.as_view(), name="sectores"),
]

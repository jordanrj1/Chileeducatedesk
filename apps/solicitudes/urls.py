from django.urls import path

from . import views

app_name = "solicitudes"
urlpatterns = [
    path("solicitudes", views.SolicitudLista.as_view(), name="lista"),
    path("solicitudes/exportar", views.SolicitudExportar.as_view(), name="exportar"),
    path("solicitudes/nueva", views.SolicitudNueva.as_view(), name="nueva"),
    path("solicitudes/<int:pk>", views.SolicitudFicha.as_view(), name="ficha"),
    path("solicitudes/<int:pk>/editar", views.SolicitudEditar.as_view(), name="editar"),
    path("solicitudes/<int:pk>/estado", views.SolicitudEstado.as_view(), name="estado"),
    path("solicitudes/<int:pk>/reabrir", views.SolicitudReabrir.as_view(), name="reabrir"),
    path("solicitudes/<int:pk>/crear-proyecto", views.SolicitudAProyecto.as_view(), name="crear_proyecto"),
    path("solicitudes/<int:pk>/crear-actividad", views.SolicitudAActividad.as_view(), name="crear_actividad"),
]

from django.urls import path

from . import views

app_name = "lugares"
urlpatterns = [
    path("lugares", views.LugarLista.as_view(), name="lista"),
    path("lugares/exportar", views.LugarExportar.as_view(), name="exportar"),
    path("lugares/nuevo", views.LugarNuevo.as_view(), name="nuevo"),
    path("lugares/<int:pk>", views.LugarFicha.as_view(), name="ficha"),
    path("lugares/<int:pk>/editar", views.LugarEditar.as_view(), name="editar"),
    path("lugares/<int:pk>/alternar", views.LugarAlternar.as_view(), name="alternar"),
]

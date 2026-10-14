"""Direcciones (rutas) de comunidades: listado, nueva, ficha, editar, desactivar, exportar e integrantes."""
from django.urls import path

from apps.nucleo.hijos import urls_hijo

from . import forms, models, views

app_name = "comunidades"
urlpatterns = [
    path("comunidades", views.ComunidadLista.as_view(), name="lista"),
    path("comunidades/exportar", views.ComunidadExportar.as_view(), name="exportar"),
    path("comunidades/opciones", views.ComunidadOpciones.as_view(), name="opciones"),
    path("comunidades/nueva", views.ComunidadNueva.as_view(), name="nueva"),
    path("comunidades/<int:pk>", views.ComunidadFicha.as_view(), name="ficha"),
    path("comunidades/<int:pk>/editar", views.ComunidadEditar.as_view(), name="editar"),
    path("comunidades/<int:pk>/alternar", views.ComunidadAlternar.as_view(), name="alternar"),
    *urls_hijo("comunidades", "integrantes", "Integrante", modelo=models.ComunidadMiembro, form_class=forms.IntegranteForm, tab="integrantes",
               etiqueta="integrante", padre_modelo=models.Comunidad, campo_padre="comunidad"),
]

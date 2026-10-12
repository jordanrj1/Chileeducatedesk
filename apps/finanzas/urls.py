from django.urls import path

from apps.nucleo.hijos import urls_hijo
from apps.proyectos.models import Proyecto

from . import forms, models, views

app_name = "finanzas"
urlpatterns = [
    path("finanzas", views.MovimientoLista.as_view(), name="lista"),
    path("finanzas/exportar", views.MovimientoExportar.as_view(), name="exportar"),
    path("finanzas/nuevo", views.MovimientoNuevo.as_view(), name="nuevo"),
    path("finanzas/<int:pk>", views.MovimientoFicha.as_view(), name="ficha"),
    path("finanzas/<int:pk>/editar", views.MovimientoEditar.as_view(), name="editar"),
    path("finanzas/<int:pk>/anular", views.MovimientoAnular.as_view(), name="anular"),
    *urls_hijo("finanzas/proyectos", "items", "Item", modelo=models.ItemPresupuesto, form_class=forms.ItemForm, tab="presupuesto", etiqueta="ítem de presupuesto", padre_modelo=Proyecto, campo_padre="proyecto"),
]

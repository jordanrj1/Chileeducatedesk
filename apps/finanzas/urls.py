"""Direcciones (rutas) de finanzas. Las que empiezan con /finanzas son de la 2.ª fase: con SEGUNDA_FASE=False responden
«no existe», aunque estén escritas aquí. Los gastos de una actividad y el presupuesto del proyecto (F28 B) cuelgan de
/actividades y /proyectos y son visibles siempre."""
from django.urls import path

from apps.nucleo.hijos import urls_hijo
from apps.proyectos.models import Proyecto

from . import forms, models, views, views_gastos

app_name = "finanzas"
urlpatterns = [
    path("finanzas", views.MovimientoLista.as_view(), name="lista"),
    path("finanzas/exportar", views.MovimientoExportar.as_view(), name="exportar"),
    path("finanzas/nuevo", views.MovimientoNuevo.as_view(), name="nuevo"),
    path("finanzas/<int:pk>", views.MovimientoFicha.as_view(), name="ficha"),
    path("finanzas/<int:pk>/editar", views.MovimientoEditar.as_view(), name="editar"),
    path("finanzas/<int:pk>/anular", views.MovimientoAnular.as_view(), name="anular"),
    # F28 B: visibles siempre
    path("actividades/<int:pk>/gastos/nuevo", views_gastos.GastoNuevo.as_view(), name="gasto_nuevo"),
    path("actividades/<int:pk>/gastos/exportar", views_gastos.GastosExportar.as_view(), name="gastos_exportar"),
    path("actividades/<int:pk>/gastos/<int:gid>/editar", views_gastos.GastoEditar.as_view(), name="gasto_editar"),
    path("actividades/<int:pk>/gastos/<int:gid>/revisar", views_gastos.GastoRevisar.as_view(), name="gasto_revisar"),
    path("actividades/<int:pk>/gastos/<int:gid>/anular", views_gastos.GastoAnular.as_view(), name="gasto_anular"),
    path("proyectos/<int:pk>/gastos/exportar", views_gastos.GastosProyectoExportar.as_view(), name="gastos_proyecto_exportar"),
    *urls_hijo("proyectos", "presupuesto", "ItemVisible", modelo=models.ItemPresupuesto, form_class=forms.ItemForm, tab="gastos", etiqueta="ítem de presupuesto", padre_modelo=Proyecto, campo_padre="proyecto"),
    *urls_hijo("finanzas/proyectos", "items", "Item", modelo=models.ItemPresupuesto, form_class=forms.ItemForm, tab="presupuesto", etiqueta="ítem de presupuesto", padre_modelo=Proyecto, campo_padre="proyecto"),
]

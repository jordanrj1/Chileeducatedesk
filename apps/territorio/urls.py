"""Direcciones (rutas) del territorio: índice, región, comuna, sector, exportar, crear y editar sectores,
y las listas que alimentan la dirección en cascada."""
from django.urls import path

from . import views

app_name = "territorio"
urlpatterns = [
    path("territorio", views.TerritorioIndice.as_view(), name="lista"),
    path("territorio/region/<int:pk>", views.RegionDetalle.as_view(), name="region"),
    path("territorio/comuna/<int:pk>", views.ComunaFicha.as_view(), name="comuna"),
    path("territorio/comuna/<int:pk>/exportar", views.ComunaExportar.as_view(), name="comuna_exportar"),
    path("territorio/comuna/<int:pk>/sectores/nuevo", views.SectorNuevo.as_view(), name="sector_nuevo"),
    path("territorio/sector/<int:pk>", views.SectorFicha.as_view(), name="sector"),
    path("territorio/sector/<int:pk>/exportar", views.SectorExportar.as_view(), name="sector_exportar"),
    path("territorio/sector/<int:pk>/editar", views.SectorEditar.as_view(), name="sector_editar"),
    path("territorio/sector/<int:pk>/alias", views.AliasNuevo.as_view(), name="alias_nuevo"),
    path("territorio/provincias", views.ProvinciasOpciones.as_view(), name="provincias"),
    path("territorio/comunas", views.ComunasOpciones.as_view(), name="comunas"),
    path("territorio/sectores", views.SectoresOpciones.as_view(), name="sectores"),
    path("territorio/sectores/crear", views.SectorCrearRapido.as_view(), name="sector_crear_rapido"),
]

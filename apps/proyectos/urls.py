"""Direcciones (rutas) de proyectos: listado, nuevo, ficha, editar, exportar y las secciones de la ficha."""
from django.urls import path

from apps.nucleo.hijos import urls_hijo

from . import forms, models, views

app_name = "proyectos"
P = dict(padre_modelo=models.Proyecto, campo_padre="proyecto")
urlpatterns = [
    path("proyectos", views.ProyectoLista.as_view(), name="lista"),
    path("proyectos/exportar", views.ProyectoExportar.as_view(), name="exportar"),
    path("proyectos/nuevo", views.ProyectoNuevo.as_view(), name="nuevo"),
    path("proyectos/<int:pk>", views.ProyectoFicha.as_view(), name="ficha"),
    path("proyectos/<int:pk>/editar", views.ProyectoEditar.as_view(), name="editar"),
    *urls_hijo("proyectos", "equipo", "Equipo", modelo=models.ProyectoPersona, form_class=forms.EquipoForm, tab="equipo", etiqueta="persona del equipo", **P),
    *urls_hijo("proyectos", "beneficiarios", "Beneficiario", modelo=models.ProyectoPersona, form_class=forms.BeneficiarioForm, tab="beneficiarios", etiqueta="beneficiario", **P),
    *urls_hijo("proyectos", "organizaciones", "Organizacion", modelo=models.ProyectoOrganizacion, form_class=forms.ProyectoOrganizacionForm, tab="organizaciones", etiqueta="organización", **P),
    *urls_hijo("proyectos", "comunidades", "Comunidad", modelo=models.ProyectoComunidad, form_class=forms.ProyectoComunidadForm, tab="comunidades", etiqueta="comunidad destinataria", **P),
    *urls_hijo("proyectos", "postulaciones", "Postulacion", modelo=models.Postulacion, form_class=forms.PostulacionForm, tab="postulacion", etiqueta="postulación", **P),
]

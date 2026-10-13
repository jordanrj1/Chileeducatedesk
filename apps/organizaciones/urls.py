from django.urls import path

from apps.nucleo.hijos import urls_hijo
from apps.personas import forms as pf, models as pm

from . import models, views

app_name = "organizaciones"
urlpatterns = [
    path("organizaciones", views.OrganizacionLista.as_view(), name="lista"),
    path("organizaciones/exportar", views.OrganizacionExportar.as_view(), name="exportar"),
    path("organizaciones/opciones", views.OrganizacionOpciones.as_view(), name="opciones"),
    path("organizaciones/nueva", views.OrganizacionNueva.as_view(), name="nueva"),
    path("organizaciones/<int:pk>", views.OrganizacionFicha.as_view(), name="ficha"),
    path("organizaciones/<int:pk>/editar", views.OrganizacionEditar.as_view(), name="editar"),
    path("organizaciones/<int:pk>/alternar", views.OrganizacionAlternar.as_view(), name="alternar"),
    path("organizaciones/<int:pk>/fusionar", views.OrganizacionFusionar.as_view(), name="fusionar"),
    path("organizaciones/<int:pk>/cerrar-autoridades", views.CerrarCargosAutoridad.as_view(), name="cerrar_autoridades"),
    path("organizaciones/<int:pk>/carreras/nuevo", views.CarreraNueva.as_view(), name="carreras_nuevo"),
    path("organizaciones/<int:pk>/carreras/<int:hijo_pk>/editar", views.CarreraEditar.as_view(), name="carreras_editar"),
    *urls_hijo("organizaciones", "personas", "PersonaCargo", modelo=pm.PersonaOrganizacion, form_class=pf.VinculoDesdeOrganizacionForm, tab="personas",
               etiqueta="persona con cargo", padre_modelo=models.Organizacion, campo_padre="organizacion"),
    *urls_hijo("organizaciones", "contactos", "Contacto", modelo=pm.Contacto, form_class=pf.ContactoForm, tab="contactos", etiqueta="contacto",
               padre_modelo=models.Organizacion, campo_padre="organizacion"),
]

from django.urls import path

from apps.nucleo.hijos import urls_hijo

from . import forms, models, views

app_name = "personas"
P = dict(padre_modelo=models.Persona, campo_padre="persona")
urlpatterns = [
    path("personas", views.PersonaLista.as_view(), name="lista"),
    path("personas/opciones", views.PersonaOpciones.as_view(), name="opciones"),
    path("personas/nueva", views.PersonaNueva.as_view(), name="nueva"),
    path("personas/<int:pk>", views.PersonaFicha.as_view(), name="ficha"),
    path("personas/<int:pk>/editar", views.PersonaEditar.as_view(), name="editar"),
    path("personas/<int:pk>/alternar", views.PersonaAlternar.as_view(), name="alternar"),
    path("personas/<int:pk>/direcciones/nuevo", views.DireccionPersonaNueva.as_view(), name="direcciones_nuevo"),
    *urls_hijo("personas", "contactos", "Contacto", modelo=models.Contacto, form_class=forms.ContactoForm, tab="contactos", etiqueta="contacto", **P),
    *urls_hijo("personas", "formacion", "Formacion", modelo=models.PersonaFormacion, form_class=forms.FormacionForm, tab="formacion", etiqueta="formación", **P),
    *urls_hijo("personas", "experiencia", "Experiencia", modelo=models.Experiencia, form_class=forms.ExperienciaForm, tab="experiencia", etiqueta="experiencia", **P),
    *urls_hijo("personas", "disponibilidad", "Disponibilidad", modelo=models.DisponibilidadPersona, form_class=forms.DisponibilidadForm, tab="disponibilidad", etiqueta="horario", **P),
    *urls_hijo("personas", "vinculos", "Vinculo", modelo=models.PersonaOrganizacion, form_class=forms.VinculoForm, tab="vinculos", etiqueta="vínculo", **P),
    *urls_hijo("personas", "emergencia", "Emergencia", modelo=models.ContactoEmergencia, form_class=forms.EmergenciaForm, tab="emergencia", etiqueta="contacto de emergencia", permiso_extra="personas.ver_sensibles", **P),
    *urls_hijo("personas", "verificaciones", "Verificacion", modelo=models.VerificacionPersona, form_class=forms.VerificacionForm, tab="verificaciones", etiqueta="verificación", permiso_extra="personas.ver_sensibles", **P),
]

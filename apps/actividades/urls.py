"""Direcciones (rutas) de actividades y calendario: qué vista atiende cada dirección.
Ejemplo: /actividades/7/participantes/nuevo la atiende la vista ParticipanteNuevo."""
from django.urls import path

from apps.nucleo.hijos import urls_hijo

from . import forms, models, views

app_name = "actividades"
A = dict(padre_modelo=models.Actividad, campo_padre="actividad")
urlpatterns = [
    path("actividades", views.ActividadLista.as_view(), name="lista"),
    path("actividades/exportar", views.ActividadExportar.as_view(), name="exportar"),
    path("actividades/opciones", views.ActividadOpciones.as_view(), name="opciones"),
    path("actividades/nueva", views.ActividadNueva.as_view(), name="nueva"),
    path("proyectos/<int:proyecto_pk>/tareas/nueva", views.TareaNueva.as_view(), name="tarea_nueva"),
    path("actividades/<int:pk>", views.ActividadFicha.as_view(), name="ficha"),
    path("actividades/<int:pk>/editar", views.ActividadEditar.as_view(), name="editar"),
    path("actividades/<int:pk>/programar", views.ProgramarVista.as_view(), name="programar"),
    path("actividades/<int:pk>/serie", views.SerieVista.as_view(), name="serie"),
    path("actividades/<int:pk>/confirmar", views.ConfirmarVista.as_view(), name="confirmar"),
    path("actividades/<int:pk>/estado", views.EstadoVista.as_view(), name="estado"),
    path("actividades/<int:pk>/resultados", views.ResultadosVista.as_view(), name="resultados"),
    path("actividades/<int:pk>/finalizar", views.FinalizarVista.as_view(), name="finalizar"),
    path("actividades/<int:pk>/reabrir", views.ReabrirVista.as_view(), name="reabrir"),
    path("actividades/<int:pk>/asistencia", views.AsistenciaVista.as_view(), name="asistencia"),
    path("actividades/<int:pk>/participantes/nuevo", views.ParticipanteNuevo.as_view(), name="participante_nuevo"),
    path("actividades/<int:pk>/participantes/rapido", views.ParticipanteRapido.as_view(), name="participante_rapido"),
    path("actividades/<int:pk>/participantes/usar/<int:persona_pk>", views.ParticipanteUsar.as_view(), name="participante_usar"),
    path("actividades/<int:pk>/participantes/<int:part_pk>/constancia", views.Constancia.as_view(), name="constancia"),
    path("actividades/<int:pk>/participantes/<int:part_pk>/quitar", views.ParticipanteQuitar.as_view(), name="participante_quitar"),
    path("actividades/<int:pk>/duplicar", views.ActividadDuplicar.as_view(), name="duplicar"),
    path("actividades/<int:pk>/participantes/<int:part_pk>/editar", views.ParticipacionEditar.as_view(), name="participante_editar"),
    path("actividades/<int:pk>/candidatos", views.Candidatos.as_view(), name="candidatos"),
    path("actividades/<int:pk>/sesiones/<int:sid>", views.SesionVista.as_view(), name="sesion"),
    path("actividades/<int:pk>/sesiones/<int:sid>/asistencia", views.SesionAsistenciaVista.as_view(), name="sesion_asistencia"),
    path("actividades/<int:pk>/organizaciones/usar/<int:org_pk>", views.OrganizacionUsar.as_view(), name="organizacion_usar"),
    path("calendario", views.Calendario.as_view(), name="calendario"),
    path("calendario/eventos", views.CalendarioEventos.as_view(), name="calendario_eventos"),
    *urls_hijo("actividades", "organizaciones", "Organizacion", modelo=models.ActividadOrganizacion, form_class=forms.ActividadOrganizacionForm, tab="organizaciones", etiqueta="organización", **A),
    *urls_hijo("actividades", "sesiones", "Sesion", modelo=models.SesionActividad, form_class=forms.SesionForm, tab="sesiones", etiqueta="sesión",
               antes_de_guardar=lambda vista, obj: setattr(obj, "redactada_por", vista.request.user), **A),
    *urls_hijo("actividades", "comunidades", "ActividadComunidad", modelo=models.ActividadComunidad, form_class=forms.ActividadComunidadForm, tab="publico",
               etiqueta="comunidad destinataria", **A),
    *urls_hijo("actividades", "territorios", "Territorio", modelo=models.ActividadTerritorio, form_class=forms.TerritorioForm, tab="info", etiqueta="territorio", **A),
]

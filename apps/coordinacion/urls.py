from django.urls import path

from apps.nucleo.hijos import urls_hijo

from . import forms, models, views

app_name = "coordinacion"
urlpatterns = [
    path("interacciones/nueva", views.InteraccionNueva.as_view(), name="interaccion_nueva"),
    path("interacciones/<int:pk>", views.InteraccionFicha.as_view(), name="interaccion_ficha"),
    path("interacciones/<int:pk>/editar", views.InteraccionEditar.as_view(), name="interaccion_editar"),
    path("interacciones/<int:pk>/cumplida", views.InteraccionCumplida.as_view(), name="interaccion_cumplida"),
    path("reuniones", views.ReunionLista.as_view(), name="reunion_lista"),
    path("reuniones/nueva", views.ReunionNueva.as_view(), name="reunion_nueva"),
    path("reuniones/<int:pk>", views.ReunionFicha.as_view(), name="reunion_ficha"),
    path("reuniones/<int:pk>/editar", views.ReunionEditar.as_view(), name="reunion_editar"),
    *urls_hijo("reuniones", "asistentes", "Asistente", modelo=models.ReunionAsistente, form_class=forms.AsistenteForm, tab="asistentes", etiqueta="asistente", padre_modelo=models.Reunion, campo_padre="reunion"),
    path("tareas", views.TareaLista.as_view(), name="tarea_lista"),
    path("tareas/exportar", views.TareaExportar.as_view(), name="tarea_exportar"),
    path("tareas/nueva", views.TareaNueva.as_view(), name="tarea_nueva"),
    path("tareas/<int:pk>", views.TareaFicha.as_view(), name="tarea_ficha"),
    path("tareas/<int:pk>/editar", views.TareaEditar.as_view(), name="tarea_editar"),
    path("tareas/<int:pk>/estado", views.TareaEstado.as_view(), name="tarea_estado"),
    *urls_hijo("tareas", "responsables", "Responsable", modelo=models.TareaResponsable, form_class=forms.ResponsableForm, tab="responsables", etiqueta="responsable", padre_modelo=models.Tarea, campo_padre="tarea"),
    path("invitaciones/nueva", views.InvitacionNueva.as_view(), name="invitacion_nueva"),
    path("invitaciones/<int:pk>", views.InvitacionFicha.as_view(), name="invitacion_ficha"),
    path("invitaciones/<int:pk>/editar", views.InvitacionEditar.as_view(), name="invitacion_editar"),
    path("colaboraciones/nueva", views.ColaboracionNueva.as_view(), name="colaboracion_nueva"),
    path("colaboraciones/<int:pk>", views.ColaboracionFicha.as_view(), name="colaboracion_ficha"),
    path("colaboraciones/<int:pk>/editar", views.ColaboracionEditar.as_view(), name="colaboracion_editar"),
]

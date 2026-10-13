from django.urls import path

from . import views

app_name = "documentos"
urlpatterns = [
    path("documentos", views.DocumentoLista.as_view(), name="lista"),
    path("documentos/nuevo", views.DocumentoNuevo.as_view(), name="nuevo"),
    path("documentos/asociar", views.DocumentoAsociar.as_view(), name="asociar"),
    path("documentos/<int:pk>/ver", views.DocumentoVer.as_view(), name="ver"),
    path("documentos/<int:pk>/transcribir", views.Transcribir.as_view(), name="transcribir"),
    path("documentos/<int:pk>", views.DocumentoFicha.as_view(), name="ficha"),
    path("documentos/<int:pk>/editar", views.DocumentoEditar.as_view(), name="editar"),
    path("documentos/<int:pk>/alternar", views.DocumentoAlternar.as_view(), name="alternar"),
    path("documentos/<int:pk>/reemplazar", views.DocumentoReemplazar.as_view(), name="reemplazar"),
    path("documentos/<int:pk>/archivo", views.DocumentoArchivo.as_view(), name="archivo"),
    path("origen/<slug:app>/<slug:modelo>/<int:pk>/nuevo", views.OrigenNuevo.as_view(), name="origen_nuevo"),
    path("origen/<int:pk>/verificar", views.OrigenVerificar.as_view(), name="origen_verificar"),
]

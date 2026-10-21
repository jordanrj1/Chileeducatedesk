"""Botón «Ya lo revisé» de los textos anteriores marcados «Por revisar» (la zona escrita de un proyecto, el rango de edad
escrito de una actividad o comunidad, la naturaleza jurídica escrita de una organización). Al confirmarlo se vacía el
texto antiguo; su valor queda en el historial del registro y en la auditoría, así que nada se pierde."""
from django.apps import apps
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View

from .auditoria import registrar

# clave: (app, modelo, campo con el texto anterior, permiso para editar, pestaña a la que se vuelve)
TEXTOS = {
    "proyecto-zona": ("proyectos", "Proyecto", "zona", "proyectos.change_proyecto", "resumen"),
    "actividad-rango": ("actividades", "Actividad", "rango_etario", "actividades.change_actividad", "publico"),
    "comunidad-rango": ("comunidades", "Comunidad", "rango_etario", "comunidades.change_comunidad", "info"),
    "organizacion-naturaleza": ("organizaciones", "Organizacion", "naturaleza_juridica", "organizaciones.change_organizacion", "info"),
}


class TextoAnteriorRevisado(View):
    def post(self, request, clave, pk):
        if clave not in TEXTOS:
            raise Http404
        app, modelo, campo, permiso, pestana = TEXTOS[clave]
        if not request.user.has_perm(permiso):
            raise PermissionDenied
        obj = get_object_or_404(apps.get_model(app, modelo), pk=pk)
        anterior = getattr(obj, campo)
        if anterior:
            setattr(obj, campo, "")
            obj.save()
            registrar(request.user, "texto_anterior_revisado", obj, f"{campo}: {anterior}")
            messages.success(request, f"Listo: se quitó el texto anterior «{anterior}». Queda guardado en el historial.")
        return HttpResponseRedirect(f"{obj.get_absolute_url()}?tab={pestana}")

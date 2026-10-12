from django.db import connection
from django.db.utils import Error as ErrorBD
from django.contrib.auth.decorators import login_not_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .permisos import ADMINISTRADOR, GESTOR, grupo_requerido


def inicio(request):
    return redirect("dashboard")


@grupo_requerido(GESTOR, ADMINISTRADOR)
def dashboard(request):
    return render(request, "nucleo/dashboard.html")


@grupo_requerido(GESTOR, ADMINISTRADOR)
def buscar(request):
    termino = request.GET.get("q", "").strip()
    # El buscador global se implementa en F15; por ahora no hay resultados.
    return render(request, "nucleo/buscar.html", {"termino": termino})


@grupo_requerido(ADMINISTRADOR)
def administracion(request):
    return render(request, "nucleo/administracion.html")


@login_not_required
def salud(request):
    """Confirma que la base responde. No expone datos."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except ErrorBD:
        return JsonResponse({"estado": "error"}, status=503)
    return JsonResponse({"estado": "ok"})


@login_not_required
def error_403(request, exception=None):
    return render(request, "errores/403.html", status=403)


@login_not_required
def error_404(request, exception=None):
    return render(request, "errores/404.html", status=404)

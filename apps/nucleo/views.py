from django.contrib.auth.decorators import login_not_required
from django.db import connection
from django.db.utils import Error as ErrorBD
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .permisos import ADMINISTRADOR, GESTOR, grupo_requerido


def inicio(request):
    return redirect("dashboard")


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


@login_not_required
def error_500(request):
    return render(request, "errores/500.html", status=500)

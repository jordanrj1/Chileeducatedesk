"""Pantallas de la cuenta propia: Mi cuenta (datos y último ingreso) y cambiar la contraseña."""
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import render
from django.urls import reverse_lazy


def mi_cuenta(request):
    return render(request, "cuentas/mi_cuenta.html", {"titulo": "Mi cuenta", "grupos": request.user.groups.values_list("name", flat=True)})


class CambiarClave(PasswordChangeView):
    template_name = "generico/formulario.html"
    success_url = reverse_lazy("cuentas:mi_cuenta")
    extra_context = {"titulo": "Cambiar contraseña", "volver_url": "/mi-cuenta", "breadcrumb": [("Mi cuenta", "/mi-cuenta")]}

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for c in form.fields.values():
            c.widget.attrs["class"] = "form-control"
        return form

    def form_valid(self, form):
        from django.contrib import messages

        messages.success(self.request, "Contraseña actualizada.")
        return super().form_valid(form)

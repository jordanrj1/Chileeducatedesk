from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views import View

from .formularios import BootstrapMixin
from .fusion import fusionar, vista_previa


class FusionForm(BootstrapMixin, forms.Form):
    destino = forms.ModelChoiceField(queryset=None, label="Ficha que se conserva")
    motivo = forms.CharField(max_length=250, label="Motivo")
    confirmo = forms.BooleanField(label="Entiendo que todo pasa a la ficha que se conserva y esta queda desactivada.")

    def __init__(self, *a, campo_destino=None, **kw):
        super().__init__(*a, **kw)
        if campo_destino is not None:
            self.fields["destino"] = campo_destino
            self.fields["destino"].widget.attrs["class"] = "form-select"
            from .formularios import fijar_valores_selectores

            fijar_valores_selectores(self)


class FusionarBase(View):
    """Fusión controlada (solo con el permiso de fusionar, que tiene el Administrador)."""

    modelo = None
    permiso = None
    titulo = "Fusionar fichas duplicadas"

    def campo_destino(self, origen):
        raise NotImplementedError

    def get_origen(self, **kw):
        return get_object_or_404(self.modelo, pk=kw["pk"])

    def permiso_requerido(self, origen):
        return self.permiso

    def dispatch(self, request, *a, **kw):
        self.origen = self.get_origen(**kw)
        if not request.user.has_perm(self.permiso_requerido(self.origen)):
            raise PermissionDenied
        return super().dispatch(request, *a, **kw)

    def volver(self):
        return self.origen.get_absolute_url()

    def _ctx(self, form):
        return {"form": form, "origen": self.origen, "previa": vista_previa(self.origen), "titulo": self.titulo, "volver_url": self.volver(), "breadcrumb": []}

    def get(self, request, **kw):
        return render(request, "generico/fusionar.html", self._ctx(FusionForm(campo_destino=self.campo_destino(self.origen))))

    def post(self, request, **kw):
        form = FusionForm(request.POST, campo_destino=self.campo_destino(self.origen))
        if not form.is_valid():
            return render(request, "generico/fusionar.html", self._ctx(form), status=400)
        destino = form.cleaned_data["destino"]
        try:
            movidos, conservados = fusionar(self.origen, destino, request.user, form.cleaned_data["motivo"])
        except ValueError as e:
            form.add_error(None, str(e))
            return render(request, "generico/fusionar.html", self._ctx(form), status=400)
        messages.success(request, f"Fichas fusionadas: {movidos} registros pasaron a «{destino}».")
        if conservados:
            messages.warning(request, f"{len(conservados)} registro(s) quedaron en la ficha desactivada porque ya existían en la que se conserva: " + "; ".join(conservados[:5]))
        return HttpResponseRedirect(self.destino_url(destino))

    def destino_url(self, destino):
        return destino.get_absolute_url()

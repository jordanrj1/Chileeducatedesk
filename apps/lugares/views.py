from datetime import date

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView

from apps.nucleo.direccion_mixin import ConDireccionMixin
from apps.nucleo.models import TipoLugar
from apps.nucleo.vistas_base import ControlVersionMixin, AlternarActivoBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, filtro_activo, opciones_modelo
from apps.territorio.models import Comuna

from .forms import LugarForm
from .models import Lugar


class LugarLista(ListaBase):
    model = Lugar
    permission_required = "lugares.view_lugar"
    titulo = "Lugares"
    url_crear = "/lugares/nuevo"
    permiso_crear = "lugares.add_lugar"
    etiqueta_crear = "+ Nuevo lugar"
    campos_busqueda = ("nombre", "direccion__calle", "condiciones")
    columnas = [("Nombre", "nombre"), ("Tipo", "tipo"), ("Comuna", "direccion.comuna"), ("Sector", lambda l: l.direccion.sector or ""), ("Capacidad", lambda l: l.capacidad or "—")]
    ordenes = {"nombre": "nombre", "capacidad": "capacidad"}
    orden_defecto = ("nombre",)
    filtros = [
        filtro_activo(),
        Filtro("tipo", "Tipo", "tipo_id", opciones_modelo(TipoLugar)),
        Filtro("comuna", "Comuna", "direccion__comuna_id", opciones_modelo(Comuna)),
        Filtro("capacidad_min", "Capacidad mínima", "capacidad__gte", convertir=int, entrada="number"),
    ]
    url_exportar = "/lugares/exportar"
    permiso_exportar = "lugares.exportar_lugar"

    def get_queryset(self):
        return super().get_queryset().select_related("tipo", "direccion__comuna", "direccion__sector")


class LugarExportar(LugarLista):
    exportar = True
    permission_required = "lugares.exportar_lugar"


class _Formulario(ConDireccionMixin, Permiso403Mixin):
    form_class = LugarForm
    model = Lugar
    template_name = "lugares/formulario.html"
    direccion_requerida = True

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo=self.titulo, volver_url=self.volver(), breadcrumb=[("Lugares", "/lugares")])
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        nuevo = not obj.pk
        if nuevo:
            obj.creado_por = self.request.user
        obj.save()
        if nuevo:
            from apps.documentos.origen import registrar_origen

            registrar_origen(obj, self.request.user)
        messages.success(self.request, "Lugar guardado.")
        return HttpResponseRedirect(obj.get_absolute_url())


class LugarNuevo(_Formulario, CreateView):
    permission_required = "lugares.add_lugar"
    titulo = "Nuevo lugar"

    def volver(self):
        return "/lugares"


class LugarEditar(ControlVersionMixin, _Formulario, UpdateView):
    permission_required = "lugares.change_lugar"
    titulo = "Editar lugar"

    def volver(self):
        return self.object.get_absolute_url()


class LugarCrearRapido(Permiso403Mixin, __import__("django.views", fromlist=["View"]).View):
    """«+ Crear lugar» desde la agenda, sin salir de la actividad. Si ya existe con ese nombre en la comuna, se usa ese."""

    permission_required = "lugares.add_lugar"

    def post(self, request):
        from django.db import transaction
        from django.http import HttpResponse
        from django.utils.html import format_html, format_html_join

        from apps.territorio.models import Direccion

        p = request.POST
        nombre = p.get("nuevo_lugar_nombre", "").strip()
        comuna = Comuna.objects.filter(pk=p.get("nuevo_lugar_comuna") or 0).first()
        tipo = TipoLugar.objects.filter(pk=p.get("nuevo_lugar_tipo") or 0, activo=True).first()
        cap = p.get("nuevo_lugar_capacidad", "").strip()
        seleccionado, nivel = None, "danger"
        if not (nombre and comuna and tipo):
            mensaje = "Para crear el lugar indica nombre, tipo y comuna."
        elif cap and (not cap.isdigit() or int(cap) < 1):
            mensaje = "La capacidad debe ser un número entero positivo."
        else:
            existente = Lugar.objects.filter(nombre__iexact=nombre, direccion__comuna=comuna).first()
            if existente:
                seleccionado, nivel, mensaje = existente.pk, "info", f"Ya existía «{existente}» en {comuna}: quedó seleccionado."
            else:
                with transaction.atomic():
                    d = Direccion.objects.create(comuna=comuna, calle=p.get("nuevo_lugar_calle", "").strip(), numero=p.get("nuevo_lugar_numero", "").strip())
                    l = Lugar.objects.create(nombre=nombre, tipo=tipo, direccion=d, capacidad=int(cap) if cap else None, creado_por=request.user)
                    from apps.documentos.origen import registrar_origen

                    registrar_origen(l, request.user)
                seleccionado, nivel, mensaje = l.pk, "success", f"Lugar «{l}» creado y seleccionado. Completa sus condiciones en su ficha cuando puedas."
        filas = [("", "", "---------")] + [(l.pk, "selected" if l.pk == seleccionado else "", f"{l} ({l.direccion.comuna}" + (f", cap. {l.capacidad})" if l.capacidad else ")")) for l in Lugar.objects.filter(activo=True).select_related("direccion__comuna")]
        html = format_html_join("", '<option value="{}" {}>{}</option>', filas)
        return HttpResponse(html + format_html('<div id="aviso-lugar" hx-swap-oob="true" class="small text-{}">{}</div>', nivel, mensaje))


class LugarAlternar(AlternarActivoBase):
    modelo = Lugar
    permission_required = "lugares.change_lugar"


class LugarFicha(FichaBase):
    model = Lugar
    permission_required = "lugares.view_lugar"
    breadcrumb = [("Lugares", "/lugares")]
    permiso_editar = "lugares.change_lugar"
    pestanas = [
        ("info", "Información", "lugares/pestanas/info.html"),
        ("uso", "Uso histórico", "lugares/pestanas/uso.html"),
        ("disponibilidad", "Disponibilidad", "lugares/pestanas/disponibilidad.html"),
        ("origen", "Origen", "documentos/pestanas/origen.html", "documentos.view_origendato"),
        ("historial", "Historial", "generico/_historial.html", "lugares.view_historicallugar"),
    ]

    def contexto_ficha(self):
        return {
            "url_editar": reverse("lugares:editar", args=[self.object.pk]),
            "url_volver": "/lugares",
            "puede_agregar": self.request.user.has_perm("lugares.change_lugar"),
        }

    def ctx_uso(self):
        return {"usos": self.object.agendas.select_related("actividad", "estado").order_by("-fecha", "-hora_inicio")[:100]}

    def ctx_origen(self):
        from apps.documentos.origen import contexto_origen

        return contexto_origen(self.object, self.request.user)

    def ctx_disponibilidad(self):
        texto = self.request.GET.get("fecha", "")
        try:
            fecha = date.fromisoformat(texto) if texto else date.today()
        except ValueError:
            fecha = date.today()
        ocupaciones = (
            self.object.agendas.filter(vigente=True, fecha=fecha).exclude(actividad__estado__codigo__in=["cancelada", "suspendida"])
            .select_related("actividad").order_by("hora_inicio")
        )
        return {"fecha": fecha, "ocupaciones": ocupaciones}

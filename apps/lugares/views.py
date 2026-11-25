"""Pantallas de lugares: listado, crear y editar con dirección en cascada, crear rápido desde la agenda
sin salir de la actividad, desactivar sin borrar y ficha con uso histórico y disponibilidad."""
from datetime import date

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView

from apps.nucleo.direccion_mixin import ComunaInicialMixin, ConDireccionMixin
from apps.nucleo.models import TipoLugar
from apps.nucleo.selector import OpcionesVista, campo_seguro, respuesta_elegido
from apps.nucleo.vistas_base import (
    AvisoDuplicadosMixin, ControlVersionMixin, AlternarActivoBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, filtro_activo, nombre_comuna, opciones_comunas, opciones_modelo,
)
from apps.territorio.models import Comuna

from .forms import LugarForm
from .models import Lugar
from .selector import LUGARES


class LugarLista(ListaBase):
    model = Lugar
    permission_required = "lugares.view_lugar"
    titulo = "Lugares"
    descripcion = "Espacios donde se realizan las actividades, con su capacidad y ubicación."
    url_crear = "/lugares/nuevo"
    permiso_crear = "lugares.add_lugar"
    etiqueta_crear = "+ Nuevo lugar"
    campos_busqueda = ("nombre", "direccion__calle", "condiciones")
    columnas = [("Nombre", "nombre"), ("Tipo", "tipo"), ("Comuna", "direccion.comuna"), ("Sector", lambda l: l.direccion.sector or ""), ("Capacidad", lambda l: l.capacidad or "—")]
    ordenes = {"nombre": "nombre", "capacidad": "capacidad"}
    orden_defecto = ("nombre",)
    filtros = [
        Filtro("tipo", "Tipo", "tipo_id", opciones_modelo(TipoLugar), principal=True),
        Filtro("comuna", "Comuna", "direccion__comuna_id", lambda: opciones_comunas(Q(pk__in=Lugar.objects.values("direccion__comuna_id"))),
               principal=True, todos="Todas", etiqueta_de=nombre_comuna),
        Filtro("capacidad_min", "Capacidad mínima", "capacidad__gte", convertir=int, entrada="number", principal=True),
        filtro_activo(),
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
    direccion_contexto = "lugar"  # al elegir la comuna se ve lo que ya hay en ella, para no duplicar

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
        else:
            from apps.actividades.afectacion import excedidas_por_capacidad

            excedidas = excedidas_por_capacidad(obj)
            if excedidas:
                messages.warning(self.request, f"Con la capacidad actual ({obj.capacidad}) quedan excedidas: " + "; ".join(t for t, _ in excedidas) + ". Revísalas antes de confirmarlas.")
        messages.success(self.request, "Lugar guardado.")
        return HttpResponseRedirect(obj.get_absolute_url())


class LugarNuevo(AvisoDuplicadosMixin, ComunaInicialMixin, _Formulario, CreateView):
    permission_required = "lugares.add_lugar"
    titulo = "Nuevo lugar"

    def volver(self):
        return "/lugares"

    def form_valid(self, form):
        from django.db import transaction

        from apps.nucleo.duplicados import lugares_parecidos

        direccion = form.instance.direccion  # ConDireccionMixin ya la guardó, dentro de su transacción
        aviso = self.aviso_duplicados(form, lambda: lugares_parecidos(form.cleaned_data.get("nombre"), direccion.comuna), "Este lugar podría ya estar registrado.")
        if aviso:
            transaction.set_rollback(True)  # sin lugar no queda una dirección suelta (la página se dibuja después)
            return aviso
        return super().form_valid(form)


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


class LugarOpciones(OpcionesVista):
    """F27: lista de lugares para los buscadores de los formularios (ver apps/lugares/selector.py)."""

    fuente = LUGARES


class LugarCrearDesdeBuscador(Permiso403Mixin, __import__("django.views", fromlist=["View"]).View):
    """F27: ventana «+ Crear lugar» de los buscadores (p. ej. «Vincular a un lugar»): nombre, tipo y comuna. Si ya hay un
    lugar con ese nombre en la comuna, se ofrece «Usar este lugar» o «Es otro: crear»; el lugar queda elegido en el
    formulario de origen, sin salir de él."""

    permission_required = "lugares.add_lugar"
    plantilla = "generico/_crear_rapida.html"

    def _ctx(self, datos, form, **extra):
        return {
            "form": form, "campo_id": campo_seguro(datos.get("campo")), "filtros": LUGARES.limpiar_filtros(datos),
            "accion": reverse("lugares:crear_desde_buscador"), "titulo": "Crear lugar", "aviso_parecido": "Este lugar podría ya existir.",
            "texto_usar": "Usar este lugar", "texto_crear_igual": "Es otro: crear", "pide_nota": False, **extra,
        }

    def get(self, request):
        from django.shortcuts import render

        from .forms import LugarRapidoForm

        return render(request, self.plantilla, self._ctx(request.GET, LugarRapidoForm(prefix="rapida", initial={"nombre": request.GET.get("q", "")[:200]})))

    def post(self, request):
        from django.db import transaction
        from django.shortcuts import render

        from apps.documentos.origen import registrar_origen
        from apps.territorio.models import Direccion

        from .forms import LugarRapidoForm

        form = LugarRapidoForm(request.POST, prefix="rapida")
        if not form.is_valid():
            return render(request, self.plantilla, self._ctx(request.POST, form))
        d = form.cleaned_data
        if not request.POST.get("confirmar_duplicado"):
            parecidos = list(Lugar.objects.filter(nombre__unaccent__iexact=d["nombre"], direccion__comuna=d["comuna"]))
            if parecidos:
                elegibles = set(LUGARES.base(**LUGARES.limpiar_filtros(request.POST)).filter(pk__in=[l.pk for l in parecidos]).values_list("pk", flat=True))
                lista = [(l, [f"mismo nombre en {d['comuna']}"], l.pk in elegibles) for l in parecidos]
                return render(request, self.plantilla, self._ctx(request.POST, form, candidatos=lista))
        with transaction.atomic():
            direccion = Direccion.objects.create(comuna=d["comuna"])
            lugar = Lugar.objects.create(nombre=d["nombre"], tipo=d["tipo"], direccion=direccion, capacidad=d.get("capacidad"), creado_por=request.user)
            registrar_origen(lugar, request.user)
        return respuesta_elegido(request.POST.get("campo"), lugar.pk, LUGARES.texto(lugar), "Lugar creado y elegido. Completa su dirección y condiciones en su ficha cuando puedas.")


class LugarAlternar(AlternarActivoBase):
    modelo = Lugar
    permission_required = "lugares.change_lugar"

    def afectados(self, obj):
        from apps.actividades.afectacion import de_lugar

        return de_lugar(obj)


class LugarFicha(FichaBase):
    model = Lugar
    template_name = "lugares/ficha.html"
    permission_required = "lugares.view_lugar"
    breadcrumb = [("Lugares", "/lugares")]
    permiso_editar = "lugares.change_lugar"
    origen_en_historial = True  # F26 Ia: «?tab=origen» de enlaces antiguos abre el historial
    alias_pestanas = {"origen": "historial"}
    pestanas = [
        ("info", "Información", "lugares/pestanas/info.html"),
        ("personas", "Personas", "lugares/pestanas/personas.html", "personas.view_persona"),
        ("uso", "Uso histórico", "lugares/pestanas/uso.html"),
        ("disponibilidad", "Disponibilidad", "lugares/pestanas/disponibilidad.html"),
        ("historial", "Historial", "generico/_historial.html", "lugares.view_historicallugar"),
    ]

    def get_queryset(self):
        return super().get_queryset().select_related("direccion__comuna")

    def contexto_ficha(self):
        return {
            "url_editar": reverse("lugares:editar", args=[self.object.pk]),
            "url_volver": "/lugares",
            "puede_agregar": self.request.user.has_perm("lugares.change_lugar"),
            "comuna_ficha": self.object.direccion.comuna,
        }

    def ctx_info(self):
        """F26 Ia: los datos vacíos se cuentan aparte («Sin completar (N)»), como en la persona."""
        lg = self.object
        campos = [("Capacidad", lg.capacidad), ("Propietaria", lg.organizacion_propietaria_id), ("Condiciones", lg.condiciones)]
        return {"datos_vacios": [e for e, v in campos if not v], "vistazo": self.vistazo()}

    def vistazo(self):
        """F26 Ib: cuántas veces se ha usado (programaciones vigentes) y la última y la próxima actividad aquí. Tres consultas."""
        from django.db.models import Q

        from apps.nucleo.vistazo import cuantas, fila, filas_ultima_y_proxima

        n = self.object.agendas.filter(vigente=True).count()
        filas = [fila("Veces usado", [], cifra=cuantas(n, "actividad programada aquí", "actividades programadas aquí"),
                      pie=("Ver uso histórico", "?tab=uso") if n else None)]
        return filas + filas_ultima_y_proxima(Q(lugar=self.object), con_lugar=False)

    def ctx_personas(self):
        """Personas vinculadas a este lugar (estudian, trabajan o participan ahí) y estudiantes de esta sede."""
        vinculadas = self.object.personas_vinculadas.select_related("persona", "tipo_relacion").order_by("-vigente", "persona__apellido_paterno")
        estudiantes = self.object.estudiantes.select_related("persona", "carrera", "organizacion").order_by("carrera__nombre", "persona__apellido_paterno")
        return {"vinculadas": vinculadas, "estudiantes_sede": estudiantes}

    def ctx_uso(self):
        return {"usos": self.object.agendas.select_related("actividad", "estado").order_by("-fecha", "-hora_inicio")[:100]}


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

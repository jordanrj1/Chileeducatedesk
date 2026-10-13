from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render  # noqa: F401
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView

from django.db.models import Q

from apps.nucleo.models import EstadoRegistro, OrigenPersona, RolParticipacion
from apps.organizaciones.models import Organizacion
from apps.territorio.models import Comuna
from apps.nucleo.vistas_base import (
    AlternarActivoBase, EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, filtro_activo, opciones_modelo,
)

from .duplicados import candidatos
from .forms import PerfilSensibleForm, PersonaDireccionForm, PersonaForm, PersonaNuevaForm, PersonaRapidaForm
from .models import Consentimiento, Contacto, PerfilSensible, Persona, PersonaDireccion


def _principal(persona, codigos):
    for c in persona.contactos.all():
        if c.vigente and c.tipo.codigo in codigos:
            return c.valor
    return ""


class PersonaLista(ListaBase):
    model = Persona
    permission_required = "personas.view_persona"
    titulo = "Personas"
    descripcion = "Voluntarios, profesionales, beneficiarios y contactos registrados."
    url_crear = "/personas/nueva"
    permiso_crear = "personas.add_persona"
    etiqueta_crear = "+ Nueva persona"
    campos_busqueda = ()
    columnas = [
        ("Nombre", lambda p: p.nombre_completo),
        ("RUT 🔒", "rut"),
        ("Correo", lambda p: _principal(p, ["correo"])),
        ("Teléfono", lambda p: _principal(p, ["telefono_movil", "telefono_fijo"])),
        ("Registro", "estado_registro"),
        ("Origen", "origen"),
    ]
    ordenes = {"nombre": "apellido_paterno", "creado": "creado_en"}
    orden_defecto = ("apellido_paterno", "apellido_materno", "nombres")
    filtros = [
        filtro_activo(),
        Filtro("registro", "Registro", "estado_registro__codigo", lambda: [(e.codigo, e.nombre) for e in EstadoRegistro.objects.all()]),
        Filtro("origen", "Origen", "origen_id", opciones_modelo(OrigenPersona)),
        Filtro("rol", "Tipo de relación", "", opciones_modelo(RolParticipacion), aplicar=lambda qs, v: qs.filter(participaciones__rol_id=v).distinct()),
        Filtro("organizacion", "Organización", "", lambda: [(str(o.pk), o.nombre) for o in Organizacion.objects.filter(activo=True)[:300]],
               aplicar=lambda qs, v: qs.filter(Q(vinculos__organizacion_id=v) | Q(formaciones__organizacion_id=v)).distinct()),
        Filtro("comuna", "Comuna", "", opciones_modelo(Comuna), aplicar=lambda qs, v: qs.filter(direcciones__vigente=True, direcciones__direccion__comuna_id=v).distinct()),
    ]
    texto_vacio = "Aún no hay personas registradas."
    url_exportar = "/personas/exportar"
    permiso_exportar = "personas.exportar_persona"

    def filtrar(self, qs):
        return super().filtrar(qs).buscar(self.request.GET.get("q"))

    def get_queryset(self):
        return super().get_queryset().select_related("estado_registro", "origen").prefetch_related("contactos__tipo")


class PersonaExportar(PersonaLista):
    exportar = True
    permission_required = "personas.exportar_persona"


class PersonaNueva(Permiso403Mixin, CreateView):
    """Ficha rápida (nombre y un contacto) o completa. Siempre busca coincidencias antes de crear (PE-04)."""

    model = Persona
    permission_required = "personas.add_persona"
    template_name = "personas/nueva.html"

    def modo(self):
        if self.request.method == "POST":
            m = self.request.POST.get("modo", "completa")  # sin «modo» (p. ej. integraciones) se aceptan todos los campos
        else:
            m = self.request.GET.get("modo", "rapida")
        return "completa" if m == "completa" else "rapida"

    def get_form_class(self):
        return PersonaNuevaForm if self.modo() == "completa" else PersonaRapidaForm

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nueva persona", volver_url="/personas", breadcrumb=[("Personas", "/personas")], modo=self.modo())
        return ctx

    def form_valid(self, form):
        d = form.cleaned_data
        rut = d.get("rut")
        cands = None
        if not self.request.POST.get("confirmar_duplicado") or not self.request.POST.get("nota_distincion", "").strip():
            cands = candidatos(
                d["nombres"], d.get("apellido_paterno", ""), d.get("apellido_materno", ""), rut[0] if rut else None, d.get("correo", ""), d.get("telefono", ""),
                documento=(d.get("tipo_documento"), d.get("numero_documento")),
            )
            if cands:
                falta_nota = bool(self.request.POST.get("confirmar_duplicado"))
                return self.render_to_response(self.get_context_data(form=form, candidatos=cands, falta_nota=falta_nota))
        with transaction.atomic():
            persona = form.save(commit=False)
            persona.creado_por = self.request.user
            nota = self.request.POST.get("nota_distincion", "").strip()
            if nota:  # PE-E2: qué la distingue de la otra persona con el mismo nombre
                persona.observaciones = (f"Se distingue de otra ficha parecida: {nota}\n" + persona.observaciones).strip()
            tiene_contacto = bool(d.get("correo") or d.get("telefono"))
            if not persona.estado_registro_id:
                codigo = "activo" if (persona.apellido_paterno and tiene_contacto) else "incompleto"
                persona.estado_registro = EstadoRegistro.objects.filter(codigo=codigo).first()
            persona.save()
            form.save_m2m()  # perfiles y áreas de interés (F22)
            from apps.nucleo.models import TipoContacto

            if d.get("correo"):
                Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="correo"), valor=d["correo"], principal=True)
            if d.get("telefono"):
                Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="telefono_movil"), valor=d["telefono"], principal=not d.get("correo"))
            from apps.documentos.origen import registrar_origen

            registrar_origen(persona, self.request.user)
        if self.request.POST.get("despues"):
            if persona.estado_registro and persona.estado_registro.codigo != "incompleto":
                persona.estado_registro = EstadoRegistro.objects.filter(codigo="incompleto").first()
                persona.save(update_fields=["estado_registro"])
            messages.success(self.request, f"{persona} registrada. Quedó en la lista de registros por completar.")
            return HttpResponseRedirect("/personas/nueva")
        messages.success(self.request, "Persona registrada. Puedes completar el resto de su ficha cuando quieras.")
        return HttpResponseRedirect(persona.get_absolute_url())


class PersonaEditar(EditarBase):
    model = Persona
    form_class = PersonaForm
    permission_required = "personas.change_persona"
    titulo = "Editar persona"
    breadcrumb = [("Personas", "/personas")]


def _hijos(objs, texto, detalle=None, url_base=None, slug=None, pk=None, vigente="vigente"):
    res = []
    for o in objs:
        h = {"texto": texto(o), "detalle": detalle(o) if detalle else "", "vigente": getattr(o, vigente, True) if vigente else True}
        if slug:
            h["url_editar"] = reverse(f"personas:{slug}_editar", args=[pk, o.pk])
            if vigente:
                h["url_alternar"] = reverse(f"personas:{slug}_alternar", args=[pk, o.pk])
        res.append(h)
    return res


class PersonaFicha(FichaBase):
    model = Persona
    template_name = "personas/ficha.html"
    permission_required = "personas.view_persona"
    pestanas_segunda_fase = {"verificaciones": "verificaciones"}
    breadcrumb = [("Personas", "/personas")]
    permiso_editar = "personas.change_persona"
    pestanas = [
        ("datos", "Datos", "personas/pestanas/datos.html"),
        ("contactos", "Contactos", "generico/_hijos.html"),
        ("direcciones", "Direcciones 🔒", "generico/_hijos.html"),
        ("formacion", "Formación", "generico/_hijos.html"),
        ("experiencia", "Experiencia", "generico/_hijos.html"),
        ("disponibilidad", "Disponibilidad", "generico/_hijos.html"),
        ("vinculos", "Organizaciones y cargos", "generico/_hijos.html"),
        ("trayectoria", "Participaciones", "personas/pestanas/trayectoria.html", "actividades.view_participacion"),
        ("documentos", "Documentos", "documentos/pestanas/lista.html", "documentos.view_documento"),
        ("interacciones", "Interacciones", "coordinacion/_interacciones.html", "coordinacion.view_interaccion"),
        ("emergencia", "Contacto de emergencia 🔒", "generico/_hijos.html", "personas.ver_sensibles"),
        ("verificaciones", "Verificaciones 🔒", "generico/_hijos.html", "personas.ver_sensibles"),
        ("sensibles", "Datos sensibles 🔒", "personas/pestanas/sensibles.html", "personas.ver_sensibles"),
        ("apoderados", "Apoderados 🔒", "generico/_hijos.html", "personas.ver_sensibles"),
        ("consentimientos", "Consentimientos", "personas/pestanas/consentimientos.html", "personas.view_consentimiento"),
        ("comunidades", "Comunidades", "generico/_hijos.html", "comunidades.view_comunidadmiembro"),
        ("origen", "Origen", "documentos/pestanas/origen.html", "documentos.view_origendato"),
        ("historial", "Historial", "generico/_historial.html", "personas.view_historicalpersona"),
    ]

    def pestanas_visibles(self):
        from django.conf import settings

        visibles = super().pestanas_visibles()
        if not getattr(settings, "DATOS_SENSIBLES", True):
            visibles = [p for p in visibles if p[0] != "sensibles"]
        return visibles

    def acciones_extra(self):
        res = []
        if self.request.user.has_perm("coordinacion.add_interaccion"):
            res.append(("Registrar interacción", f"/interacciones/nueva?persona={self.object.pk}"))
        if self.request.user.has_perm("actividades.change_actividad"):
            from apps.actividades.afectacion import a_cargo_de

            if a_cargo_de(self.object).exists():
                res.append(("Reasignar sus actividades", f"/personas/{self.object.pk}/reasignar"))
        if self.request.user.has_perm("personas.fusionar_persona") and self.object.activo:
            res.append(("Fusionar con otra ficha", f"/personas/{self.object.pk}/fusionar"))
        return res

    def contexto_ficha(self):
        p = self.object
        return {
            "url_editar": reverse("personas:editar", args=[p.pk]),
            "url_volver": "/personas",
            "correo_principal": _principal(p, ["correo"]),
            "telefono_principal": _principal(p, ["telefono_movil", "telefono_fijo"]),
            "avisos_consentimiento": p.avisos_consentimiento() if self.request.user.has_perm("personas.view_consentimiento") else [],
            "puede_agregar": self.request.user.has_perm("personas.change_persona"),
        }

    def encabezado(self):
        return self.object.nombre_completo

    def _hijo_ctx(self, titulo, slug, etiqueta, objs, **kw):
        return {
            "titulo_pestana": titulo, "etiqueta_nuevo": etiqueta, "url_nuevo": reverse(f"personas:{slug}_nuevo", args=[self.object.pk]),
            "hijos": _hijos(objs, pk=self.object.pk, slug=slug, **kw), "vacio": f"Sin {titulo.lower()} registrados.",
        }

    def ctx_trayectoria(self):
        from apps.actividades.alcance import horas_persona

        p = self.object
        return {
            "horas_acumuladas": horas_persona(p),
            "participaciones": p.participaciones.select_related("actividad__estado", "actividad__proyecto", "rol", "estado").order_by("-actividad__creado_en"),
            "reuniones": p.reuniones.select_related("reunion").order_by("-reunion__fecha"),
            "tareas": p.tareas_asignadas.select_related("tarea").order_by("-tarea__creado_en"),
            "proyectos": p.proyectos.select_related("proyecto"),
            "vinculos": p.vinculos.select_related("organizacion"),
            "invitaciones": p.invitaciones.select_related("actividad"),
        }

    def ctx_interacciones(self):
        return {"interacciones": self.object.interacciones.select_related("canal", "actividad", "solicitud").order_by("-fecha"), "url_nueva_interaccion": f"/interacciones/nueva?persona={self.object.pk}"}

    def ctx_documentos(self):
        docs = self.object.documentos.select_related("tipo")
        if not self.request.user.has_perm("documentos.ver_restringido"):
            docs = docs.filter(restringido=False)
        return {"documentos": docs, "url_nuevo_doc": f"/documentos/nuevo?persona={self.object.pk}", "url_asociar_doc": f"/documentos/asociar?persona={self.object.pk}"}

    def ctx_origen(self):
        from apps.documentos.origen import contexto_origen

        return contexto_origen(self.object, self.request.user)

    def ctx_contactos(self):
        return self._hijo_ctx("Contactos", "contactos", "Contacto", self.object.contactos.select_related("tipo"),
                              texto=lambda c: f"{c.tipo}: {c.valor}", detalle=lambda c: " · ".join(x for x in [c.proposito, "Principal" if c.principal else ""] if x))

    def ctx_direcciones(self):
        ctx = self._hijo_ctx("Direcciones", "direcciones", "Dirección", self.object.direcciones.select_related("direccion__comuna", "direccion__sector"),
                             texto=lambda d: str(d.direccion), detalle=lambda d: d.get_tipo_display())
        for h in ctx["hijos"]:
            h.pop("url_editar", None)  # una dirección se reemplaza agregando otra y marcando la anterior como no vigente
        return ctx

    def ctx_formacion(self):
        def detalle(f):
            partes = [f.get_estado_display(), f.sede, f.get_jornada_display() if f.jornada else "", f"{f.nivel_actual}.º año" if f.nivel_actual else "",
                      f.asignatura, f"docente: {f.docente}" if f.docente_id else "", f"{f.horas_comprometidas} h comprometidas" if f.horas_comprometidas else ""]
            return " · ".join(x for x in partes if x)

        return self._hijo_ctx("Formación", "formacion", "Formación", self.object.formaciones.select_related("organizacion", "carrera", "docente"),
                              texto=lambda f: str(f), detalle=detalle)

    def ctx_experiencia(self):
        return self._hijo_ctx("Experiencia", "experiencia", "Experiencia", self.object.experiencias.all(),
                              texto=lambda e: e.descripcion, detalle=lambda e: e.lugar)

    def ctx_disponibilidad(self):
        return self._hijo_ctx("Disponibilidad", "disponibilidad", "Horario", self.object.disponibilidades.all(),
                              texto=lambda d: str(d), detalle=lambda d: d.comentario)

    def ctx_vinculos(self):
        return self._hijo_ctx("Organizaciones y cargos", "vinculos", "Vínculo", self.object.vinculos.select_related("organizacion"),
                              texto=lambda v: f"{v.cargo or 'Vínculo'} · {v.organizacion}", detalle=lambda v: f"{v.get_tipo_cargo_display()} · {v.fecha_inicio or '?'} a {v.fecha_termino or 'actualidad'}", vigente=None)

    def ctx_emergencia(self):
        return self._hijo_ctx("Contacto de emergencia", "emergencia", "Contacto", self.object.contactos_emergencia.all(),
                              texto=lambda c: c.nombre, detalle=lambda c: f"{c.parentesco} · {c.telefono}")

    def ctx_sensibles(self):
        from django.conf import settings

        perfil = getattr(self.object, "perfil_sensible", None)
        return {"perfil": perfil, "consentimiento_sensibles": self.object.consentimiento_vigente("sensibles"),
                "puede_editar_sensibles": self.request.user.has_perm("personas.change_persona") and getattr(settings, "DATOS_SENSIBLES", True)}

    def ctx_apoderados(self):
        return self._hijo_ctx("Apoderados", "apoderados", "Apoderado", self.object.apoderados.select_related("apoderado"),
                              texto=lambda a: str(a.apoderado), detalle=lambda a: " · ".join(x for x in [a.parentesco, "Tutor legal" if a.tutor_legal else ""] if x))

    def ctx_consentimientos(self):
        p = self.object
        estado = []
        for codigo, nombre in Consentimiento.TIPOS:
            if codigo == "apoderado" and not p.es_menor:
                continue
            ultimo = p.consentimientos.filter(tipo=codigo).order_by("-fecha", "-pk").first()
            estado.append({"nombre": nombre, "ultimo": ultimo, "vigente": bool(ultimo and ultimo.vigente)})
        return {
            "estado_consentimientos": estado,
            "consentimientos": p.consentimientos.select_related("otorgado_por", "documento", "registrado_por"),
            "puede_agregar_consentimiento": self.request.user.has_perm("personas.add_consentimiento"),
        }

    def ctx_comunidades(self):
        ctx = self._hijo_ctx("Comunidades", "comunidades", "Comunidad", self.object.comunidades.select_related("comunidad__comuna"),
                             texto=lambda m: str(m.comunidad), detalle=lambda m: " · ".join(x for x in [m.get_rol_display(), m.comunidad.territorio,
                                                                                                         f"desde {m.desde:%d-%m-%Y}" if m.desde else ""] if x))
        ctx["puede_agregar"] = self.request.user.has_perm("comunidades.add_comunidadmiembro")
        return ctx

    def ctx_verificaciones(self):
        return self._hijo_ctx("Verificaciones", "verificaciones", "Verificación", self.object.verificaciones.all(),
                              texto=lambda v: v.tipo, detalle=lambda v: f"{v.fecha:%d-%m-%Y}" + (f" · vigente hasta {v.vigente_hasta:%d-%m-%Y}" if v.vigente_hasta else "") + (" · VENCIDA" if v.vencida else ""))


class PersonaDatosPersonales(Permiso403Mixin, View):
    """Derecho de acceso: todos los datos de una persona en un Excel, para entregárselos si los pide.

    Los datos sensibles solo se incluyen con el permiso correspondiente. Queda en la auditoría.
    """

    permission_required = "personas.exportar_persona"

    def get(self, request, pk):
        from io import BytesIO

        from django.http import HttpResponse
        from openpyxl import Workbook

        from apps.nucleo.auditoria import registrar
        from apps.nucleo.exportacion import _seguro

        p = get_object_or_404(Persona, pk=pk)
        libro = Workbook()
        hojas = [("Datos", ["Campo", "Valor"], [
            ("Nombres", p.nombres), ("Apellido paterno", p.apellido_paterno), ("Apellido materno", p.apellido_materno), ("RUT", p.rut),
            ("Profesión u oficio", p.profesion), ("Sitio web", p.sitio_web), ("Origen", p.origen or ""), ("Estado del registro", p.estado_registro or ""),
            ("Observaciones", p.observaciones), ("Registrada el", f"{p.creado_en:%d-%m-%Y}"),
        ])]
        hojas.append(("Contactos", ["Tipo", "Valor", "Vigente"], [(c.tipo, c.valor, "Sí" if c.vigente else "No") for c in p.contactos.select_related("tipo")]))
        hojas.append(("Direcciones", ["Tipo", "Dirección", "Vigente"], [(d.get_tipo_display(), d.direccion, "Sí" if d.vigente else "No") for d in p.direcciones.select_related("direccion__comuna")]))
        hojas.append(("Formación", ["Institución", "Carrera", "Estado"], [(f.organizacion, f.carrera or "", f.get_estado_display()) for f in p.formaciones.select_related("organizacion", "carrera")]))
        hojas.append(("Cargos", ["Organización", "Cargo", "Desde", "Hasta"], [(v.organizacion, v.cargo, v.fecha_inicio or "", v.fecha_termino or "") for v in p.vinculos.select_related("organizacion")]))
        hojas.append(("Participaciones", ["Actividad", "Rol", "Estado", "Asistencia"], [
            (x.actividad, x.rol, x.estado, {True: "Asistió", False: "No asistió", None: ""}[x.asistencia]) for x in p.participaciones.select_related("actividad", "rol", "estado")
        ]))
        if request.user.has_perm("personas.ver_sensibles"):
            hojas.append(("Emergencia", ["Nombre", "Parentesco", "Teléfono"], [(c.nombre, c.parentesco, c.telefono) for c in p.contactos_emergencia.all()]))
            hojas.append(("Verificaciones", ["Tipo", "Fecha", "Vigente hasta"], [(v.tipo, v.fecha, v.vigente_hasta or "") for v in p.verificaciones.all()]))
        libro.remove(libro.active)
        for titulo, encabezados, filas in hojas:
            h = libro.create_sheet(titulo)
            h.append(encabezados)
            for fila in filas:
                h.append([_seguro(v) for v in fila])
        from apps.nucleo.exportacion import agregar_aviso

        agregar_aviso(libro, request.user)
        buffer = BytesIO()
        libro.save(buffer)
        registrar(request.user, "datos_personales_exportados", p, "derecho de acceso")
        r = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        r["Content-Disposition"] = f'attachment; filename="datos_persona_{p.pk}.xlsx"'
        return r


class PersonaFusionar(__import__("apps.nucleo.vistas_fusion", fromlist=["FusionarBase"]).FusionarBase):
    modelo = Persona
    permiso = "personas.fusionar_persona"
    titulo = "Fusionar personas duplicadas"

    def campo_destino(self, origen):
        from django.urls import reverse_lazy

        from apps.nucleo.formularios import SelectorField

        return SelectorField(Persona.objects.filter(activo=True).exclude(pk=origen.pk), reverse_lazy("personas:opciones"), label="Ficha que se conserva")


class PersonaReasignar(Permiso403Mixin, View):
    """AT-E6: pasar las actividades en curso o futuras de un responsable a otra persona."""

    permission_required = "actividades.change_actividad"

    def _form(self, persona, data=None):
        from django import forms as f
        from django.urls import reverse_lazy

        from apps.actividades.afectacion import a_cargo_de
        from apps.nucleo.formularios import BootstrapMixin, SelectorField

        class F(BootstrapMixin, f.Form):
            actividades = f.ModelMultipleChoiceField(a_cargo_de(persona), widget=f.CheckboxSelectMultiple, label="Actividades a reasignar")
            nuevo = SelectorField(Persona.objects.filter(activo=True).exclude(pk=persona.pk), reverse_lazy("personas:opciones"), label="Nuevo responsable")
            motivo = f.CharField(max_length=250)

        form = F(data, initial={"actividades": list(a_cargo_de(persona))})
        form.fields["actividades"].widget.attrs["class"] = ""
        return form

    def get(self, request, pk):
        p = get_object_or_404(Persona, pk=pk)
        return render(request, "generico/formulario.html", {"form": self._form(p), "titulo": f"Reasignar actividades de {p}", "volver_url": p.get_absolute_url(), "breadcrumb": [(str(p), p.get_absolute_url())]})

    def post(self, request, pk):
        from apps.nucleo.auditoria import registrar

        p = get_object_or_404(Persona, pk=pk)
        form = self._form(p, request.POST)
        if not form.is_valid():
            return render(request, "generico/formulario.html", {"form": form, "titulo": f"Reasignar actividades de {p}", "volver_url": p.get_absolute_url(), "breadcrumb": []}, status=400)
        nuevo = form.cleaned_data["nuevo"]
        n = 0
        with transaction.atomic():
            for a in form.cleaned_data["actividades"]:
                a.responsable = nuevo
                a.save()  # queda en el historial de cada actividad
                n += 1
        registrar(request.user, "responsable_reasignado", p, f"{n} actividades a {nuevo}. Motivo: {form.cleaned_data['motivo']}")
        messages.success(request, f"{n} actividad(es) reasignadas a {nuevo}.")
        return HttpResponseRedirect(p.get_absolute_url())


class PersonaAlternar(AlternarActivoBase):
    modelo = Persona
    permission_required = "personas.change_persona"

    def afectados(self, obj):
        from apps.actividades.afectacion import de_persona

        return de_persona(obj)


class DireccionPersonaNueva(Permiso403Mixin, CreateView):
    """Agrega una dirección (residencia/procedencia) a una persona."""

    form_class = PersonaDireccionForm
    permission_required = "personas.change_persona"
    template_name = "personas/direccion.html"

    def dispatch(self, request, *a, **kw):
        self.persona = get_object_or_404(Persona, pk=kw["pk"])
        return super().dispatch(request, *a, **kw)

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        url = f"{self.persona.get_absolute_url()}?tab=direcciones"
        ctx.update(titulo="Agregar dirección", volver_url=url, breadcrumb=[(self.persona.nombre_completo, self.persona.get_absolute_url())])
        return ctx

    def form_valid(self, form):
        form.save_para(self.persona)
        messages.success(self.request, "Dirección guardada.")
        return HttpResponseRedirect(f"{self.persona.get_absolute_url()}?tab=direcciones")


class PersonaOpciones(Permiso403Mixin, View):
    """<option> de personas que calzan con `q` (para los selectores con búsqueda)."""

    permission_required = "personas.view_persona"

    def get(self, request):
        from django.http import HttpResponse
        from django.utils.html import format_html_join

        qs = Persona.objects.filter(activo=True).exclude(estado_registro__codigo__in=["fallecida", "fusionada"]).buscar(request.GET.get("q", ""))[:25]
        opciones = [("", "---------")] + [(p.pk, p.nombre_completo + (f" · {p.rut}" if p.rut else "")) for p in qs]
        return HttpResponse(format_html_join("", '<option value="{}">{}</option>', opciones))


class PerfilSensibleEditar(Permiso403Mixin, View):
    """Datos sensibles (F22): permiso propio, consentimiento obligatorio y ajuste DATOS_SENSIBLES."""

    permission_required = ("personas.change_persona", "personas.ver_sensibles")

    def dispatch(self, request, *a, **kw):
        from django.conf import settings
        from django.http import Http404

        if not getattr(settings, "DATOS_SENSIBLES", True):
            raise Http404("El registro de datos sensibles está desactivado.")
        return super().dispatch(request, *a, **kw)

    def _contexto(self, persona, form):
        return {"form": form, "titulo": f"Datos sensibles de {persona.nombre_completo}", "volver_url": f"{persona.get_absolute_url()}?tab=sensibles",
                "breadcrumb": [("Personas", "/personas"), (persona.nombre_completo, persona.get_absolute_url())],
                "bajada": "Solo los ve quien tiene permiso de datos sensibles. Se guardan únicamente con el consentimiento explícito de la persona o de su apoderado."}

    def get(self, request, pk):
        from django.shortcuts import render

        persona = get_object_or_404(Persona, pk=pk)
        form = PerfilSensibleForm(instance=getattr(persona, "perfil_sensible", None), persona=persona)
        return render(request, "generico/formulario.html", self._contexto(persona, form))

    def post(self, request, pk):
        from django.shortcuts import render

        persona = get_object_or_404(Persona, pk=pk)
        instancia = getattr(persona, "perfil_sensible", None) or PerfilSensible(persona=persona)
        form = PerfilSensibleForm(request.POST, instance=instancia, persona=persona)
        if not form.is_valid():
            return render(request, "generico/formulario.html", self._contexto(persona, form), status=400)
        with transaction.atomic():
            if form.cleaned_data.get("consentimiento"):
                Consentimiento.objects.create(persona=persona, tipo="sensibles", otorgado=True, fecha=form.cleaned_data["consentimiento_fecha"],
                                              medio=form.cleaned_data.get("consentimiento_medio") or "papel", registrado_por=request.user)
            form.save()
        from apps.nucleo.auditoria import registrar

        registrar(request.user, "datos_sensibles_editados", persona, "")
        messages.success(request, "Datos sensibles guardados.")
        return HttpResponseRedirect(f"{persona.get_absolute_url()}?tab=sensibles")

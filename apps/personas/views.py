"""Pantallas de personas: listado con filtros, crear con aviso de duplicados, ficha con pestañas (las restringidas solo
con permiso), editar, desactivar, unir repetidas (Administrador), reasignar, datos personales y datos sensibles."""
from apps.nucleo.utilidades import plural
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render  # noqa: F401
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView

from django.db.models import Q

from apps.nucleo.models import AreaTematica, EstadoRegistro, OrigenPersona, PerfilPersona, RolParticipacion
from apps.organizaciones.models import Organizacion
from apps.nucleo.vistas_base import (
    AlternarActivoBase, EditarBase, FichaBase, Filtro, ListaBase, Permiso403Mixin, filtro_activo, nombre_comuna, nombre_organizacion,
    opciones_comunas, opciones_modelo, opciones_organizaciones,
)

from apps.nucleo.selector import OpcionesVista, campo_seguro, respuesta_elegido

from .duplicados import candidatos_ficha_rapida
from .forms import PerfilSensibleForm, PersonaDireccionForm, PersonaForm, PersonaNuevaForm, PersonaRapidaForm
from .models import Consentimiento, FichaInvitado, FichaVecino, FichaVoluntario, PerfilSensible, Persona, PersonaDireccion
from .selector import AYUDA_RESPONSABLE, PERSONAS


def _principal(persona, codigos):
    for c in persona.contactos.all():
        if c.vigente and c.tipo.codigo in codigos:
            return c.valor
    return ""


# Permiso que deja ver el RUT en la lista de personas y en sus exportaciones (el mismo del territorio y del informe de proyecto)
PERMISO_RUT = "personas.exportar_persona"


def _contacto_principal(persona):
    """Correo o teléfono vigente, primero el marcado como principal y, entre iguales, el correo. Usa lo precargado."""
    tipos = {"correo": 0, "telefono_movil": 1, "telefono_fijo": 2}
    candidatos = [c for c in persona.contactos.all() if c.vigente and c.tipo.codigo in tipos]
    if not candidatos:
        return ""
    return min(candidatos, key=lambda c: (not c.principal, tipos[c.tipo.codigo], c.pk)).valor


def _comuna_residencia(persona):
    """Comuna de la residencia vigente (la primera registrada). Usa lo precargado."""
    residencias = sorted((d for d in persona.direcciones.all() if d.vigente and d.tipo == "residencia"), key=lambda d: d.pk)
    return residencias[0].direccion.comuna if residencias else None


def _sin_cortes(texto):
    from django.utils.html import format_html

    return format_html('<span class="text-nowrap">{}</span>', texto) if texto else ""


def _estado_ficha(persona):
    """Insignia del estado de la ficha y, si está incompleta (o sin estado), debajo lo que le falta. Con otro estado
    (activo, por verificar…) no se agrega nada, para no mostrar dos verdades."""
    from django.utils.html import format_html

    from apps.nucleo.templatetags.fche import badge_estado

    e = persona.estado_registro
    insignia = badge_estado(e.codigo, e.nombre) if e else ""
    falta = persona.faltantes() if e is None or e.codigo == "incompleto" else []
    if not falta:
        return insignia
    return format_html('{}<div class="small text-muted">Falta: {}</div>', insignia, ", ".join(falta))


def _opciones_comunidad():
    from apps.comunidades.models import Comunidad

    return [(str(c.pk), c.nombre) for c in Comunidad.objects.filter(activo=True)]


def _organizaciones_con_personas():
    """Organizaciones con alguna persona vinculada o formándose en ellas: las únicas que filtran algo."""
    from .models import PersonaFormacion, PersonaOrganizacion

    return Organizacion.objects.filter(
        Q(pk__in=PersonaOrganizacion.objects.values("organizacion_id")) | Q(pk__in=PersonaFormacion.objects.values("organizacion_id"))
    )


def _filtrar_edad(qs, tramo):
    """Tramos de edad a partir de la fecha de nacimiento (F22)."""
    from django.utils import timezone

    hoy = timezone.localdate()

    def hace(anios):
        try:
            return hoy.replace(year=hoy.year - anios)
        except ValueError:  # 29 de febrero
            return hoy.replace(year=hoy.year - anios, day=28)

    if tramo == "sin":
        return qs.filter(fecha_nacimiento__isnull=True)
    limites = {"menor": (0, 17), "18_29": (18, 29), "30_59": (30, 59), "60": (60, 150)}
    if tramo not in limites:
        raise ValueError(tramo)
    desde, hasta = limites[tramo]
    return qs.filter(fecha_nacimiento__lte=hace(desde), fecha_nacimiento__gt=hace(hasta + 1)) if desde else qs.filter(fecha_nacimiento__gt=hace(hasta + 1))


class PersonaLista(ListaBase):
    model = Persona
    permission_required = "personas.view_persona"
    titulo = "Personas"
    descripcion = "Voluntarios, profesionales, beneficiarios y contactos registrados."
    url_crear = "/personas/nueva"
    permiso_crear = "personas.add_persona"
    etiqueta_crear = "+ Nueva persona"
    campos_busqueda = ()  # busca con Persona.objects.buscar (nombre, RUT, correo o teléfono), ver filtrar()
    buscable = True
    texto_busqueda = "Nombre, RUT, correo o teléfono…"
    # F26 Ib: Nombre · Perfil · Contacto · Comuna · Edad · Estado de la ficha. El RUT, solo con el permiso que lo deja ver
    # (PERMISO_RUT); «Origen» queda como filtro en «Más filtros». Todo sale de lo precargado: sin consultas por fila.
    columnas = [
        ("Nombre", lambda p: p.nombre_completo),
        ("Perfil", lambda p: ", ".join(x.nombre for x in p.perfiles.all())),
        ("Contacto", lambda p: _contacto_principal(p)),
        ("Comuna", lambda p: _comuna_residencia(p) or ""),
        ("Edad", lambda p: p.edad if p.edad is not None else ""),
        ("Estado de la ficha", lambda p: _estado_ficha(p)),
    ]
    columna_rut = ("RUT 🔒", lambda p: _sin_cortes(p.rut))
    # El Excel conserva lo útil por separado: correo y teléfono, lo que le falta y el origen
    columnas_excel = [
        ("Nombre", lambda p: p.nombre_completo),
        ("RUT", "rut"),
        ("Perfil", lambda p: ", ".join(x.nombre for x in p.perfiles.all())),
        ("Correo", lambda p: _principal(p, ["correo"])),
        ("Teléfono", lambda p: _principal(p, ["telefono_movil", "telefono_fijo"])),
        ("Comuna", lambda p: _comuna_residencia(p) or ""),
        ("Edad", lambda p: p.edad if p.edad is not None else ""),
        ("Estado de la ficha", "estado_registro"),
        ("Le falta", lambda p: ", ".join(p.faltantes())),
        ("Origen", "origen"),
    ]
    ordenes = {"nombre": "apellido_paterno", "creado": "creado_en"}
    orden_defecto = ("apellido_paterno", "apellido_materno", "nombres")
    filtros = [
        # A la vista: Perfil, Comuna y Comunidad (decidido con el usuario). El resto, en «Más filtros».
        Filtro("perfil", "Perfil", "", lambda: [(str(p.pk), p.nombre) for p in PerfilPersona.objects.filter(activo=True)], aplicar=lambda qs, v: qs.filter(perfiles__id=v).distinct(),
               principal=True),
        Filtro("comuna", "Comuna", "", lambda: opciones_comunas(Q(pk__in=PersonaDireccion.objects.filter(vigente=True).values("direccion__comuna_id"))),
               aplicar=lambda qs, v: qs.filter(direcciones__vigente=True, direcciones__direccion__comuna_id=v).distinct(), principal=True, todos="Todas",
               etiqueta_de=nombre_comuna),
        Filtro("comunidad", "Comunidad", "", lambda: _opciones_comunidad(),
               aplicar=lambda qs, v: qs.filter(comunidades__comunidad_id=v, comunidades__vigente=True).distinct(), principal=True, todos="Todas"),
        Filtro("rol", "Tipo de relación", "", opciones_modelo(RolParticipacion), aplicar=lambda qs, v: qs.filter(participaciones__rol_id=v).distinct(), grupo="Relación"),
        Filtro("organizacion", "Organización", "", lambda: opciones_organizaciones(_organizaciones_con_personas()),
               aplicar=lambda qs, v: qs.filter(Q(vinculos__organizacion_id=v) | Q(formaciones__organizacion_id=v)).distinct(), grupo="Relación", todos="Todas",
               tope=300, etiqueta_de=nombre_organizacion),
        Filtro("interes", "Interés", "", lambda: [(str(a.pk), a.nombre) for a in AreaTematica.objects.filter(activo=True)], aplicar=lambda qs, v: qs.filter(areas_interes__id=v).distinct(),
               grupo="Perfil"),
        Filtro("edad", "Edad", "", lambda: [("menor", "Menores de 18"), ("18_29", "18 a 29"), ("30_59", "30 a 59"), ("60", "60 o más"), ("sin", "Sin fecha de nacimiento")],
               aplicar=lambda qs, v: _filtrar_edad(qs, v), grupo="Perfil", todos="Todas"),
        Filtro("registro", "Estado del registro", "estado_registro__codigo", lambda: [(e.codigo, e.nombre) for e in EstadoRegistro.objects.all()], grupo="Registro"),
        Filtro("origen", "Origen", "origen_id", opciones_modelo(OrigenPersona), grupo="Registro"),
        filtro_activo(),
    ]
    texto_vacio = "Aún no hay personas registradas."
    url_exportar = "/personas/exportar"
    permiso_exportar = "personas.exportar_persona"

    def filtrar(self, qs):
        return super().filtrar(qs).buscar(self.request.GET.get("q"))

    def get_queryset(self):
        # con_completitud(): contactos, direcciones, comunidades, perfiles y formaciones para `faltantes()`; más el tipo de
        # contacto y la comuna de la dirección. Número fijo de consultas por página.
        return (super().get_queryset().select_related("estado_registro", "origen").con_completitud()
                .prefetch_related("contactos__tipo", "direcciones__direccion__comuna"))

    def columnas_visibles(self):
        if not self.request.user.has_perm(PERMISO_RUT):
            return self.columnas
        return [self.columnas[0], self.columna_rut, *self.columnas[1:]]

    def columnas_exportacion(self):
        if self.request.user.has_perm(PERMISO_RUT):
            return self.columnas_excel
        return [c for c in self.columnas_excel if c[0] != "RUT"]


class PersonaExportar(PersonaLista):
    exportar = True
    permission_required = "personas.exportar_persona"


class PersonaNueva(Permiso403Mixin, CreateView):
    """Ficha rápida (nombre y un contacto) o completa, con el «Tipo de registro» (estudiante, vecino, invitado, voluntario)
    y la sección de cada tipo marcado (apps/personas/fichas.py). Siempre busca coincidencias antes de crear (PE-04):
    el aviso de duplicados aparece antes de guardar nada, también lo de las secciones."""

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

    def get_form(self, form_class=None):
        from .fichas import RegistroFichas

        form = super().get_form(form_class)
        form.separar_tipos()
        datos = self.request.POST if self.request.method == "POST" else None
        self.fichas = RegistroFichas(datos, self.request.user, base=form)
        from .relaciones import organizacion_comunidad_form, relaciones_formset

        self.procedencia = organizacion_comunidad_form(datos)  # F26 P2: su organización y su comunidad, una sola vez
        self.relaciones = relaciones_formset(datos)  # F25: las otras relaciones (proyectos, tareas y actividades)
        return form

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx.update(titulo="Nueva persona", volver_url="/personas", breadcrumb=[("Personas", "/personas")], modo=self.modo(), fichas=self.fichas,
                   relaciones=self.relaciones, procedencia=self.procedencia)
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        if self.fichas.solo_mostrar:  # «Mostrar secciones» o «Actualizar listas»: se vuelve a dibujar sin guardar ni marcar errores
            from apps.territorio.ubicacion import sin_errores

            sin_errores(form)
            return self.render_to_response(self.get_context_data(form=form))
        from .relaciones import relaciones_validas

        if all([form.is_valid(), self.fichas.is_valid(), relaciones_validas(self.relaciones),
                not self.procedencia.is_bound or self.procedencia.is_valid()]):
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        d = form.cleaned_data
        cands = None
        if not self.request.POST.get("confirmar_duplicado") or not self.request.POST.get("nota_distincion", "").strip():
            cands = candidatos_ficha_rapida(d)
            if cands:
                falta_nota = bool(self.request.POST.get("confirmar_duplicado"))
                return self.render_to_response(self.get_context_data(form=form, candidatos=cands, falta_nota=falta_nota))
        with transaction.atomic():
            persona = form.save(commit=False)
            persona.creado_por = self.request.user
            nota = self.request.POST.get("nota_distincion", "").strip()
            if nota:  # PE-E2: qué la distingue de la otra persona con el mismo nombre
                persona.observaciones = (f"Se distingue de otra ficha parecida: {nota}\n" + persona.observaciones).strip()
            # F26 P2: «activo» o «incompleto» se calcula solo (apps/personas/senales.py) al guardar la persona, sus contactos,
            # su dirección y su formación; un estado manual elegido en el formulario (p. ej. «Por verificar») se respeta
            persona.save()
            form.save_m2m()  # perfiles (también los «Tipo de registro») y áreas de interés (F22)
            self.fichas.guardar(persona)  # las secciones de los tipos marcados
            from .servicios import completar_ficha_rapida

            completar_ficha_rapida(persona, d)  # contactos y, en la ficha rápida, la comuna donde vive (si la ficha de vecino no dio la dirección)
            from .relaciones import guardar_organizacion_comunidad, guardar_relaciones

            guardar_organizacion_comunidad(self.procedencia, persona, self.request.user)
            guardar_relaciones(self.relaciones, persona, self.request.user)
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
    """Editar la persona, con su «Tipo de registro» y la sección de cada tipo marcado, en una sola transacción."""

    model = Persona
    form_class = PersonaForm
    permission_required = "personas.change_persona"
    titulo = "Editar persona"
    breadcrumb = [("Personas", "/personas")]
    template_name = "personas/editar.html"

    def get_form(self, form_class=None):
        from .fichas import RegistroFichas

        form = super().get_form(form_class)
        form.separar_tipos()
        datos = self.request.POST if self.request.method == "POST" else None
        self.fichas = RegistroFichas(datos, self.request.user, persona=self.object, base=form)
        return form

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["fichas"] = self.fichas
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if self.fichas.solo_mostrar:
            from apps.territorio.ubicacion import sin_errores

            sin_errores(form)
            return self.render_to_response(self.get_context_data(form=form))
        if all([form.is_valid(), self.fichas.is_valid()]):
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        if self.version_en_conflicto():
            form.add_error(None, self.MENSAJE_VERSION)
            return self.form_invalid(form)
        with transaction.atomic():
            respuesta = super().form_valid(form)
            self.fichas.guardar(self.object)
        return respuesta


class PersonaFichaTipo(Permiso403Mixin, View):
    """«Editar» de una tarjeta de la pestaña Datos: solo la sección de ese tipo (estudiante, vecino, invitado o voluntario).
    Al guardar, si la persona aún no tenía un perfil con esa ficha, se le marca el primero que la abre."""

    permission_required = "personas.change_persona"

    def _preparar(self, request, pk, codigo, datos=None):
        from django.http import Http404

        from .fichas import POR_CODIGO, RegistroFichas

        clase = POR_CODIGO.get(codigo)
        if clase is None:
            raise Http404
        if not request.user.has_perm(clase.permiso):
            raise PermissionDenied
        persona = get_object_or_404(Persona, pk=pk)
        return persona, clase, RegistroFichas(datos, request.user, persona=persona, solo=codigo)

    def _render(self, request, persona, clase, registro):
        ctx = {"titulo": f"{clase.titulo}: {persona.nombre_completo}", "volver_url": f"{persona.get_absolute_url()}?tab=datos",
               "breadcrumb": [("Personas", "/personas"), (persona.nombre_completo, persona.get_absolute_url())], "seccion": registro.secciones[0],
               "persona": persona, "bajada": clase.ayuda}
        return render(request, "personas/ficha_tipo.html", ctx)

    def get(self, request, pk, codigo):
        return self._render(request, *self._preparar(request, pk, codigo))

    def post(self, request, pk, codigo):
        persona, clase, registro = self._preparar(request, pk, codigo, request.POST)
        if not registro.is_valid():
            return self._render(request, persona, clase, registro)
        with transaction.atomic():
            registro.guardar(persona)
            if not persona.perfiles.filter(ficha=codigo).exists():
                perfil = PerfilPersona.objects.filter(activo=True, ficha=codigo).order_by("orden", "nombre").first()
                if perfil:
                    persona.perfiles.add(perfil)
        messages.success(request, f"{clase.titulo}: datos guardados.")
        return HttpResponseRedirect(f"{persona.get_absolute_url()}?tab=datos")


def formulario_con_usuario(vista):
    """get_form_kwargs de la formación (pestaña Formación): pasa el usuario, que decide si puede crear una sede o una carrera."""
    kw = super(type(vista), vista).get_form_kwargs()
    kw["usuario"] = vista.request.user
    return kw


class EstudiosDependientes(Permiso403Mixin, View):
    """Sede y carrera de la institución elegida: personas/fichas/_estudios.html las vuelve a dibujar al cambiarla."""

    permission_required = "personas.view_persona"

    def get(self, request):
        from apps.territorio.ubicacion import prefijo_seguro

        from .forms import FormacionForm

        prefijo = prefijo_seguro(request.GET.get("_prefijo"))
        datos = request.GET.copy()
        datos[f"{prefijo}-_actualizar_estudios" if prefijo else "_actualizar_estudios"] = "1"  # solo dibujar: sin errores
        form = FormacionForm(datos, prefix=prefijo or None, usuario=request.user)
        return render(request, "personas/fichas/_estudios_dependientes.html", {"form": form})


def _hijos(objs, texto, detalle=None, url_base=None, slug=None, pk=None, vigente="vigente", url=None):
    res = []
    for o in objs:
        h = {"texto": texto(o), "detalle": detalle(o) if detalle else "", "vigente": getattr(o, vigente, True) if vigente else True,
             "url": url(o) if url else ""}
        if slug:
            h["url_editar"] = reverse(f"personas:{slug}_editar", args=[pk, o.pk])
            if vigente:
                h["url_alternar"] = reverse(f"personas:{slug}_alternar", args=[pk, o.pk])
        res.append(h)
    return res


# Ficha de persona en 8 pestañas (antes 17). Cada pestaña reúne secciones; una sección se ve solo con su permiso
# y la pestaña aparece si tiene al menos una sección visible. Los nombres antiguos siguen abriendo su pestaña.
SECCIONES_PERSONA = {
    "contacto": [("contactos", None), ("direcciones", None), ("emergencia", "personas.ver_sensibles")],
    "estudios": [("formacion", None), ("experiencia", None), ("disponibilidad", None)],
    "participaciones": [("trayectoria", "actividades.view_participacion"), ("interacciones", "coordinacion.view_interaccion")],
    "privacidad": [("sensibles", "personas.ver_sensibles"), ("apoderados", "personas.ver_sensibles"),
                   ("consentimientos", "personas.view_consentimiento"), ("verificaciones", "personas.ver_sensibles")],
    "historial": [("cambios", "personas.view_historicalpersona"), ("origen", "documentos.view_origendato")],
}
ALIAS_PERSONA = {
    "datos": "resumen", "contactos": "contacto", "direcciones": "contacto", "emergencia": "contacto",
    "formacion": "estudios", "experiencia": "estudios", "disponibilidad": "estudios", "comunidades": "vinculos",
    "trayectoria": "participaciones", "interacciones": "participaciones",
    "sensibles": "privacidad", "apoderados": "privacidad", "consentimientos": "privacidad", "verificaciones": "privacidad",
    "origen": "historial",
}


NOMBRE_GRUPO_VACIO = {"Organizaciones y cargos": "organizaciones", "Actividades y tareas": "actividades"}


def _sin(nombres):
    """[«organizaciones», «estudios», «lugares»] → «Sin organizaciones, estudios ni lugares.»"""
    if not nombres:
        return ""
    texto = nombres[0] if len(nombres) == 1 else f"{', '.join(nombres[:-1])} ni {nombres[-1]}"
    return f"Sin {texto}."


class PersonaFicha(FichaBase):
    model = Persona
    template_name = "personas/ficha.html"
    permission_required = "personas.view_persona"
    breadcrumb = [("Personas", "/personas")]
    permiso_editar = "personas.change_persona"
    pestanas = [
        ("resumen", "Resumen", "personas/pestanas/resumen.html"),
        ("contacto", "Contacto", "personas/pestanas/contacto.html"),
        ("estudios", "Estudios y trayectoria", "personas/pestanas/estudios.html"),
        ("vinculos", "Cargos y vínculos", "personas/pestanas/vinculos.html"),
        ("participaciones", "Participaciones", "personas/pestanas/participaciones.html"),
        ("documentos", "Documentos", "documentos/pestanas/lista.html", "documentos.view_documento"),
        ("privacidad", "Privacidad 🔒", "personas/pestanas/privacidad.html"),
        ("historial", "Historial", "personas/pestanas/historial.html"),
    ]
    alias_pestanas = ALIAS_PERSONA

    def get_queryset(self):
        """F26 Rb: lo que miran la cabecera, el resumen y `faltantes()` se lee una vez (contactos con su tipo, perfiles…)."""
        from django.db.models import Prefetch

        from .models import Contacto

        return Persona.objects.select_related("ficha_voluntario", "ficha_invitado").prefetch_related(
            Prefetch("contactos", queryset=Contacto.objects.select_related("tipo")), "direcciones", "comunidades", "perfiles", "formaciones",
            Prefetch("consentimientos", queryset=Consentimiento.objects.order_by("-fecha", "-pk")))

    def secciones(self, pestana):
        """Secciones visibles de una pestaña según los permisos (y los ajustes de datos sensibles y de segunda fase)."""
        from django.conf import settings

        from apps.nucleo.fases import modulo_activo

        u = self.request.user
        res = []
        for clave, permiso in SECCIONES_PERSONA.get(pestana, []):
            if permiso and not u.has_perm(permiso):
                continue
            if clave == "sensibles" and not getattr(settings, "DATOS_SENSIBLES", True):
                continue
            if clave == "verificaciones" and not modulo_activo("verificaciones"):
                continue
            res.append(clave)
        return res

    def pestanas_visibles(self):
        visibles = super().pestanas_visibles()
        return [p for p in visibles if p[0] not in SECCIONES_PERSONA or self.secciones(p[0])]

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
            "comuna_residencia": self.comuna_residencia(),
        }

    def comuna_residencia(self):
        """Comuna de la residencia vigente (la primera si hay varias): enlaza la cabecera con su ficha en Territorio. Una sola consulta."""
        residencia = (
            self.object.direcciones.filter(tipo="residencia", vigente=True).select_related("direccion__comuna").order_by("pk").first()
        )
        return residencia.direccion.comuna if residencia else None

    def encabezado(self):
        return self.object.nombre_completo

    def _hijo_ctx(self, titulo, slug, etiqueta, objs, **kw):
        return {
            "titulo_pestana": titulo, "etiqueta_nuevo": etiqueta, "url_nuevo": reverse(f"personas:{slug}_nuevo", args=[self.object.pk]),
            "hijos": _hijos(objs, pk=self.object.pk, slug=slug, **kw), "vacio": f"Sin {titulo.lower()} registrados.",
            "puede_agregar": self.request.user.has_perm("personas.change_persona"),
        }

    def _por_seccion(self, pestana):
        """{sección: contexto de la sección} con las secciones visibles de la pestaña; la plantilla las incluye con `with`."""
        ctx = {"secciones": self.secciones(pestana)}
        for clave in ctx["secciones"]:
            ctx[clave] = getattr(self, f"ctx_{clave}")()
        return ctx

    def ctx_resumen(self):
        """Solo los datos con valor; los vacíos se cuentan aparte («Sin completar (N)»). Más las tarjetas por tipo de registro,
        el contacto principal y la dirección vigente."""
        from .fichas import tarjetas

        p = self.object
        nacimiento = ""
        if p.fecha_nacimiento:
            nacimiento = "Aproximada" if p.fecha_nacimiento_aproximada else f"{p.fecha_nacimiento:%d-%m-%Y}"
            if p.edad is not None:
                nacimiento += f" ({'≈ ' if p.fecha_nacimiento_aproximada else ''}{p.edad} años)"
        campos = [
            # (etiqueta, valor, forma, restringido, ancho). forma: texto, parrafo, etiquetas, enlace
            ("RUT", p.rut, "texto", True, False),
            (p.get_tipo_documento_display() if p.numero_documento else "Otro documento", p.numero_documento, "texto", True, False),
            ("Fecha de nacimiento", nacimiento, "texto", False, False),
            ("Sexo", p.get_sexo_display(), "texto", False, False),
            ("Nacionalidad", p.nacionalidad, "texto", False, False),
            ("Nombre social", p.nombre_social, "texto", False, False),
            ("Perfil en la Fundación", [str(x) for x in p.perfiles.all()], "etiquetas", False, False),
            ("Nivel educacional", p.get_nivel_educacional_display(), "texto", False, False),
            ("Situación ocupacional", p.get_situacion_ocupacional_display(), "texto", False, False),
            ("Profesión u oficio", p.profesion, "texto", False, False),
            ("Sitio web", p.sitio_web, "enlace", False, False),
            ("Idiomas", p.idiomas, "texto", False, False),
            ("Canal de contacto preferido", str(p.canal_preferido or ""), "texto", False, False),
            ("Áreas de interés", [str(x) for x in p.areas_interes.all()], "etiquetas", False, True),
            ("Habilidades y conocimientos", p.habilidades, "parrafo", False, True),
            ("Origen", str(p.origen or ""), "texto", False, False),
            ("Observaciones", p.observaciones, "parrafo", False, True),
        ]
        llenos = [{"etiqueta": e, "valor": v, "forma": f, "restringido": r, "ancho": a} for e, v, f, r, a in campos if v]
        vacios = [{"etiqueta": e, "restringido": r} for e, v, f, r, a in campos if not v and e != "Otro documento"]
        residencia = p.direcciones.filter(vigente=True).select_related("direccion__comuna", "direccion__sector").order_by("tipo", "pk").first()
        return {
            "datos_llenos": llenos, "datos_vacios": vacios, "tarjetas_fichas": self._tarjetas_sin_repetir(tarjetas(p, self.request.user)),
            "direccion_vigente": residencia, "resumen_360": self.resumen_360(),
            "pie_vistazo": ("Ver todos los cargos y vínculos", "?tab=vinculos"),
        }

    @staticmethod
    def _tarjetas_sin_repetir(lista):
        """F26 P3a: la formación vigente y las comunidades ya están en el Resumen 360°: no se repiten en las tarjetas."""
        for t in lista:
            if t["codigo"] == "estudiante":
                t["filas"], t["vacio"] = [], "Su formación vigente aparece arriba, en el resumen."
            elif t["codigo"] == "vecino":
                t["filas"] = [f for f in t["filas"] if f["etiqueta"] != "Comunidad"]
        return lista

    def resumen_360(self):
        """F26 P3a: la persona de un vistazo: organización y cargo vigentes (con el rol del catálogo), formación vigente,
        comunidades vigentes, sus últimas 3 participaciones, la próxima actividad programada y lo que le falta a la ficha.
        Todo con enlaces. Número fijo de consultas, sin importar cuántos registros tenga."""
        from django.utils import timezone

        from apps.actividades.models import AgendaActividad

        from .vinculos import cargos_y_vinculos

        p = self.object
        grupos = dict(cargos_y_vinculos(p))
        vigentes = {clave: [f for f in grupos.get(titulo, []) if f["vigente"]]
                    for clave, titulo in (("cargos", "Organizaciones y cargos"), ("estudios", "Estudios"), ("comunidades", "Comunidades"))}
        ultimas = grupos.get("Actividades y tareas", [])[:3] if self.request.user.has_perm("actividades.view_participacion") else None
        proxima, ver_actividades = None, self.request.user.has_perm("actividades.view_actividad")
        if ver_actividades:
            suyas = p.participaciones.exclude(estado__codigo__in=["rechazo", "cancelo", "registro_erroneo"]).values("actividad_id")
            proxima = (AgendaActividad.objects.filter(
                vigente=True, fecha__gte=timezone.localdate(), actividad__estado__codigo__in=["planificada", "confirmada", "reprogramada"],
                actividad_id__in=suyas)
                .select_related("actividad__proyecto", "lugar").order_by("fecha", "hora_inicio", "pk").first())
        return self._filas_vistazo({**vigentes, "ultimas": ultimas, "proxima": proxima, "ver_actividades": ver_actividades, "faltantes": p.faltantes()})

    def _filas_vistazo(self, r):
        """F26 Ib: el mismo «De un vistazo» de siempre, en filas para el parcial común (generico/_de_un_vistazo.html)."""
        from apps.nucleo.vistazo import fila, item, item_agenda

        def renglones(filas, entre_parentesis=True):
            return [item((f["nombre"], f["url"]), (f["rol"], ""), nota=(f"({f['detalle']})" if entre_parentesis else f"· {f['detalle']}") if f.get("detalle") else "")
                    for f in filas]

        filas = [
            fila("Organización y cargo", renglones(r["cargos"]), "Sin cargos vigentes"),
            fila("Formación vigente", renglones(r["estudios"]), "Sin formación vigente"),
            fila("Comunidades", [item((f["nombre"], f["url"]), (f["rol"], "")) for f in r["comunidades"]], "Sin comunidades vigentes"),
        ]
        if r["ver_actividades"]:
            filas.append(fila("Próxima actividad", [item_agenda(r["proxima"])] if r["proxima"] else [], "Ninguna programada"))
        if r["ultimas"] is not None:
            filas.append(fila("Últimas participaciones", renglones(r["ultimas"], entre_parentesis=False), "Aún no participa en actividades",
                              ancho=True, lista=True, pie=("Ver todas", "?tab=participaciones") if r["ultimas"] else None))
        completar = None
        if r["faltantes"] and self.request.user.has_perm(self.permiso_editar):
            completar = ("Completar ficha", reverse("personas:editar", args=[self.object.pk]))
        filas.append(fila("Le falta", [item((", ".join(r["faltantes"]), ""))] if r["faltantes"] else [], "Nada: la ficha tiene lo mínimo",
                          ancho=True, pie=completar, pie_en_linea=True))
        return {**r, "filas": filas}

    def ctx_contacto(self):
        return self._por_seccion("contacto")

    def ctx_estudios(self):
        return self._por_seccion("estudios")

    def ctx_participaciones(self):
        ctx = {"secciones": self.secciones("participaciones")}
        for clave in ctx["secciones"]:
            ctx.update(getattr(self, f"ctx_{clave}")())  # sin «hijos»: sus nombres no chocan
        return ctx

    def ctx_privacidad(self):
        ctx = self._por_seccion("privacidad")
        for plano in ("sensibles", "consentimientos"):  # sin «hijos»: sus nombres van directo a la plantilla
            if plano in ctx:
                ctx.update(ctx.pop(plano))
        return ctx

    def ctx_historial(self):
        secciones = self.secciones("historial")
        ctx = {"secciones": secciones}
        if "cambios" in secciones:
            ctx["cambios"] = super().ctx_historial()["cambios"]
        if "origen" in secciones:
            ctx.update(self.ctx_origen())  # al final de la pestaña, «Origen de la información»
        return ctx

    def ctx_trayectoria(self):
        from apps.actividades.alcance import horas_persona

        p = self.object
        return {
            "horas_acumuladas": horas_persona(p),
            "participaciones": p.participaciones.select_related("actividad__estado", "actividad__proyecto", "rol", "estado").order_by("-actividad__creado_en"),
            "reuniones": p.reuniones.select_related("reunion").order_by("-reunion__fecha"),
            "tareas": p.tareas_asignadas.select_related("tarea").order_by("-tarea__creado_en"),
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
        return ctx

    def ctx_formacion(self):
        def detalle(f):
            partes = [f.get_estado_display(), f.sede, f.get_jornada_display() if f.jornada else "", f"{f.nivel_actual}.º año" if f.nivel_actual else "",
                      f.asignatura, f"docente: {f.docente}" if f.docente_id else "", f"{f.horas_comprometidas} h comprometidas" if f.horas_comprometidas else ""]
            return " · ".join(x for x in partes if x)

        return self._hijo_ctx("Formación", "formacion", "Formación", self.object.formaciones.select_related("organizacion", "carrera", "docente"),
                              texto=lambda f: str(f), detalle=detalle, url=lambda f: f.organizacion.get_absolute_url())

    def ctx_experiencia(self):
        """F25: arriba, los cargos y roles ya terminados (se arman solos desde «Cargos y vínculos»); abajo, la experiencia
        fuera de la Fundación, que se carga a mano."""
        from .vinculos import cargos_y_vinculos

        terminados = [(titulo, [f for f in filas if not f["vigente"]]) for titulo, filas in cargos_y_vinculos(self.object)]
        ctx = self._hijo_ctx("Experiencia fuera de la Fundación", "experiencia", "Experiencia fuera de la Fundación", self.object.experiencias.all(),
                             texto=lambda e: e.descripcion, detalle=lambda e: e.lugar)
        ctx.update(terminados=[(t, filas) for t, filas in terminados if filas],
                   vacio="Sin experiencia fuera de la Fundación registrada.")
        return ctx

    def ctx_disponibilidad(self):
        return self._hijo_ctx("Disponibilidad", "disponibilidad", "Horario", self.object.disponibilidades.all(),
                              texto=lambda d: str(d), detalle=lambda d: d.comentario)

    def ctx_vinculos(self):
        from .vinculos import cargos_y_vinculos

        todos = cargos_y_vinculos(self.object)
        # F26 Ib: solo los grupos con datos; los vacíos, resumidos en una línea («Sin organizaciones, estudios ni lugares.»)
        vacios = [NOMBRE_GRUPO_VACIO.get(t, t.lower()) for t, filas in todos if not filas]
        return {"grupos": [(t, filas) for t, filas in todos if filas], "grupos_vacios": _sin(vacios),
                "url_nuevo": reverse("personas:vinculos_nuevo", args=[self.object.pk]),
                "url_nuevo_lugar": reverse("personas:lugares_nuevo", args=[self.object.pk]),
                "url_nueva_comunidad": reverse("personas:comunidades_nuevo", args=[self.object.pk])}  # antes en la pestaña Comunidades

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
            ultimo = p.ultimo_consentimiento(codigo)
            estado.append({"nombre": nombre, "ultimo": ultimo, "vigente": bool(ultimo and ultimo.vigente)})
        return {
            "estado_consentimientos": estado,
            "consentimientos": p.consentimientos.select_related("otorgado_por", "documento", "registrado_por"),
            "puede_agregar_consentimiento": self.request.user.has_perm("personas.add_consentimiento"),
        }

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
            ("Nombre social", p.nombre_social), ("Fecha de nacimiento", f"{p.fecha_nacimiento:%d-%m-%Y}" if p.fecha_nacimiento else ""),
            ("Fecha de nacimiento aproximada", ("Sí" if p.fecha_nacimiento_aproximada else "No") if p.fecha_nacimiento else ""),
            ("Sexo", p.get_sexo_display()), ("Nacionalidad", p.nacionalidad),
            ("Perfiles", ", ".join(str(x) for x in p.perfiles.all())), ("Nivel educacional", p.get_nivel_educacional_display()),
            ("Situación ocupacional", p.get_situacion_ocupacional_display()), ("Áreas de interés", ", ".join(str(x) for x in p.areas_interes.all())),
            ("Habilidades", p.habilidades), ("Idiomas", p.idiomas), ("Canal preferido", p.canal_preferido or ""),
            ("Profesión u oficio", p.profesion), ("Sitio web", p.sitio_web), ("Origen", p.origen or ""), ("Estado del registro", p.estado_registro or ""),
            ("Observaciones", p.observaciones), ("Registrada el", f"{p.creado_en:%d-%m-%Y}"),
        ])]
        hojas.append(("Contactos", ["Tipo", "Valor", "Vigente"], [(c.tipo, c.valor, "Sí" if c.vigente else "No") for c in p.contactos.select_related("tipo")]))
        hojas.append(("Direcciones", ["Tipo", "Dirección", "Vigente"], [(d.get_tipo_display(), d.direccion, "Sí" if d.vigente else "No") for d in p.direcciones.select_related("direccion__comuna")]))
        hojas.append(("Formación", ["Institución", "Carrera", "Estado", "Sede", "Jornada", "Año que cursa", "Asignatura", "Horas comprometidas"], [
            (f.organizacion, f.carrera or "", f.get_estado_display(), f.sede_institucion or f.sede, f.get_jornada_display(), f.nivel_actual or "", f.asignatura, f.horas_comprometidas or "")
            for f in p.formaciones.select_related("organizacion", "carrera", "sede_institucion")]))
        hojas.append(("Comunidades", ["Comunidad", "Rol", "Desde", "Hasta", "Vigente"], [
            (m.comunidad, m.get_rol_display(), m.desde or "", m.hasta or "", "Sí" if m.vigente else "No") for m in p.comunidades.select_related("comunidad")]))
        hojas.append(("Consentimientos", ["Tipo", "Otorgado", "Fecha", "Medio", "Revocado el"], [
            (c.get_tipo_display(), "Sí" if c.otorgado else "No", c.fecha, c.get_medio_display(), c.revocado_en or "") for c in p.consentimientos.all()]))
        hojas.append(("Cargos", ["Organización", "Cargo", "Desde", "Hasta"], [(v.organizacion, v.cargo, v.fecha_inicio or "", v.fecha_termino or "") for v in p.vinculos.select_related("organizacion")]))
        hojas.append(("Participaciones", ["Actividad", "Rol", "Estado", "Asistencia"], [
            (x.actividad, x.rol, x.estado, {True: "Asistió", False: "No asistió", None: ""}[x.asistencia]) for x in p.participaciones.select_related("actividad", "rol", "estado")
        ]))
        si_no = {True: "Sí", False: "No", None: ""}
        fv = FichaVecino.objects.filter(persona=p).first()
        if fv:
            hogar = [("Jefatura de hogar", si_no[fv.jefatura_hogar]), ("Integrantes del hogar", fv.integrantes_hogar or ""), ("", "")]
            hogar.append(("Cantidad · parentesco · tramo · vive en el hogar", ""))
            hogar += [("", f"{i.cantidad} · {i.parentesco} · {i.tramo or 'sin tramo'} · {'sí' if i.vive_en_hogar else 'no'}")
                      for i in fv.integrantes.select_related("parentesco", "tramo")]
            familiares = [(v.familiar, v.parentesco) for v in p.familiares.select_related("familiar", "parentesco")]
            if familiares:
                hogar += [("", ""), ("Familiares vinculados", "Parentesco")] + familiares
            hojas.append(("Ficha de vecino", ["Campo", "Valor"], hogar))
        fi = FichaInvitado.objects.filter(persona=p).select_related("tipo", "invitado_por", "organizacion", "actividad").first()
        if fi:
            hojas.append(("Ficha de invitado", ["Campo", "Valor"], [
                ("Tipo de invitado", fi.tipo or ""), ("Invitado o invitada por", fi.invitado_por or ""), ("Organización de procedencia", fi.organizacion or ""),
                ("Cargo", fi.cargo), ("Motivo de la invitación", fi.motivo), ("Actividad", fi.actividad or ""),
            ]))
        fvol = FichaVoluntario.objects.filter(persona=p).select_related("estado").first()
        if fvol:
            hojas.append(("Ficha de voluntario", ["Campo", "Valor"], [
                ("Estado del voluntariado", fvol.estado or ""), ("Fecha de ingreso", f"{fvol.fecha_ingreso:%d-%m-%Y}" if fvol.fecha_ingreso else ""),
                ("Horas disponibles por semana", fvol.horas_semanales if fvol.horas_semanales is not None else ""), ("Motivación u observaciones", fvol.motivacion),
            ]))
        if request.user.has_perm("personas.ver_sensibles"):
            hojas.append(("Emergencia", ["Nombre", "Parentesco", "Teléfono"], [(c.nombre, c.parentesco, c.telefono) for c in p.contactos_emergencia.all()]))
            hojas.append(("Verificaciones", ["Tipo", "Fecha", "Vigente hasta"], [(v.tipo, v.fecha, v.vigente_hasta or "") for v in p.verificaciones.all()]))
            hojas.append(("Apoderados", ["Apoderado", "Parentesco", "Tutor legal"], [(a.apoderado, a.parentesco, "Sí" if a.tutor_legal else "No") for a in p.apoderados.select_related("apoderado")]))
            ps = getattr(p, "perfil_sensible", None)
            if ps:
                hojas.append(("Datos sensibles", ["Campo", "Valor"], [
                    ("Género", ps.get_genero_display()), ("Pueblo originario", ps.get_pueblo_originario_display()),
                    ("Discapacidad", {True: "Sí", False: "No", None: ""}[ps.discapacidad]), ("Necesidades de apoyo", ps.necesidades_apoyo),
                    ("Condiciones de salud", ps.condiciones_salud), ("Alergias", ps.alergias), ("Previsión", ps.get_prevision_salud_display()),
                    ("Jefatura de hogar", {True: "Sí", False: "No", None: ""}[ps.jefatura_hogar]), ("Integrantes del hogar", ps.integrantes_hogar or ""),
                    ("Tramo RSH", ps.get_tramo_rsh_display()),
                ]))
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
        from apps.nucleo.formularios import SelectorField

        return SelectorField(PERSONAS, filtros={"excluir": origen.pk}, crear=False, label="Ficha que se conserva")


class PersonaReasignar(Permiso403Mixin, View):
    """AT-E6: pasar las actividades en curso o futuras de un responsable a otra persona."""

    permission_required = "actividades.change_actividad"

    def _form(self, persona, data=None):
        from django import forms as f

        from apps.actividades.afectacion import a_cargo_de
        from apps.nucleo.formularios import BootstrapMixin, SelectorField

        class F(BootstrapMixin, f.Form):
            actividades = f.ModelMultipleChoiceField(a_cargo_de(persona), widget=f.CheckboxSelectMultiple, label="Actividades a reasignar")
            nuevo = SelectorField(PERSONAS, filtros={"equipo_primero": 1, "excluir": persona.pk}, crear=False, label="Nuevo responsable", help_text=AYUDA_RESPONSABLE)
            motivo = f.CharField(max_length=250)

        return F(data, initial={"actividades": list(a_cargo_de(persona))})

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
        messages.success(request, f"{plural(n, 'actividad reasignada', 'actividades reasignadas')} a {nuevo}.")
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


class DireccionPersonaEditar(DireccionPersonaNueva):
    """Corrige una dirección ya registrada (calle, número, comuna, sector o tipo). Si la persona se cambió de casa,
    lo correcto es agregar la nueva y dar de baja la anterior, para que quede la historia."""

    def dispatch(self, request, *a, **kw):
        self.registro = get_object_or_404(PersonaDireccion.objects.select_related("direccion"), pk=kw["hijo_pk"], persona_id=kw["pk"])
        return super().dispatch(request, *a, **kw)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["instance"] = self.registro.direccion
        kw.setdefault("initial", {})["tipo"] = self.registro.tipo
        return kw

    def get_context_data(self, **kw):
        ctx = super().get_context_data(**kw)
        ctx["titulo"] = "Editar dirección"
        return ctx

    def form_valid(self, form):
        form.save()
        self.registro.tipo = form.cleaned_data["tipo"]
        self.registro.save(update_fields=["tipo"])
        messages.success(self.request, "Dirección actualizada.")
        return HttpResponseRedirect(f"{self.persona.get_absolute_url()}?tab=direcciones")


class PersonaCrearRapida(Permiso403Mixin, View):
    """Ventana «+ Crear persona» de los buscadores: pide lo mínimo, avisa si ya existe alguien parecido
    («Usar esta persona» o «Es otra persona: crear» con qué la distingue) y deja a la persona elegida
    en el formulario de origen, sin salir de él."""

    permission_required = "personas.add_persona"
    plantilla = "generico/_crear_rapida.html"

    def _ctx(self, datos, form, **extra):
        return {
            "form": form, "campo_id": campo_seguro(datos.get("campo")), "filtros": PERSONAS.limpiar_filtros(datos), "accion": reverse("personas:crear_rapida"),
            "titulo": "Crear persona", "aviso_parecido": "Esta persona podría ya existir.", "texto_usar": "Usar esta persona",
            "texto_crear_igual": "Es otra persona: crear", "pide_nota": True, "por_secciones": True, **extra,
        }

    def get(self, request):
        from .forms import PersonaCrearRapidaForm, inicial_desde_texto

        form = PersonaCrearRapidaForm(prefix="rapida", initial=inicial_desde_texto(request.GET.get("q", "")[:150]))
        return render(request, self.plantilla, self._ctx(request.GET, form))

    def post(self, request):
        from django.db.models import prefetch_related_objects

        from .forms import PersonaCrearRapidaForm
        from .servicios import crear_persona_rapida

        form = PersonaCrearRapidaForm(request.POST, prefix="rapida")
        if not form.is_valid():  # 200: la ventana vuelve a dibujarse con los errores
            return render(request, self.plantilla, self._ctx(request.POST, form))
        d = form.cleaned_data
        nota = request.POST.get("nota_distincion", "").strip()[:200]
        confirmar = bool(request.POST.get("confirmar_duplicado"))
        if not (confirmar and nota):
            cands = candidatos_ficha_rapida(d)
            if cands:
                personas = [p for p, _ in cands]
                prefetch_related_objects(personas, "contactos")
                filtros = PERSONAS.limpiar_filtros(request.POST)
                elegibles = set(PERSONAS.base(**filtros).filter(pk__in=[p.pk for p in personas]).values_list("pk", flat=True))
                lista = [(p, razones, p.pk in elegibles) for p, razones in cands]
                return render(request, self.plantilla, self._ctx(request.POST, form, candidatos=lista, falta_nota=confirmar, nota=nota))
        persona = crear_persona_rapida(form, request.user, nota)
        return respuesta_elegido(request.POST.get("campo"), persona.pk, PERSONAS.texto(persona), "Persona creada y elegida. Completa su ficha cuando puedas.")


class PersonaOpciones(OpcionesVista):
    """Lista de personas para los buscadores de los formularios (ver apps/personas/selector.py)."""

    fuente = PERSONAS


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


class PersonaResumen(Permiso403Mixin, View):
    """F25 E5: resumen corto de una persona para el panel lateral de Participantes (fragmento HTML que se carga con HTMX).
    Sin JavaScript, el enlace del nombre lleva a la ficha completa. Número fijo de consultas."""

    permission_required = "personas.view_persona"

    def get(self, request, pk):
        from django.db.models import Prefetch
        from django.utils import timezone

        from .models import Contacto, PersonaFormacion, PersonaOrganizacion

        hoy = timezone.localdate()
        p = get_object_or_404(
            Persona.objects.select_related("estado_registro").prefetch_related(
                Prefetch("contactos", queryset=Contacto.objects.filter(vigente=True).select_related("tipo")),
                Prefetch("vinculos", queryset=PersonaOrganizacion.objects.filter(Q(fecha_termino__isnull=True) | Q(fecha_termino__gte=hoy))
                         .select_related("organizacion"), to_attr="vinculos_vigentes"),
                Prefetch("formaciones", queryset=PersonaFormacion.objects.filter(vigente=True).select_related("organizacion", "sede_institucion", "carrera"),
                         to_attr="formaciones_vigentes"),
            ),
            pk=pk,
        )
        u = request.user
        residencia = p.direcciones.filter(tipo="residencia", vigente=True).select_related("direccion__comuna").order_by("pk").first()
        comunidades = []
        if u.has_perm("comunidades.view_comunidadmiembro"):
            comunidades = list(p.comunidades.filter(vigente=True).select_related("comunidad"))
        participaciones = []
        if u.has_perm("actividades.view_participacion"):
            participaciones = list(p.participaciones.exclude(estado__codigo="registro_erroneo")
                                   .select_related("actividad__proyecto", "rol").order_by("-fecha", "-pk")[:5])
        return render(request, "personas/_resumen.html", {
            "persona": p,
            "contactos": [c for c in p.contactos.all() if c.principal] or list(p.contactos.all())[:2],
            "comuna_residencia": residencia.direccion.comuna if residencia else None,
            "comunidades": comunidades,
            "participaciones": participaciones,
            "puede_editar": u.has_perm("personas.change_persona"),
        })

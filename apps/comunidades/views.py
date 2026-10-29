"""Pantallas de comunidades: listado con filtros, crear (con la comuna ya elegida si viene del territorio),
ficha con integrantes, actividades y alcance, desactivar sin borrar y exportar."""
from django.db import transaction
from django.db.models import Count, Q
from django.urls import reverse

from apps.nucleo.direccion_mixin import ComunaInicialMixin
from apps.nucleo.selector import OpcionesVista
from apps.nucleo.vistas_base import (
    AvisoDuplicadosMixin, AlternarActivoBase, CrearBase, EditarBase, FichaBase, Filtro, ListaBase, filtro_activo, nombre_comuna, opciones_comunas,
)

from .forms import ComunidadForm
from .models import Comunidad
from .selector import COMUNIDADES
from .servicios import asegurar_referente, referente_del_padron


class ComunidadLista(ListaBase):
    model = Comunidad
    permission_required = "comunidades.view_comunidad"
    titulo = "Comunidades"
    descripcion = "Grupos de personas de un sector o espacio a quienes van dirigidas las actividades: su padrón, diagnóstico y alcance."
    campos_busqueda = ("nombre", "descripcion", "comuna__nombre", "sector__nombre", "organizacion__nombre")
    columnas = [
        ("Comunidad", "nombre"), ("Tipo", "get_tipo_display"), ("Territorio", "territorio"), ("Organización", lambda c: c.organizacion or "—"),
        ("Integrantes", lambda c: c.n_miembros), ("Actividades", lambda c: c.n_actividades), ("Estado", lambda c: "Activa" if c.activo else "Inactiva"),
    ]
    orden_defecto = ("nombre",)
    filtros = [
        Filtro("tipo", "Tipo", "tipo", lambda: list(Comunidad.TIPOS), principal=True),
        Filtro("comuna", "Comuna", "comuna_id", lambda: opciones_comunas(Q(pk__in=Comunidad.objects.values("comuna_id"))), principal=True, todos="Todas",
               etiqueta_de=nombre_comuna),
        filtro_activo(femenino=True),
    ]
    url_crear = "/comunidades/nueva"
    permiso_crear = "comunidades.add_comunidad"
    etiqueta_crear = "+ Nueva comunidad"
    url_exportar = "/comunidades/exportar"
    permiso_exportar = "comunidades.exportar_comunidad"
    texto_vacio = "Aún no hay comunidades registradas."

    def get_queryset(self):
        return super().get_queryset().select_related("comuna", "sector", "organizacion").annotate(
            n_miembros=Count("miembros", filter=Q(miembros__vigente=True), distinct=True),
            n_actividades=Count("actividades_dirigidas", filter=Q(actividades_dirigidas__vigente=True), distinct=True),
        )


class ComunidadExportar(ComunidadLista):
    exportar = True
    permission_required = "comunidades.exportar_comunidad"


class ComunidadNueva(AvisoDuplicadosMixin, ComunaInicialMixin, CrearBase):
    model = Comunidad
    form_class = ComunidadForm
    permission_required = "comunidades.add_comunidad"
    titulo = "Nueva comunidad"
    breadcrumb = [("Comunidades", "/comunidades")]
    mensaje_ok = "Comunidad registrada. Agrega a sus integrantes desde la pestaña «Integrantes»."

    def form_valid(self, form):
        from apps.nucleo.duplicados import comunidades_parecidas

        d = form.cleaned_data
        aviso = self.aviso_duplicados(form, lambda: comunidades_parecidas(d.get("nombre"), d.get("comuna"), d.get("sector")),
                                      "Esta comunidad podría ya estar registrada.")
        if aviso:
            return aviso
        with transaction.atomic():
            respuesta = super().form_valid(form)
            asegurar_referente(self.object)  # F26 P2: el referente queda en su padrón
        return respuesta

    def get_initial(self):
        ini = super().get_initial()
        if self.request.GET.get("comuna", "").isdigit():
            ini["comuna"] = self.request.GET["comuna"]
        sector = self.sector_inicial()  # desde la ficha de un sector: parte con ese sector elegido
        if sector:
            ini["sector"] = sector.pk
        return ini


class ComunidadEditar(EditarBase):
    model = Comunidad
    form_class = ComunidadForm
    permission_required = "comunidades.change_comunidad"
    titulo = "Editar comunidad"
    breadcrumb = [("Comunidades", "/comunidades")]

    def form_valid(self, form):
        with transaction.atomic():
            respuesta = super().form_valid(form)
            if respuesta.status_code == 302:  # guardado (sin conflicto de versión)
                asegurar_referente(self.object)  # F26 P2: el referente queda en su padrón
        return respuesta


class ComunidadAlternar(AlternarActivoBase):
    modelo = Comunidad
    permission_required = "comunidades.change_comunidad"


class ComunidadOpciones(OpcionesVista):
    """Lista de comunidades para los buscadores (ver apps/comunidades/selector.py)."""

    fuente = COMUNIDADES


class ComunidadFicha(FichaBase):
    model = Comunidad
    template_name = "comunidades/ficha.html"
    permission_required = "comunidades.view_comunidad"
    breadcrumb = [("Comunidades", "/comunidades")]
    permiso_editar = "comunidades.change_comunidad"
    pestanas = [
        ("info", "Información", "comunidades/pestanas/info.html"),
        ("integrantes", "Integrantes", "generico/_hijos.html", "comunidades.view_comunidadmiembro"),
        ("actividades", "Actividades y proyectos", "comunidades/pestanas/actividades.html", "actividades.view_actividad"),
        ("alcance", "Alcance", "actividades/pestanas/alcance.html", "actividades.view_participacion"),
        ("historial", "Historial", "generico/_historial.html", "comunidades.view_historicalcomunidad"),
    ]

    def get_queryset(self):
        return super().get_queryset().select_related("comuna__provincia__region", "sector", "organizacion", "referente")

    def contexto_ficha(self):
        c = self.object
        return {
            "url_editar": reverse("comunidades:editar", args=[c.pk]),
            "url_volver": "/comunidades",
            "puede_agregar": self.request.user.has_perm("comunidades.change_comunidad"),
            "n_integrantes": self.n_integrantes(),
            # F26 P2: si el campo está vacío, el referente (o dirigente) de su padrón
            "referente_mostrado": self.referente_mostrado(),
        }

    def n_integrantes(self):
        if not hasattr(self, "_n_integrantes"):
            self._n_integrantes = self.object.miembros.filter(vigente=True).count()
        return self._n_integrantes

    def referente_mostrado(self):
        if not hasattr(self, "_referente"):
            self._referente = self.object.referente or referente_del_padron(self.object)
        return self._referente

    def ctx_info(self):
        """F26 Ia: los datos vacíos se cuentan aparte («Sin completar (N)»), como en la persona. Tramos y áreas: una consulta cada uno."""
        c = self.object
        tramos, areas = list(c.tramos_etarios.all()), list(c.areas_interes.all())
        campos = [
            ("Sector", c.sector_id), ("Organización que la representa", c.organizacion_id),
            ("Referente o dirigente", self.referente_mostrado()), ("Población estimada", c.poblacion_estimada),
            ("Edades principales", tramos or c.rango_etario), ("Áreas de interés", areas), ("Descripción", c.descripcion),
            ("Diagnóstico y necesidades", c.diagnostico),
        ]
        return {"tramos_info": tramos, "areas_info": areas, "datos_vacios": [e for e, v in campos if not v], "vistazo": self.vistazo()}

    def vistazo(self):
        """F26 Ib: integrantes vigentes (de su población estimada), referente y la última y la próxima actividad dirigida a
        ella o con participantes de ella. El referente y la población ya no se repiten en los datos de abajo. Consultas fijas."""
        from apps.actividades.models import ActividadComunidad, Participacion
        from apps.nucleo.vistazo import cuantas, fila, filas_ultima_y_proxima, item

        c, u = self.object, self.request.user
        n = self.n_integrantes()
        cifra = cuantas(n, "integrante vigente", "integrantes vigentes")
        if c.poblacion_estimada:
            cifra += f" de ~{c.poblacion_estimada} (población estimada)"
        ver_padron = u.has_perm("comunidades.view_comunidadmiembro")
        filas = [fila("Integrantes", [], cifra=cifra, pie=("Ver integrantes", "?tab=integrantes") if ver_padron and n else None)]
        ref = self.referente_mostrado()
        filas.append(fila("Referente o dirigente", [item((ref, ref.get_absolute_url()), nota="según su padrón" if not c.referente_id else "")] if ref else [],
                          "Sin referente registrado"))
        if u.has_perm("actividades.view_actividad"):
            filas += filas_ultima_y_proxima(
                Q(actividad_id__in=ActividadComunidad.objects.filter(comunidad=c, vigente=True).values("actividad_id"))
                | Q(actividad_id__in=Participacion.objects.filter(comunidad=c).values("actividad_id")))
        return filas

    def ctx_integrantes(self):
        pk = self.object.pk
        hijos = [{
            "texto": str(m.persona), "url": m.persona.get_absolute_url(), "badge": m.get_rol_display() if m.rol != "integrante" else "",
            "detalle": " · ".join(x for x in [f"desde {m.desde:%d-%m-%Y}" if m.desde else "", f"hasta {m.hasta:%d-%m-%Y}" if m.hasta else "", m.observaciones] if x),
            "vigente": m.vigente, "url_editar": reverse("comunidades:integrantes_editar", args=[pk, m.pk]), "url_alternar": reverse("comunidades:integrantes_alternar", args=[pk, m.pk]),
        } for m in self.object.miembros.select_related("persona")]
        return {"titulo_pestana": "Integrantes", "etiqueta_nuevo": "Integrante", "url_nuevo": reverse("comunidades:integrantes_nuevo", args=[pk]), "hijos": hijos,
                "vacio": "Aún no hay integrantes registrados. Agrega a los vecinos y vecinas que participan, o cárgalos desde una planilla.",
                "puede_agregar": self.request.user.has_perm("comunidades.add_comunidadmiembro")}

    def ctx_actividades(self):
        c = self.object
        return {
            "dirigidas": c.actividades_dirigidas.filter(vigente=True).select_related("actividad__estado", "actividad__tipo").order_by("-actividad__creado_en"),
            "proyectos": c.proyectos_dirigidos.filter(vigente=True).select_related("proyecto"),
        }

    def ctx_alcance(self):
        from apps.actividades.alcance import alcance
        from apps.actividades.models import Actividad

        actividades = Actividad.objects.filter(Q(comunidades_destino__comunidad=self.object, comunidades_destino__vigente=True) | Q(participaciones__comunidad=self.object)).distinct()
        return {"alcance": alcance(actividades), "contexto_alcance": "las actividades dirigidas a esta comunidad"}

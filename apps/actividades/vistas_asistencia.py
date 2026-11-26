"""F28 · Pantallas de la asistencia por jornada (specs/f28/spec.md, puntos 2 a 4): el panel de «Equipo y asistencia»
(matriz personas × jornadas y «Pasar lista» de la jornada elegida), las acciones de la lista (guardar, marcar el resto
como ausente, cerrar, reabrir, suspender, incluir a quien se digitó tarde, conteo sin nombres), «+ Nueva jornada»,
«Quitar de la tarea» y «Reincorporar», y el Excel de la matriz.

Todo funciona sin JavaScript (formularios normales). Cada envío lleva la marca de envío único (F26 Ra) y la lista lleva
su versión: un doble clic guarda una vez y otra pestaña con la lista vieja recibe el aviso de que cambió."""
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from apps.nucleo.auditoria import registrar
from apps.nucleo.utilidades import plural
from apps.nucleo.vistas_base import Permiso403Mixin

from . import asistencia
from .forms import JornadaForm, RetiroForm
from .models import Actividad, CambioLista, Participacion
from .reglas import ReglaNegocio

FILTROS_GRUPO = [("", "Todos"), ("ejecutor", "Equipo ejecutor"), ("contacto", "Invitados y contactos"), ("asistente", "Beneficiarios")]


def url_gasto_de_jornada(jornada, usuario=None):
    """F28 B: la dirección de «¿Hubo gastos este día?» de una jornada guardada (el registro de gasto con la jornada elegida).
    Sin permiso para registrar gastos, no se muestra."""
    if jornada is None or not jornada.pk or (usuario is not None and not usuario.has_perm("finanzas.add_movimiento")):
        return None
    return f"{reverse('finanzas:gasto_nuevo', args=[jornada.actividad_id])}?jornada={jornada.pk}"


def url_lista(actividad, jornada=None):
    jid = (jornada.pk if jornada is not None and jornada.pk else "programada") if jornada is not None else None
    base = f"{actividad.get_absolute_url()}?tab=participantes"
    return f"{base}&jornada={jid}#pasar-lista" if jid else f"{base}#pasar-lista"


def ruta_jornada(jornada):
    """Segmento de la dirección: el número de la jornada guardada, o «programada»."""
    return str(jornada.pk) if jornada.pk else "programada"


def contexto_asistencia(request, actividad, partes):
    """Contexto del panel de asistencia de «Equipo y asistencia». `partes`: las participaciones no erróneas ya leídas
    (con persona, rol y estado). Consultas fijas: jornadas, marcas y, de la jornada elegida, sus cambios de lista."""
    u = request.user
    js = asistencia.jornadas(actividad)
    grupo = request.GET.get("grupo", "")
    grupo = grupo if grupo in dict(FILTROS_GRUPO) else ""
    mat = asistencia.matriz(actividad, grupo, partes=partes, js=js)
    elegida = asistencia.elegir_jornada(js, request.GET.get("jornada"))
    columna = next((c for c in mat["columnas"] if c["jornada"] is elegida), None)
    puede, motivo = asistencia.puede_pasar_lista(actividad, elegida)
    puede_marcar = u.has_perm("actividades.change_participacion")
    despues = []
    if elegida is not None and elegida.fecha:
        ids_lista = columna["personas"] if columna else set()
        despues = [p for p in partes if p.persona_id not in ids_lista and p.activa and p.inscrito_en and p.inscrito_en > elegida.fecha]
    cambios = list(CambioLista.objects.filter(sesion=elegida).select_related("usuario")[:5]) if elegida is not None and elegida.pk else []
    return {
        "jornadas": js, "matriz": mat, "filtros_grupo": FILTROS_GRUPO, "grupo_matriz": grupo,
        "jornada": elegida, "lista_jornada": columna["lista"] if columna else [], "columna_elegida": columna,
        "ruta_jornada": ruta_jornada(elegida) if elegida is not None else "",
        "marcas_opciones": asistencia.MARCAS, "puede_pasar_lista": puede and puede_marcar, "motivo_sin_lista": motivo,
        "puede_marcar": puede_marcar,
        "puede_suspender": puede_marcar and elegida is not None and elegida.lista_abierta and actividad.estado.codigo in ("planificada", "confirmada", "reprogramada"),
        "puede_nueva_jornada": u.has_perm("actividades.add_sesionactividad") and actividad.estado.codigo not in ("cancelada", "realizada"),
        "puede_exportar_asistencia": u.has_perm("actividades.exportar_actividad"),
        "inscritas_despues": despues, "cambios_lista": cambios,
        "url_gasto_jornada": url_gasto_de_jornada(elegida, u) if elegida is not None else None,
        "url_llego": (_url_llego(actividad, elegida) if elegida is not None and u.has_perm("actividades.add_participacion") else None),
    }


def _url_llego(actividad, jornada):
    from .views import url_agregar_persona

    return url_agregar_persona(actividad, llego=True, volver=None) + f"&jornada={ruta_jornada(jornada)}"


class _Jornada(Permiso403Mixin, View):
    permission_required = "actividades.change_participacion"

    def dispatch(self, request, *a, **kw):
        self.actividad = get_object_or_404(Actividad.objects.select_related("estado", "proyecto"), pk=kw["pk"])
        return super().dispatch(request, *a, **kw)

    def jornada(self, jid):
        js = asistencia.jornadas(self.actividad)
        if jid == "programada":
            j = next((j for j in js if not j.pk), None)
        elif jid == "hoy":
            j = asistencia.jornada_para_marcar(self.actividad, js)
        elif str(jid).isdigit():
            j = next((j for j in js if j.pk == int(jid)), None)
        else:
            j = None
        if j is None:
            raise Http404("Jornada no encontrada.")
        return j

    def volver(self, jornada=None):
        return HttpResponseRedirect(url_lista(self.actividad, jornada))


class ListaGuardar(_Jornada):
    """«Guardar lista», «Marcar el resto como ausente» (accion=resto) y «Cerrar lista» (accion=cerrar)."""

    def post(self, request, pk, jid):
        j = self.jornada(jid)
        accion = request.POST.get("accion", "guardar")
        valores = {}
        for pid in request.POST.getlist("en_lista"):
            if pid.isdigit():
                valores[int(pid)] = (request.POST.get(f"marca_{pid}", ""), request.POST.get(f"obs_{pid}", ""))
        try:
            res = asistencia.guardar_lista(self.actividad, j, request.user, valores, version=request.POST.get("_version"),
                                           resto_ausente=accion == "resto", cerrar=accion == "cerrar")
        except ReglaNegocio as e:
            for m in e.mensajes:
                messages.error(request, m)
            return self.volver(j)
        if res.cerrada:
            messages.success(request, f"Lista de la {res.jornada.nombre_jornada.lower()} guardada y cerrada.")
        elif accion == "cerrar":
            messages.success(request, f"Lista guardada ({plural(res.cambios, 'cambio', 'cambios')}).")
            messages.error(request, asistencia.texto_sin_marcar(res.sin_marcar))
        else:
            messages.success(request, f"Lista guardada ({plural(res.cambios, 'cambio', 'cambios')})."
                             + (f" Quedan {len(res.sin_marcar)} sin marcar." if res.sin_marcar else ""))
        return self.volver(res.jornada)


class ListaReabrir(_Jornada):
    def post(self, request, pk, jid):
        j = self.jornada(jid)
        try:
            j = asistencia.reabrir_lista(self.actividad, j, request.user, request.POST.get("motivo", ""))
        except ReglaNegocio as e:
            for m in e.mensajes:
                messages.error(request, m)
        else:
            messages.success(request, f"Lista de la {j.nombre_jornada.lower()} reabierta. Corrígela y vuelve a cerrarla.")
        return self.volver(j)


class JornadaSuspender(_Jornada):
    def post(self, request, pk, jid):
        j = self.jornada(jid)
        try:
            j = asistencia.suspender_jornada(self.actividad, j, request.user, request.POST.get("motivo", ""))
        except ReglaNegocio as e:
            for m in e.mensajes:
                messages.error(request, m)
        else:
            messages.success(request, f"{j.nombre_jornada} suspendida: no tiene lista y no cuenta para el porcentaje.")
        return self.volver(j)


class ListaIncluir(_Jornada):
    """Quienes se inscribieron después de la jornada (p. ej. se digitaron tarde) quedan inscritas desde su fecha."""

    def post(self, request, pk, jid):
        j = self.jornada(jid)
        ids = [int(x) for x in request.POST.getlist("incluir") if x.isdigit()]
        if not ids:
            messages.error(request, "Marca a quiénes incluir en esta lista.")
            return self.volver(j)
        try:
            n, j = asistencia.incluir_desde(self.actividad, j, request.user, ids)
        except ReglaNegocio as e:
            for m in e.mensajes:
                messages.error(request, m)
            return self.volver(j)
        messages.success(request, f"{plural(n, 'persona incluida', 'personas incluidas')} desde esta jornada.")
        return self.volver(j)


class JornadaConteo(_Jornada):
    """«Registrar conteo sin nombres»: guarda la jornada (si es la programada) y abre su formulario, en la sección del conteo."""

    permission_required = "actividades.change_sesionactividad"

    def post(self, request, pk, jid):
        j = asistencia.guardar_jornada_programada(self.actividad, self.jornada(jid))
        return HttpResponseRedirect(reverse("actividades:sesiones_editar", args=[self.actividad.pk, j.pk]))


class JornadaNueva(Permiso403Mixin, View):
    """«+ Nueva jornada»: otro día o bloque de la tarea (fecha, horas y lugar)."""

    permission_required = "actividades.add_sesionactividad"
    template_name = "generico/formulario.html"

    def _ctx(self, a, form):
        url = a.get_absolute_url()
        return {"form": form, "titulo": "Nueva jornada", "volver_url": f"{url}?tab=participantes#asistencia",
                "breadcrumb": [(a.nombre, url), ("Equipo y asistencia", f"{url}?tab=participantes")],
                "bajada": f"Otro día o bloque de «{a.nombre}» (por ejemplo, la tarde del mismo día). Cada jornada tiene su propia lista."}

    def _actividad(self, pk):
        return get_object_or_404(Actividad.objects.select_related("estado", "proyecto"), pk=pk)

    def get(self, request, pk):
        a = self._actividad(pk)
        ag = a.agenda_vigente
        inicial = {"hora_inicio": ag.hora_inicio, "hora_fin": ag.hora_fin, "lugar": ag.lugar_id} if ag else {}
        return render(request, self.template_name, self._ctx(a, JornadaForm(initial=inicial)))

    def post(self, request, pk):
        a = self._actividad(pk)
        form = JornadaForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            try:
                j = asistencia.nueva_jornada(a, request.user, d["fecha"], d.get("hora_inicio"), d.get("hora_fin"), d.get("lugar"), d.get("nombre", ""))
            except ReglaNegocio as e:
                for m in e.mensajes:
                    form.add_error(None, m)
            else:
                messages.success(request, f"{j.nombre_jornada} agregada ({j.fecha:%d-%m-%Y}).")
                return HttpResponseRedirect(url_lista(a, j))
        return render(request, self.template_name, self._ctx(a, form), status=400)


class _Inscripcion(Permiso403Mixin, View):
    permission_required = "actividades.change_participacion"

    def participacion(self, pk, part_pk):
        return get_object_or_404(Participacion.objects.select_related("persona", "actividad__estado", "actividad__proyecto", "estado", "rol"),
                                 pk=part_pk, actividad_id=pk)

    def volver(self, p):
        from .views import _pestana_de

        return HttpResponseRedirect(f"{p.actividad.get_absolute_url()}?tab={_pestana_de(p.actividad, p)}")


class ParticipanteRetirar(_Inscripcion):
    """«Quitar de la tarea»: queda «Retirado», con fecha y motivo; conserva sus asistencias."""

    def _ctx(self, p, form):
        a = p.actividad
        que = "la tarea" if a.proyecto_id else "la actividad"
        return {"form": form, "titulo": f"Quitar a {p.persona} de {que}", "volver_url": f"{a.get_absolute_url()}?tab=participantes",
                "breadcrumb": [(a.nombre, a.get_absolute_url())],
                "bajada": (f"{p.persona} ({p.rol_y_cargo}) queda «Retirado»: conserva sus asistencias y no aparece en las listas desde el día "
                           f"siguiente al retiro. Si se relacionó por error, usa «Registro erróneo». «Reincorporar» deshace un retiro.")}

    def get(self, request, pk, part_pk):
        p = self.participacion(pk, part_pk)
        return render(request, "generico/formulario.html", self._ctx(p, RetiroForm(initial={"fecha": timezone.localdate()})))

    def post(self, request, pk, part_pk):
        p = self.participacion(pk, part_pk)
        form = RetiroForm(request.POST)
        if form.is_valid():
            try:
                asistencia.retirar(p, request.user, form.cleaned_data["motivo"], form.cleaned_data["fecha"])
            except ReglaNegocio as e:
                for m in e.mensajes:
                    form.add_error(None, m)
            else:
                messages.success(request, f"{p.persona} quedó retirada ({p.rol}). Conserva sus asistencias.")
                return self.volver(p)
        return render(request, "generico/formulario.html", self._ctx(p, form), status=400)


class ParticipanteReincorporar(_Inscripcion):
    def post(self, request, pk, part_pk):
        p = self.participacion(pk, part_pk)
        try:
            asistencia.reincorporar(p, request.user)
        except ReglaNegocio as e:
            for m in e.mensajes:
                messages.error(request, m)
        else:
            messages.success(request, f"{p.persona} reincorporada: vuelve a aparecer en las listas.")
        return self.volver(p)


class AsistenciaExportar(Permiso403Mixin, View):
    """Excel de la matriz de asistencia (con permiso de exportar). Sin `personas.exportar_persona`, los menores de edad
    no se nombran: se cuentan al final (igual que el informe del proyecto) [V#2]."""

    permission_required = ("actividades.exportar_actividad", "actividades.view_participacion")

    def get(self, request, pk):
        from apps.nucleo.exportacion import _seguro, agregar_aviso
        from io import BytesIO

        from django.http import HttpResponse
        from django.utils.text import slugify
        from openpyxl import Workbook

        a = get_object_or_404(Actividad.objects.select_related("estado"), pk=pk)
        mat = asistencia.matriz(a)
        con_menores = request.user.has_perm("personas.exportar_persona")
        libro = Workbook()
        hoja = libro.active
        hoja.title = "Asistencia"
        cabecera = ["Persona", "Rol"] + [f"{c['jornada'].nombre_jornada} {c['jornada'].fecha:%d-%m-%Y}" if c["jornada"].fecha else c["jornada"].nombre_jornada
                                         for c in mat["columnas"]] + ["Días presentes", "% asistencia"]
        hoja.append([_seguro(x) for x in cabecera])
        menores = 0
        for f in mat["filas"]:
            if f["persona"].es_menor and not con_menores:
                menores += 1
                continue
            celdas = [c["nombre"] if c["marca"] else ("" if c["en_lista"] else "—") for c in f["celdas"]]
            r = f["resumen"]
            hoja.append([_seguro(x) for x in [f["persona"].nombre_completo, f["roles"], *celdas, r["presentes"],
                                              f"{r['porcentaje']} %" if r["porcentaje"] is not None else ""]])
        pie = ["Presentes / inscritos", ""] + [f"{c['presentes']} / {c['inscritos']}" + (" (suspendida)" if c["jornada"].suspendida else "")
                                              for c in mat["columnas"]]
        hoja.append([_seguro(x) for x in pie])
        if menores:
            hoja.append([f"Menores de edad en la lista: {menores} (no se nombran por protección de datos; pendiente V#2)"])
        agregar_aviso(libro, request.user)
        buffer = BytesIO()
        libro.save(buffer)
        registrar(request.user, "exportacion", a, f"Matriz de asistencia: {len(mat['filas'])} personas, {len(mat['columnas'])} jornadas")
        r = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        r["Content-Disposition"] = f'attachment; filename="asistencia_{slugify(a.nombre)[:60]}_{timezone.localdate():%Y-%m-%d}.xlsx"'
        return r


def legado_valores(actividad, jornada, valores_participacion):
    """Las rutas de antes (por participación: asistió sí / no / vacío) traducidas a marcas por persona de la jornada.
    Devuelve ({persona_id: (marca, None)}, [personas que llegaron sin estar en la lista ese día])."""
    partes = {p.pk: p for p in asistencia.participaciones(actividad)}
    valores, llegaron = {}, []
    for pid, v in valores_participacion.items():
        p = partes.get(pid)
        if p is None:
            continue
        if not p.en_lista_de(jornada.fecha):
            if v is True:
                llegaron.append(p.persona)
            continue
        valores[p.persona_id] = ({True: asistencia.M.PRESENTE, False: asistencia.M.AUSENTE}.get(v, ""), None)
    return valores, llegaron

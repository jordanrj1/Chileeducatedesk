"""Qué actividades se ofrecen en los buscadores de los formularios y cómo se muestran (nombre, estado y fecha).
Algunos campos ofrecen solo las actividades principales (no las charlas de una jornada) o solo las que siguen abiertas."""
from django.db.models import Prefetch

from apps.nucleo.selector import Fuente, pk_seguro

from .models import Actividad, AgendaActividad


class Actividades(Fuente):
    modelo = Actividad
    permiso_ver = "actividades.view_actividad"
    url_opciones = "actividades:opciones"
    placeholder = "Escribe el nombre de la actividad…"
    texto_vacio = "Aún no hay actividades registradas."
    filtros_permitidos = ("raiz", "abiertas", "excluir", "tareas")

    def base(self, raiz="", abiertas="", excluir="", tareas="", **_):
        qs = Actividad.objects.all()
        if tareas == "1":  # solo las tareas de proyectos (actividades con proyecto)
            qs = qs.filter(proyecto__isnull=False)
        if raiz == "1":
            qs = qs.filter(actividad_padre__isnull=True)
        if abiertas == "1":
            qs = qs.exclude(estado__codigo__in=["cancelada", "realizada"])
        pk = pk_seguro(excluir)
        if pk:
            qs = qs.exclude(pk=pk)
        return qs

    def buscar(self, qs, q):
        for palabra in q.split():
            qs = qs.filter(nombre__unaccent__icontains=palabra)
        return qs

    def ordenar(self, qs):
        return qs.order_by("-creado_en", "-pk")  # las más recientes primero

    def con_relaciones(self, qs):
        vigente = AgendaActividad.objects.filter(vigente=True)
        return qs.select_related("estado").prefetch_related(Prefetch("agendas", queryset=vigente, to_attr="agenda_vigente_sel"))

    def texto(self, a):
        return a.nombre

    def detalle(self, a):
        partes = [a.estado.nombre]
        agenda = next(iter(getattr(a, "agenda_vigente_sel", None) or []), None)
        if agenda is not None:
            partes.append(f"{agenda.fecha:%d-%m-%Y}")
        return " · ".join(partes)

    def marca(self, a):
        return f"({a.estado.nombre.lower()})"


ACTIVIDADES = Actividades()

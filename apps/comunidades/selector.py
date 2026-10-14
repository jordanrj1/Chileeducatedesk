"""Qué comunidades se ofrecen en los buscadores de los formularios y cómo se muestran (nombre y territorio)."""
from django.db.models import Q

from apps.nucleo.selector import Fuente, pk_seguro

from .models import Comunidad


class Comunidades(Fuente):
    modelo = Comunidad
    permiso_ver = "comunidades.view_comunidad"
    url_opciones = "comunidades:opciones"
    placeholder = "Escribe el nombre de la comunidad o su comuna…"
    texto_vacio = "Aún no hay comunidades registradas."
    filtros_permitidos = ("excluir",)

    def base(self, excluir="", **_):
        qs = Comunidad.objects.filter(activo=True)
        pk = pk_seguro(excluir)
        return qs.exclude(pk=pk) if pk else qs

    def buscar(self, qs, q):
        for palabra in q.split():
            qs = qs.filter(Q(nombre__unaccent__icontains=palabra) | Q(comuna__nombre__unaccent__icontains=palabra))
        return qs

    def ordenar(self, qs):
        return qs.order_by("nombre", "pk")

    def con_relaciones(self, qs):
        return qs.select_related("comuna", "sector__sector_padre")

    def texto(self, c):
        return c.nombre

    def detalle(self, c):
        return c.territorio


COMUNIDADES = Comunidades()

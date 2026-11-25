"""F27: qué lugares se ofrecen en los buscadores de los formularios y cómo se muestran (nombre, tipo, comuna y capacidad,
para distinguir lugares con el mismo nombre)."""
from django.db.models import Q

from apps.nucleo.selector import Fuente, pk_seguro

from .models import Lugar


class Lugares(Fuente):
    modelo = Lugar
    permiso_ver = "lugares.view_lugar"
    url_opciones = "lugares:opciones"
    url_crear = "lugares:crear_desde_buscador"
    permiso_crear = "lugares.add_lugar"
    etiqueta_crear = "lugar"
    placeholder = "Escribe el nombre del lugar o su comuna…"
    texto_vacio = "Aún no hay lugares registrados."
    filtros_permitidos = ("excluir",)

    def base(self, excluir="", **_):
        qs = Lugar.objects.filter(activo=True)
        pk = pk_seguro(excluir)
        return qs.exclude(pk=pk) if pk else qs

    def buscar(self, qs, q):
        for palabra in q.split():
            qs = qs.filter(Q(nombre__unaccent__icontains=palabra) | Q(direccion__comuna__nombre__unaccent__icontains=palabra))
        return qs

    def ordenar(self, qs):
        return qs.order_by("nombre", "pk")

    def con_relaciones(self, qs):
        return qs.select_related("tipo", "direccion__comuna")

    def texto(self, l):
        return l.nombre

    def detalle(self, l):
        partes = [l.tipo.nombre, l.direccion.comuna.nombre if l.direccion_id and l.direccion.comuna_id else ""]
        partes.append(f"capacidad {l.capacidad}" if l.capacidad else "")
        return " · ".join(p for p in partes if p)


LUGARES = Lugares()

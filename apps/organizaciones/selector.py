"""Qué organizaciones se ofrecen en los buscadores de los formularios y cómo se muestran (nombre, tipo y comuna).
Un campo puede limitarse a un tipo (por ejemplo, solo instituciones educativas) y la lista ofrece solo ese tipo."""
from django.db.models import Q

from apps.nucleo.selector import Fuente, pk_seguro

from .models import Organizacion


class Organizaciones(Fuente):
    modelo = Organizacion
    permiso_ver = "organizaciones.view_organizacion"
    url_opciones = "organizaciones:opciones"
    url_crear = "organizaciones:crear_rapida"
    permiso_crear = "organizaciones.add_organizacion"
    etiqueta_crear = "organización"
    placeholder = "Escribe el nombre de la organización…"
    texto_vacio = "Aún no hay organizaciones registradas."
    filtros_permitidos = ("tipo", "excluir")

    def base(self, tipo="", excluir="", **_):
        qs = Organizacion.objects.filter(activo=True)
        if tipo:
            qs = qs.filter(tipo__codigo=tipo)
        pk = pk_seguro(excluir)
        if pk:
            qs = qs.exclude(pk=pk)
        return qs

    def buscar(self, qs, q):
        for palabra in q.split():
            qs = qs.filter(Q(nombre__unaccent__icontains=palabra) | Q(otro_identificador__unaccent__icontains=palabra))
        return qs

    def ordenar(self, qs):
        return qs.order_by("nombre", "pk")

    def con_relaciones(self, qs):
        return qs.select_related("tipo", "direccion__comuna")

    def texto(self, o):
        return o.nombre

    def detalle(self, o):
        partes = [o.tipo.nombre]
        if o.direccion_id and o.direccion.comuna_id:
            partes.append(o.direccion.comuna.nombre)
        return " · ".join(partes)


ORGANIZACIONES = Organizaciones()

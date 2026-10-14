"""Buscar antes de crear una organización: encuentra las que tienen el mismo RUT o un nombre parecido.
Solo muestra las coincidencias; Claudio decide si usa la existente o crea de todos modos.
Lo usan el formulario de organización y la ventana «+ Crear organización» de los buscadores."""
from .models import Organizacion


def organizaciones_parecidas(nombre, rut=None, excluir=None):
    """[(organización, [razones])]: mismo RUT o nombre parecido (pg_trgm)."""
    from django.contrib.postgres.search import TrigramSimilarity

    encontradas = {}
    if rut:
        for o in Organizacion.objects.filter(rut_numero=rut[0]).select_related("tipo"):
            encontradas[o.pk] = (o, ["mismo RUT"])
    if nombre:
        for o in Organizacion.objects.annotate(sim=TrigramSimilarity("nombre", nombre)).filter(sim__gte=0.45).select_related("tipo").order_by("-sim")[:10]:
            encontradas.setdefault(o.pk, (o, []))[1].append(f"nombre parecido ({int(o.sim * 100)}%)")
    return [v for k, v in encontradas.items() if k != excluir]

"""Buscar antes de crear (RNF-16). Muestra coincidencias; nunca fusiona ni bloquea sola."""
from django.contrib.postgres.lookups import Unaccent
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Value
from django.db.models.functions import Concat

from apps.nucleo.utilidades import normalizar_telefono

from .models import Contacto, Persona

UMBRAL_NOMBRE = 0.45


def candidatos(nombres="", apellido_paterno="", apellido_materno="", rut_numero=None, correo="", telefono="", excluir=None, documento=None):
    """[(persona, [razones])] ordenado por fuerza de la coincidencia."""
    encontrados = {}

    def marcar(persona, razon, peso):
        entrada = encontrados.setdefault(persona.pk, [persona, [], 0])
        entrada[1].append(razon)
        entrada[2] += peso

    if rut_numero:
        for p in Persona.objects.filter(rut_numero=rut_numero):
            marcar(p, "mismo RUT", 100)
    if documento and documento[1]:
        for p in Persona.objects.filter(tipo_documento=documento[0], numero_documento=documento[1].strip().upper()):
            marcar(p, "mismo documento", 100)
    correo = (correo or "").strip().lower()
    if correo:
        for c in Contacto.objects.filter(persona__isnull=False, tipo__codigo="correo", valor_normalizado=correo).select_related("persona"):
            marcar(c.persona, "mismo correo", 60)
    tel = normalizar_telefono(telefono)
    if tel.startswith("+"):
        for c in Contacto.objects.filter(persona__isnull=False, tipo__codigo__in=["telefono_movil", "telefono_fijo"], valor_normalizado=tel).select_related("persona"):
            marcar(c.persona, "mismo teléfono", 40)
    texto = " ".join(p for p in [nombres, apellido_paterno, apellido_materno] if p).strip()
    if texto:
        qs = (
            Persona.objects.annotate(
                _nombre=Unaccent(Concat("nombres", Value(" "), "apellido_paterno", Value(" "), "apellido_materno"))
            )
            .annotate(similitud=TrigramSimilarity("_nombre", Unaccent(Value(texto))))
            .filter(similitud__gte=UMBRAL_NOMBRE)
            .order_by("-similitud")[:10]
        )
        for p in qs:
            marcar(p, f"nombre parecido ({int(p.similitud * 100)}%)", int(p.similitud * 50))
    resultado = [(p, razones) for p, razones, _ in sorted(encontrados.values(), key=lambda e: -e[2])]
    if excluir:
        resultado = [(p, r) for p, r in resultado if p.pk != excluir]
    return resultado

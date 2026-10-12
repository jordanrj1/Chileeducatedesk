"""Carga regiones, provincias y comunas desde un CSV con códigos CUT (fuente oficial).

Columnas: region_codigo, region_nombre, provincia_codigo, provincia_nombre, comuna_codigo, comuna_nombre
Es idempotente: se puede ejecutar de nuevo para actualizar.
"""
import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.territorio.models import Comuna, Provincia, Region

COLUMNAS = ["region_codigo", "region_nombre", "provincia_codigo", "provincia_nombre", "comuna_codigo", "comuna_nombre"]


class Command(BaseCommand):
    help = "Carga el territorio desde un CSV con códigos CUT."

    def add_arguments(self, parser):
        parser.add_argument("archivo")

    @transaction.atomic
    def handle(self, *args, archivo, **opts):
        try:
            f = open(archivo, newline="", encoding="utf-8-sig")
        except OSError as e:
            raise CommandError(f"No se pudo abrir el archivo: {e}")
        with f:
            lector = csv.DictReader(f)
            faltan = [c for c in COLUMNAS if c not in (lector.fieldnames or [])]
            if faltan:
                raise CommandError(f"Faltan columnas: {', '.join(faltan)}")
            n = 0
            for fila in lector:
                region, _ = Region.objects.update_or_create(codigo=fila["region_codigo"].strip(), defaults={"nombre": fila["region_nombre"].strip()})
                prov, _ = Provincia.objects.update_or_create(codigo=fila["provincia_codigo"].strip(), defaults={"region": region, "nombre": fila["provincia_nombre"].strip()})
                Comuna.objects.update_or_create(codigo=fila["comuna_codigo"].strip(), defaults={"provincia": prov, "nombre": fila["comuna_nombre"].strip()})
                n += 1
        self.stdout.write(self.style.SUCCESS(f"{n} comunas procesadas."))

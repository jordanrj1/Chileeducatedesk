"""Comando `vincular_zonas_proyectos`: enlaza la zona escrita a mano de cada proyecto con su comuna o sector, solo cuando
coincide exactamente con uno (ver apps/proyectos/zona.py). Se puede repetir; iniciar.bat e iniciar.sh lo llaman después de
cargar el territorio oficial, porque la migración corre antes de que estén las comunas. Nunca borra el texto.
  --simular   muestra lo que enlazaría, sin guardar nada.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.proyectos.models import Proyecto, ProyectoTerritorio
from apps.proyectos.zona import vincular_zonas
from apps.territorio.models import Comuna, Sector, SectorAlias


class Command(BaseCommand):
    help = "Enlaza la zona escrita de los proyectos con su comuna o sector cuando coincide con uno solo. Nunca borra el texto."

    def add_arguments(self, parser):
        parser.add_argument("--simular", action="store_true", help="Muestra lo que enlazaría, sin guardar nada.")

    def handle(self, *args, simular, **opts):
        with transaction.atomic():
            enlazados = vincular_zonas(Proyecto, ProyectoTerritorio, Comuna, Sector, SectorAlias, simular=simular)
        for proyecto, nivel, territorio in enlazados:
            self.stdout.write(f"  {proyecto.nombre}: «{proyecto.zona}» → {nivel} {territorio}")
        verbo = "Se enlazarían" if simular else "Se enlazaron"
        self.stdout.write(f"Zonas de proyectos: {verbo} {len(enlazados)}." if enlazados else "Zonas de proyectos: nada que enlazar.")

"""F26 P2: `manage.py diferencias_datos` muestra los datos con dos verdades (por categoría: cifra y hasta 20 ejemplos con
id y enlace relativo). Solo lee: corre dentro de una transacción de solo lectura y nunca escribe."""
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.personas.diferencias import diferencias


class Command(BaseCommand):
    help = "Informe de diferencias entre participaciones, vínculos, padrones, equipos, perfiles y sedes. Solo lectura."

    def add_arguments(self, parser):
        parser.add_argument("--ejemplos", type=int, default=20, help="Cuántos ejemplos mostrar por categoría (20 por omisión).")

    def handle(self, *args, **opciones):
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as c:
                    c.execute("SET TRANSACTION READ ONLY")  # garantía: cualquier escritura fallaría
            categorias = diferencias(limite=opciones["ejemplos"])
        total = sum(c["cifra"] for c in categorias)
        self.stdout.write(f"Informe de diferencias (solo lectura): {total} en total.\n")
        for c in categorias:
            self.stdout.write(f"\n[{c['clave']}] {c['titulo']}: {c['cifra']}")
            for e in c["ejemplos"]:
                self.stdout.write(f"  - #{e['id']} {e['texto']} → {e['url']}")
            if c["cifra"] > len(c["ejemplos"]):
                self.stdout.write(f"  … y {c['cifra'] - len(c['ejemplos'])} más.")

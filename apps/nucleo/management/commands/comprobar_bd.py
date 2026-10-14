"""Comando que revisa si la base de datos responde, antes de arrancar el sistema.
Si no responde, explica qué revisar (servicio de PostgreSQL, datos de conexión en .env) (OP-E3)."""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.utils import Error


class Command(BaseCommand):
    help = "Comprueba la conexión con PostgreSQL."

    def handle(self, *args, **opts):
        try:
            with connection.cursor() as c:
                c.execute("SELECT 1")
        except Error as e:
            raise CommandError(f"La base de datos no responde: {e}")
        self.stdout.write(self.style.SUCCESS("Base de datos: OK"))

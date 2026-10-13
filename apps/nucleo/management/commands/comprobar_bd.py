"""OP-E3: responde con código 0 si la base contesta; si no, explica qué revisar."""
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

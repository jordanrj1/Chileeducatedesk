from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Búsqueda sin distinguir tildes (PE-E8, BU-E1)."""

    dependencies = [("nucleo", "0006_lista_de_espera")]
    operations = [UnaccentExtension()]

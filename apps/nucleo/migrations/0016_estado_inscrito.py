# F25 E2: el estado de participación «Confirmado» se muestra como «Inscrito» (el código «confirmado» no cambia).
# Solo de datos e idempotente: cambia el nombre únicamente si hoy se llama exactamente «Confirmado»; si ya se editó
# en Catálogos, se respeta. Al revertir vuelve a «Confirmado» solo si se llama «Inscrito».
from django.db import migrations


def _renombrar(apps, antes, despues):
    E = apps.get_model("nucleo", "EstadoParticipacion")
    E.objects.filter(codigo="confirmado", nombre=antes).update(nombre=despues)


def a_inscrito(apps, schema_editor):
    _renombrar(apps, "Confirmado", "Inscrito")


def a_confirmado(apps, schema_editor):
    _renombrar(apps, "Inscrito", "Confirmado")


class Migration(migrations.Migration):
    dependencies = [("nucleo", "0015_rol_perfil")]
    operations = [migrations.RunPython(a_inscrito, a_confirmado)]

from django.db import migrations


def agregar(apps, schema_editor):
    E = apps.get_model("nucleo", "EstadoParticipacion")
    E.objects.get_or_create(codigo="lista_espera", defaults={"nombre": "En lista de espera", "orden": 9})


class Migration(migrations.Migration):
    dependencies = [("nucleo", "0005_permiso_desactivar_catalogos")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]

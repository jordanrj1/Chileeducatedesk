from django.db import migrations


def agregar(apps, schema_editor):
    E = apps.get_model("nucleo", "EstadoActividad")
    E.objects.get_or_create(codigo="cerrada", defaults={"nombre": "Cerrada", "orden": 8})


class Migration(migrations.Migration):
    dependencies = [("nucleo", "0003_catalogos_iniciales")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]

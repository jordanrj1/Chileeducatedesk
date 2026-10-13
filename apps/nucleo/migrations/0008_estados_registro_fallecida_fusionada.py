from django.db import migrations


def agregar(apps, schema_editor):
    E = apps.get_model("nucleo", "EstadoRegistro")
    E.objects.get_or_create(codigo="fallecida", defaults={"nombre": "Fallecida/o", "orden": 5})
    E.objects.get_or_create(codigo="fusionada", defaults={"nombre": "Fusionada en otra ficha", "orden": 6})


class Migration(migrations.Migration):
    dependencies = [("nucleo", "0007_extension_unaccent")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]

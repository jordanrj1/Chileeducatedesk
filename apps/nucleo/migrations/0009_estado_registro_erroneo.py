from django.db import migrations


def agregar(apps, schema_editor):
    E = apps.get_model("nucleo", "EstadoParticipacion")
    E.objects.get_or_create(codigo="registro_erroneo", defaults={"nombre": "Registro erróneo (quitada)", "orden": 10})


class Migration(migrations.Migration):
    """HI-E2: quitar a una persona relacionada por error, sin borrar en silencio."""

    dependencies = [("nucleo", "0008_estados_registro_fallecida_fusionada")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]

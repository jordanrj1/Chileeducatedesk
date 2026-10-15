# Tramos de edad de la comunidad. Aditiva: agrega la relación con el catálogo y marca los tramos que se reconocen
# en el texto anterior («rango etario»), sin borrarlo. Solo toca registros sin tramos, así que se puede repetir.

from django.db import migrations, models


def convertir(apps, schema_editor):
    from apps.nucleo.tramos import asignar_desde_texto

    asignar_desde_texto(apps.get_model("comunidades", "Comunidad"), apps.get_model("nucleo", "TramoEtario"))


class Migration(migrations.Migration):

    dependencies = [
        ('comunidades', '0001_initial'),
        ('nucleo', '0012_tramo_etario'),
    ]

    operations = [
        migrations.AddField(
            model_name='comunidad',
            name='tramos_etarios',
            field=models.ManyToManyField(blank=True, related_name='comunidades', to='nucleo.tramoetario', verbose_name='edades principales'),
        ),
        migrations.RunPython(convertir, migrations.RunPython.noop),
    ]

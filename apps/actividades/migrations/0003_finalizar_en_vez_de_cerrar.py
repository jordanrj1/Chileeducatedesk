"""El estado «cerrada» se elimina: finalizar deja la actividad como «realizada» (decisión del 12-10-2026)."""
from django.db import migrations


def cerrada_a_realizada(apps, schema_editor):
    Estado = apps.get_model("nucleo", "EstadoActividad")
    cerrada = Estado.objects.filter(codigo="cerrada").first()
    if not cerrada:
        return
    realizada = Estado.objects.get(codigo="realizada")
    for nombre in ("Actividad", "AgendaActividad"):
        apps.get_model("actividades", nombre).objects.filter(estado=cerrada).update(estado=realizada)
    apps.get_model("actividades", "HistoricalActividad").objects.filter(estado_id=cerrada.pk).update(estado_id=realizada.pk)
    cerrada.delete()


class Migration(migrations.Migration):
    dependencies = [("actividades", "0002_initial"), ("nucleo", "0004_estado_cerrada")]

    operations = [
        migrations.RenameField("actividad", "cerrada_en", "finalizada_en"),
        migrations.RenameField("actividad", "cerrada_por", "finalizada_por"),
        migrations.RenameField("historicalactividad", "cerrada_en", "finalizada_en"),
        migrations.RenameField("historicalactividad", "cerrada_por", "finalizada_por"),
        migrations.RunPython(cerrada_a_realizada, migrations.RunPython.noop),
    ]

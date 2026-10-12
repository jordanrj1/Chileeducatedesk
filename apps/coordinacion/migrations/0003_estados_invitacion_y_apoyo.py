from django.db import migrations, models


def renombrar(apps, schema_editor):
    apps.get_model("coordinacion", "Invitacion").objects.filter(estado="pendiente").update(estado="enviada")
    C = apps.get_model("coordinacion", "Colaboracion")
    C.objects.filter(estado="solicitada").update(estado="enviada")
    C.objects.filter(estado="acordada").update(estado="aceptada")


class Migration(migrations.Migration):
    dependencies = [("coordinacion", "0002_initial")]
    operations = [
        migrations.AlterField("colaboracion", "estado", models.CharField(choices=[("enviada", "Enviada"), ("respondio", "Respondió"), ("aceptada", "Aceptó"), ("rechazada", "Rechazó"), ("sin_respuesta", "Sin respuesta"), ("cumplida", "Cumplida")], default="enviada", max_length=14)),
        migrations.AlterField("invitacion", "estado", models.CharField(choices=[("enviada", "Enviada"), ("respondio", "Respondió"), ("aceptada", "Aceptó"), ("rechazada", "Rechazó"), ("sin_respuesta", "Sin respuesta")], default="enviada", max_length=14)),
        migrations.RunPython(renombrar, migrations.RunPython.noop),
    ]

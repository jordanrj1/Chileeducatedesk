# F28: estado de inscripción «Retirado» (quien deja la tarea: conserva sus asistencias y no aparece en las jornadas
# siguientes). Solo de datos e idempotente: lo crea por su código solo si no existe; si ya existe (o se editó en
# Catálogos), no lo toca. Al revertir no borra nada: puede estar en uso.
from django.db import migrations


def agregar(apps, schema_editor):
    E = apps.get_model("nucleo", "EstadoParticipacion")
    E.objects.get_or_create(codigo="retirado", defaults={
        "nombre": "Retirado", "orden": 11,
        "descripcion": "Dejó la tarea: conserva sus asistencias y no aparece en las listas de las jornadas siguientes.",
    })


class Migration(migrations.Migration):
    dependencies = [("nucleo", "0019_catalogos_descripcion_relacion_lugar")]
    operations = [migrations.RunPython(agregar, migrations.RunPython.noop)]

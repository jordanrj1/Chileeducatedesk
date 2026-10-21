# F25 F3: dos roles cortos para el grupo «Invitados y contactos»: «Invitado o invitada» y «Autoridad».
# El detalle (p. ej. «Alcalde de Hualpén») va en el cargo o función libre de cada participación.
# Solo de datos e idempotente: crea cada rol por su código solo si no existe; si ya existe (o se editó en Catálogos),
# no lo toca. Al revertir no borra nada: los roles pueden estar en uso.
from django.db import migrations

ROLES = [("invitado", "Invitado o invitada", 11), ("autoridad", "Autoridad", 12)]


def crear(apps, schema_editor):
    Rol = apps.get_model("nucleo", "RolParticipacion")
    for codigo, nombre, orden in ROLES:
        Rol.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "orden": orden, "grupo": "contacto"})


class Migration(migrations.Migration):
    dependencies = [("nucleo", "0016_estado_inscrito")]
    operations = [migrations.RunPython(crear, migrations.RunPython.noop)]

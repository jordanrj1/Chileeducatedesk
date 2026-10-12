from django.db import migrations

GRUPOS = ["Gestor", "Administrador"]


def crear_grupos(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nombre in GRUPOS:
        Group.objects.get_or_create(name=nombre)


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(crear_grupos, migrations.RunPython.noop)]

"""F29: el Superadministrador reemplaza al Administrador. Renombra el grupo conservando a sus usuarios; reversible."""
from django.db import migrations

ANTES, DESPUES = "Administrador", "Superadministrador"


def _renombrar(apps, de, a):
    Group = apps.get_model("auth", "Group")
    origen = Group.objects.filter(name=de).first()
    destino = Group.objects.filter(name=a).first()
    if origen and destino:  # ya existían los dos: los usuarios y permisos pasan al destino
        for u in origen.user_set.all():
            u.groups.add(destino)
        destino.permissions.add(*origen.permissions.all())
        origen.delete()
    elif origen:
        origen.name = a
        origen.save(update_fields=["name"])
    else:
        Group.objects.get_or_create(name=a)


def a_superadmin(apps, schema_editor):
    _renombrar(apps, ANTES, DESPUES)
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    Group.objects.get(name=DESPUES).permissions.add(*Permission.objects.all())


def a_administrador(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    if Group.objects.filter(name=DESPUES).exists():
        _renombrar(apps, DESPUES, ANTES)


class Migration(migrations.Migration):
    dependencies = [("auth", "0012_alter_user_first_name_max_length"), ("cuentas", "0003_initial")]
    operations = [
        migrations.AlterModelOptions(name="permisoinicial", options={"permissions": [("respaldar", "Ver los respaldos y respaldar ahora")]}),
        migrations.RunPython(a_superadmin, a_administrador),
    ]

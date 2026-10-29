# F26 P2: catálogo «Rol en la organización» (estudiante, docente, funcionario o funcionaria, dirigente, socio o socia,
# practicante, autoridad, otro). Aditiva: crea la tabla y siembra cada valor solo si su código no existe, sin pisar lo
# editado en Catálogos. Al revertir, la tabla se elimina con sus valores.

from django.db import migrations, models

from apps.personas.rol_organizacion import ROLES


def sembrar(apps, schema_editor):
    Rol = apps.get_model("nucleo", "RolOrganizacion")
    for codigo, nombre, orden in ROLES:
        Rol.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "orden": orden})


class Migration(migrations.Migration):

    dependencies = [
        ('nucleo', '0017_roles_invitado_autoridad'),
    ]

    operations = [
        migrations.CreateModel(
            name='RolOrganizacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.SlugField(help_text='Identificador interno; no cambia.', max_length=60, unique=True, verbose_name='código')),
                ('nombre', models.CharField(max_length=100)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'rol en la organización',
                'verbose_name_plural': 'roles en la organización',
                'ordering': ['orden', 'nombre'],
                'permissions': [('desactivar_rolorganizacion', 'Puede desactivar valores de roles en la organización')],
                'abstract': False,
            },
        ),
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]

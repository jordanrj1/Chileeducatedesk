# F27 · Catálogos que se explican solos. Aditiva y de datos:
# - `descripcion` opcional en todos los catálogos y `con_cargo` en «Rol en la organización»;
# - el catálogo nuevo «Relación con un lugar» (RelacionLugar) con sus valores agrupados por ámbito;
# - los roles nuevos (representante legal, voluntario, contacto, egresado, vecino, apoderado, beneficiario) se crean solo
#   si su código no existe; a los que ya estaban se les completa la descripción solo si está vacía, sin pisar lo
#   editado en Catálogos, y se fija si admiten cargo.
# Al revertir, las columnas y la tabla nuevas se eliminan con sus valores.

from django.db import migrations, models

from apps.personas.relacion_lugar import RELACIONES
from apps.personas.rol_organizacion import ROLES_F27


def sembrar(apps, schema_editor):
    Rol = apps.get_model("nucleo", "RolOrganizacion")
    for codigo, nombre, orden, con_cargo, descripcion in ROLES_F27:
        rol, creado = Rol.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "orden": orden, "con_cargo": con_cargo,
                                                                         "descripcion": descripcion})
        if not creado:
            rol.con_cargo = con_cargo
            rol.descripcion = rol.descripcion or descripcion
            rol.save(update_fields=["con_cargo", "descripcion"])
    Relacion = apps.get_model("nucleo", "RelacionLugar")
    for codigo, nombre, ambito, orden, descripcion in RELACIONES:
        Relacion.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "ambito": ambito, "orden": orden, "descripcion": descripcion})


class Migration(migrations.Migration):

    dependencies = [
        ('nucleo', '0018_rol_organizacion'),
    ]

    operations = [
        migrations.CreateModel(
            name='RelacionLugar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.SlugField(help_text='Identificador interno; no cambia.', max_length=60, unique=True, verbose_name='código')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción')),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
                ('ambito', models.CharField(choices=[('estudio', 'Estudio'), ('trabajo', 'Trabajo'), ('comunidad', 'Comunidad'), ('residencia', 'Residencia'), ('otra', 'Otra')], default='otra', help_text='Agrupa las opciones en la lista. Ej.: «Hace su práctica ahí» va en Estudio.', max_length=12, verbose_name='ámbito')),
            ],
            options={
                'verbose_name': 'relación con un lugar',
                'verbose_name_plural': 'relaciones con un lugar',
                'ordering': ['orden', 'nombre'],
                'permissions': [('desactivar_relacionlugar', 'Puede desactivar valores de relaciones con un lugar')],
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='areatematica',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='canal',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='estadoactividad',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='estadoparticipacion',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='estadoregistro',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='estadosolicitud',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='estadovoluntario',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='modalidad',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='naturalezajuridica',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='origenpersona',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='parentesco',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='perfilpersona',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='rolorganizacion',
            name='con_cargo',
            field=models.BooleanField(default=True, help_text='Márcalo si quien tiene este rol puede ocupar un cargo (presidenta, encargado, director). Si no, el tipo de cargo no se pide.', verbose_name='admite cargo'),
        ),
        migrations.AddField(
            model_name='rolorganizacion',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='rolparticipacion',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='tipoactividad',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='tipocontacto',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='tipodocumento',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='tipointervencion',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='tipoinvitado',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='tipolugar',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='tipoorganizacion',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.AddField(
            model_name='tramoetario',
            name='descripcion',
            field=models.CharField(blank=True, help_text='Opcional. Explica cuándo usar este valor; se muestra bajo la lista al elegirlo.', max_length=300, verbose_name='descripción'),
        ),
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]

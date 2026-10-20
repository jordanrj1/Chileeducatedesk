# Catálogo de naturalezas jurídicas (la forma legal con que se constituyó una organización), con valores iniciales
# por validar con el cliente. Aditiva: crea la tabla y siembra cada valor solo si su código no existe, así que se puede
# volver a ejecutar sin duplicar ni pisar lo editado en Catálogos.

from django.db import migrations, models

SEMILLAS = [
    ("organizacion_comunitaria_territorial", "Organización comunitaria territorial (junta de vecinos)"),
    ("organizacion_comunitaria_funcional", "Organización comunitaria funcional"),
    ("corporacion", "Corporación"),
    ("fundacion", "Fundación"),
    ("sociedad_o_empresa", "Sociedad o empresa"),
    ("servicio_publico", "Servicio público"),
    ("establecimiento_educacional", "Establecimiento educacional"),
    ("otra", "Otra"),
]


def sembrar(apps, schema_editor):
    Naturaleza = apps.get_model("nucleo", "NaturalezaJuridica")
    for orden, (codigo, nombre) in enumerate(SEMILLAS, start=1):
        Naturaleza.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "orden": orden})


class Migration(migrations.Migration):

    dependencies = [
        ('nucleo', '0013_fichas_por_tipo'),
    ]

    operations = [
        migrations.CreateModel(
            name='NaturalezaJuridica',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.SlugField(help_text='Identificador interno; no cambia.', max_length=60, unique=True, verbose_name='código')),
                ('nombre', models.CharField(max_length=100)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'naturaleza jurídica',
                'verbose_name_plural': 'naturalezas jurídicas',
                'ordering': ['orden', 'nombre'],
                'permissions': [('desactivar_naturalezajuridica', 'Puede desactivar valores de naturalezas jurídicas')],
                'abstract': False,
            },
        ),
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]

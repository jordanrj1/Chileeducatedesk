# Catálogo de tramos de edad con sus valores iniciales (por validar con el cliente). Aditiva: crea la tabla y siembra
# los seis tramos solo si su código no existe, así que se puede volver a ejecutar sin duplicar ni pisar lo editado.

from django.db import migrations, models

SEMILLAS = [
    ("primera_infancia", "Primera infancia", 0, 5),
    ("ninez", "Niñez", 6, 12),
    ("adolescencia", "Adolescencia", 13, 17),
    ("jovenes", "Jóvenes", 18, 29),
    ("personas_adultas", "Personas adultas", 30, 59),
    ("personas_mayores", "Personas mayores", 60, None),
]


def sembrar(apps, schema_editor):
    Tramo = apps.get_model("nucleo", "TramoEtario")
    for orden, (codigo, nombre, minimo, maximo) in enumerate(SEMILLAS, start=1):
        Tramo.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "orden": orden, "edad_min": minimo, "edad_max": maximo})


class Migration(migrations.Migration):

    dependencies = [
        ('nucleo', '0011_semillas_f22'),
    ]

    operations = [
        migrations.CreateModel(
            name='TramoEtario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.SlugField(help_text='Identificador interno; no cambia.', max_length=60, unique=True, verbose_name='código')),
                ('nombre', models.CharField(max_length=100)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
                ('edad_min', models.PositiveSmallIntegerField(blank=True, help_text='En años. Ej.: 18.', null=True, verbose_name='edad mínima')),
                ('edad_max', models.PositiveSmallIntegerField(blank=True, help_text='En años. Déjala vacía si no tiene tope (Ej.: 60 o más).', null=True, verbose_name='edad máxima')),
            ],
            options={
                'verbose_name': 'tramo de edad',
                'verbose_name_plural': 'tramos de edad',
                'ordering': ['orden', 'nombre'],
                'permissions': [('desactivar_tramoetario', 'Puede desactivar valores de tramos de edad')],
                'abstract': False,
                'constraints': [models.CheckConstraint(condition=models.Q(('edad_min__isnull', True), ('edad_max__isnull', True), ('edad_max__gte', models.F('edad_min')), _connector='OR'), name='tramo_etario_edad_max_mayor_o_igual')],
            },
        ),
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]

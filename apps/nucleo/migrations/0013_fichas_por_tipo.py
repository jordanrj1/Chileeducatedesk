# Fichas por tipo de persona: qué ficha abre cada perfil y los catálogos nuevos (parentesco, tipo de invitado y estado
# del voluntariado), más el perfil «Invitado o invitada» y el tipo de lugar «Casa matriz». Aditiva y conservadora:
# solo crea lo que falta por código y solo asigna la ficha a un perfil que aún no tiene una, así que repetirla no cambia nada.

from django.db import migrations, models

# Valores iniciales por validar con el cliente
SEMILLAS = {
    "Parentesco": [
        ("hijo_o_hija", "Hijo o hija"), ("nieto_o_nieta", "Nieto o nieta"), ("pareja", "Pareja"), ("padre_o_madre", "Padre o madre"),
        ("hermano_o_hermana", "Hermano o hermana"), ("abuelo_o_abuela", "Abuelo o abuela"), ("otro_familiar", "Otro familiar"),
        ("sin_parentesco", "Sin parentesco"),
    ],
    "TipoInvitado": [
        ("autoridad", "Autoridad"), ("expositor_o_expositora", "Expositor o expositora"), ("invitado_o_invitada_especial", "Invitado o invitada especial"),
        ("prensa", "Prensa"), ("aliado_o_patrocinador", "Aliado o patrocinador"), ("otro", "Otro"),
    ],
    "EstadoVoluntario": [("postulante", "Postulante"), ("activo", "Activo"), ("en_pausa", "En pausa"), ("retirado", "Retirado")],
}
# Qué ficha abre cada perfil al comienzo. El resto queda sin ficha propia (se puede cambiar en Catálogos).
FICHAS = {
    "estudiante": "estudiante",
    "vecino_o_vecina_de_la_comunidad": "vecino",
    "voluntario_o_voluntaria": "voluntario",
    "invitado_o_invitada": "invitado",
}


def _siguiente_orden(Modelo):
    return (Modelo.objects.aggregate(m=models.Max("orden"))["m"] or 0) + 1


def sembrar(apps, schema_editor):
    for nombre_modelo, valores in SEMILLAS.items():
        Modelo = apps.get_model("nucleo", nombre_modelo)
        for orden, (codigo, nombre) in enumerate(valores, start=1):
            Modelo.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "orden": orden})
    Perfil = apps.get_model("nucleo", "PerfilPersona")
    if not Perfil.objects.filter(codigo="invitado_o_invitada").exists():
        Perfil.objects.create(codigo="invitado_o_invitada", nombre="Invitado o invitada", orden=_siguiente_orden(Perfil))
    for codigo, ficha in FICHAS.items():
        Perfil.objects.filter(codigo=codigo, ficha="").update(ficha=ficha)
    TipoLugar = apps.get_model("nucleo", "TipoLugar")
    if not TipoLugar.objects.filter(codigo="casa_matriz").exists():
        TipoLugar.objects.create(codigo="casa_matriz", nombre="Casa matriz", orden=_siguiente_orden(TipoLugar))


class Migration(migrations.Migration):

    dependencies = [
        ('nucleo', '0012_tramo_etario'),
    ]

    operations = [
        migrations.CreateModel(
            name='EstadoVoluntario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.SlugField(help_text='Identificador interno; no cambia.', max_length=60, unique=True, verbose_name='código')),
                ('nombre', models.CharField(max_length=100)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'estado del voluntariado',
                'verbose_name_plural': 'estados del voluntariado',
                'ordering': ['orden', 'nombre'],
                'permissions': [('desactivar_estadovoluntario', 'Puede desactivar valores de estados del voluntariado')],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Parentesco',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.SlugField(help_text='Identificador interno; no cambia.', max_length=60, unique=True, verbose_name='código')),
                ('nombre', models.CharField(max_length=100)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'parentesco',
                'verbose_name_plural': 'parentescos',
                'ordering': ['orden', 'nombre'],
                'permissions': [('desactivar_parentesco', 'Puede desactivar valores de parentescos')],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TipoInvitado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.SlugField(help_text='Identificador interno; no cambia.', max_length=60, unique=True, verbose_name='código')),
                ('nombre', models.CharField(max_length=100)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'tipo de invitado',
                'verbose_name_plural': 'tipos de invitado',
                'ordering': ['orden', 'nombre'],
                'permissions': [('desactivar_tipoinvitado', 'Puede desactivar valores de tipos de invitado')],
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='perfilpersona',
            name='ficha',
            field=models.CharField(blank=True, choices=[('', 'Sin ficha propia'), ('estudiante', 'Estudiante'), ('vecino', 'Vecino o vecina'), ('invitado', 'Invitado o invitada'), ('voluntario', 'Voluntario o voluntaria')], help_text='Qué datos propios se piden al registrar a alguien con este perfil. Ej.: Estudiante pide institución, sede y carrera.', max_length=12),
        ),
        migrations.RunPython(sembrar, migrations.RunPython.noop),
    ]

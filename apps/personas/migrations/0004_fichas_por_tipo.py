# Fichas por tipo de persona: sexo y fecha de nacimiento aproximada en la persona, la sede del estudiante como lugar
# de su institución y las tablas nuevas del vecino (hogar, integrantes y familiares), del invitado y del voluntario.
# Aditiva: copia la jefatura y los integrantes del hogar desde los datos sensibles sin borrar esas columnas, y solo
# completa lo que la ficha del vecino tiene vacío, así que repetirla no pisa nada. El tramo RSH se queda donde está.

import django.db.models.deletion
import simple_history.models
from django.conf import settings
from django.db import migrations, models


def copiar_hogar(apps, schema_editor):
    PerfilSensible = apps.get_model("personas", "PerfilSensible")
    FichaVecino = apps.get_model("personas", "FichaVecino")
    con_hogar = PerfilSensible.objects.filter(models.Q(jefatura_hogar__isnull=False) | models.Q(integrantes_hogar__isnull=False))
    fichas = {f.persona_id: f for f in FichaVecino.objects.filter(persona_id__in=con_hogar.values("persona_id"))}
    nuevas = []
    for ps in con_hogar.only("persona_id", "jefatura_hogar", "integrantes_hogar"):
        ficha = fichas.get(ps.persona_id)
        if ficha is None:
            nuevas.append(FichaVecino(persona_id=ps.persona_id, jefatura_hogar=ps.jefatura_hogar, integrantes_hogar=ps.integrantes_hogar))
            continue
        cambios = [c for c in ("jefatura_hogar", "integrantes_hogar") if getattr(ficha, c) is None and getattr(ps, c) is not None]
        for c in cambios:
            setattr(ficha, c, getattr(ps, c))
        if cambios:
            ficha.save(update_fields=cambios)
    FichaVecino.objects.bulk_create(nuevas)


class Migration(migrations.Migration):

    dependencies = [
        ('actividades', '0008_tramos_etarios'),
        ('lugares', '0001_initial'),
        ('nucleo', '0013_fichas_por_tipo'),
        ('organizaciones', '0002_documento_y_fusion'),
        ('personas', '0003_ingesta_ampliada'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalpersona',
            name='fecha_nacimiento_aproximada',
            field=models.BooleanField(default=False, help_text='Marcada si solo se conoce la edad: se guarda el 1 de enero del año que corresponde.', verbose_name='fecha de nacimiento aproximada'),
        ),
        migrations.AddField(
            model_name='historicalpersona',
            name='sexo',
            field=models.CharField(blank=True, choices=[('mujer', 'Mujer'), ('hombre', 'Hombre'), ('otro', 'Otro'), ('no_informa', 'No informa')], help_text='Opcional. La identidad de género se registra aparte, en los datos sensibles.', max_length=10),
        ),
        migrations.AddField(
            model_name='persona',
            name='fecha_nacimiento_aproximada',
            field=models.BooleanField(default=False, help_text='Marcada si solo se conoce la edad: se guarda el 1 de enero del año que corresponde.', verbose_name='fecha de nacimiento aproximada'),
        ),
        migrations.AddField(
            model_name='persona',
            name='sexo',
            field=models.CharField(blank=True, choices=[('mujer', 'Mujer'), ('hombre', 'Hombre'), ('otro', 'Otro'), ('no_informa', 'No informa')], help_text='Opcional. La identidad de género se registra aparte, en los datos sensibles.', max_length=10),
        ),
        migrations.AddField(
            model_name='personaformacion',
            name='sede_institucion',
            field=models.ForeignKey(blank=True, help_text='Un lugar de la institución, de tipo sede o casa matriz.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='estudiantes', to='lugares.lugar', verbose_name='sede o casa matriz'),
        ),
        migrations.CreateModel(
            name='FichaInvitado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cargo', models.CharField(blank=True, help_text='Ej.: alcaldesa, director de escuela, periodista.', max_length=120)),
                ('motivo', models.TextField(blank=True, verbose_name='motivo de la invitación')),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('actividad', models.ForeignKey(blank=True, help_text='Opcional: la actividad a la que se le invitó.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='actividades.actividad')),
                ('invitado_por', models.ForeignKey(blank=True, help_text='Quién la invitó o la contactó, si se sabe.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='invitados_referidos', to='personas.persona', verbose_name='invitado o invitada por')),
                ('organizacion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='organizaciones.organizacion', verbose_name='organización de procedencia')),
                ('persona', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='ficha_invitado', to='personas.persona')),
                ('tipo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='nucleo.tipoinvitado', verbose_name='tipo de invitado')),
            ],
            options={
                'verbose_name': 'ficha de invitado o invitada',
                'verbose_name_plural': 'fichas de invitados e invitadas',
            },
        ),
        migrations.CreateModel(
            name='FichaVecino',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jefatura_hogar', models.BooleanField(blank=True, null=True, verbose_name='es jefe o jefa de hogar')),
                ('integrantes_hogar', models.PositiveSmallIntegerField(blank=True, help_text='Cuántas personas viven en el hogar, contándola a ella. Ej.: 4.', null=True, verbose_name='integrantes del hogar')),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('persona', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='ficha_vecino', to='personas.persona')),
            ],
            options={
                'verbose_name': 'ficha de vecino o vecina',
                'verbose_name_plural': 'fichas de vecinos y vecinas',
            },
        ),
        migrations.CreateModel(
            name='HistoricalFamiliarVinculado',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('familiar', models.ForeignKey(blank=True, db_constraint=False, help_text='Otra persona ya registrada.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='personas.persona')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('parentesco', models.ForeignKey(blank=True, db_constraint=False, help_text='Qué es el familiar para esta persona. Ej.: hijo o hija.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='nucleo.parentesco')),
                ('persona', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='personas.persona')),
            ],
            options={
                'verbose_name': 'historical familiar vinculado',
                'verbose_name_plural': 'historical familiares vinculados',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalFichaInvitado',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('cargo', models.CharField(blank=True, help_text='Ej.: alcaldesa, director de escuela, periodista.', max_length=120)),
                ('motivo', models.TextField(blank=True, verbose_name='motivo de la invitación')),
                ('actualizado_en', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('actividad', models.ForeignKey(blank=True, db_constraint=False, help_text='Opcional: la actividad a la que se le invitó.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='actividades.actividad')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('invitado_por', models.ForeignKey(blank=True, db_constraint=False, help_text='Quién la invitó o la contactó, si se sabe.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='personas.persona', verbose_name='invitado o invitada por')),
                ('organizacion', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='organizaciones.organizacion', verbose_name='organización de procedencia')),
                ('persona', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='personas.persona')),
                ('tipo', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='nucleo.tipoinvitado', verbose_name='tipo de invitado')),
            ],
            options={
                'verbose_name': 'historical ficha de invitado o invitada',
                'verbose_name_plural': 'historical fichas de invitados e invitadas',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalFichaVecino',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('jefatura_hogar', models.BooleanField(blank=True, null=True, verbose_name='es jefe o jefa de hogar')),
                ('integrantes_hogar', models.PositiveSmallIntegerField(blank=True, help_text='Cuántas personas viven en el hogar, contándola a ella. Ej.: 4.', null=True, verbose_name='integrantes del hogar')),
                ('actualizado_en', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('persona', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='personas.persona')),
            ],
            options={
                'verbose_name': 'historical ficha de vecino o vecina',
                'verbose_name_plural': 'historical fichas de vecinos y vecinas',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalFichaVoluntario',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('fecha_ingreso', models.DateField(blank=True, null=True, verbose_name='fecha de ingreso')),
                ('horas_semanales', models.PositiveSmallIntegerField(blank=True, help_text='Ej.: 4.', null=True, verbose_name='horas disponibles por semana')),
                ('motivacion', models.TextField(blank=True, verbose_name='motivación u observaciones')),
                ('actualizado_en', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('estado', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='nucleo.estadovoluntario', verbose_name='estado del voluntariado')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('persona', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='personas.persona')),
            ],
            options={
                'verbose_name': 'historical ficha de voluntario o voluntaria',
                'verbose_name_plural': 'historical fichas de voluntarios y voluntarias',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalIntegranteHogar',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('cantidad', models.PositiveSmallIntegerField(default=1, help_text='Ej.: 2 si son dos hijos del mismo tramo.')),
                ('vive_en_hogar', models.BooleanField(default=True, help_text='Desmárcala para familiares que viven en otra casa, como nietos.', verbose_name='vive en el hogar')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('ficha', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='personas.fichavecino')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('parentesco', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='nucleo.parentesco')),
                ('tramo', models.ForeignKey(blank=True, db_constraint=False, help_text='Déjalo vacío si no se sabe la edad.', null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='nucleo.tramoetario', verbose_name='tramo de edad')),
            ],
            options={
                'verbose_name': 'historical integrante del hogar',
                'verbose_name_plural': 'historical integrantes del hogar',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='FamiliarVinculado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('familiar', models.ForeignKey(help_text='Otra persona ya registrada.', on_delete=django.db.models.deletion.PROTECT, related_name='familiar_de', to='personas.persona')),
                ('parentesco', models.ForeignKey(help_text='Qué es el familiar para esta persona. Ej.: hijo o hija.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='nucleo.parentesco')),
                ('persona', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='familiares', to='personas.persona')),
            ],
            options={
                'verbose_name': 'familiar vinculado',
                'verbose_name_plural': 'familiares vinculados',
                'ordering': ['parentesco__orden', 'pk'],
                'constraints': [models.UniqueConstraint(fields=('persona', 'familiar'), name='familiar_vinculado_unico'), models.CheckConstraint(condition=models.Q(('persona', models.F('familiar')), _negated=True), name='familiar_vinculado_no_es_la_misma')],
            },
        ),
        migrations.CreateModel(
            name='FichaVoluntario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_ingreso', models.DateField(blank=True, null=True, verbose_name='fecha de ingreso')),
                ('horas_semanales', models.PositiveSmallIntegerField(blank=True, help_text='Ej.: 4.', null=True, verbose_name='horas disponibles por semana')),
                ('motivacion', models.TextField(blank=True, verbose_name='motivación u observaciones')),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('estado', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='nucleo.estadovoluntario', verbose_name='estado del voluntariado')),
                ('persona', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='ficha_voluntario', to='personas.persona')),
            ],
            options={
                'verbose_name': 'ficha de voluntario o voluntaria',
                'verbose_name_plural': 'fichas de voluntarios y voluntarias',
                'constraints': [models.CheckConstraint(condition=models.Q(('horas_semanales__isnull', True), ('horas_semanales__lte', 168), _connector='OR'), name='ficha_voluntario_horas_posibles')],
            },
        ),
        migrations.CreateModel(
            name='IntegranteHogar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveSmallIntegerField(default=1, help_text='Ej.: 2 si son dos hijos del mismo tramo.')),
                ('vive_en_hogar', models.BooleanField(default=True, help_text='Desmárcala para familiares que viven en otra casa, como nietos.', verbose_name='vive en el hogar')),
                ('ficha', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='integrantes', to='personas.fichavecino')),
                ('parentesco', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='nucleo.parentesco')),
                ('tramo', models.ForeignKey(blank=True, help_text='Déjalo vacío si no se sabe la edad.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='nucleo.tramoetario', verbose_name='tramo de edad')),
            ],
            options={
                'verbose_name': 'integrante del hogar',
                'verbose_name_plural': 'integrantes del hogar',
                'ordering': ['-vive_en_hogar', 'parentesco__orden', 'tramo__orden', 'pk'],
                'constraints': [models.CheckConstraint(condition=models.Q(('cantidad__gte', 1)), name='integrante_hogar_cantidad_positiva'), models.UniqueConstraint(condition=models.Q(('tramo__isnull', False)), fields=('ficha', 'parentesco', 'tramo', 'vive_en_hogar'), name='integrante_hogar_unico'), models.UniqueConstraint(condition=models.Q(('tramo__isnull', True)), fields=('ficha', 'parentesco', 'vive_en_hogar'), name='integrante_hogar_unico_sin_tramo')],
            },
        ),
        migrations.RunPython(copiar_hogar, migrations.RunPython.noop),
    ]

# Dónde se desarrolla el proyecto (ProyectoTerritorio). Aditiva: crea la tabla y enlaza la «zona» escrita a mano solo si
# coincide exactamente (sin tildes ni mayúsculas) con una sola comuna o sector; el texto no se borra. Se puede repetir:
# no toca proyectos que ya tienen territorios. Para repetirlo después de cargar el territorio: vincular_zonas_proyectos.

import django.db.models.deletion
from django.db import migrations, models


def vincular(apps, schema_editor):
    from apps.proyectos.zona import vincular_zonas

    vincular_zonas(
        apps.get_model("proyectos", "Proyecto"), apps.get_model("proyectos", "ProyectoTerritorio"), apps.get_model("territorio", "Comuna"),
        apps.get_model("territorio", "Sector"), apps.get_model("territorio", "SectorAlias"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('proyectos', '0002_area_tematica_y_comunidades'),
        ('territorio', '0004_sector_desactivable_e_historial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProyectoTerritorio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vigente', models.BooleanField(default=True)),
                ('comuna', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='territorio.comuna')),
                ('provincia', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='territorio.provincia')),
                ('proyecto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='territorios', to='proyectos.proyecto')),
                ('region', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='territorio.region')),
                ('sector', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='territorio.sector')),
            ],
            options={
                'verbose_name': 'territorio del proyecto',
                'verbose_name_plural': 'territorios del proyecto',
                'constraints': [models.CheckConstraint(condition=models.Q(models.Q(('comuna__isnull', True), ('provincia__isnull', True), ('region__isnull', False), ('sector__isnull', True)), models.Q(('comuna__isnull', True), ('provincia__isnull', False), ('region__isnull', True), ('sector__isnull', True)), models.Q(('comuna__isnull', False), ('provincia__isnull', True), ('region__isnull', True), ('sector__isnull', True)), models.Q(('comuna__isnull', True), ('provincia__isnull', True), ('region__isnull', True), ('sector__isnull', False)), _connector='OR'), name='proyecto_territorio_un_nivel'), models.UniqueConstraint(condition=models.Q(('sector__isnull', False)), fields=('proyecto', 'sector'), name='proyecto_territorio_sector_unico'), models.UniqueConstraint(condition=models.Q(('comuna__isnull', False)), fields=('proyecto', 'comuna'), name='proyecto_territorio_comuna_unico'), models.UniqueConstraint(condition=models.Q(('provincia__isnull', False)), fields=('proyecto', 'provincia'), name='proyecto_territorio_provincia_unico'), models.UniqueConstraint(condition=models.Q(('region__isnull', False)), fields=('proyecto', 'region'), name='proyecto_territorio_region_unico')],
            },
        ),
        migrations.RunPython(vincular, migrations.RunPython.noop),
    ]

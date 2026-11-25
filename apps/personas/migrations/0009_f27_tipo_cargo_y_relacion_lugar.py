# F27 · Vínculos con o sin cargo y relación precisa con un lugar. Aditiva y de datos (no borra nada):
# - `PersonaOrganizacion.tipo_cargo` pasa a ser opcional y sin «Funcional» por defecto; los vínculos con un rol sin
#   cargo (estudiante, vecina…) y sin cargo escrito quedan sin tipo de cargo (solo ese caso).
# - `PersonaLugar.tipo_relacion` (FK al catálogo «Relación con un lugar») se rellena desde el texto `relacion`, que se
#   conserva. La unicidad pasa de (persona, lugar, relacion) a (persona, lugar, tipo_relacion): el catálogo distingue
#   relaciones que el texto antiguo juntaba (trabaja ahí / dirige el lugar). Cambiar la restricción no borra filas.
# Al revertir, el FK se elimina y vuelve la restricción anterior; los tipos de cargo vaciados no se restauran.

import django.db.models.deletion
from django.db import migrations, models

from apps.personas.relacion_lugar import DESDE_ANTIGUA


def limpiar_tipo_cargo(apps, schema_editor):
    """Vínculo con rol sin cargo y sin cargo escrito → sin tipo de cargo. Una sola actualización."""
    Vinculo = apps.get_model("personas", "PersonaOrganizacion")
    return Vinculo.objects.filter(rol__con_cargo=False, cargo="").exclude(tipo_cargo="").update(tipo_cargo="")


def rellenar_tipo_relacion(apps, schema_editor):
    """`relacion` (texto) → `tipo_relacion` (catálogo). Una actualización por valor, no por fila."""
    Relacion = apps.get_model("nucleo", "RelacionLugar")
    PersonaLugar = apps.get_model("personas", "PersonaLugar")
    por_codigo = dict(Relacion.objects.values_list("codigo", "pk"))
    n = 0
    for antigua, codigo in DESDE_ANTIGUA.items():
        if codigo in por_codigo:
            n += PersonaLugar.objects.filter(tipo_relacion__isnull=True, relacion=antigua).update(tipo_relacion_id=por_codigo[codigo])
    return n


class Migration(migrations.Migration):

    dependencies = [
        ('lugares', '0001_initial'),
        ('nucleo', '0019_catalogos_descripcion_relacion_lugar'),
        ('personas', '0008_responsables_y_referentes'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='personalugar',
            name='persona_lugar_unico',
        ),
        migrations.AddField(
            model_name='historicalpersonalugar',
            name='tipo_relacion',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='nucleo.relacionlugar', verbose_name='qué hace ahí'),
        ),
        migrations.AddField(
            model_name='personalugar',
            name='tipo_relacion',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='nucleo.relacionlugar', verbose_name='qué hace ahí'),
        ),
        migrations.AlterField(
            model_name='historicalpersonalugar',
            name='relacion',
            field=models.CharField(choices=[('estudia', 'Estudia ahí'), ('trabaja', 'Trabaja ahí'), ('participa', 'Participa o asiste ahí'), ('vive', 'Vive ahí o al lado'), ('otra', 'Otra')], default='participa', max_length=12, verbose_name='qué hace ahí (anterior)'),
        ),
        migrations.AlterField(
            model_name='personalugar',
            name='relacion',
            field=models.CharField(choices=[('estudia', 'Estudia ahí'), ('trabaja', 'Trabaja ahí'), ('participa', 'Participa o asiste ahí'), ('vive', 'Vive ahí o al lado'), ('otra', 'Otra')], default='participa', max_length=12, verbose_name='qué hace ahí (anterior)'),
        ),
        migrations.AlterField(
            model_name='personaorganizacion',
            name='tipo_cargo',
            field=models.CharField(blank=True, choices=[('directorio', 'Directorio'), ('funcional', 'Funcional'), ('autoridad', 'Autoridad')], default='', max_length=12, verbose_name='tipo de cargo'),
        ),
        migrations.RunPython(limpiar_tipo_cargo, migrations.RunPython.noop),
        migrations.RunPython(rellenar_tipo_relacion, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='personalugar',
            constraint=models.UniqueConstraint(fields=('persona', 'lugar', 'tipo_relacion'), name='persona_lugar_relacion_unico'),
        ),
    ]

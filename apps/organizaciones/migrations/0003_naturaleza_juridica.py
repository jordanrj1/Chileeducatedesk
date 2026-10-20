# La naturaleza jurídica de la organización pasa a elegirse del catálogo. Aditiva y conservadora: agrega la columna nueva
# y, si el texto escrito antes coincide exactamente con un valor del catálogo (sin contar mayúsculas ni espacios de más),
# lo elige. El texto antiguo no se borra: queda como «texto anterior» para revisarlo. Repetirla no cambia nada.

import django.db.models.deletion
from django.db import migrations, models


def _clave(texto):
    return " ".join((texto or "").split()).casefold()


def enlazar(apps, schema_editor):
    Naturaleza = apps.get_model("nucleo", "NaturalezaJuridica")
    Organizacion = apps.get_model("organizaciones", "Organizacion")
    por_nombre = {}
    for n in Naturaleza.objects.all():
        por_nombre.setdefault(_clave(n.nombre), n.pk)
    for org in Organizacion.objects.filter(naturaleza__isnull=True).exclude(naturaleza_juridica=""):
        pk = por_nombre.get(_clave(org.naturaleza_juridica))
        if pk:
            Organizacion.objects.filter(pk=org.pk).update(naturaleza_id=pk)


class Migration(migrations.Migration):

    dependencies = [
        ('nucleo', '0014_naturaleza_juridica'),
        ('organizaciones', '0002_documento_y_fusion'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalorganizacion',
            name='naturaleza',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='nucleo.naturalezajuridica', verbose_name='naturaleza jurídica'),
        ),
        migrations.AddField(
            model_name='organizacion',
            name='naturaleza',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='nucleo.naturalezajuridica', verbose_name='naturaleza jurídica'),
        ),
        migrations.AlterField(
            model_name='historicalorganizacion',
            name='naturaleza_juridica',
            field=models.CharField(blank=True, max_length=120, verbose_name='naturaleza jurídica (texto anterior)'),
        ),
        migrations.AlterField(
            model_name='organizacion',
            name='naturaleza_juridica',
            field=models.CharField(blank=True, max_length=120, verbose_name='naturaleza jurídica (texto anterior)'),
        ),
        migrations.RunPython(enlazar, migrations.RunPython.noop),
    ]

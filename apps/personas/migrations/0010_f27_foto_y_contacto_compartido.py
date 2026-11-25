# F27 A2 · Aditiva (no borra nada):
# - `Persona.foto` (archivo en MEDIA_ROOT, servido por la vista protegida `personas:foto`) y su columna en el historial;
# - `Contacto.compartido`, `motivo_compartido` y `nota_compartido` (contacto repetido aprobado como compartido);
# - tipo de documento «Consentimiento firmado» (catálogo), para el respaldo común de los consentimientos.
# Al revertir se quitan las columnas; el valor del catálogo se conserva si ya lo usa algún documento.

import apps.personas.models
from django.db import migrations, models


def sembrar_tipo_consentimiento(apps, schema_editor):
    TipoDocumento = apps.get_model("nucleo", "TipoDocumento")
    TipoDocumento.objects.get_or_create(codigo="consentimiento", defaults={
        "nombre": "Consentimiento firmado", "orden": 90,
        "descripcion": "Formulario de consentimiento firmado por la persona o su apoderado (datos, imagen, contacto…)."})


class Migration(migrations.Migration):

    dependencies = [
        ('personas', '0009_f27_tipo_cargo_y_relacion_lugar'),
        ('nucleo', '0019_catalogos_descripcion_relacion_lugar'),
    ]

    operations = [
        migrations.AddField(
            model_name='contacto',
            name='compartido',
            field=models.BooleanField(default=False, verbose_name='compartido con otra persona'),
        ),
        migrations.AddField(
            model_name='contacto',
            name='motivo_compartido',
            field=models.CharField(blank=True, choices=[('familiar', 'Familiar'), ('apoderado', 'Apoderado o apoderada'), ('institucion', 'Teléfono o correo de la institución'), ('otro', 'Otro')], max_length=12, verbose_name='motivo'),
        ),
        migrations.AddField(
            model_name='contacto',
            name='nota_compartido',
            field=models.CharField(blank=True, max_length=150, verbose_name='nota'),
        ),
        migrations.AddField(
            model_name='historicalpersona',
            name='foto',
            field=models.TextField(blank=True, help_text='Solo para reconocer a la persona dentro del sistema; no se publica. JPG, PNG o WEBP de hasta 3 MB.', max_length=200, validators=[apps.personas.models.validar_foto], verbose_name='foto'),
        ),
        migrations.AddField(
            model_name='persona',
            name='foto',
            field=models.FileField(blank=True, help_text='Solo para reconocer a la persona dentro del sistema; no se publica. JPG, PNG o WEBP de hasta 3 MB.', max_length=200, upload_to=apps.personas.models.ruta_foto, validators=[apps.personas.models.validar_foto], verbose_name='foto'),
        ),
        migrations.RunPython(sembrar_tipo_consentimiento, migrations.RunPython.noop),
    ]

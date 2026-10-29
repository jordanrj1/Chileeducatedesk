# F26 P2: `PersonaOrganizacion.rol` (FK opcional al catálogo «Rol en la organización»). Aditiva: agrega la columna y la
# rellena leyendo el prefijo del cargo escrito («Docente de Lenguaje» → docente); sin coincidencia queda vacía. El cargo
# libre no se toca. Al revertir, la columna se elimina.

import django.db.models.deletion
from django.db import migrations, models

from apps.personas.rol_organizacion import codigo_desde_cargo


def rellenar_rol(apps, schema_editor):
    """Una consulta para los roles y una actualización por rol (no por fila)."""
    Rol = apps.get_model("nucleo", "RolOrganizacion")
    Vinculo = apps.get_model("personas", "PersonaOrganizacion")
    roles = dict(Rol.objects.values_list("codigo", "pk"))
    por_rol = {}
    for pk, cargo in Vinculo.objects.filter(rol__isnull=True).exclude(cargo="").values_list("pk", "cargo"):
        codigo = codigo_desde_cargo(cargo)
        if codigo in roles:
            por_rol.setdefault(roles[codigo], []).append(pk)
    for rol_id, pks in por_rol.items():
        Vinculo.objects.filter(pk__in=pks).update(rol_id=rol_id)


class Migration(migrations.Migration):

    dependencies = [
        ('nucleo', '0018_rol_organizacion'),
        ('personas', '0006_persona_lugar'),
    ]

    operations = [
        migrations.AddField(
            model_name='personaorganizacion',
            name='rol',
            field=models.ForeignKey(blank=True, help_text='Ej.: Docente. El detalle va en el cargo (Profesora de Lenguaje).', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='nucleo.rolorganizacion', verbose_name='rol en la organización'),
        ),
        migrations.RunPython(rellenar_rol, migrations.RunPython.noop),
    ]

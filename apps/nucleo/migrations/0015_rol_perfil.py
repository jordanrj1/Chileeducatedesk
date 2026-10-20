# Cada rol de participación puede llevar un perfil de persona: al sumar a alguien con ese rol, se le agrega el perfil.
# Aditiva: agrega el campo y asigna el perfil inicial solo a los roles que no tienen uno (se puede volver a ejecutar
# sin pisar lo editado en Catálogos). Si un rol o un perfil no existe, se salta.

import django.db.models.deletion
from django.db import migrations, models

ROL_A_PERFIL = {
    "estudiante": "estudiante",
    "practicante": "estudiante",
    "ayudante": "estudiante",
    "voluntario": "voluntario_o_voluntaria",
    "tallerista": "tallerista_o_profesional",
    "tutor": "docente_o_academico",
    "beneficiario": "beneficiario_o_beneficiaria",
    "contacto_institucional": "funcionario_institucional",
}


def asignar(apps, schema_editor):
    Rol = apps.get_model("nucleo", "RolParticipacion")
    Perfil = apps.get_model("nucleo", "PerfilPersona")
    perfiles = {p.codigo: p for p in Perfil.objects.filter(codigo__in=set(ROL_A_PERFIL.values()))}
    for rol in Rol.objects.filter(codigo__in=ROL_A_PERFIL, perfil__isnull=True):
        perfil = perfiles.get(ROL_A_PERFIL[rol.codigo])
        if perfil:
            rol.perfil = perfil
            rol.save(update_fields=["perfil"])


class Migration(migrations.Migration):

    dependencies = [
        ('nucleo', '0014_naturaleza_juridica'),
    ]

    operations = [
        migrations.AddField(
            model_name='rolparticipacion',
            name='perfil',
            field=models.ForeignKey(blank=True, help_text='Perfil que se agrega a la persona al sumarla con este rol. Ej.: Voluntario → Voluntario o voluntaria.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='nucleo.perfilpersona'),
        ),
        migrations.RunPython(asignar, migrations.RunPython.noop),
    ]

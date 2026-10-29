# F26 P2 · Una sola verdad para responsables y referentes, aplicada a lo ya registrado. Solo de datos y conservadora:
# SOLO CREA las filas que faltan; nunca borra ni cambia otras. Repetirla no cambia nada. Revertirla no hace nada.
# - Proyecto con responsable que no está en su equipo → ProyectoPersona (equipo, responsable).
# - Actividad o tarea con responsable que no está en su equipo ejecutor → Participacion «Inscrito» con el rol
#   Coordinador (o el primer rol activo del equipo ejecutor), como hace actividades.servicios.asegurar_responsable_en_equipo.
# - Comunidad con referente que no está en su padrón → ComunidadMiembro con rol «referente».

from django.db import migrations


def aplicar(apps, schema_editor):
    Proyecto = apps.get_model("proyectos", "Proyecto")
    ProyectoPersona = apps.get_model("proyectos", "ProyectoPersona")
    Actividad = apps.get_model("actividades", "Actividad")
    Participacion = apps.get_model("actividades", "Participacion")
    Comunidad = apps.get_model("comunidades", "Comunidad")
    ComunidadMiembro = apps.get_model("comunidades", "ComunidadMiembro")
    RolParticipacion = apps.get_model("nucleo", "RolParticipacion")
    EstadoParticipacion = apps.get_model("nucleo", "EstadoParticipacion")

    # Proyectos
    en_equipo = set(ProyectoPersona.objects.filter(tipo="equipo").values_list("proyecto_id", "persona_id"))
    ProyectoPersona.objects.bulk_create([
        ProyectoPersona(proyecto_id=p, persona_id=r, tipo="equipo", es_responsable=True, vigente=True)
        for p, r in Proyecto.objects.filter(responsable__isnull=False).values_list("pk", "responsable_id") if (p, r) not in en_equipo
    ])

    # Actividades y tareas
    roles = RolParticipacion.objects.filter(activo=True, grupo="ejecutor").order_by("orden", "nombre")
    rol = roles.filter(codigo="coordinador").first() or roles.first()
    estado = EstadoParticipacion.objects.filter(codigo="confirmado").first()
    if rol is not None and estado is not None:
        ya = set(Participacion.objects.filter(rol__grupo="ejecutor").exclude(estado__codigo="registro_erroneo")
                 .values_list("actividad_id", "persona_id"))
        con_rol = set(Participacion.objects.filter(rol=rol).values_list("actividad_id", "persona_id"))  # (actividad, persona, rol) es único
        Participacion.objects.bulk_create([
            Participacion(actividad_id=a, persona_id=r, rol=rol, estado=estado)
            for a, r in Actividad.objects.filter(responsable__isnull=False).values_list("pk", "responsable_id")
            if (a, r) not in ya and (a, r) not in con_rol
        ])

    # Comunidades
    en_padron = set(ComunidadMiembro.objects.values_list("comunidad_id", "persona_id"))
    ComunidadMiembro.objects.bulk_create([
        ComunidadMiembro(comunidad_id=c, persona_id=r, rol="referente", vigente=True)
        for c, r in Comunidad.objects.filter(referente__isnull=False).values_list("pk", "referente_id") if (c, r) not in en_padron
    ])


class Migration(migrations.Migration):
    dependencies = [
        ("personas", "0007_vinculo_rol"),
        ("proyectos", "0003_proyecto_territorio"),
        ("actividades", "0010_participacion_cargo"),
        ("comunidades", "0002_tramos_etarios"),
        ("nucleo", "0018_rol_organizacion"),
    ]

    operations = [migrations.RunPython(aplicar, migrations.RunPython.noop)]

"""F26 P2: informe de diferencias (datos con dos verdades). Solo lee: nunca escribe.
Cada categoría es una consulta para la cifra y otra para hasta `limite` ejemplos (id, texto y enlace relativo), sin
consultas por fila. Lo usa `manage.py diferencias_datos`."""
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone


def _vigente_po(hoy):
    return Q(fecha_termino__isnull=True) | Q(fecha_termino__gte=hoy)


def _categoria(clave, titulo, qs, fila, limite):
    return {"clave": clave, "titulo": titulo, "cifra": qs.count(), "ejemplos": [fila(o) for o in qs[:limite]]}


def _participaciones(hoy):
    from apps.actividades.models import Participacion
    from apps.comunidades.models import ComunidadMiembro
    from apps.personas.models import PersonaFormacion, PersonaOrganizacion

    # .values("pk") en las subconsultas: no leen columnas que aún no existan en una base sin migrar
    vinculo = PersonaOrganizacion.objects.filter(_vigente_po(hoy), persona_id=OuterRef("persona_id"), organizacion_id=OuterRef("institucion_id")).values("pk")
    formacion = PersonaFormacion.objects.filter(vigente=True, persona_id=OuterRef("persona_id"), organizacion_id=OuterRef("institucion_id")).values("pk")
    miembro = ComunidadMiembro.objects.filter(vigente=True, persona_id=OuterRef("persona_id"), comunidad_id=OuterRef("comunidad_id")).values("pk")
    base = Participacion.objects.exclude(estado__codigo="registro_erroneo").select_related("persona", "actividad", "institucion", "comunidad").order_by("pk")
    inst = base.filter(institucion__isnull=False).exclude(Exists(vinculo)).exclude(Exists(formacion))
    com = base.filter(comunidad__isnull=False).exclude(Exists(miembro))
    return inst, com


def diferencias(limite=20):
    """Lista de categorías: {"clave", "titulo", "cifra", "ejemplos": [{"id", "texto", "url"}]}."""
    from apps.actividades.models import Actividad, Participacion
    from apps.comunidades.models import Comunidad, ComunidadMiembro
    from apps.personas.models import Persona, PersonaDireccion, PersonaFormacion
    from apps.proyectos.models import Proyecto, ProyectoPersona

    hoy = timezone.localdate()
    res = []
    inst, com = _participaciones(hoy)

    def fila_part(campo):
        return lambda p: {"id": p.pk, "texto": f"{p.persona} en «{p.actividad}»: {getattr(p, campo)}", "url": f"{p.actividad.get_absolute_url()}?tab=participantes"}

    res.append(_categoria("participacion_institucion", "Participaciones cuya institución no está en un vínculo vigente de la persona (ni en su formación)",
                          inst, fila_part("institucion"), limite))
    res.append(_categoria("participacion_comunidad", "Participaciones cuya comunidad no está en el padrón vigente de la persona",
                          com, fila_part("comunidad"), limite))

    en_padron = ComunidadMiembro.objects.filter(vigente=True, comunidad_id=OuterRef("pk"), persona_id=OuterRef("referente_id")).values("pk")
    referentes = Comunidad.objects.filter(referente__isnull=False).exclude(Exists(en_padron)).select_related("referente").order_by("pk")
    res.append(_categoria("referente_fuera_padron", "Comunidades cuyo referente no está en su padrón vigente", referentes,
                          lambda c: {"id": c.pk, "texto": f"{c}: {c.referente}", "url": c.get_absolute_url()}, limite))

    en_equipo = Participacion.objects.filter(actividad_id=OuterRef("pk"), persona_id=OuterRef("responsable_id")).exclude(estado__codigo="registro_erroneo").values("pk")
    actividades = Actividad.objects.filter(responsable__isnull=False).exclude(Exists(en_equipo)).select_related("responsable").order_by("pk")
    res.append(_categoria("responsable_actividad_fuera_equipo", "Actividades o tareas cuyo responsable no está entre sus participantes", actividades,
                          lambda a: {"id": a.pk, "texto": f"{a.nombre}: {a.responsable}", "url": a.get_absolute_url()}, limite))

    en_proyecto = ProyectoPersona.objects.filter(proyecto_id=OuterRef("pk"), persona_id=OuterRef("responsable_id"), tipo="equipo", vigente=True).values("pk")
    proyectos = Proyecto.objects.filter(responsable__isnull=False).exclude(Exists(en_proyecto)).select_related("responsable").order_by("pk")
    res.append(_categoria("responsable_proyecto_fuera_equipo", "Proyectos cuyo responsable no está en el equipo vigente", proyectos,
                          lambda p: {"id": p.pk, "texto": f"{p.nombre}: {p.responsable}", "url": p.get_absolute_url()}, limite))

    personas = Persona.objects.filter(activo=True).order_by("pk")
    fila_persona = lambda p: {"id": p.pk, "texto": str(p), "url": p.get_absolute_url()}  # noqa: E731
    formacion = PersonaFormacion.objects.filter(persona_id=OuterRef("pk"), vigente=True).values("pk")
    res.append(_categoria("perfil_estudiante_sin_formacion", "Personas con perfil de estudiante sin formación vigente",
                          personas.filter(perfiles__ficha="estudiante").distinct().exclude(Exists(formacion)), fila_persona, limite))
    residencia = PersonaDireccion.objects.filter(persona_id=OuterRef("pk"), tipo="residencia", vigente=True).values("pk")
    comunidad = ComunidadMiembro.objects.filter(persona_id=OuterRef("pk"), vigente=True).values("pk")
    res.append(_categoria("perfil_vecino_sin_territorio", "Personas con perfil de vecino o vecina sin dirección de residencia ni comunidad vigente",
                          personas.filter(perfiles__ficha="vecino").distinct().exclude(Exists(residencia)).exclude(Exists(comunidad)), fila_persona, limite))
    res.append(_categoria("perfil_invitado_sin_ficha", "Personas con perfil de invitado o invitada sin su ficha de invitado",
                          personas.filter(perfiles__ficha="invitado", ficha_invitado__isnull=True).distinct(), fila_persona, limite))
    res.append(_categoria("perfil_voluntario_sin_ficha", "Personas con perfil de voluntario o voluntaria sin su ficha de voluntariado",
                          personas.filter(perfiles__ficha="voluntario", ficha_voluntario__isnull=True).distinct(), fila_persona, limite))

    sedes = PersonaFormacion.objects.exclude(sede="").filter(sede_institucion__isnull=True).select_related("persona", "organizacion").order_by("pk")
    res.append(_categoria("sede_en_texto", "Formaciones con la sede escrita como texto, sin la sede registrada", sedes,
                          lambda f: {"id": f.pk, "texto": f"{f.persona} · {f.organizacion}: «{f.sede}»", "url": f"{f.persona.get_absolute_url()}?tab=estudios"},
                          limite))
    return res

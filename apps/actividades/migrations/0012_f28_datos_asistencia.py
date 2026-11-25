# F28 punto 6 (specs/f28/spec.md): la asistencia pasa a las jornadas. Solo de datos; al revertir no hace nada.
# - Las marcas de las sesiones (asistió sí / no) pasan a Presente / Ausente; las listas con marcas quedan cerradas como
#   «migradas».
# - En las actividades con asistencia marcada y sin jornadas se crea la jornada 1, con la fecha vigente de la agenda; cada
#   marca pasa a esa jornada (verdadero → Presente; falso → Ausente; una por persona) y la lista queda cerrada como «migrada».
# - Las participaciones en «Asistió» o «No asistió» vuelven a «Inscrito» (código confirmado): vuelven a su tarea.
# - «Inscrita desde» de cada participación: la fecha más temprana entre su alta, su primera jornada y la fecha programada,
#   para que nadie desaparezca de las listas que ya existían [P].
# - Todo queda en el historial de cada registro (motivo «F28: …») y en la auditoría («asistencia_migrada»).
from django.db import migrations
from django.utils import timezone

MOTIVO = "F28: asistencia por jornada"


def _historia(Hist, obj, tipo, ahora):
    datos = {f.attname: getattr(obj, f.attname) for f in obj._meta.concrete_fields}
    Hist.objects.create(**datos, history_date=ahora, history_type=tipo, history_change_reason=MOTIVO, history_user_id=None)


def migrar(apps, schema_editor):
    Estado = apps.get_model("nucleo", "EstadoParticipacion")
    Auditoria = apps.get_model("nucleo", "Auditoria")
    Actividad = apps.get_model("actividades", "Actividad")
    Agenda = apps.get_model("actividades", "AgendaActividad")
    Part = apps.get_model("actividades", "Participacion")
    HPart = apps.get_model("actividades", "HistoricalParticipacion")
    Sesion = apps.get_model("actividades", "SesionActividad")
    HSesion = apps.get_model("actividades", "HistoricalSesionActividad")
    Marca = apps.get_model("actividades", "SesionAsistencia")
    HMarca = apps.get_model("actividades", "HistoricalSesionAsistencia")
    Cambio = apps.get_model("actividades", "CambioLista")
    ahora = timezone.now()
    resumen = {}  # actividad_id -> [textos]

    def anotar(actividad_id, texto):
        resumen.setdefault(actividad_id, []).append(texto)

    # 1. Marcas de las sesiones: asistió sí / no → Presente / Ausente
    for m in Marca.objects.filter(marca="", asistio__isnull=False):
        m.marca = "presente" if m.asistio else "ausente"
        m.save(update_fields=["marca"])
        _historia(HMarca, m, "~", ahora)
    # 2. Las listas de las sesiones con marcas quedan cerradas como «migradas»
    con_marcas = Marca.objects.exclude(marca="").values("sesion_id")
    for s in Sesion.objects.filter(pk__in=con_marcas).exclude(estado_lista="cerrada"):
        s.estado_lista, s.cerrada_en, s.version_lista = "cerrada", ahora, (s.version_lista or 0) + 1
        s.save(update_fields=["estado_lista", "cerrada_en", "version_lista"])
        _historia(HSesion, s, "~", ahora)
        Cambio.objects.create(sesion=s, accion="migrada", motivo="Lista con las marcas de la sesión anterior a F28.")
        anotar(s.actividad_id, f"sesión {s.numero}: lista cerrada como migrada")

    # 3. Actividades con asistencia marcada y sin jornadas: jornada 1 con la fecha vigente de la agenda
    erroneo = list(Estado.objects.filter(codigo="registro_erroneo").values_list("pk", flat=True))
    con_asistencia = set(Part.objects.filter(asistencia__isnull=False).exclude(estado_id__in=erroneo).values_list("actividad_id", flat=True))
    con_jornadas = set(Sesion.objects.values_list("actividad_id", flat=True))
    for aid in sorted(con_asistencia - con_jornadas):
        agenda = (Agenda.objects.filter(actividad_id=aid, vigente=True).first()
                  or Agenda.objects.filter(actividad_id=aid).order_by("-version").first())
        partes = list(Part.objects.filter(actividad_id=aid).exclude(estado_id__in=erroneo).select_related("rol").order_by("rol__orden", "rol_id", "pk"))
        fecha = agenda.fecha if agenda else min((p.fecha for p in partes if p.fecha), default=timezone.localdate())
        j = Sesion.objects.create(actividad_id=aid, numero=1, fecha=fecha, hora_inicio=agenda.hora_inicio if agenda else None,
                                  hora_fin=agenda.hora_fin if agenda else None, lugar_id=agenda.lugar_id if agenda else None,
                                  estado_lista="cerrada", cerrada_en=ahora, version_lista=1)
        _historia(HSesion, j, "+", ahora)
        por_persona = {}
        for p in partes:
            if p.asistencia is not None:
                por_persona.setdefault(p.persona_id, []).append(p)
        n = 0
        for suyas in por_persona.values():
            vino = [p for p in suyas if p.asistencia]
            p = vino[0] if vino else suyas[0]
            m = Marca.objects.create(sesion=j, participacion=p, marca="presente" if vino else "ausente", asistio=bool(vino))
            _historia(HMarca, m, "+", ahora)
            n += 1
        Cambio.objects.create(sesion=j, accion="migrada", motivo="Jornada 1 creada con la asistencia anterior a F28.")
        anotar(aid, f"jornada 1 ({fecha:%d-%m-%Y}) con {n} marcas, lista cerrada como migrada")

    # 4. «Asistió» y «No asistió» vuelven a «Inscrito»
    confirmado = Estado.objects.filter(codigo="confirmado").first()
    viejos = list(Estado.objects.filter(codigo__in=["asistio", "no_asistio"]).values_list("pk", flat=True))
    if confirmado and viejos:
        cuantas = {}
        for p in Part.objects.filter(estado_id__in=viejos):
            p.estado_id = confirmado.pk
            p.save(update_fields=["estado"])
            _historia(HPart, p, "~", ahora)
            cuantas[p.actividad_id] = cuantas.get(p.actividad_id, 0) + 1
        for aid, n in cuantas.items():
            anotar(aid, f"{n} inscripciones en «Asistió» o «No asistió» vuelven a «Inscrito»")

    # 5. «Inscrita desde»: la fecha más temprana entre su alta, su primera jornada y la fecha programada
    primera = {}
    for aid, f in Sesion.objects.filter(vigente=True, fecha__isnull=False).values_list("actividad_id", "fecha"):
        primera[aid] = min(f, primera.get(aid, f))
    programada = dict(Agenda.objects.filter(vigente=True).values_list("actividad_id", "fecha"))
    pendientes = []
    for p in Part.objects.filter(inscrito_en__isnull=True).only("pk", "actividad_id", "fecha"):
        candidatas = [f for f in (p.fecha, primera.get(p.actividad_id), programada.get(p.actividad_id)) if f]
        if candidatas:
            p.inscrito_en = min(candidatas)
            pendientes.append(p)
    Part.objects.bulk_update(pendientes, ["inscrito_en"], batch_size=500)

    nombres = dict(Actividad.objects.filter(pk__in=list(resumen)).values_list("pk", "nombre"))
    for aid, textos in resumen.items():
        Auditoria.objects.create(usuario=None, usuario_nombre="", accion="asistencia_migrada", objeto=str(nombres.get(aid, aid))[:200],
                                 detalle=f"{MOTIVO}: " + "; ".join(textos))


class Migration(migrations.Migration):
    dependencies = [
        ("actividades", "0011_f28_asistencia_por_jornada"),
        ("nucleo", "0020_estado_retirado"),
    ]
    operations = [migrations.RunPython(migrar, migrations.RunPython.noop)]

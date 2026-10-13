"""F16 — Búsqueda asistida. Propone candidatos con razones y conflictos; nunca asigna por sí sola."""
from dataclasses import dataclass, field

from django.db.models import Count, Q

from apps.lugares.models import Lugar
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona

from .reglas import conflictos_de_persona, fuera_de_disponibilidad, intervalo, participaciones_activas, se_solapan


@dataclass
class Candidato:
    objeto: object
    estado: str  # ok | sin_datos | conflicto
    razones: list = field(default_factory=list)
    puntaje: int = 0


ORDEN = {"ok": 0, "sin_datos": 1, "conflicto": 2}


def _ordenar(lista):
    return sorted(lista, key=lambda c: (ORDEN[c.estado], -c.puntaje))


def buscar_personas(actividad, texto="", area="", institucion=None, carrera=None, comuna=None, solo_disponibles=False, limite=60):
    ya = actividad.participaciones.values_list("persona_id", flat=True)
    qs = Persona.objects.filter(activo=True).exclude(pk__in=ya).exclude(estado_registro__codigo__in=["fallecida", "fusionada"]).buscar(texto)
    if institucion:
        qs = qs.filter(formaciones__organizacion_id=institucion, formaciones__vigente=True)
    if carrera:
        qs = qs.filter(formaciones__carrera_id=carrera)
    if comuna:
        qs = qs.filter(direcciones__direccion__comuna_id=comuna, direcciones__vigente=True)
    if area:
        qs = qs.filter(Q(profesion__unaccent__icontains=area) | Q(formaciones__carrera__nombre__unaccent__icontains=area) | Q(experiencias__descripcion__unaccent__icontains=area))
    qs = qs.annotate(n_actividades=Count("participaciones", distinct=True)).distinct().order_by("-n_actividades", "apellido_paterno")[: limite * 3]
    agenda = actividad.agenda_vigente
    res = []
    for p in qs:
        razones, estado = [], "sin_datos"
        if agenda and agenda.hora_inicio:
            conflictos = conflictos_de_persona(p, agenda, excluir_actividad=actividad)
            if conflictos:
                estado = "conflicto"
                razones += [f"Conflicto de horario: «{c.actividad}» a las {c.hora_inicio:%H:%M}" for c in conflictos]
            elif fuera_de_disponibilidad(p, agenda):
                estado = "conflicto"
                razones.append("Declaró disponibilidad en otros horarios")
            elif p.disponibilidades.filter(vigente=True).exists():
                estado = "ok"
                razones.append("Disponible en ese horario")
            else:
                razones.append("Sin horarios declarados")
        else:
            razones.append("La actividad aún no tiene fecha y hora: no se puede revisar la disponibilidad")
        if p.n_actividades:
            razones.append(f"Ha participado en {p.n_actividades} actividad(es)")
        c = Candidato(p, estado, razones, p.n_actividades)
        if solo_disponibles and estado == "conflicto":
            continue
        res.append(c)
    return _ordenar(res)[:limite]


def buscar_lugares(actividad, cantidad=None, comuna=None, texto="", limite=40):
    agenda = actividad.agenda_vigente
    cantidad = cantidad or len(participaciones_activas(actividad)) or None
    qs = Lugar.objects.filter(activo=True).select_related("direccion__comuna", "tipo")
    if comuna:
        qs = qs.filter(direccion__comuna_id=comuna)
    if texto:
        qs = qs.filter(Q(nombre__unaccent__icontains=texto) | Q(direccion__calle__unaccent__icontains=texto))
    res = []
    for l in qs[: limite * 3]:
        razones, estado = [], "ok"
        if l.capacidad is None:
            estado = "sin_datos"
            razones.append("Sin capacidad registrada")
        elif cantidad and l.capacidad < cantidad:
            estado = "conflicto"
            razones.append(f"Capacidad {l.capacidad} para {cantidad} participantes")
        else:
            razones.append(f"Capacidad {l.capacidad}")
        if agenda and agenda.hora_inicio:
            mio = intervalo(agenda.hora_inicio, agenda.hora_fin)
            for o in l.agendas.filter(vigente=True, fecha=agenda.fecha).exclude(actividad=actividad).exclude(actividad__estado__codigo__in=("cancelada", "suspendida", "pendiente")).select_related("actividad"):
                if se_solapan(mio, intervalo(o.hora_inicio, o.hora_fin)):
                    estado = "conflicto"
                    razones.append(f"Ocupado por «{o.actividad}» a las {o.hora_inicio:%H:%M}")
        if l.condiciones:
            razones.append(f"Condiciones: {l.condiciones[:80]}")
        res.append(Candidato(l, estado, razones))
    return _ordenar(res)[:limite]


def buscar_organizaciones(actividad, tipo=None, comuna=None, texto="", limite=40):
    ya = actividad.organizaciones.values_list("organizacion_id", flat=True)
    qs = Organizacion.objects.filter(activo=True).exclude(pk__in=ya).select_related("tipo", "direccion__comuna")
    if tipo:
        qs = qs.filter(tipo_id=tipo)
    if comuna:
        qs = qs.filter(Q(direccion__comuna_id=comuna) | Q(comuna_municipal_id=comuna))
    if texto:
        qs = qs.filter(nombre__unaccent__icontains=texto)
    qs = qs.annotate(n_actividades=Count("actividades", distinct=True)).order_by("-n_actividades", "nombre")[:limite]
    res = []
    for o in qs:
        razones = [f"Ha intervenido en {o.n_actividades} actividad(es)"] if o.n_actividades else ["Sin actividades previas"]
        res.append(Candidato(o, "ok" if o.n_actividades else "sin_datos", razones, o.n_actividades))
    return _ordenar(res)

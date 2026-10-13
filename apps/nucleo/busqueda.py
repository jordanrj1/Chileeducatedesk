"""F15 — Búsqueda transversal. Cada tipo respeta el permiso de ver ese tipo de registro."""
from dataclasses import dataclass
from datetime import date

from django.db.models import Q

TIPOS = [
    ("persona", "Personas"), ("organizacion", "Organizaciones"), ("proyecto", "Proyectos"), ("actividad", "Actividades"),
    ("lugar", "Lugares"), ("reunion", "Reuniones"), ("documento", "Documentos"),
]
LIMITE_POR_TIPO = 200


@dataclass
class Resultado:
    tipo: str
    titulo: str
    url: str
    detalle: str = ""
    estado: str = ""
    fecha: str = ""


def _fecha(txt):
    try:
        return date.fromisoformat(txt) if txt else None
    except ValueError:
        return None


def _personas(u, f):
    from apps.personas.models import Persona

    qs = Persona.objects.filter(activo=True).buscar(f["q"]).select_related("estado_registro")
    if f["comuna"]:
        qs = qs.filter(direcciones__direccion__comuna_id=f["comuna"], direcciones__vigente=True)
    if f["estado_registro"]:
        qs = qs.filter(estado_registro__codigo=f["estado_registro"])
    if f["tipo_actividad"]:
        qs = qs.filter(participaciones__actividad__tipo_id=f["tipo_actividad"])
    for p in qs.distinct()[:LIMITE_POR_TIPO]:
        n = p.participaciones.count()
        det = " · ".join(x for x in [p.profesion, f"{n} participación(es)" if n else "", str(p.estado_registro or "")] if x)
        yield Resultado("persona", p.nombre_completo, p.get_absolute_url(), det)


def _organizaciones(u, f):
    from django.db.models import Count

    from apps.organizaciones.models import Organizacion

    qs = Organizacion.objects.filter(activo=True)
    if f["q"]:
        digitos = "".join(c for c in f["q"] if c.isdigit())
        cond = Q(nombre__icontains=f["q"]) | Q(otro_identificador__icontains=f["q"]) | Q(descripcion__icontains=f["q"])
        if len(digitos) >= 4:
            cond |= Q(rut_numero__icontains=digitos)
        qs = qs.filter(cond)
    if f["comuna"]:
        qs = qs.filter(Q(direccion__comuna_id=f["comuna"]) | Q(comuna_municipal_id=f["comuna"]))
    if f["con_actividades"]:
        qs = qs.filter(actividades__isnull=False)
    qs = qs.select_related("tipo").annotate(n=Count("actividades", distinct=True)).distinct()[:LIMITE_POR_TIPO]
    for o in qs:
        yield Resultado("organizacion", o.nombre, o.get_absolute_url(), f"{o.tipo} · {o.n} actividad(es)")


def _proyectos(u, f):
    from apps.proyectos.models import Proyecto

    qs = Proyecto.objects.all()
    if f["q"]:
        qs = qs.filter(Q(nombre__icontains=f["q"]) | Q(descripcion__icontains=f["q"]) | Q(zona__icontains=f["q"]) | Q(objetivo_general__icontains=f["q"]))
    if f["desde"]:
        qs = qs.filter(Q(fecha_termino__gte=f["desde"]) | Q(fecha_termino__isnull=True))
    if f["hasta"]:
        qs = qs.filter(Q(fecha_inicio__lte=f["hasta"]) | Q(fecha_inicio__isnull=True))
    if f["zona_nombre"]:
        qs = qs.filter(zona__icontains=f["zona_nombre"])
    for p in qs[:LIMITE_POR_TIPO]:
        yield Resultado("proyecto", p.nombre, p.get_absolute_url(), p.zona, p.get_estado_display(), f"{p.fecha_inicio:%d-%m-%Y}" if p.fecha_inicio else "")


def _actividades(u, f):
    from apps.actividades.models import Actividad, AgendaActividad
    from django.db.models import Exists, OuterRef

    qs = Actividad.objects.select_related("estado", "proyecto", "tipo")
    if f["q"]:
        qs = qs.filter(Q(nombre__icontains=f["q"]) | Q(objetivo__icontains=f["q"]) | Q(descripcion__icontains=f["q"]) | Q(proyecto__nombre__icontains=f["q"]))
    if f["estado"]:
        qs = qs.filter(estado__codigo=f["estado"])
    if f["tipo_actividad"]:
        qs = qs.filter(tipo_id=f["tipo_actividad"])
    if f["comuna"]:
        qs = qs.filter(Q(agendas__vigente=True, agendas__lugar__direccion__comuna_id=f["comuna"]) | Q(territorios__vigente=True, territorios__comuna_id=f["comuna"])).distinct()
    if f["desde"] or f["hasta"]:
        ag = AgendaActividad.objects.filter(actividad=OuterRef("pk"), vigente=True)
        if f["desde"]:
            ag = ag.filter(fecha__gte=f["desde"])
        if f["hasta"]:
            ag = ag.filter(fecha__lte=f["hasta"])
        qs = qs.filter(Exists(ag))
    for a in qs[:LIMITE_POR_TIPO]:
        ag = a.agenda_vigente
        det = " · ".join(x for x in [str(a.proyecto) if a.proyecto_id else "", str(a.tipo) if a.tipo_id else "", str(ag.lugar) if ag and ag.lugar else ""] if x)
        yield Resultado("actividad", a.nombre, a.get_absolute_url(), det, a.estado.nombre, f"{ag.fecha:%d-%m-%Y}" if ag else "")


def _lugares(u, f):
    from apps.lugares.models import Lugar

    qs = Lugar.objects.filter(activo=True).select_related("direccion__comuna", "tipo")
    if f["q"]:
        qs = qs.filter(Q(nombre__icontains=f["q"]) | Q(direccion__calle__icontains=f["q"]) | Q(condiciones__icontains=f["q"]))
    if f["comuna"]:
        qs = qs.filter(direccion__comuna_id=f["comuna"])
    for l in qs[:LIMITE_POR_TIPO]:
        yield Resultado("lugar", l.nombre, l.get_absolute_url(), f"{l.tipo} · {l.direccion.comuna}" + (f" · capacidad {l.capacidad}" if l.capacidad else ""))


def _reuniones(u, f):
    from apps.coordinacion.models import Reunion

    qs = Reunion.objects.all()
    if f["q"]:
        qs = qs.filter(Q(titulo__icontains=f["q"]) | Q(objetivo__icontains=f["q"]) | Q(temas__icontains=f["q"]) | Q(acuerdos__icontains=f["q"]))
    if f["desde"]:
        qs = qs.filter(fecha__gte=f["desde"])
    if f["hasta"]:
        qs = qs.filter(fecha__lte=f["hasta"])
    for r in qs[:LIMITE_POR_TIPO]:
        yield Resultado("reunion", r.titulo, r.get_absolute_url(), str(r.actividad or r.proyecto or ""), "", f"{r.fecha:%d-%m-%Y}")


def _documentos(u, f):
    from apps.documentos.models import Documento

    qs = Documento.objects.filter(activo=True).select_related("tipo")
    if not u.has_perm("documentos.ver_restringido"):
        qs = qs.filter(restringido=False)
    if f["q"]:
        qs = qs.filter(Q(nombre__icontains=f["q"]) | Q(descripcion__icontains=f["q"]) | Q(folio__icontains=f["q"]) | Q(emisor__icontains=f["q"]))
    if f["desde"]:
        qs = qs.filter(fecha__gte=f["desde"])
    if f["hasta"]:
        qs = qs.filter(fecha__lte=f["hasta"])
    for d in qs[:LIMITE_POR_TIPO]:
        yield Resultado("documento", d.nombre, d.get_absolute_url(), str(d.tipo), "", f"{d.fecha:%d-%m-%Y}")


PROVEEDORES = {
    "persona": ("personas.view_persona", _personas), "organizacion": ("organizaciones.view_organizacion", _organizaciones),
    "proyecto": ("proyectos.view_proyecto", _proyectos), "actividad": ("actividades.view_actividad", _actividades),
    "lugar": ("lugares.view_lugar", _lugares), "reunion": ("coordinacion.view_reunion", _reuniones), "documento": ("documentos.view_documento", _documentos),
}


def buscar(user, params):
    from apps.territorio.models import Comuna

    entero = lambda k: int(params[k]) if params.get(k, "").isdigit() else None
    comuna = entero("zona")
    f = {
        "q": params.get("q", "").strip(), "estado": params.get("estado", ""), "estado_registro": params.get("registro", ""),
        "comuna": comuna, "zona_nombre": (Comuna.objects.filter(pk=comuna).values_list("nombre", flat=True).first() or "") if comuna else "",
        "desde": _fecha(params.get("desde")), "hasta": _fecha(params.get("hasta")), "tipo_actividad": entero("tipo_actividad"),
        "con_actividades": params.get("con_actividades") == "1",
    }
    tipo = params.get("tipo", "")
    resultados = []
    for clave, (perm, proveedor) in PROVEEDORES.items():
        if tipo and tipo != clave:
            continue
        if not user.has_perm(perm):
            continue
        if clave == "reunion":
            from .fases import modulo_activo

            if not modulo_activo("reuniones"):
                continue
        # «Estado» y «tipo de actividad» solo tienen sentido para actividades y personas
        if f["estado"] and clave not in ("actividad",):
            continue
        resultados.extend(proveedor(user, f))
    return resultados

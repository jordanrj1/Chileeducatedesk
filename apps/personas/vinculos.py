"""Cargos y vínculos de una persona, reunidos desde todas partes: organizaciones con cargo, estudios, comunidades,
proyectos y actividades o tareas. Sirve para ver de un vistazo qué cargos ostenta hoy y cuáles tuvo, con enlaces.
También agrupa a los estudiantes de una institución por carrera, para la ficha de la organización.
Cada grupo usa una sola consulta, sin importar cuántos registros tenga.
F26 P2: `vincular()` es la única puerta para crear o reutilizar el vínculo de una persona con una organización, sus
estudios o su comunidad, desde cualquier pantalla que lo haga de paso."""
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from .rol_organizacion import codigo_desde_cargo


def _vigente(activo, hasta):
    """Vigente si no se dio de baja y su fecha de término no pasó."""
    return bool(activo) and (hasta is None or hasta >= timezone.localdate())


def _periodo(desde, hasta):
    if not desde and not hasta:
        return ""
    return f"{desde:%d-%m-%Y} a {hasta:%d-%m-%Y}" if desde and hasta else (f"desde {desde:%d-%m-%Y}" if desde else f"hasta {hasta:%d-%m-%Y}")


def _rol_organizacion(rol, cargo):
    """(RolOrganizacion o None, código). `rol` acepta un valor del catálogo, un rol de participación o un código;
    si no se da, se deduce del prefijo del cargo («Docente de …» → docente)."""
    from apps.nucleo.models import RolOrganizacion

    if isinstance(rol, RolOrganizacion):
        return rol, rol.codigo
    codigos = [c for c in (getattr(rol, "codigo", rol), codigo_desde_cargo(cargo)) if c]
    if not codigos:
        return None, ""
    encontrados = {r.codigo: r for r in RolOrganizacion.objects.filter(codigo__in=codigos)}
    elegido = next((c for c in codigos if c in encontrados), None)  # p. ej., rol «Voluntario» sin par: vale el prefijo del cargo
    return encontrados.get(elegido), elegido or codigos[0]


def _completar(obj, valores):
    """Llena solo los campos vacíos (sin pisar datos existentes). Devuelve si cambió algo."""
    cambios = [c for c, v in valores.items() if v not in (None, "") and getattr(obj, c) in (None, "")]
    for c in cambios:
        setattr(obj, c, valores[c])
    if cambios:
        obj.save(update_fields=cambios)
    return bool(cambios)


def _formacion(persona, organizacion, carrera, estado, desde, hasta):
    from .models import PersonaFormacion

    hoy = timezone.localdate()
    qs = PersonaFormacion.objects.filter(persona=persona, organizacion=organizacion)
    if carrera is not None:
        qs = qs.filter(Q(carrera=carrera) | Q(carrera__isnull=True))
    # primero la vigente y, entre ellas, la de la misma carrera
    f = sorted(qs, key=lambda x: (not x.vigente, carrera is not None and x.carrera_id != carrera.pk, -x.pk))
    if f:
        f = f[0]
        _completar(f, {"carrera_id": carrera.pk if carrera is not None else None, "anio_inicio": desde.year if desde else None})
        return f, False
    return PersonaFormacion.objects.create(persona=persona, organizacion=organizacion, carrera=carrera, estado=estado or "estudiante",
                                           anio_inicio=desde.year if desde else None, anio_termino=hasta.year if hasta else None,
                                           vigente=hasta is None or hasta >= hoy), True


def _vinculo(persona, organizacion, cargo, rol, tipo_cargo, desde, hasta):
    from .models import PersonaOrganizacion

    hoy = timezone.localdate()
    qs = PersonaOrganizacion.objects.filter(persona=persona, organizacion=organizacion)
    if hasta is not None and hasta < hoy:  # un cargo que ya terminó: se reutiliza solo si es el mismo período
        qs = qs.filter(fecha_inicio=desde, fecha_termino=hasta)
    else:
        qs = qs.filter(Q(fecha_termino__isnull=True) | Q(fecha_termino__gte=hoy))

    def compatible(v):  # mismo cargo (o sin cargo) y mismo rol (o sin rol): se puede completar sin pisar
        return ((not cargo or not v.cargo or v.cargo.lower() == cargo.lower())
                and (rol is None or v.rol_id is None or v.rol_id == rol.pk))

    candidatos = sorted((v for v in qs if compatible(v)),
                        key=lambda v: (not (cargo and v.cargo.lower() == cargo.lower()), not (rol is not None and v.rol_id == rol.pk), -v.pk))
    if candidatos:
        v = candidatos[0]
        _completar(v, {"cargo": cargo, "rol_id": rol.pk if rol is not None else None, "fecha_inicio": desde})
        return v, False
    tipo = tipo_cargo or ("autoridad" if rol is not None and rol.codigo == "autoridad" else "funcional")
    return PersonaOrganizacion.objects.create(persona=persona, organizacion=organizacion, cargo=cargo[:120], rol=rol, tipo_cargo=tipo,
                                              fecha_inicio=desde, fecha_termino=hasta), True


def vincular(persona, *, organizacion=None, comunidad=None, cargo="", rol=None, estado_formacion=None, carrera=None, desde=None,
             hasta=None, tipo_cargo=None, rol_comunidad=None):
    """F26 P2: crea o REUTILIZA, sin duplicar y en una transacción:
    - con `organizacion`: su formación (PersonaFormacion) si se da `estado_formacion` o `carrera`, o si la organización
      es una institución educativa y el rol es «estudiante»; si no, su vínculo (PersonaOrganizacion). Se reutiliza el
      vínculo vigente compatible con esa organización y se completan el cargo y el rol vacíos, sin pisar lo que ya hay;
    - con `comunidad`: su lugar en el padrón (ComunidadMiembro, uno por persona y comunidad).
    `rol` acepta un valor de «Rol en la organización», un rol de participación o un código; sin él, se deduce del cargo.
    Devuelve {"formacion", "vinculo", "miembro"} con lo creado o reutilizado (None si no aplica) y "creados", la lista de
    lo que se creó."""
    from apps.comunidades.models import ComunidadMiembro

    cargo = (cargo or "").strip()[:120]
    res = {"formacion": None, "vinculo": None, "miembro": None, "creados": []}
    with transaction.atomic():
        if organizacion is not None:
            rol_obj, codigo = _rol_organizacion(rol, cargo)
            es_formacion = estado_formacion or carrera is not None or (codigo == "estudiante" and organizacion.es_educativa)
            if es_formacion:
                obj, creado = _formacion(persona, organizacion, carrera, estado_formacion, desde, hasta)
                res["formacion"] = obj
            else:
                obj, creado = _vinculo(persona, organizacion, cargo, rol_obj, tipo_cargo, desde, hasta)
                res["vinculo"] = obj
            if creado:
                res["creados"].append(obj)
        if comunidad is not None:
            obj, creado = ComunidadMiembro.objects.get_or_create(comunidad=comunidad, persona=persona,
                                                                 defaults={"rol": rol_comunidad or "integrante", "desde": desde})
            res["miembro"] = obj
            if creado:
                res["creados"].append(obj)
    return res


def vincular_contacto(persona, organizacion):
    """La persona de contacto de una organización (en una solicitud, una actividad o un proyecto) queda vinculada a
    ella, si aún no lo estaba. Sin persona u organización no hace nada."""
    if persona is None or organizacion is None:
        return None
    return vincular(persona, organizacion=organizacion)["vinculo"]


def cargos_y_vinculos(persona):
    """Lista de grupos (titulo, filas). Cada fila: nombre, url, rol, detalle, periodo y si está vigente."""
    grupos = []
    # F26 P2: el rol del catálogo si lo tiene (con el cargo como detalle); si no, el cargo o el tipo de cargo, como antes
    filas = [{"nombre": str(v.organizacion), "url": v.organizacion.get_absolute_url(),
              "rol": str(v.rol) if v.rol_id else (v.cargo or v.get_tipo_cargo_display()),
              "detalle": " · ".join(x for x in [v.cargo if v.rol_id and v.cargo.lower() != v.rol.nombre.lower() else "",
                                                 v.get_tipo_cargo_display() if v.cargo or v.rol_id else ""] if x),
              "periodo": _periodo(v.fecha_inicio, v.fecha_termino),
              "vigente": _vigente(True, v.fecha_termino), "url_editar": reverse("personas:vinculos_editar", args=[persona.pk, v.pk])}
             for v in persona.vinculos.select_related("organizacion", "rol").order_by("-fecha_inicio")]
    grupos.append(("Organizaciones y cargos", filas))
    filas = [{"nombre": str(f.organizacion), "url": f.organizacion.get_absolute_url(),
              "rol": f.get_estado_display() + (f" de {f.carrera}" if f.carrera_id else ""),
              "detalle": " · ".join(x for x in [str(f.sede_institucion or f.sede or ""), f"{f.nivel_actual}.º año" if f.nivel_actual else ""] if x),
              "periodo": " a ".join(str(a) for a in [f.anio_inicio, f.anio_termino] if a), "vigente": f.vigente}
             for f in persona.formaciones.select_related("organizacion", "carrera", "sede_institucion")]
    grupos.append(("Estudios", filas))
    filas = [{"nombre": str(l.lugar), "url": l.lugar.get_absolute_url(), "rol": l.get_relacion_display(), "detalle": l.observaciones,
              "periodo": _periodo(l.desde, l.hasta), "vigente": _vigente(l.vigente, l.hasta),
              "url_editar": reverse("personas:lugares_editar", args=[persona.pk, l.pk])}
             for l in persona.lugares_vinculados.select_related("lugar")]
    grupos.append(("Lugares", filas))
    filas = [{"nombre": str(m.comunidad), "url": m.comunidad.get_absolute_url(), "rol": m.get_rol_display(), "detalle": str(m.comunidad.territorio),
              "periodo": _periodo(m.desde, m.hasta), "vigente": _vigente(m.vigente, m.hasta)}
             for m in persona.comunidades.select_related("comunidad__comuna", "comunidad__sector")]
    grupos.append(("Comunidades", filas))
    filas = [{"nombre": str(p.proyecto), "url": p.proyecto.get_absolute_url(),
              "rol": (str(p.rol) if p.rol_id else p.get_tipo_display()) + (" · responsable" if p.es_responsable else ""),
              "detalle": p.get_tipo_display(), "periodo": _periodo(p.desde, p.hasta), "vigente": _vigente(p.vigente, p.hasta)}
             for p in persona.proyectos.select_related("proyecto", "rol")]
    grupos.append(("Proyectos", filas))
    filas = []
    for p in persona.participaciones.select_related("actividad__proyecto", "actividad__estado", "rol", "estado").order_by("-actividad__creado_en"):
        a = p.actividad
        filas.append({"nombre": a.nombre, "url": a.get_absolute_url(), "rol": str(p.rol),
                      "detalle": " · ".join(x for x in [f"Tarea del proyecto «{a.proyecto}»" if a.proyecto_id else "Actividad", str(p.estado),
                                                        {True: "asistió", False: "no asistió"}.get(p.asistencia, "")] if x),
                      "periodo": "", "vigente": a.estado.codigo not in ("realizada", "cancelada")})
    grupos.append(("Actividades y tareas", filas))
    return grupos


def estudiantes_por_carrera(organizacion):
    """[(carrera, [filas])] de quienes estudian o estudiaron en la institución, y los docentes o tutores a cargo."""
    grupos, docentes = {}, {}
    for f in organizacion.formaciones.select_related("persona", "carrera", "sede_institucion", "docente").order_by("carrera__nombre", "persona__apellido_paterno", "persona__nombres"):
        grupos.setdefault(f.carrera.nombre if f.carrera_id else "Sin carrera indicada", []).append({
            "nombre": str(f.persona), "url": f.persona.get_absolute_url(), "estado": f.get_estado_display(),
            "detalle": " · ".join(x for x in [str(f.sede_institucion or f.sede or ""), f"{f.nivel_actual}.º año" if f.nivel_actual else "",
                                               f"ingreso {f.anio_inicio}" if f.anio_inicio else ""] if x),
            "vigente": f.vigente})
        if f.docente_id:
            docentes[f.docente_id] = f.docente
    return list(grupos.items()), sorted(docentes.values(), key=str)

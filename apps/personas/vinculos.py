"""Cargos y vínculos de una persona, reunidos desde todas partes: organizaciones con cargo, estudios, comunidades,
proyectos y actividades o tareas. Sirve para ver de un vistazo qué cargos ostenta hoy y cuáles tuvo, con enlaces.
También agrupa a los estudiantes de una institución por carrera, para la ficha de la organización.
Cada grupo usa una sola consulta, sin importar cuántos registros tenga."""
from django.urls import reverse
from django.utils import timezone


def _vigente(activo, hasta):
    """Vigente si no se dio de baja y su fecha de término no pasó."""
    return bool(activo) and (hasta is None or hasta >= timezone.localdate())


def _periodo(desde, hasta):
    if not desde and not hasta:
        return ""
    return f"{desde:%d-%m-%Y} a {hasta:%d-%m-%Y}" if desde and hasta else (f"desde {desde:%d-%m-%Y}" if desde else f"hasta {hasta:%d-%m-%Y}")


def cargos_y_vinculos(persona):
    """Lista de grupos (titulo, filas). Cada fila: nombre, url, rol, detalle, periodo y si está vigente."""
    grupos = []
    filas = [{"nombre": str(v.organizacion), "url": v.organizacion.get_absolute_url(), "rol": v.cargo or v.get_tipo_cargo_display(),
              "detalle": v.get_tipo_cargo_display() if v.cargo else "", "periodo": _periodo(v.fecha_inicio, v.fecha_termino),
              "vigente": _vigente(True, v.fecha_termino), "url_editar": reverse("personas:vinculos_editar", args=[persona.pk, v.pk])}
             for v in persona.vinculos.select_related("organizacion").order_by("-fecha_inicio")]
    grupos.append(("Organizaciones y cargos", filas))
    filas = [{"nombre": str(f.organizacion), "url": f.organizacion.get_absolute_url(),
              "rol": f.get_estado_display() + (f" de {f.carrera}" if f.carrera_id else ""),
              "detalle": " · ".join(x for x in [str(f.sede_institucion or f.sede or ""), f"{f.nivel_actual}.º año" if f.nivel_actual else ""] if x),
              "periodo": " a ".join(str(a) for a in [f.anio_inicio, f.anio_termino] if a), "vigente": f.vigente}
             for f in persona.formaciones.select_related("organizacion", "carrera", "sede_institucion")]
    grupos.append(("Estudios", filas))
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

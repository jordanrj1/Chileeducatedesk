"""Suma lo presupuestado, gastado y aportado de un proyecto, para la pestaña Presupuesto (2.ª fase, oculta)."""
from django.db.models import Sum


def _suma(qs):
    return qs.aggregate(t=Sum("monto"))["t"] or 0


def resumen_proyecto(proyecto):
    mov = proyecto.movimientos.filter(anulado=False)
    presupuestado = proyecto.items_presupuesto.filter(vigente=True).aggregate(t=Sum("monto_estimado"))["t"] or 0
    gastado, aportes, donaciones = (_suma(mov.filter(tipo=t)) for t in ("gasto", "aporte", "donacion"))
    return {"presupuestado": presupuestado, "gastado": gastado, "aportes": aportes, "donaciones": donaciones, "saldo": aportes + donaciones - gastado}


# --- F28 B: gastos de una actividad y de un proyecto -------------------------------------------------------------------
def _jornada_orden(j):
    return (j.fecha is None, j.fecha or 0, j.numero)


def gastos_actividad(actividad):
    """Gastos de una actividad o tarea, agrupados por jornada («Toda la tarea» primero), con el total (sin anulados),
    cuántos no tienen comprobante y cuántos esperan revisión. Una sola consulta."""
    from .models import Movimiento

    gastos = list(Movimiento.objects.filter(actividad=actividad, tipo="gasto")
                  .select_related("categoria", "sesion", "pagado_por", "organizacion", "documento", "revisado_por").order_by("fecha", "id"))
    grupos = {}
    for g in gastos:
        grupos.setdefault(g.sesion_id, {"jornada": g.sesion, "gastos": [], "total": 0, "n": 0})
        grupo = grupos[g.sesion_id]
        grupo["gastos"].append(g)
        if not g.anulado:
            grupo["total"] += g.monto
            grupo["n"] += 1
    ordenados = sorted(grupos.values(), key=lambda x: (x["jornada"] is not None, _jornada_orden(x["jornada"]) if x["jornada"] else (False, 0, 0)))
    vivos = [g for g in gastos if not g.anulado]
    return {
        "grupos": ordenados, "total": sum(g.monto for g in vivos), "n": len(vivos), "n_total": len(gastos),
        "sin_comprobante": sum(1 for g in vivos if g.sin_comprobante),
        "por_revisar": sum(1 for g in vivos if g.estado == "registrado"),
    }


def gastos_proyecto(proyecto):
    """Gasto del proyecto por tarea, por jornada y por categoría frente a su presupuesto (ítems vigentes), con aviso si se
    excede. Dos consultas, sin importar cuántos gastos haya. Los anulados no cuentan."""
    from .categorias import A_PRESUPUESTO
    from .models import ItemPresupuesto, Movimiento

    gastos = [g for g in Movimiento.objects.filter(proyecto=proyecto, tipo="gasto", anulado=False)
              .select_related("actividad", "sesion", "categoria").order_by("fecha", "id")]
    items = list(proyecto.items_presupuesto.filter(vigente=True))
    etiquetas = dict(ItemPresupuesto.CATEGORIAS)
    tareas, categorias, presup_cat = {}, {}, {}
    for g in gastos:
        t = tareas.setdefault(g.actividad_id, {"tarea": g.actividad, "total": 0, "n": 0, "sin_comprobante": 0, "sin_jornada": 0, "jornadas": {}})
        t["total"] += g.monto
        t["n"] += 1
        t["sin_comprobante"] += 1 if g.sin_comprobante else 0
        if g.sesion_id:
            j = t["jornadas"].setdefault(g.sesion_id, {"jornada": g.sesion, "total": 0})
            j["total"] += g.monto
        else:
            t["sin_jornada"] += g.monto
        codigo = g.categoria.codigo if g.categoria_id else ""
        nombre = g.categoria.nombre if g.categoria_id else "Sin categoría"
        c = categorias.setdefault(nombre, {"nombre": nombre, "total": 0, "presupuesto": A_PRESUPUESTO.get(codigo, "otros")})
        c["total"] += g.monto
    for i in items:
        presup_cat[i.categoria] = presup_cat.get(i.categoria, 0) + i.monto_estimado
    gastado_por_item = {}
    for c in categorias.values():
        gastado_por_item[c["presupuesto"]] = gastado_por_item.get(c["presupuesto"], 0) + c["total"]
    comparacion = []
    for clave in dict(ItemPresupuesto.CATEGORIAS):
        presupuestado, gastado = presup_cat.get(clave, 0), gastado_por_item.get(clave, 0)
        if presupuestado or gastado:
            comparacion.append({"categoria": etiquetas[clave], "presupuestado": presupuestado, "gastado": gastado,
                                "diferencia": presupuestado - gastado, "excedido": presupuestado > 0 and gastado > presupuestado,
                                "sin_presupuesto": presupuestado == 0})
    total, presupuestado = sum(g.monto for g in gastos), sum(i.monto_estimado for i in items)
    return {
        "total": total, "n": len(gastos), "presupuestado": presupuestado, "diferencia": presupuestado - total,
        "excedido": presupuestado > 0 and total > presupuestado, "exceso": max(total - presupuestado, 0) if presupuestado else 0,
        "sin_presupuesto": not items, "comparacion": comparacion, "items": items,
        "sin_comprobante": sum(1 for g in gastos if g.sin_comprobante),
        "tareas": sorted(tareas.values(), key=lambda t: (t["tarea"] is None, -t["total"])),
        "categorias": sorted(categorias.values(), key=lambda c: -c["total"]),
    }

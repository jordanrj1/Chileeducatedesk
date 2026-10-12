from django.db.models import Sum


def _suma(qs):
    return qs.aggregate(t=Sum("monto"))["t"] or 0


def resumen_proyecto(proyecto):
    mov = proyecto.movimientos.filter(anulado=False)
    presupuestado = proyecto.items_presupuesto.filter(vigente=True).aggregate(t=Sum("monto_estimado"))["t"] or 0
    gastado, aportes, donaciones = (_suma(mov.filter(tipo=t)) for t in ("gasto", "aporte", "donacion"))
    return {"presupuestado": presupuestado, "gastado": gastado, "aportes": aportes, "donaciones": donaciones, "saldo": aportes + donaciones - gastado}

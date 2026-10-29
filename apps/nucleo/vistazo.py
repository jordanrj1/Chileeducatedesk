"""«De un vistazo» (F26 P3a e Ib): el bloque de arriba de las fichas de persona, organización, comunidad y lugar.

Cada ficha arma una lista de filas con `fila()` e `item()` y la dibuja `templates/generico/_de_un_vistazo.html`.
`ultima_y_proxima()` da la última actividad realizada y la próxima programada de un grupo de actividades en dos consultas,
sin importar cuántas sean.
"""
from django.utils import timezone

ESTADOS_PROGRAMADOS = ("planificada", "confirmada", "reprogramada")


def item(*partes, nota=""):
    """Un renglón: partes (texto, url) unidas con « · » (con enlace si hay url) y una nota corta en gris."""
    return {"partes": [(str(t), u or "") for t, u in partes if t not in (None, "")], "nota": nota}


def fila(etiqueta, items=(), vacio="", *, cifra="", ancho=False, lista=False, pie=None, pie_en_linea=False):
    """Una fila del vistazo. `cifra`: texto destacado antes de los renglones. `pie`: (texto, url) de un enlace al final;
    `pie_en_linea` lo pone a continuación (« · Completar ficha») en vez de debajo."""
    return {"etiqueta": etiqueta, "items": list(items), "vacio": vacio, "cifra": cifra, "ancho": ancho, "lista": lista,
            "pie": pie, "pie_en_linea": pie_en_linea}


def item_agenda(agenda, con_lugar=True):
    """Actividad, fecha y hora (y lugar) de una programación."""
    cuando = f"{agenda.fecha:%d-%m-%Y}" + (f", {agenda.hora_inicio:%H:%M}" if agenda.hora_inicio else "")
    partes = [(agenda.actividad.nombre, agenda.actividad.get_absolute_url()), (cuando, "")]
    if con_lugar and agenda.lugar_id:
        partes.append((agenda.lugar, agenda.lugar.get_absolute_url()))
    return item(*partes)


def ultima_y_proxima(condicion):
    """(última realizada, próxima programada): programaciones vigentes que cumplen `condicion` (un Q sobre AgendaActividad).
    Dos consultas."""
    from apps.actividades.models import AgendaActividad

    base = AgendaActividad.objects.filter(condicion, vigente=True).select_related("actividad", "lugar")
    ultima = base.filter(actividad__estado__codigo="realizada").order_by("-fecha", "-hora_inicio", "-pk").first()
    proxima = (base.filter(fecha__gte=timezone.localdate(), actividad__estado__codigo__in=ESTADOS_PROGRAMADOS)
               .order_by("fecha", "hora_inicio", "pk").first())
    return ultima, proxima


def filas_ultima_y_proxima(condicion, con_lugar=True):
    ultima, proxima = ultima_y_proxima(condicion)
    return [
        fila("Última actividad", [item_agenda(ultima, con_lugar)] if ultima else [], "Ninguna realizada"),
        fila("Próxima actividad", [item_agenda(proxima, con_lugar)] if proxima else [], "Ninguna programada"),
    ]


def cuantas(n, singular, plural):
    """«1 actividad», «3 actividades», «Sin actividades»."""
    return f"Sin {plural}" if not n else f"{n} {singular if n == 1 else plural}"

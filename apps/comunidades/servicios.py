"""F26 P2: una sola verdad para el referente de una comunidad: quien figura como referente está en su padrón."""
from django.db.models import Case, IntegerField, Value, When


def asegurar_referente(comunidad):
    """El referente queda en el padrón vigente con rol «Referente» (con `vincular()`, sin duplicar). Si ya estaba como
    integrante, pasa a referente; si estaba dado de baja, vuelve a estar vigente. Un dirigente o vocero conserva su rol."""
    from apps.personas.vinculos import vincular

    if not comunidad.referente_id:
        return None
    m = vincular(comunidad.referente, comunidad=comunidad, rol_comunidad="referente")["miembro"]
    cambios = []
    if m.rol == "integrante":
        m.rol = "referente"
        cambios.append("rol")
    if not m.vigente:
        m.vigente, m.hasta = True, None
        cambios += ["vigente", "hasta"]
    if cambios:
        m.save(update_fields=cambios)
    return m


def referente_del_padron(comunidad):
    """Para mostrar en la ficha cuando el campo «referente» está vacío: el integrante vigente con rol referente (o, si no
    hay, dirigente). Una consulta. None si no hay."""
    m = (comunidad.miembros.filter(vigente=True, rol__in=["referente", "dirigente"]).select_related("persona")
         .annotate(_orden=Case(When(rol="referente", then=Value(0)), default=Value(1), output_field=IntegerField()))
         .order_by("_orden", "pk").first())
    return m.persona if m else None

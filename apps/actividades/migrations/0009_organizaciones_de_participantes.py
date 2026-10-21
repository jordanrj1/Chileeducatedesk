# Aplica una vez, a lo ya registrado, la regla de F25 E4: la organización de procedencia de cada participante queda en
# la actividad como «Aporta personas», si la actividad aún no tenía ningún registro de esa organización. Solo agrega;
# repetirla no cambia nada; no toca participaciones marcadas como «registro erróneo».
from django.db import migrations


def vincular(apps, schema_editor):
    Participacion = apps.get_model("actividades", "Participacion")
    ActividadOrganizacion = apps.get_model("actividades", "ActividadOrganizacion")
    TipoIntervencion = apps.get_model("nucleo", "TipoIntervencion")
    tipo = TipoIntervencion.objects.filter(codigo="aporta_personas").first()
    pares = set(Participacion.objects.filter(institucion__isnull=False).exclude(estado__codigo="registro_erroneo")
                .values_list("actividad_id", "institucion_id"))
    existentes = set(ActividadOrganizacion.objects.values_list("actividad_id", "organizacion_id"))
    ActividadOrganizacion.objects.bulk_create([
        ActividadOrganizacion(actividad_id=a, organizacion_id=o, tipo_intervencion=tipo, vigente=True) for a, o in sorted(pares - existentes)
    ])


class Migration(migrations.Migration):
    dependencies = [("actividades", "0008_tramos_etarios"), ("nucleo", "0016_estado_inscrito")]
    operations = [migrations.RunPython(vincular, migrations.RunPython.noop)]

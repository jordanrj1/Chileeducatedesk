# Enlaza la sede que se escribió como texto con el lugar de la institución que se llama igual (sin contar tildes,
# mayúsculas ni espacios de más). Conservadora: solo si hay exactamente un lugar de esa institución, de tipo sede o
# casa matriz, con ese nombre, y la formación aún no tiene sede enlazada. No crea lugares (un lugar exige dirección),
# no borra el texto y se puede repetir sin cambiar nada.

import unicodedata

from django.db import migrations

TIPOS_SEDE = ("sede", "casa_matriz")


def _clave(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def enlazar_sedes(apps, schema_editor):
    PersonaFormacion = apps.get_model("personas", "PersonaFormacion")
    Lugar = apps.get_model("lugares", "Lugar")
    pendientes = list(PersonaFormacion.objects.filter(sede_institucion__isnull=True).exclude(sede="").only("pk", "organizacion_id", "sede"))
    if not pendientes:
        return
    candidatos = {}
    lugares = Lugar.objects.filter(organizacion_propietaria_id__in={f.organizacion_id for f in pendientes}, tipo__codigo__in=TIPOS_SEDE)
    for lugar in lugares.only("pk", "nombre", "organizacion_propietaria_id"):
        candidatos.setdefault((lugar.organizacion_propietaria_id, _clave(lugar.nombre)), []).append(lugar.pk)
    por_lugar = {}
    for f in pendientes:
        encontrados = candidatos.get((f.organizacion_id, _clave(f.sede)), [])
        if len(encontrados) == 1:  # dos lugares con el mismo nombre: no se adivina
            por_lugar.setdefault(encontrados[0], []).append(f.pk)
    for lugar_pk, formaciones in por_lugar.items():
        PersonaFormacion.objects.filter(pk__in=formaciones, sede_institucion__isnull=True).update(sede_institucion_id=lugar_pk)


class Migration(migrations.Migration):

    dependencies = [
        ("lugares", "0001_initial"),
        ("personas", "0004_fichas_por_tipo"),
    ]

    operations = [
        migrations.RunPython(enlazar_sedes, migrations.RunPython.noop),
    ]

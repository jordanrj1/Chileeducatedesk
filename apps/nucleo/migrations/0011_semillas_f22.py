from django.db import migrations

SEMILLAS = {
    "PerfilPersona": [
        "estudiante", "vecino o vecina de la comunidad", "voluntario o voluntaria", "tallerista o profesional", "dirigente social",
        "docente o académico", "funcionario institucional", "beneficiario o beneficiaria", "apoderado o apoderada",
    ],
    "AreaTematica": [
        "educación", "educación financiera", "salud y bienestar", "medioambiente", "emprendimiento y empleo", "tecnología y alfabetización digital",
        "cultura y artes", "deporte y recreación", "personas mayores", "infancia y juventud", "inclusión y discapacidad", "vivienda y barrio",
        "participación ciudadana",
    ],
}
GRUPOS = {
    "ejecutor": ["estudiante", "practicante", "ayudante", "voluntario", "tutor", "tallerista", "coordinador"],
    "asistente": ["participante", "beneficiario"],
    "contacto": ["contacto_institucional"],
}


def _codigo(nombre):
    import unicodedata

    base = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return "_".join(base.lower().replace("-", " ").split())[:60]


def sembrar(apps, schema_editor):
    for nombre_modelo, valores in SEMILLAS.items():
        Modelo = apps.get_model("nucleo", nombre_modelo)
        for orden, nombre in enumerate(valores, start=1):
            Modelo.objects.get_or_create(codigo=_codigo(nombre), defaults={"nombre": nombre[0].upper() + nombre[1:], "orden": orden})
    Rol = apps.get_model("nucleo", "RolParticipacion")
    for grupo, codigos in GRUPOS.items():
        Rol.objects.filter(codigo__in=codigos).update(grupo=grupo)


class Migration(migrations.Migration):
    dependencies = [("nucleo", "0010_catalogos_f22")]
    operations = [migrations.RunPython(sembrar, migrations.RunPython.noop)]

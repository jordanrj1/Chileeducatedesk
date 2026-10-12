from django.db import migrations

SEMILLAS = {
    "EstadoActividad": ["planificada", "confirmada", "reprogramada", "suspendida", "cancelada", "realizada", "pendiente"],
    "EstadoSolicitud": ["pendiente", "en seguimiento", "convertida", "descartada"],
    "EstadoParticipacion": ["invitado", "interesado", "disponible", "confirmado", "asistió", "no asistió", "rechazó", "canceló"],
    "RolParticipacion": ["estudiante", "practicante", "ayudante", "voluntario", "tutor", "tallerista", "coordinador", "participante", "beneficiario", "contacto institucional"],
    "TipoOrganizacion": ["institución educativa", "municipalidad", "junta de vecinos o comité", "empresa o partner", "fundación u ONG", "otra"],
    "TipoActividad": ["taller", "charla", "jornada", "live", "difusión", "campaña"],
    "TipoContacto": ["teléfono móvil", "teléfono fijo", "correo", "sitio web", "red social"],
    "Canal": ["llamado", "correo", "mensaje", "reunión", "presencial", "otro"],
    "Modalidad": ["presencial", "virtual", "híbrida"],
    "OrigenPersona": ["invitación", "difusión", "interés propio", "derivación", "búsqueda activa"],
    "EstadoRegistro": ["activo", "incompleto", "por verificar", "desactualizado"],
    "TipoLugar": ["sede", "sala", "salón comunitario", "establecimiento educacional", "espacio público", "otro"],
    "TipoDocumento": ["minuta", "carta", "ficha", "postulación", "certificado", "listado", "acta", "otro"],
    "TipoIntervencion": ["solicita", "articula", "coordina", "facilita espacio", "aporta personas", "aporta recursos"],
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


class Migration(migrations.Migration):
    dependencies = [("nucleo", "0002_initial")]
    operations = [migrations.RunPython(sembrar, migrations.RunPython.noop)]

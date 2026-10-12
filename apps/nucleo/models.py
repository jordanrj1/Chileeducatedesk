from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Catalogo(models.Model):
    """Valor de lista editable desde la interfaz. `codigo` es estable: la lógica usa `codigo`, no `nombre`."""

    codigo = models.SlugField("código", max_length=60, unique=True, help_text="Identificador interno; no cambia.")
    nombre = models.CharField(max_length=100)
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = slugify(self.nombre).replace("-", "_")[:60]  # slugify quita acentos
        super().save(*args, **kwargs)


def _catalogo(nombre_clase, verbose, verbose_plural):
    return type(
        nombre_clase,
        (Catalogo,),
        {
            "__module__": __name__,
            "Meta": type("Meta", (Catalogo.Meta,), {"abstract": False, "verbose_name": verbose, "verbose_name_plural": verbose_plural}),
        },
    )


EstadoActividad = _catalogo("EstadoActividad", "estado de actividad", "estados de actividad")
EstadoSolicitud = _catalogo("EstadoSolicitud", "estado de solicitud", "estados de solicitud")
EstadoParticipacion = _catalogo("EstadoParticipacion", "estado de participación", "estados de participación")
RolParticipacion = _catalogo("RolParticipacion", "rol de participación", "roles de participación")
TipoOrganizacion = _catalogo("TipoOrganizacion", "tipo de organización", "tipos de organización")
TipoActividad = _catalogo("TipoActividad", "tipo de actividad", "tipos de actividad")
TipoContacto = _catalogo("TipoContacto", "tipo de contacto", "tipos de contacto")
Canal = _catalogo("Canal", "canal", "canales")
Modalidad = _catalogo("Modalidad", "modalidad", "modalidades")
OrigenPersona = _catalogo("OrigenPersona", "origen de persona", "orígenes de persona")
EstadoRegistro = _catalogo("EstadoRegistro", "estado de registro", "estados de registro")
TipoLugar = _catalogo("TipoLugar", "tipo de lugar", "tipos de lugar")
TipoDocumento = _catalogo("TipoDocumento", "tipo de documento", "tipos de documento")
TipoIntervencion = _catalogo("TipoIntervencion", "tipo de intervención", "tipos de intervención")

CATALOGOS = {
    "estado-actividad": EstadoActividad,
    "estado-solicitud": EstadoSolicitud,
    "estado-participacion": EstadoParticipacion,
    "rol-participacion": RolParticipacion,
    "tipo-organizacion": TipoOrganizacion,
    "tipo-actividad": TipoActividad,
    "tipo-contacto": TipoContacto,
    "canal": Canal,
    "modalidad": Modalidad,
    "origen-persona": OrigenPersona,
    "estado-registro": EstadoRegistro,
    "tipo-lugar": TipoLugar,
    "tipo-documento": TipoDocumento,
    "tipo-intervencion": TipoIntervencion,
}


class Auditoria(models.Model):
    """Registro de operaciones sensibles (RF-26, RNF-13). Se escribe solo desde el sistema."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    usuario_nombre = models.CharField(max_length=150, blank=True)
    accion = models.CharField(max_length=60)
    objeto = models.CharField(max_length=200, blank=True)
    detalle = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "auditoría"
        indexes = [models.Index(fields=["accion"]), models.Index(fields=["fecha"])]

    def __str__(self):
        return f"{self.fecha:%d-%m-%Y %H:%M} {self.accion}"

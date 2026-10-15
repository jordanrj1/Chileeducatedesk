"""Catálogos (las listas de opciones que Claudio puede ampliar: tipos, estados, roles, canales…) y la tabla de auditoría.
Los valores de un catálogo no se borran: se desactivan, y los registros antiguos los conservan."""
from django.conf import settings
from django.core.exceptions import ValidationError
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
            "Meta": type("Meta", (Catalogo.Meta,), {
                "abstract": False, "verbose_name": verbose, "verbose_name_plural": verbose_plural,
                # Desactivar es del Administrador; el Gestor agrega y edita valores (CA-01, CA-03)
                "permissions": [(f"desactivar_{nombre_clase.lower()}", f"Puede desactivar valores de {verbose_plural}")],
            }),
        },
    )


EstadoActividad = _catalogo("EstadoActividad", "estado de actividad", "estados de actividad")
EstadoSolicitud = _catalogo("EstadoSolicitud", "estado de solicitud", "estados de solicitud")
EstadoParticipacion = _catalogo("EstadoParticipacion", "estado de participación", "estados de participación")


class RolParticipacion(Catalogo):
    """Rol en una actividad. El grupo separa a quien ejecuta de quien asiste (F22)."""

    GRUPOS = [("ejecutor", "Equipo ejecutor"), ("asistente", "Asistentes"), ("contacto", "Contacto institucional")]
    grupo = models.CharField(max_length=10, choices=GRUPOS, default="asistente", help_text="Equipo ejecutor (realiza la actividad), asistentes (a quienes va dirigida) o contacto.")
    campos_extra = ["grupo"]

    class Meta(Catalogo.Meta):
        verbose_name = "rol de participación"
        verbose_name_plural = "roles de participación"
        permissions = [("desactivar_rolparticipacion", "Puede desactivar valores de roles de participación")]


class TramoEtario(Catalogo):
    """Tramo de edad: a qué edades va dirigida una actividad o qué edades predominan en una comunidad (y, más adelante,
    los integrantes del hogar). Sin edad máxima quiere decir «o más». Los valores iniciales están por validar con el cliente."""

    edad_min = models.PositiveSmallIntegerField("edad mínima", null=True, blank=True, help_text="En años. Ej.: 18.")
    edad_max = models.PositiveSmallIntegerField("edad máxima", null=True, blank=True, help_text="En años. Déjala vacía si no tiene tope (Ej.: 60 o más).")
    campos_extra = ["edad_min", "edad_max"]

    class Meta(Catalogo.Meta):
        verbose_name = "tramo de edad"
        verbose_name_plural = "tramos de edad"
        permissions = [("desactivar_tramoetario", "Puede desactivar valores de tramos de edad")]
        constraints = [models.CheckConstraint(
            condition=models.Q(edad_min__isnull=True) | models.Q(edad_max__isnull=True) | models.Q(edad_max__gte=models.F("edad_min")),
            name="tramo_etario_edad_max_mayor_o_igual",
        )]

    def clean(self):
        if self.edad_min is not None and self.edad_max is not None and self.edad_max < self.edad_min:
            raise ValidationError({"edad_max": "La edad máxima no puede ser menor que la mínima."})

    @property
    def edades(self):
        """«18 a 29 años», «60 años o más», «hasta 5 años» o vacío si no tiene edades."""
        if self.edad_min is not None and self.edad_max is not None:
            return f"{self.edad_min} a {self.edad_max} años"
        if self.edad_min is not None:
            return f"{self.edad_min} años o más"
        if self.edad_max is not None:
            return f"hasta {self.edad_max} años"
        return ""

    @property
    def etiqueta(self):
        return f"{self.nombre} ({self.edades})" if self.edades else self.nombre

    @classmethod
    def para_elegir(cls, conservar=None):
        """Tramos activos más los que el registro ya tenía (`conservar`: consulta o lista de ids), para no perderlos al editar."""
        filtro = models.Q(activo=True)
        if conservar is not None:
            filtro |= models.Q(pk__in=conservar)
        return cls.objects.filter(filtro)


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


class PerfilPersona(Catalogo):
    """Qué es una persona para la Fundación (estudiante, vecina, voluntario…). Puede tener varios.
    `ficha` dice qué datos propios se piden al marcar el perfil; así un perfil nuevo puede abrir una ficha que ya existe."""

    FICHAS = [
        ("", "Sin ficha propia"), ("estudiante", "Estudiante"), ("vecino", "Vecino o vecina"),
        ("invitado", "Invitado o invitada"), ("voluntario", "Voluntario o voluntaria"),
    ]
    ficha = models.CharField(max_length=12, choices=FICHAS, blank=True,
                             help_text="Qué datos propios se piden al registrar a alguien con este perfil. Ej.: Estudiante pide institución, sede y carrera.")
    campos_extra = ["ficha"]

    class Meta(Catalogo.Meta):
        verbose_name = "perfil de persona"
        verbose_name_plural = "perfiles de persona"
        permissions = [("desactivar_perfilpersona", "Puede desactivar valores de perfiles de persona")]


AreaTematica = _catalogo("AreaTematica", "área temática", "áreas temáticas")
# Fichas por tipo de persona: parentesco de los familiares del vecino, tipo de invitado y estado del voluntariado
Parentesco = _catalogo("Parentesco", "parentesco", "parentescos")
TipoInvitado = _catalogo("TipoInvitado", "tipo de invitado", "tipos de invitado")
EstadoVoluntario = _catalogo("EstadoVoluntario", "estado del voluntariado", "estados del voluntariado")

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
    "perfil-persona": PerfilPersona,
    "area-tematica": AreaTematica,
    "tramo-etario": TramoEtario,
    "parentesco": Parentesco,
    "tipo-invitado": TipoInvitado,
    "estado-voluntario": EstadoVoluntario,
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

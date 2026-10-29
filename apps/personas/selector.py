"""Qué personas se ofrecen en los buscadores de los formularios y cómo se muestran (nombre, RUT y cargo vigente).
Para el responsable de una actividad, proyecto o tarea aparece primero el «Equipo de la Fundación»: quienes tienen
un cargo vigente en la organización marcada «es la Fundación» o una cuenta en el sistema."""
from django.conf import settings
from django.db.models import BooleanField, Exists, ExpressionWrapper, OuterRef, Prefetch, Q
from django.utils import timezone

from apps.nucleo.selector import Fuente, pk_seguro

from .models import Persona, PersonaOrganizacion

AYUDA_RESPONSABLE = (
    "Primero aparece el equipo de la Fundación. Para sumar a alguien al equipo: Organizaciones → la Fundación → "
    "Personas relacionadas → Agregar persona con cargo."
)
# F26 Ia: actividad, tarea y proyecto suman solos al responsable a su equipo; basta la ayuda corta.
AYUDA_RESPONSABLE_EQUIPO = "Queda en el equipo automáticamente."


def _vinculos_vigentes():
    hoy = timezone.localdate()
    return PersonaOrganizacion.objects.filter(Q(fecha_termino__isnull=True) | Q(fecha_termino__gte=hoy))


def es_equipo():
    """Expresión: la persona tiene un cargo vigente en la Fundación o tiene cuenta."""
    from apps.cuentas.models import PerfilCuenta

    vinculo = _vinculos_vigentes().filter(persona=OuterRef("pk"), organizacion__es_propia=True)
    cuenta = PerfilCuenta.objects.filter(persona=OuterRef("pk"))
    return ExpressionWrapper(Exists(vinculo) | Exists(cuenta), output_field=BooleanField())


class Personas(Fuente):
    modelo = Persona
    permiso_ver = "personas.view_persona"
    url_opciones = "personas:opciones"
    url_crear = "personas:crear_rapida"
    permiso_crear = "personas.add_persona"
    etiqueta_crear = "persona"
    placeholder = "Escribe un nombre, RUT o teléfono…"
    texto_vacio = "Aún no hay personas registradas."
    filtros_permitidos = ("equipo_primero", "excluir")

    @staticmethod
    def solo_equipo(filtros):
        return filtros.get("equipo_primero") == "1" and getattr(settings, "RESPONSABLE_SOLO_EQUIPO", False)

    def base(self, equipo_primero="", excluir="", **_):
        qs = Persona.objects.filter(activo=True).exclude(estado_registro__codigo__in=["fallecida", "fusionada"])
        if equipo_primero == "1":
            qs = qs.annotate(es_equipo=es_equipo())
            if self.solo_equipo({"equipo_primero": equipo_primero}):
                qs = qs.filter(es_equipo=True)
        pk = pk_seguro(excluir)
        if pk:
            qs = qs.exclude(pk=pk)
        return qs

    def buscar(self, qs, q):
        return qs.buscar(q)

    def ordenar(self, qs):
        orden = ["nombres", "apellido_paterno", "apellido_materno", "pk"]  # como se lee en la lista
        if "es_equipo" in qs.query.annotations:
            orden.insert(0, "-es_equipo")
        return qs.order_by(*orden)

    def con_relaciones(self, qs):
        vigentes = _vinculos_vigentes().select_related("organizacion").order_by("-organizacion__es_propia", "-fecha_inicio", "pk")
        return qs.select_related("estado_registro").prefetch_related(Prefetch("vinculos", queryset=vigentes, to_attr="vinculos_vigentes"))

    def texto(self, p):
        return p.nombre_completo

    def detalle(self, p):
        partes = [f"RUT {p.rut}" if p.rut else "sin RUT"]
        vinculo = next(iter(getattr(p, "vinculos_vigentes", None) or []), None)
        if vinculo is not None:
            partes.append(f"{vinculo.cargo} en {vinculo.organizacion}" if vinculo.cargo else str(vinculo.organizacion))
        return " · ".join(partes)

    def marca(self, p):
        codigo = getattr(p.estado_registro, "codigo", "")
        if codigo == "fallecida":
            return "(fallecida)"
        if codigo == "fusionada":
            return "(fusionada en otra ficha)"
        return super().marca(p)

    def agrupar(self, objs):
        objs = list(objs)
        if not objs or not hasattr(objs[0], "es_equipo"):
            return [(None, objs)]
        return [("Equipo de la Fundación", [p for p in objs if p.es_equipo]), ("Otras personas", [p for p in objs if not p.es_equipo])]

    def aviso(self, filtros):
        if filtros.get("equipo_primero") != "1":
            return ""
        from apps.organizaciones.models import Organizacion

        if Organizacion.objects.filter(es_propia=True).exists():
            return ""
        return "Aún no hay una organización marcada «es la Fundación»: márcala en Organizaciones para ver aquí primero al equipo."

    def puede_crear(self, usuario, filtros):
        # con el responsable limitado al equipo, una persona recién creada no sería aceptada
        return super().puede_crear(usuario, filtros) and not self.solo_equipo(filtros)


class PersonasSinCuenta(Personas):
    """Para crear una cuenta: solo personas que todavía no tienen una."""

    permiso_ver = "auth.add_user"
    url_opciones = "cuentas_admin:personas_libres"
    url_crear = ""
    filtros_permitidos = ()

    def base(self, **_):
        return Persona.objects.filter(activo=True, cuenta__isnull=True)

    def marca(self, p):
        return "" if p.activo else "(desactivada)"


PERSONAS = Personas()
PERSONAS_SIN_CUENTA = PersonasSinCuenta()

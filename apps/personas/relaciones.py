"""Sección «Relaciones» de «Nueva persona» (F25): filas que unen a la persona con una organización, una comunidad,
un proyecto o tarea, o una actividad. Cada fila crea el vínculo que corresponde (PersonaOrganizacion, PersonaFormacion,
ComunidadMiembro, ProyectoPersona o Participacion) dentro de la misma transacción que crea la persona.
Las filas vacías se ignoran y nada es obligatorio."""
from django import forms
from django.utils import timezone
from django.forms import BaseFormSet, formset_factory

from apps.actividades.selector import ACTIVIDADES
from apps.comunidades.models import ComunidadMiembro
from apps.comunidades.selector import COMUNIDADES
from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import RolParticipacion
from apps.organizaciones.selector import ORGANIZACIONES

PREFIJO = "relaciones"
TIPOS = [("", "Elegir…"), ("organizacion", "Organización"), ("comunidad", "Comunidad"), ("proyecto", "Proyecto o tarea"), ("actividad", "Actividad")]
ROLES_ORGANIZACION = [("", "Elegir…"), ("estudiante", "Estudiante"), ("docente", "Docente"), ("funcionario", "Funcionario/a"),
                      ("dirigente", "Dirigente"), ("socio", "Socio/a"), ("practicante", "Practicante"), ("otro", "Otro")]
COMO = [("equipo", "Parte del equipo"), ("beneficiario", "Beneficiario/a")]

# Qué campos se ven según el tipo de la fila (o según el rol, para «viene por» del practicante)
SEGUN_TIPO = {
    "organizacion": "organizacion", "rol_organizacion": "organizacion", "cargo": "organizacion",
    "comunidad": "comunidad", "rol_comunidad": "comunidad",
    "proyecto": "proyecto", "tarea": "proyecto", "como": "proyecto", "es_responsable": "proyecto",
    "actividad": "actividad", "rol": "proyecto actividad", "desde": "organizacion comunidad proyecto", "hasta": "organizacion proyecto",
}


def _proyectos():
    from apps.proyectos.models import Proyecto

    return Proyecto.objects.order_by("nombre")


class RelacionForm(BootstrapMixin, forms.Form):
    tipo = forms.ChoiceField(choices=TIPOS, required=False, label="Tipo de relación",
                             help_text="Al elegirlo aparecen solo los datos de ese tipo.")
    organizacion = SelectorField(ORGANIZACIONES, required=False, label="Organización", help_text="Si no está, créala desde aquí.")
    rol_organizacion = forms.ChoiceField(choices=ROLES_ORGANIZACION, required=False, label="Rol en la organización")
    cargo = forms.CharField(max_length=80, required=False, label="Cargo o detalle", help_text="Ej.: Profesora de Lenguaje, Tesorera.")
    viene_actividad = SelectorField(ACTIVIDADES, required=False, crear=False, label="Viene por la actividad o tarea",
                                    help_text="Opcional. Queda también como participante (practicante).")
    viene_proyecto = forms.ModelChoiceField(_proyectos(), required=False, label="O viene por el proyecto",
                                            help_text="Opcional. Queda en el equipo del proyecto como practicante.")
    comunidad = SelectorField(COMUNIDADES, required=False, crear=False, label="Comunidad")
    rol_comunidad = forms.ChoiceField(choices=[("", "Elegir…")] + ComunidadMiembro.ROLES, required=False, label="Rol en la comunidad")
    proyecto = forms.ModelChoiceField(_proyectos(), required=False, label="Proyecto")
    tarea = SelectorField(ACTIVIDADES, filtros={"tareas": 1}, required=False, crear=False, label="O una tarea de un proyecto")
    como = forms.ChoiceField(choices=COMO, required=False, initial="equipo", label="Cómo participa")
    actividad = SelectorField(ACTIVIDADES, required=False, crear=False, label="Actividad")
    rol = forms.ModelChoiceField(RolParticipacion.objects.filter(activo=True), required=False, label="Rol",
                                 help_text="Ej.: Voluntario, Tallerista.")
    es_responsable = forms.BooleanField(required=False, label="Es responsable")
    desde = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), required=False, label="Desde")
    hasta = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), required=False, label="Hasta",
                            help_text="Vacío si sigue vigente.")

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["viene_proyecto"].queryset = self.fields["proyecto"].queryset = _proyectos()
        tipo = self.add_prefix("tipo")
        for nombre, valores in SEGUN_TIPO.items():
            self.fields[nombre].widget.attrs.update({"data-mostrar-si-campo": tipo, "data-mostrar-si-valor": valores})
        for nombre in ("viene_actividad", "viene_proyecto"):
            self.fields[nombre].widget.attrs.update({"data-mostrar-si-campo": self.add_prefix("rol_organizacion"), "data-mostrar-si-valor": "practicante"})

    def has_changed(self):
        # «Cómo participa» parte en «equipo»: no basta para considerar la fila llena
        return any(n != "como" for n in self.changed_data)

    def clean(self):
        d = super().clean()
        tipo = d.get("tipo")
        if not tipo:
            raise forms.ValidationError("Elige el tipo de relación, o deja la fila vacía.")
        if d.get("desde") and d.get("hasta") and d["hasta"] < d["desde"]:
            self.add_error("hasta", "La fecha de término no puede ser anterior a la de inicio.")
        if tipo == "organizacion":
            org = d.get("organizacion")
            if not org:
                self.add_error("organizacion", "Elige la organización.")
            if not d.get("rol_organizacion"):
                self.add_error("rol_organizacion", "Elige el rol en la organización.")
            elif d["rol_organizacion"] == "estudiante" and org and not org.es_educativa:
                self.add_error("rol_organizacion", f"«{org}» no es una institución educativa: elige otro rol (por ejemplo, Socio/a u Otro).")
            if d.get("rol_organizacion") == "practicante" and d.get("viene_actividad") and d.get("viene_proyecto"):
                self.add_error("viene_proyecto", "Indica la actividad o tarea, o el proyecto, pero no ambos.")
        elif tipo == "comunidad":
            if not d.get("comunidad"):
                self.add_error("comunidad", "Elige la comunidad.")
        elif tipo == "proyecto":
            if not d.get("proyecto") and not d.get("tarea"):
                self.add_error("proyecto", "Elige el proyecto o una tarea.")
            if d.get("tarea") and not d["tarea"].proyecto_id:
                self.add_error("tarea", "Esa actividad no es una tarea de un proyecto: usa el tipo «Actividad».")
        elif tipo == "actividad":
            if not d.get("actividad"):
                self.add_error("actividad", "Elige la actividad.")
            if not d.get("rol"):
                self.add_error("rol", "Elige el rol en la actividad.")
        return d


class BaseRelaciones(BaseFormSet):
    def filas_llenas(self):
        return [f.cleaned_data for f in self.forms if f.has_changed() and f.cleaned_data]


RelacionesFormSet = formset_factory(RelacionForm, formset=BaseRelaciones, extra=2, max_num=30, validate_max=True)


def relaciones_formset(datos=None):
    """Sin los datos de la sección (p. ej. un envío sin relaciones) el formset queda sin enviar: no hay filas que guardar."""
    if datos is not None and f"{PREFIJO}-TOTAL_FORMS" not in datos:
        datos = None
    return RelacionesFormSet(datos, prefix=PREFIJO)


def relaciones_validas(formset):
    return not formset.is_bound or formset.is_valid()


def _rol(codigo):
    return RolParticipacion.objects.filter(codigo=codigo).first()


def _participar(persona, actividad, rol, usuario):
    """Suma a la persona como participante (confirmada) y le agrega el perfil del rol. Nunca duplica."""
    from apps.actividades.models import Participacion
    from apps.actividades.views import _perfil_del_rol
    from apps.nucleo.models import EstadoParticipacion

    estado = EstadoParticipacion.objects.filter(codigo="confirmado").first() or EstadoParticipacion.objects.filter(codigo="invitado").first()
    Participacion.objects.get_or_create(actividad=actividad, persona=persona, rol=rol, defaults={"estado": estado, "creado_por": usuario})
    _perfil_del_rol(persona, rol)


def _en_proyecto(persona, proyecto, tipo, rol=None, responsable=False, desde=None, hasta=None):
    from apps.proyectos.models import ProyectoPersona

    ProyectoPersona.objects.get_or_create(proyecto=proyecto, persona=persona, tipo=tipo,
                                          defaults={"rol": rol, "es_responsable": responsable, "desde": desde, "hasta": hasta})


def guardar_relaciones(formset, persona, usuario):
    """Crea los vínculos de cada fila llena. Se llama dentro de la transacción que crea la persona."""
    if not formset.is_bound:
        return 0
    from apps.personas.models import PersonaFormacion, PersonaOrganizacion

    filas = formset.filas_llenas()
    for d in filas:
        tipo, desde, hasta = d["tipo"], d.get("desde"), d.get("hasta")
        if tipo == "organizacion":
            org, rol, detalle = d["organizacion"], d["rol_organizacion"], d.get("cargo", "").strip()
            if rol == "estudiante":
                PersonaFormacion.objects.create(persona=persona, organizacion=org, estado="estudiante",
                                                anio_inicio=desde.year if desde else None, anio_termino=hasta.year if hasta else None,
                                                asignatura=detalle, vigente=hasta is None or hasta >= timezone.localdate())
                continue
            nombre = dict(ROLES_ORGANIZACION)[rol] if rol != "otro" else ""
            cargo = " · ".join(x for x in [nombre, detalle] if x) or "Otro"
            PersonaOrganizacion.objects.create(persona=persona, organizacion=org, cargo=cargo[:120],
                                               tipo_cargo="directorio" if rol == "dirigente" else "funcional", fecha_inicio=desde, fecha_termino=hasta)
            if rol == "practicante":
                practicante = _rol("practicante")
                if d.get("viene_actividad") and practicante:
                    _participar(persona, d["viene_actividad"], practicante, usuario)
                if d.get("viene_proyecto"):
                    _en_proyecto(persona, d["viene_proyecto"], "equipo", rol=practicante, desde=desde, hasta=hasta)
        elif tipo == "comunidad":
            ComunidadMiembro.objects.get_or_create(comunidad=d["comunidad"], persona=persona,
                                                   defaults={"rol": d.get("rol_comunidad") or "integrante", "desde": desde})
        elif tipo == "proyecto":
            como = d.get("como") or "equipo"
            rol = d.get("rol") if como == "equipo" else None
            if d.get("proyecto"):
                _en_proyecto(persona, d["proyecto"], como, rol=rol, responsable=como == "equipo" and d.get("es_responsable"), desde=desde, hasta=hasta)
            if d.get("tarea"):
                rol_tarea = rol or _rol("beneficiario" if como == "beneficiario" else "participante") or RolParticipacion.objects.filter(activo=True).first()
                _participar(persona, d["tarea"], rol_tarea, usuario)
        elif tipo == "actividad":
            _participar(persona, d["actividad"], d["rol"], usuario)
    return len(filas)

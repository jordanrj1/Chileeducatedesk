"""Al registrar una persona (F25, F26 P2):
- «Organización y comunidad» (`OrganizacionComunidadForm`), dentro del bloque «Tipo de persona»: su organización con
  rol y cargo, y su comunidad, una sola vez. Si es estudiante, su institución y carrera se piden en «Estudiante»; si es
  vecino o vecina, su comunidad va en «Vecino o vecina»; si es invitado, su organización va en «Invitado».
- «Relaciones»: filas para las otras relaciones, un proyecto o tarea, o una actividad.
Todo lo que crea vínculos con organizaciones o comunidades pasa por `vincular()`, dentro de la misma transacción que
crea la persona. Las filas vacías se ignoran y nada es obligatorio."""
from django import forms
from django.forms import BaseFormSet, formset_factory

from apps.actividades.selector import ACTIVIDADES
from apps.comunidades.models import ComunidadMiembro
from apps.comunidades.selector import COMUNIDADES
from apps.nucleo.formularios import BootstrapMixin, SelectorField
from apps.nucleo.models import EstadoParticipacion, RolOrganizacion, RolParticipacion
from apps.organizaciones.selector import ORGANIZACIONES

PREFIJO = "relaciones"
PREFIJO_VINCULO = "vin"
TIPOS = [("", "Elegir…"), ("proyecto", "Proyecto o tarea"), ("actividad", "Actividad")]
COMO = [("equipo", "Parte del equipo"), ("beneficiario", "Beneficiario/a")]

# Qué campos se ven según el tipo de la fila
SEGUN_TIPO = {
    "proyecto": "proyecto", "tarea": "proyecto", "como": "proyecto", "es_responsable": "proyecto",
    "actividad": "actividad", "estado": "actividad", "rol": "proyecto actividad", "desde": "proyecto", "hasta": "proyecto",
}
# Campos de «Organización y comunidad» que no se piden si ya los pide la sección de un tipo marcado (con JavaScript;
# sin él se ven todos y se guarda lo que se escriba, sin duplicar)
OCULTAR_SI_TIPO = {"organizacion": "estudiante invitado", "rol_organizacion": "estudiante invitado", "cargo": "estudiante invitado",
                   "desde": "estudiante invitado", "comunidad": "vecino", "rol_comunidad": "vecino"}


def _proyectos():
    from apps.proyectos.models import Proyecto

    return Proyecto.objects.order_by("nombre")


class RelacionForm(BootstrapMixin, forms.Form):
    tipo = forms.ChoiceField(choices=TIPOS, required=False, label="Tipo de relación",
                             help_text="Al elegirlo aparecen solo los datos de ese tipo.")
    proyecto = forms.ModelChoiceField(_proyectos(), required=False, label="Proyecto")
    tarea = SelectorField(ACTIVIDADES, filtros={"tareas": 1}, required=False, crear=False, label="O una tarea de un proyecto")
    como = forms.ChoiceField(choices=COMO, required=False, initial="equipo", label="Cómo participa")
    actividad = SelectorField(ACTIVIDADES, required=False, crear=False, label="Actividad")
    rol = forms.ModelChoiceField(RolParticipacion.objects.filter(activo=True), required=False, label="Rol",
                                 help_text="Ej.: Voluntario, Tallerista.")
    estado = forms.ModelChoiceField(EstadoParticipacion.objects.none(), required=False, label="Estado en la actividad",
                                    help_text="Si no eliges, queda «Inscrito».")
    es_responsable = forms.BooleanField(required=False, label="Es responsable")
    desde = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), required=False, label="Desde")
    hasta = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), required=False, label="Hasta",
                            help_text="Vacío si sigue vigente.")

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.actividades.forms import estados_para_elegir

        self.fields["proyecto"].queryset = _proyectos()
        self.fields["estado"].queryset = estados_para_elegir()  # F25 E2: los cinco estados que se eligen a mano
        tipo = self.add_prefix("tipo")
        for nombre, valores in SEGUN_TIPO.items():
            self.fields[nombre].widget.attrs.update({"data-mostrar-si-campo": tipo, "data-mostrar-si-valor": valores})

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
        if tipo == "proyecto":
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


class OrganizacionComunidadForm(BootstrapMixin, forms.Form):
    """F26 P2: «Organización y comunidad», una sola vez, en el bloque «Tipo de persona». Reemplaza las filas de tipo
    organización y comunidad que tenía «Relaciones». Más organizaciones o comunidades se agregan después en su ficha."""

    organizacion = SelectorField(ORGANIZACIONES, required=False, label="Organización",
                                 help_text="Donde trabaja, participa o representa. Ej.: la junta de vecinos. Si no está, créala desde aquí.")
    rol_organizacion = forms.ModelChoiceField(RolOrganizacion.objects.none(), required=False, label="Rol en la organización",
                                              help_text="Ej.: Dirigente. El detalle va en el cargo.")
    cargo = forms.CharField(max_length=120, required=False, label="Cargo o detalle", help_text="Ej.: Profesora de Lenguaje, Tesorera.")
    desde = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), required=False, label="Desde")
    viene_actividad = SelectorField(ACTIVIDADES, required=False, crear=False, label="Viene por la actividad o tarea",
                                    help_text="Opcional. Queda también como participante (practicante).")
    viene_proyecto = forms.ModelChoiceField(_proyectos(), required=False, label="O viene por el proyecto",
                                            help_text="Opcional. Queda en el equipo del proyecto como practicante.")
    comunidad = SelectorField(COMUNIDADES, required=False, crear=False, label="Comunidad",
                              help_text="Si integra una comunidad (vecinal, de apoderados, indígena…).")
    rol_comunidad = forms.ChoiceField(choices=ComunidadMiembro.ROLES, required=False, initial="integrante", label="Rol en la comunidad")

    def __init__(self, *a, **kw):
        kw.setdefault("prefix", PREFIJO_VINCULO)
        super().__init__(*a, **kw)
        rol = self.fields["rol_organizacion"]
        rol.queryset = RolOrganizacion.objects.filter(activo=True)
        rol.to_field_name = "codigo"  # se envía el código (estudiante, practicante…), estable entre bases
        self.fields["viene_proyecto"].queryset = _proyectos()
        for nombre, tipos in OCULTAR_SI_TIPO.items():
            self.fields[nombre].widget.attrs["data-ocultar-si-tipo"] = tipos
        for nombre in ("viene_actividad", "viene_proyecto"):
            self.fields[nombre].widget.attrs.update({"data-mostrar-si-campo": self.add_prefix("rol_organizacion"), "data-mostrar-si-valor": "practicante"})

    def has_changed(self):
        return any(n != "rol_comunidad" for n in self.changed_data)  # el rol parte en «Integrante»: no basta

    def clean(self):
        d = super().clean()
        org, rol = d.get("organizacion"), d.get("rol_organizacion")
        if (rol or (d.get("cargo") or "").strip()) and not org:
            self.add_error("organizacion", "Elige la organización del rol o del cargo, o deja esos datos vacíos.")
        if rol and rol.codigo == "estudiante" and org and not org.es_educativa:
            self.add_error("rol_organizacion", f"«{org}» no es una institución educativa: elige otro rol (por ejemplo, Socio o socia u Otro).")
        if d.get("viene_actividad") and d.get("viene_proyecto"):
            self.add_error("viene_proyecto", "Indica la actividad o tarea, o el proyecto, pero no ambos.")
        return d


def organizacion_comunidad_form(datos=None):
    """Sin sus campos en lo enviado (p. ej. una integración) queda sin enviar: no guarda nada."""
    if datos is not None and not any(k.startswith(f"{PREFIJO_VINCULO}-") for k in datos):
        datos = None
    return OrganizacionComunidadForm(datos)


def guardar_organizacion_comunidad(form, persona, usuario):
    """Crea (o reutiliza) con `vincular()` el vínculo con la organización (o la formación, si es estudiante de una
    institución educativa) y el lugar en el padrón de la comunidad. Se llama dentro de la transacción que crea la persona."""
    if not form.is_bound or not form.has_changed():
        return
    from apps.personas.vinculos import vincular

    d = form.cleaned_data
    org, rol, detalle, desde = d.get("organizacion"), d.get("rol_organizacion"), (d.get("cargo") or "").strip(), d.get("desde")
    if org:
        if rol and rol.codigo == "estudiante" and org.es_educativa:  # vincular() la deja como formación, sin duplicar
            f = vincular(persona, organizacion=org, rol=rol, estado_formacion="estudiante", desde=desde)["formacion"]
            if detalle and not f.asignatura:
                f.asignatura = detalle[:200]
                f.save(update_fields=["asignatura"])
        else:
            vincular(persona, organizacion=org, cargo=detalle, rol=rol, desde=desde,
                     tipo_cargo="directorio" if rol and rol.codigo == "dirigente" else ("autoridad" if rol and rol.codigo == "autoridad" else "funcional"))
    if rol and rol.codigo == "practicante":
        practicante = _rol("practicante")
        if d.get("viene_actividad") and practicante:
            _participar(persona, d["viene_actividad"], practicante, usuario)
        if d.get("viene_proyecto"):
            _en_proyecto(persona, d["viene_proyecto"], "equipo", rol=practicante, desde=desde)
    if d.get("comunidad"):
        vincular(persona, comunidad=d["comunidad"], rol_comunidad=d.get("rol_comunidad") or "integrante", desde=desde)


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


def _participar(persona, actividad, rol, usuario, estado=None):
    """Suma a la persona como participante («Inscrito», o el estado elegido en la fila) y le agrega el perfil del rol. Nunca duplica."""
    from apps.actividades.forms import estado_inicial
    from apps.actividades.models import Participacion
    from apps.actividades.views import _perfil_del_rol

    estado = estado or estado_inicial()
    asistencia = {"asistio": True, "no_asistio": False}.get(estado.codigo)
    from apps.actividades.servicios import asegurar_organizacion

    part, creada = Participacion.objects.get_or_create(actividad=actividad, persona=persona, rol=rol,
                                                       defaults={"estado": estado, "creado_por": usuario, "asistencia": asistencia})
    if creada:
        asegurar_organizacion(part)  # F25 E4: su institución queda en la actividad como «Aporta personas»
    _perfil_del_rol(persona, rol)


def _en_proyecto(persona, proyecto, tipo, rol=None, responsable=False, desde=None, hasta=None):
    from apps.proyectos.models import ProyectoPersona

    pp, _ = ProyectoPersona.objects.get_or_create(proyecto=proyecto, persona=persona, tipo=tipo,
                                                  defaults={"rol": rol, "es_responsable": responsable, "desde": desde, "hasta": hasta})
    if responsable and pp.es_responsable:  # F26 P2: también el responsable del proyecto (una sola verdad)
        from apps.proyectos.servicios import responsable_desde_equipo

        responsable_desde_equipo(pp)


def guardar_relaciones(formset, persona, usuario):
    """Crea los vínculos de cada fila llena. Se llama dentro de la transacción que crea la persona."""
    if not formset.is_bound:
        return 0
    filas = formset.filas_llenas()
    for d in filas:
        tipo, desde, hasta = d["tipo"], d.get("desde"), d.get("hasta")
        if tipo == "proyecto":
            como = d.get("como") or "equipo"
            rol = d.get("rol") if como == "equipo" else None
            if d.get("proyecto"):
                _en_proyecto(persona, d["proyecto"], como, rol=rol, responsable=como == "equipo" and d.get("es_responsable"), desde=desde, hasta=hasta)
            if d.get("tarea"):
                rol_tarea = rol or _rol("beneficiario" if como == "beneficiario" else "participante") or RolParticipacion.objects.filter(activo=True).first()
                _participar(persona, d["tarea"], rol_tarea, usuario)
        elif tipo == "actividad":
            _participar(persona, d["actividad"], d["rol"], usuario, d.get("estado"))
    return len(filas)

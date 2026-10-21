"""Fichas por tipo de persona en el formulario: al marcar «Estudiante», «Vecino o vecina», «Invitado» o «Voluntario»
aparece su sección y al guardar se escriben solo las secciones marcadas, en la misma transacción que la persona.
Cada sección dice qué formularios lleva, cómo se guarda y qué resume su tarjeta en la pestaña Datos de la ficha.
Lo usan Personas → Nueva, Editar y «Editar» de cada tarjeta."""
from django import forms
from django.db.models import Q
from django.forms import BaseFormSet, BaseInlineFormSet, inlineformset_factory
from django.forms.utils import ErrorList
from django.urls import reverse

from apps.actividades.selector import ACTIVIDADES
from apps.nucleo.formularios import BootstrapMixin, SelectorField, fijar_valores_selectores
from apps.nucleo.models import EstadoVoluntario, Parentesco, PerfilPersona, TipoInvitado, TramoEtario
from apps.nucleo.selector import pk_seguro
from apps.organizaciones.selector import ORGANIZACIONES
from apps.territorio.forms import DireccionForm
from apps.territorio.ubicacion import sin_errores

from .forms import EstudianteForm, _mismo_nombre, edad_aproximada
from .models import FamiliarVinculado, FichaInvitado, FichaVecino, FichaVoluntario, IntegranteHogar, Persona, PersonaDireccion, PersonaFormacion
from .selector import PERSONAS

SI_NO = [("", "Sin información"), (True, "Sí"), (False, "No")]


def _activos(modelo, actual=None):
    """Valores activos de un catálogo, más el que el registro ya tenía (para no perderlo al editar)."""
    return modelo.objects.filter(Q(activo=True) | Q(pk=actual or 0))


# --- Formularios de cada ficha ------------------------------------------------------------------------------------

class ResidenciaForm(DireccionForm):
    """Dirección de residencia del vecino o vecina (número de casa, comuna y sector) y su comunidad, en cascada.
    Si la comunidad no está en la lista, se escribe su nombre y se crea al guardar, en la comuna y el sector elegidos."""

    rol_comunidad = forms.ChoiceField(choices=[], initial="integrante", required=False, label="Rol en la comunidad")
    nueva_comunidad = forms.CharField(required=False, max_length=200, label="¿No está la comunidad? Escribe su nombre",
                                      help_text="Se crea al guardar, en la comuna y el sector elegidos. Ej.: Vecinos de Villa Los Aromos.",
                                      widget=forms.TextInput(attrs={"autocomplete": "off"}))

    def __init__(self, *a, usuario=None, **kw):
        from apps.comunidades.models import ComunidadMiembro

        self.usuario = usuario
        puede_unir = bool(usuario and usuario.has_perm("comunidades.add_comunidadmiembro"))
        self.puede_crear_comunidad = puede_unir and usuario.has_perm("comunidades.add_comunidad")
        kw.setdefault("ubicacion_comunidad", puede_unir)
        super().__init__(*a, **kw)
        self.fields["numero"].label = "Número de casa"
        self.fields["calle"].label = "Calle o pasaje"
        if puede_unir:
            self.fields["rol_comunidad"].choices = ComunidadMiembro.ROLES
        else:
            self.fields.pop("rol_comunidad")
        if not self.puede_crear_comunidad:
            self.fields.pop("nueva_comunidad")

    def clean(self):
        from apps.comunidades.models import Comunidad

        d = super().clean()
        nueva = " ".join((d.get("nueva_comunidad") or "").split())
        if nueva:
            if d.get("comunidad"):
                self.add_error("nueva_comunidad", "Elige una comunidad de la lista o escribe una nueva, no las dos.")
            elif d.get("comuna"):
                igual = _mismo_nombre(Comunidad.objects.filter(comuna=d["comuna"]), nueva)
                if igual:
                    self.add_error("nueva_comunidad", f"Ya existe «{igual.nombre}» en {d['comuna'].nombre}: elígela en la lista.")
        return d

    def guardar(self, persona):
        from apps.comunidades.models import Comunidad, ComunidadMiembro

        d = self.cleaned_data
        PersonaDireccion.objects.create(persona=persona, direccion=self.save(), tipo="residencia")
        comunidad = d.get("comunidad")
        nueva = " ".join((d.get("nueva_comunidad") or "").split())
        if not comunidad and nueva and self.puede_crear_comunidad:
            comunidad = Comunidad.objects.create(nombre=nueva, comuna=d["comuna"], sector=d.get("sector"), tipo="vecinal", creado_por=self.usuario)
        if comunidad:
            ComunidadMiembro.objects.get_or_create(comunidad=comunidad, persona=persona, defaults={"rol": d.get("rol_comunidad") or "integrante"})


class DatosVecinoForm(BootstrapMixin, forms.Form):
    """Edad y sexo del vecino, cuando el formulario de la persona no los pide (ficha rápida o «Editar» de la tarjeta)."""

    edad = edad_aproximada()
    sexo = forms.ChoiceField(choices=[("", "---------")] + Persona.SEXOS, required=False,
                             help_text="Opcional. La identidad de género se registra aparte, en los datos sensibles 🔒.")

    def __init__(self, *a, persona=None, **kw):
        self.persona = persona
        if persona is not None and persona.pk:
            kw.setdefault("initial", {"sexo": persona.sexo})
        super().__init__(*a, **kw)

    def clean_edad(self):
        edad = self.cleaned_data.get("edad")
        p = self.persona
        if edad is not None and p is not None and p.fecha_nacimiento and not p.fecha_nacimiento_aproximada:
            raise forms.ValidationError("Ya tiene su fecha de nacimiento exacta: si hay que corregirla, hazlo en «Editar» de la persona.")
        return edad

    def guardar(self, persona):
        d = self.cleaned_data
        if "sexo" in self.changed_data:
            persona.sexo = d.get("sexo") or ""
        if d.get("edad") is not None:
            persona.fijar_edad_aproximada(d["edad"])
        persona.save()


def _datos_vecino(datos, persona, base):
    """Edad y sexo del vecino: solo los que el formulario de la persona no pide (la ficha rápida ya trae el sexo)."""
    faltan = [c for c in ("edad", "sexo") if base is None or c not in base.fields]
    if not faltan:
        return None
    form = DatosVecinoForm(datos, prefix="vec-per", persona=persona)
    for c in ("edad", "sexo"):
        if c not in faltan:
            form.fields.pop(c)
    return form


class FichaVecinoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = FichaVecino
        fields = ["jefatura_hogar", "integrantes_hogar"]
        widgets = {"jefatura_hogar": forms.Select(choices=SI_NO)}


class IntegranteForm(BootstrapMixin, forms.ModelForm):
    """Una fila del hogar: «2 · Hijo o hija · Niñez · vive en el hogar». Sin nombres."""

    class Meta:
        model = IntegranteHogar
        fields = ["cantidad", "parentesco", "tramo", "vive_en_hogar"]
        widgets = {"cantidad": forms.NumberInput(attrs={"min": 1, "max": 99})}

    def __init__(self, *a, opciones=None, **kw):
        super().__init__(*a, **kw)
        cantidad = self.fields["cantidad"]
        cantidad.required = False
        cantidad.widget.attrs.update(placeholder="1", min=1)
        if not self.instance.pk:
            self.initial["cantidad"] = None  # una fila vacía no cuenta como escrita
        self.fields["parentesco"].queryset = _activos(Parentesco, self.instance.parentesco_id)
        tramo = self.fields["tramo"]
        tramo.queryset = TramoEtario.para_elegir(conservar=[self.instance.tramo_id] if self.instance.tramo_id else None)
        tramo.label_from_instance = lambda t: t.etiqueta
        tramo.empty_label = "No se sabe"
        for campo in self.fields.values():  # la explicación va una sola vez, arriba de las filas
            campo.help_text = ""
        _usar_opciones(self, opciones)

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")
        if cantidad is None:
            return 1
        if cantidad < 1:
            raise forms.ValidationError("Debe ser 1 o más.")
        return cantidad


def _usar_opciones(form, opciones):
    """Las listas de la fila usan las opciones ya leídas por el grupo (sin una consulta por fila al dibujarlas)."""
    for campo, lista in (opciones or {}).items():
        form.fields[campo].choices = [("", form.fields[campo].empty_label)] + lista


class FilasBase(BaseInlineFormSet):
    """Filas de un grupo: las ya guardadas se pueden quitar con una casilla «Quitar esta fila».
    Las opciones de los catálogos (parentesco, tramo) se leen una sola vez para todas las filas."""

    catalogos = {"parentesco": Parentesco}

    def get_form_kwargs(self, index):
        kw = super().get_form_kwargs(index)
        kw["opciones"] = self.opciones()
        return kw

    def opciones(self):
        if getattr(self, "_opciones", None) is None:
            filas = self.get_queryset() if self.instance.pk else None
            self._opciones = {}
            for campo, modelo in self.catalogos.items():
                usados = [u for u in filas.values_list(f"{campo}_id", flat=True) if u] if filas is not None else []
                etiqueta = (lambda o: o.etiqueta) if hasattr(modelo, "etiqueta") else str  # el tramo muestra sus edades
                self._opciones[campo] = [(o.pk, etiqueta(o)) for o in modelo.objects.filter(Q(activo=True) | Q(pk__in=usados))]
        return self._opciones

    def add_fields(self, form, index):
        super().add_fields(form, index)
        if "DELETE" in form.fields:
            form.fields["DELETE"].label = "Quitar esta fila"
            form.fields["DELETE"].widget.attrs["class"] = "form-check-input"


class FilasHogar(FilasBase):
    catalogos = {"parentesco": Parentesco, "tramo": TramoEtario}

    def clean(self):
        super().clean()
        vistas = set()
        for f in self.forms:
            d = getattr(f, "cleaned_data", None) or {}
            if not d or d.get("DELETE") or not d.get("parentesco"):
                continue
            clave = (d["parentesco"].pk, d["tramo"].pk if d.get("tramo") else None, bool(d.get("vive_en_hogar")))
            if clave in vistas:
                raise forms.ValidationError("Hay dos filas con el mismo parentesco, edad y lugar donde vive: suma las cantidades en una sola fila.")
            vistas.add(clave)


IntegrantesFormSet = inlineformset_factory(FichaVecino, IntegranteHogar, form=IntegranteForm, formset=FilasHogar, extra=3, can_delete=True,
                                           can_delete_extra=False)


class FamiliarForm(BootstrapMixin, forms.ModelForm):
    """Un familiar que ya está registrado como persona (no se crea una persona solo para contarla)."""

    familiar = SelectorField(PERSONAS, crear=False, label="Familiar ya registrado")

    class Meta:
        model = FamiliarVinculado
        fields = ["familiar", "parentesco"]

    def __init__(self, *a, persona=None, opciones=None, **kw):
        super().__init__(*a, **kw)
        self.fields["parentesco"].queryset = _activos(Parentesco, self.instance.parentesco_id)
        self.fields["parentesco"].help_text = ""
        _usar_opciones(self, opciones)
        if persona is not None and persona.pk:
            self.fields["familiar"].con_filtros(excluir=persona.pk)  # nadie es su propio familiar
            fijar_valores_selectores(self)


class FilasFamiliares(FilasBase):
    def clean(self):
        super().clean()
        vistos = set()
        for f in self.forms:
            d = getattr(f, "cleaned_data", None) or {}
            if d and not d.get("DELETE") and d.get("familiar"):
                if d["familiar"].pk in vistos:
                    raise forms.ValidationError("Ese familiar está dos veces: déjalo en una sola fila.")
                vistos.add(d["familiar"].pk)


FamiliaresFormSet = inlineformset_factory(Persona, FamiliarVinculado, fk_name="persona", form=FamiliarForm, formset=FilasFamiliares, extra=2,
                                          can_delete=True, can_delete_extra=False)


class FichaInvitadoForm(BootstrapMixin, forms.ModelForm):
    invitado_por = SelectorField(PERSONAS, required=False, label="Invitado o invitada por", help_text="Quién la invitó o la contactó, si se sabe.")
    organizacion = SelectorField(ORGANIZACIONES, required=False, label="Organización de procedencia", help_text="Ej.: la municipalidad o el medio de prensa.")
    actividad = SelectorField(ACTIVIDADES, required=False, crear=False, label="Actividad", help_text="Opcional: la actividad a la que se le invitó.")

    class Meta:
        model = FichaInvitado
        fields = ["tipo", "organizacion", "cargo", "invitado_por", "actividad", "motivo"]
        widgets = {"motivo": forms.Textarea(attrs={"rows": 2})}
        help_texts = {"tipo": "Ej.: Autoridad.", "motivo": "Para qué se le invitó. Ej.: expositora en la charla de reciclaje."}

    def __init__(self, *a, persona=None, **kw):
        super().__init__(*a, **kw)
        self.fields["tipo"].queryset = _activos(TipoInvitado, self.instance.tipo_id)
        if persona is not None and persona.pk:
            self.fields["invitado_por"].con_filtros(excluir=persona.pk)  # quien invita es otra persona
            fijar_valores_selectores(self)


class FichaVoluntarioForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = FichaVoluntario
        fields = ["estado", "fecha_ingreso", "horas_semanales", "motivacion"]
        widgets = {"fecha_ingreso": forms.DateInput, "motivacion": forms.Textarea(attrs={"rows": 2})}
        help_texts = {"estado": "Ej.: Activo.", "fecha_ingreso": "Cuándo empezó como voluntario o voluntaria. Ej.: 01-03-2026.",
                      "motivacion": "Ej.: quiere apoyar los talleres con niños los sábados."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["estado"].queryset = _activos(EstadoVoluntario, self.instance.estado_id)


# --- Secciones -----------------------------------------------------------------------------------------------------

def _con_datos(f):
    """Una parte de la sección se valida y se guarda si ya existía (al editar) o si trae algo escrito. Un campo que no llegó
    en lo enviado no cuenta como escrito (p. ej. el estado «Estudiante» que viene marcado de antemano)."""
    if isinstance(f, BaseFormSet):
        return f.initial_form_count() > 0 or any(_con_datos(sub) for sub in f.forms)
    if getattr(getattr(f, "instance", None), "pk", None):
        return True
    return f.is_bound and any(f.add_prefix(n) in f.data for n in f.changed_data)


def _sin_errores(f):
    """Un formulario (o grupo de filas) que no se valida no muestra errores al volver a dibujarse."""
    if isinstance(f, BaseFormSet):
        f._errors, f._non_form_errors = [], ErrorList()
        for sub in f.forms:
            sin_errores(sub)
    else:
        sin_errores(f)


def _uno_a_uno(persona, relacion):
    return getattr(persona, relacion, None) if persona is not None and persona.pk else None


class Seccion:
    """Una ficha por tipo: sus formularios (`armar`), cómo se guardan (`guardar`) y su tarjeta en la pestaña Datos (`tarjeta`)."""

    codigo = ""  # el valor de PerfilPersona.ficha
    titulo = ""
    ayuda = ""
    plantilla = "personas/fichas/_campos.html"
    permiso = ""  # para ofrecerla y guardarla
    restringida = False

    def __init__(self, registro):
        self.registro = registro
        self.formularios = {k: v for k, v in self.armar(registro.datos, registro.persona, registro.usuario).items() if v is not None}

    @property
    def elegida(self):
        return self.codigo in self.registro.elegidas

    def armar(self, datos, persona, usuario):
        return {}

    def a_procesar(self):
        return [f for f in self.formularios.values() if _con_datos(f)]

    def guardar(self, persona):
        raise NotImplementedError

    def url_editar(self, persona):
        return reverse("personas:ficha_tipo", args=[persona.pk, self.codigo])

    @classmethod
    def tarjeta(cls, persona, datos):
        return []


class SeccionEstudiante(Seccion):
    codigo, titulo = "estudiante", "Estudiante"
    ayuda = "Institución, sede o casa matriz y carrera. Si la sede o la carrera no están en la lista, escríbelas y se crean al guardar."
    plantilla = "personas/fichas/_estudiante.html"
    permiso = "personas.add_personaformacion"

    def armar(self, datos, persona, usuario):
        actual = persona.formaciones.filter(vigente=True).order_by("-pk").first() if persona is not None and persona.pk else None
        return {"estudios": EstudianteForm(datos, prefix="est", instance=actual, usuario=usuario)}

    def guardar(self, persona):
        f = self.formularios["estudios"]
        if f in self.a_procesar():
            obj = f.save(commit=False)
            obj.persona = persona
            f.crear_lo_escrito(obj)
            obj.save()

    @classmethod
    def tarjeta(cls, persona, datos):
        filas = []
        for f in datos["formaciones"]:
            detalle = " · ".join(x for x in [f.sede_institucion.nombre if f.sede_institucion_id else f.sede, f.get_estado_display(),
                                             f"{f.nivel_actual}.º año" if f.nivel_actual else "", f.get_jornada_display() if f.jornada else ""] if x)
            filas.append({"etiqueta": str(f.organizacion), "valor": " · ".join(x for x in [f.carrera.nombre if f.carrera_id else "", detalle] if x)})
        return filas


class SeccionVecino(Seccion):
    codigo, titulo = "vecino", "Vecino o vecina"
    ayuda = "Dónde vive (número de casa, comuna, sector y comunidad) y, si lo cuenta, cómo es su hogar."
    plantilla = "personas/fichas/_vecino.html"
    permiso = "personas.add_fichavecino"

    def armar(self, datos, persona, usuario):
        self.residencia = None
        if persona is not None and persona.pk:
            self.residencia = (persona.direcciones.filter(tipo="residencia", vigente=True).select_related("direccion__comuna", "direccion__sector")
                               .order_by("-pk").first())
        base = self.registro.base
        ficha = _uno_a_uno(persona, "ficha_vecino")
        return {
            "residencia": None if self.residencia else ResidenciaForm(datos, prefix="vec", usuario=usuario),
            "datos": _datos_vecino(datos, persona, base),
            "hogar": FichaVecinoForm(datos, prefix="vec-hog", instance=ficha),
            "integrantes": IntegrantesFormSet(datos, prefix="vec-int", instance=ficha or FichaVecino()),
            "familiares": FamiliaresFormSet(datos, prefix="vec-fam", instance=persona if persona is not None and persona.pk else Persona(),
                                            form_kwargs={"persona": persona}),
        }

    def guardar(self, persona):
        procesar = self.a_procesar()
        f = self.formularios
        for nombre in ("residencia", "datos"):
            if f.get(nombre) in procesar:
                f[nombre].guardar(persona)
        if f["hogar"] in procesar or f["integrantes"] in procesar:
            if f["hogar"] in procesar:
                ficha = f["hogar"].save(commit=False)
                ficha.persona = persona
                ficha.save()
            else:
                ficha, _ = FichaVecino.objects.get_or_create(persona=persona)
            if f["integrantes"] in procesar:
                f["integrantes"].instance = ficha
                f["integrantes"].save()
        if f["familiares"] in procesar:
            f["familiares"].instance = persona
            f["familiares"].save()

    @classmethod
    def tarjeta(cls, persona, datos):
        r = datos["residencia"]
        filas = [
            {"etiqueta": "Residencia", "valor": f"{r.direccion}, {r.direccion.comuna}" if r else ""},
            {"etiqueta": "Comunidad", "enlaces": [(m.comunidad.nombre, m.comunidad.get_absolute_url()) for m in datos["comunidades"]]},
        ]
        ficha = datos["ficha_vecino"]
        if ficha is not None:
            jefatura = {True: "Sí", False: "No"}.get(ficha.jefatura_hogar, "")
            filas += [
                {"etiqueta": "Jefe o jefa de hogar", "valor": jefatura, "restringido": True},
                {"etiqueta": "Integrantes del hogar", "valor": ficha.integrantes_hogar or "", "restringido": True},
                {"etiqueta": "Familiares contados", "valor": " · ".join(str(i) for i in datos["integrantes"]) if datos["integrantes"] else "", "restringido": True},
            ]
        if datos["familiares"]:
            filas.append({"etiqueta": "Familiares registrados", "restringido": True,
                          "enlaces": [(f"{v.familiar} ({v.parentesco})", v.familiar.get_absolute_url()) for v in datos["familiares"]]})
        return filas


class SeccionInvitado(Seccion):
    codigo, titulo = "invitado", "Invitado o invitada"
    ayuda = "Quién es y por qué se le invita: autoridad, expositor, prensa… La invitación a cada actividad se registra en la actividad."
    permiso = "personas.add_fichainvitado"

    def armar(self, datos, persona, usuario):
        return {"ficha": FichaInvitadoForm(datos, prefix="inv", instance=_uno_a_uno(persona, "ficha_invitado"), persona=persona)}

    def guardar(self, persona):
        f = self.formularios["ficha"]
        if f in self.a_procesar():
            obj = f.save(commit=False)
            obj.persona = persona
            obj.save()

    @classmethod
    def tarjeta(cls, persona, datos):
        fi = datos["ficha_invitado"]
        if fi is None:
            return []
        return [
            {"etiqueta": "Tipo", "valor": str(fi.tipo or "")},
            {"etiqueta": "Organización y cargo", "valor": " · ".join(x for x in [str(fi.organizacion or ""), fi.cargo] if x)},
            {"etiqueta": "Invitado o invitada por", "valor": str(fi.invitado_por or "")},
            {"etiqueta": "Actividad", "valor": str(fi.actividad or "")},
            {"etiqueta": "Motivo", "valor": fi.motivo},
        ]


class SeccionVoluntario(Seccion):
    codigo, titulo = "voluntario", "Voluntario o voluntaria"
    ayuda = "Estado del voluntariado, desde cuándo y cuántas horas puede dar. Su disponibilidad por día y su experiencia siguen en sus pestañas."
    permiso = "personas.add_fichavoluntario"

    def armar(self, datos, persona, usuario):
        return {"ficha": FichaVoluntarioForm(datos, prefix="vol", instance=_uno_a_uno(persona, "ficha_voluntario"))}

    guardar = SeccionInvitado.guardar

    @classmethod
    def tarjeta(cls, persona, datos):
        fv = datos["ficha_voluntario"]
        if fv is None:
            return []
        return [
            {"etiqueta": "Estado", "valor": str(fv.estado or "")},
            {"etiqueta": "Fecha de ingreso", "valor": f"{fv.fecha_ingreso:%d-%m-%Y}" if fv.fecha_ingreso else ""},
            {"etiqueta": "Horas por semana", "valor": fv.horas_semanales or ""},
            {"etiqueta": "Motivación u observaciones", "valor": fv.motivacion},
        ]


SECCIONES = (SeccionEstudiante, SeccionVecino, SeccionInvitado, SeccionVoluntario)
POR_CODIGO = {s.codigo: s for s in SECCIONES}


class RegistroFichas:
    """Las secciones por tipo de un formulario de persona.

    - `datos`: lo enviado (o None al abrir el formulario); `persona`: al editar; `base`: el formulario de la persona
      (de él salen los perfiles marcados); `solo`: una sola ficha (el «Editar» de su tarjeta).
    - Se dibujan todas las secciones que el usuario puede llenar; las no marcadas van ocultas (`hidden`).
    - «Mostrar secciones» (sin JavaScript) o «Actualizar listas» vuelven a dibujar sin guardar ni marcar errores (`solo_mostrar`).
    - `is_valid()` y `guardar()` solo miran las secciones marcadas, y dentro de ellas solo lo que trae datos.
    """

    def __init__(self, datos=None, usuario=None, persona=None, base=None, solo=None):
        self.usuario, self.persona, self.base = usuario, persona, base
        self.solo_mostrar = datos is not None and any(
            datos.get(k) for k in datos if k == "_mostrar" or k.endswith("_actualizar_ubicacion") or k.endswith("_actualizar_estudios"))
        if self.solo_mostrar:  # la ubicación y los estudios vuelven a armar sus listas como con «Actualizar listas»
            datos = datos.copy()
            datos["vec-_actualizar_ubicacion"] = datos["est-_actualizar_estudios"] = "1"
        self.datos = datos
        self.elegidas = {solo} if solo else self._elegidas()
        clases = [c for c in SECCIONES if (solo is None or c.codigo == solo) and usuario is not None and usuario.has_perm(c.permiso)]
        self.secciones = [c(self) for c in clases]
        self.hay_errores = False
        if self.solo_mostrar:
            for s in self.secciones:
                for f in s.formularios.values():
                    _sin_errores(f)

    def _elegidas(self):
        if self.datos is not None:
            pks = self.datos.getlist("perfiles")
        elif self.base is not None and "perfiles" in self.base.fields:
            pks = self.base["perfiles"].value() or []
        else:
            pks = []
        pks = [p for p in (pk_seguro(v) for v in pks) if p]
        if not pks:
            return set()
        return set(PerfilPersona.objects.filter(pk__in=pks).exclude(ficha="").values_list("ficha", flat=True))

    def is_valid(self):
        """Valida lo que trae datos en las secciones marcadas; lo demás queda sin errores (no se guarda)."""
        if self.solo_mostrar:
            return False
        ok = True
        for s in self.secciones:
            procesar = s.a_procesar() if s.elegida else []
            for f in s.formularios.values():
                if f in procesar:
                    ok = f.is_valid() and ok
                else:
                    _sin_errores(f)
        self.hay_errores = not ok
        return ok

    def guardar(self, persona):
        """Guarda las secciones marcadas. Se llama dentro de la transacción que guarda a la persona."""
        for s in self.secciones:
            if s.elegida:
                s.guardar(persona)


def tarjetas(persona, usuario):
    """Una tarjeta por cada tipo que la persona tiene (por su perfil o porque ya tiene datos de ese tipo), con su resumen
    y «Editar». Usa un número fijo de consultas."""
    from apps.comunidades.models import ComunidadMiembro

    p = (Persona.objects.select_related("ficha_vecino", "ficha_invitado__tipo", "ficha_invitado__organizacion", "ficha_invitado__invitado_por",
                                        "ficha_invitado__actividad", "ficha_voluntario__estado").get(pk=persona.pk))
    marcadas = set(p.perfiles.exclude(ficha="").values_list("ficha", flat=True))
    datos = {
        "formaciones": list(PersonaFormacion.objects.filter(persona=p, vigente=True).select_related("organizacion", "carrera", "sede_institucion")),
        "ficha_vecino": _uno_a_uno(p, "ficha_vecino"), "ficha_invitado": _uno_a_uno(p, "ficha_invitado"), "ficha_voluntario": _uno_a_uno(p, "ficha_voluntario"),
        "residencia": None, "comunidades": [], "integrantes": [], "familiares": [],
    }
    con_datos = {"estudiante": bool(datos["formaciones"]), "vecino": datos["ficha_vecino"] is not None,
                 "invitado": datos["ficha_invitado"] is not None, "voluntario": datos["ficha_voluntario"] is not None}
    if "vecino" in marcadas or con_datos["vecino"]:
        datos["residencia"] = (p.direcciones.filter(tipo="residencia", vigente=True).select_related("direccion__comuna", "direccion__sector__sector_padre")
                               .order_by("-pk").first())
        datos["comunidades"] = list(ComunidadMiembro.objects.filter(persona=p, vigente=True).select_related("comunidad"))
        datos["familiares"] = list(p.familiares.select_related("familiar", "parentesco"))
        if datos["ficha_vecino"] is not None:
            datos["integrantes"] = list(datos["ficha_vecino"].integrantes.select_related("parentesco", "tramo"))
    res = []
    for clase in SECCIONES:
        if clase.codigo not in marcadas and not con_datos[clase.codigo]:
            continue
        puede = usuario.has_perm("personas.change_persona") and usuario.has_perm(clase.permiso)
        res.append({
            "codigo": clase.codigo, "titulo": clase.titulo, "filas": clase.tarjeta(p, datos),
            "url_editar": reverse("personas:ficha_tipo", args=[p.pk, clase.codigo]) if puede else "",
            "vacio": "Aún sin datos propios de este tipo.",
        })
    return res

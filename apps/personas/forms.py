"""Formularios de persona: ficha rápida (solo nombre) y completa por secciones, contactos, direcciones, formación
(institución → sede y carrera en cascada, con crear en el momento), cargos en organizaciones, experiencia, disponibilidad,
y los restringidos (emergencia, datos sensibles, consentimientos, apoderados, verificaciones)."""
import json

from django import forms
from django.db.models import Q
from django.urls import reverse

from apps.nucleo.formularios import BloqueDeSeccion, BootstrapMixin, SelectorField
from apps.nucleo.models import AreaTematica, Canal, EstadoRegistro, OrigenPersona, PerfilPersona, TipoContacto
from apps.nucleo.rut import CampoRut
from apps.nucleo.selector import pk_seguro
from apps.nucleo.utilidades import normalizar_telefono, telefono_normalizado_valido
from apps.organizaciones.models import Carrera, Organizacion
from apps.organizaciones.selector import ORGANIZACIONES
from apps.territorio.forms import DireccionForm
from apps.territorio.models import Comuna

from .selector import PERSONAS
from .models import (
    PersonaLugar,
    Apoderado, Consentimiento, Contacto, ContactoEmergencia, DisponibilidadPersona, Experiencia, PerfilSensible, Persona, PersonaDireccion,
    PersonaFormacion, PersonaOrganizacion, VerificacionPersona,
)


def selector_persona(**kw):
    return SelectorField(PERSONAS, **kw)


CAMPOS_PERFIL = ["nombre_social", "fecha_nacimiento", "nacionalidad", "perfiles", "nivel_educacional", "situacion_ocupacional",
                 "areas_interes", "habilidades", "idiomas", "canal_preferido"]

SECCIONES_PERSONA = [
    ("Identificación", "Solo el nombre es obligatorio; el resto se puede completar después.",
     ["nombres", "apellido_paterno", "apellido_materno", "nombre_social", "rut", "sin_rut", "tipo_documento", "numero_documento", "fecha_nacimiento", "edad",
      "sexo", "nacionalidad"]),
    ("Contacto", "Un dato basta para registrarla.", ["correo", "telefono", "canal_preferido"]),
    ("Perfil y ocupación", "Qué es esta persona para la Fundación y a qué se dedica. Sirve para filtrar el banco de personas.",
     ["perfiles", "nivel_educacional", "situacion_ocupacional", "profesion", "sitio_web"]),
    ("Intereses y habilidades", "Para invitarla a las actividades que le interesan y encontrar talleristas y voluntarios.",
     ["areas_interes", "habilidades", "idiomas"]),
    ("Registro", "", ["origen", "estado_registro", "observaciones"]),
]


def edad_aproximada():
    return forms.IntegerField(
        required=False, min_value=0, max_value=120, label="Edad (si no sabes la fecha)",
        help_text="Ej.: 67. Se guarda como fecha aproximada: el 1 de enero del año que corresponde.",
    )


class PersonaForm(BootstrapMixin, forms.ModelForm):
    """Ficha completa por secciones (F22). Solo el nombre es obligatorio: se puede completar después.
    Los perfiles con ficha propia (estudiante, vecino…) se pueden mostrar aparte como «Tipo de registro» (ver `separar_tipos`)."""

    rut = CampoRut(label="RUT")
    sin_rut = forms.BooleanField(required=False, label="No tiene RUT chileno (por ejemplo, una persona extranjera)",
                                 help_text="Al marcarlo se pide el tipo y el número de su documento.")
    edad = edad_aproximada()
    secciones = SECCIONES_PERSONA

    class Meta:
        model = Persona
        fields = ["nombres", "apellido_paterno", "apellido_materno", "rut", "tipo_documento", "numero_documento", *CAMPOS_PERFIL[:2], "sexo",
                  CAMPOS_PERFIL[2], "profesion", "sitio_web", *CAMPOS_PERFIL[3:], "origen", "estado_registro", "observaciones"]
        widgets = {
            "perfiles": forms.CheckboxSelectMultiple, "areas_interes": forms.CheckboxSelectMultiple,
            "fecha_nacimiento": forms.DateInput, "habilidades": forms.Textarea(attrs={"rows": 2}),
        }
        labels = {
            "tipo_documento": "Documento (si no tiene RUT)", "numero_documento": "N.º del documento", "perfiles": "¿Qué es para la Fundación?",
            "areas_interes": "Temas que le interesan", "idiomas": "Idiomas que habla", "origen": "¿Cómo llegó a la Fundación?",
            "estado_registro": "Estado de la ficha", "canal_preferido": "¿Cómo prefiere que la contacten?",
        }
        help_texts = {
            "nombres": "Ej.: María José.",
            "tipo_documento": "Para quien no tiene RUT, por ejemplo una persona extranjera. Ej.: Pasaporte.",
            "numero_documento": "Ej.: AB123456.",
            "nacionalidad": "Ej.: Venezolana.",
            "perfiles": "Marca uno o más. Ej.: Estudiante y Voluntaria.",
            "areas_interes": "Sirven para invitarla a actividades. Ej.: Medio ambiente.",
            "idiomas": "Ej.: Español y creole haitiano.",
            "profesion": "Ej.: Técnica en enfermería; gásfiter.",
            "sitio_web": "Ej.: https://www.linkedin.com/in/nombre",
            "nivel_educacional": "El más alto que alcanzó. Ej.: Media completa.",
            "situacion_ocupacional": "A qué se dedica hoy. Ej.: Trabaja y estudia.",
            "origen": "Ej.: Derivación (la envió la municipalidad).",
            "estado_registro": "Qué tan completa está la ficha. Ej.: Incompleto, si falta el apellido o un contacto.",
            "canal_preferido": "Ej.: WhatsApp.",
            "observaciones": "Lo que convenga saber y no tenga otro lugar. Ej.: prefiere que la llamen en la tarde.",
        }

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        if "origen" in self.fields:
            self.fields["origen"].queryset = OrigenPersona.objects.filter(activo=True)
        if "estado_registro" in self.fields:  # «Fusionada» la pone solo la fusión de fichas (se conserva si ya la tenía)
            self.fields["estado_registro"].queryset = (EstadoRegistro.objects.filter(activo=True).exclude(codigo="fusionada")
                                                       | EstadoRegistro.objects.filter(pk=self.instance.estado_registro_id or 0))
        if "perfiles" in self.fields:
            self.fields["perfiles"].queryset = PerfilPersona.objects.filter(activo=True)
        if "areas_interes" in self.fields:
            self.fields["areas_interes"].queryset = AreaTematica.objects.filter(activo=True)
        if "canal_preferido" in self.fields:
            self.fields["canal_preferido"].queryset = Canal.objects.filter(activo=True)
        if "nacionalidad" in self.fields:
            self.fields["nacionalidad"].widget.attrs.update(list="nacionalidades", placeholder="Ej.: chilena")
        if self.instance.pk and self.instance.rut_numero:
            self.initial["rut"] = self.instance.rut
        if "fecha_nacimiento" in self.fields and self.instance.fecha_nacimiento_aproximada:
            self.fields["fecha_nacimiento"].help_text = "Fecha aproximada: se calculó desde la edad. Si sabes la fecha exacta, escríbela."
        if "sexo" in self.fields:
            self.fields["sexo"].help_text = "Opcional. La identidad de género se registra aparte, en los datos sensibles 🔒."
        # Campos que cambian según lo escrito: el RUT o el documento extranjero; la edad solo si falta la fecha
        if "sin_rut" in self.fields:
            if self.instance.pk and self.instance.numero_documento and not self.instance.rut_numero:
                self.initial["sin_rut"] = True
            marca = self.add_prefix("sin_rut")
            if "rut" in self.fields:
                self.fields["rut"].widget.attrs["data-ocultar-si-marcado"] = marca
            for c in ("tipo_documento", "numero_documento"):
                if c in self.fields:
                    self.fields[c].widget.attrs["data-mostrar-si-marcado"] = marca
        if "edad" in self.fields and "fecha_nacimiento" in self.fields:
            self.fields["edad"].widget.attrs["data-mostrar-si-vacio"] = self.add_prefix("fecha_nacimiento")
            self.fields["fecha_nacimiento"].widget.attrs["data-edad"] = "1"
        self.tipos = []  # perfiles con ficha propia, cuando se muestran aparte (separar_tipos)

    def separar_tipos(self):
        """Los perfiles con ficha propia (estudiante, vecino, invitado, voluntario) se marcan arriba como «Tipo de registro»
        (botones que muestran su sección); la lista de perfiles queda con los demás. Lo enviado sigue siendo `perfiles`."""
        campo = self.fields.get("perfiles")
        if campo is None:
            return
        todos = list(campo.queryset)
        self.tipos = [p for p in todos if p.ficha]
        campo.widget.choices = [(p.pk, str(p)) for p in todos if not p.ficha]
        campo.label = "Otros perfiles"
        campo.help_text = "Los tipos con datos propios (como estudiante o voluntario) se marcan arriba, en «Tipo de registro»."

    def tipos_ui(self):
        """Botones de «Tipo de registro»: [(perfil, marcado)]."""
        if not self.tipos:
            return []
        marcados = {str(v) for v in (self["perfiles"].value() or [])}
        return [(p, str(p.pk) in marcados) for p in self.tipos]

    perfiles_en_lista = True  # la ficha rápida solo muestra los tipos, no la lista de otros perfiles

    def secciones_ui(self):
        res = super().secciones_ui()
        if res and self.tipos and not self.perfiles_en_lista:
            res = [s._replace(campos=[c for c in s.campos if getattr(c, "name", "") != "perfiles"]) for s in res]
            res = [s for s in res if s.campos]
        return res

    def clean_rut(self):
        valor = self.cleaned_data.get("rut")
        if valor:
            existe = Persona.objects.filter(rut_numero=valor[0]).exclude(pk=self.instance.pk).first()
            if existe:
                raise forms.ValidationError(f"Ya existe una persona con ese RUT: {existe.nombre_completo}.")
        return valor

    def clean(self):
        d = super().clean()
        tipo, numero = d.get("tipo_documento"), (d.get("numero_documento") or "").strip().upper()
        if numero and not tipo:
            self.add_error("tipo_documento", "Indica el tipo de documento.")
        if tipo and not numero:
            self.add_error("numero_documento", "Indica el número del documento.")
        if tipo and numero:
            d["numero_documento"] = numero
            otra = Persona.objects.filter(tipo_documento=tipo, numero_documento=numero).exclude(pk=self.instance.pk).first()
            if otra:
                self.add_error("numero_documento", f"Ya existe una persona con ese documento: {otra.nombre_completo}.")
        if d.get("edad") is not None and d.get("fecha_nacimiento") and "fecha_nacimiento" in self.changed_data:
            self.add_error("edad", "Escribe la fecha de nacimiento o la edad, no las dos.")
        return d

    def save(self, commit=True):
        obj = super().save(commit=False)
        rut = self.cleaned_data.get("rut")
        obj.rut_numero, obj.rut_dv = rut if rut else (None, None)
        if self.cleaned_data.get("edad") is not None:
            obj.fijar_edad_aproximada(self.cleaned_data["edad"])
        elif "fecha_nacimiento" in self.changed_data:
            obj.fecha_nacimiento_aproximada = False  # se escribió la fecha: ya no es aproximada
        if commit:
            obj.save()
        return obj


class PersonaNuevaForm(PersonaForm):
    """Ficha rápida: nombre y un dato de contacto; el resto después."""

    correo = forms.EmailField(required=False, label="Correo electrónico", help_text="Ej.: nombre@ejemplo.cl")
    telefono = forms.CharField(label="Teléfono", required=False, max_length=40, help_text="Ej.: +56 9 1234 5678.")

    class Meta(PersonaForm.Meta):
        fields = ["nombres", "apellido_paterno", "apellido_materno", "rut", "tipo_documento", "numero_documento", *CAMPOS_PERFIL[:2], "sexo",
                  CAMPOS_PERFIL[2], "correo", "telefono", "profesion", *CAMPOS_PERFIL[3:], "origen", "observaciones"]

    def clean_telefono(self):
        t = self.cleaned_data.get("telefono", "").strip()
        if t and not telefono_normalizado_valido(normalizar_telefono(t)):
            raise forms.ValidationError("No se pudo interpretar el teléfono. Usa el formato +56 9 1234 5678.")
        return t


# F25 E1: la ficha rápida es una sola. La usan la ventana «+ Crear persona» de los buscadores, «Crear persona nueva» al
# agregar participantes y el modo rápido de Personas → Nueva: mismos campos, mismas etiquetas y la misma validación.
CAMPOS_FICHA_RAPIDA = ["nombres", "apellido_paterno", "apellido_materno", "rut", "sin_rut", "tipo_documento", "numero_documento",
                       "nacionalidad", "sexo", "fecha_nacimiento", "telefono", "correo", "comuna"]
SECCIONES_FICHA_RAPIDA = [
    ("Persona", "Solo el nombre es obligatorio; el resto se completa si se sabe.", CAMPOS_FICHA_RAPIDA[:10]),
    ("Contacto y comuna", "", CAMPOS_FICHA_RAPIDA[10:]),
]


class FichaRapidaForm(PersonaNuevaForm):
    """Ficha rápida única (F25 E1). Valida igual que la ficha completa: RUT o documento únicos, con aviso."""

    comuna = forms.ModelChoiceField(Comuna.objects.order_by("nombre"), required=False, label="Comuna donde vive",
                                    help_text="Así aparece en el territorio. Ej.: Hualpén.")
    edad = None  # en la ficha rápida basta la fecha de nacimiento, si se sabe
    secciones = SECCIONES_FICHA_RAPIDA
    field_order = CAMPOS_FICHA_RAPIDA

    class Meta(PersonaNuevaForm.Meta):
        fields = ["nombres", "apellido_paterno", "apellido_materno", "rut", "tipo_documento", "numero_documento", "nacionalidad", "sexo",
                  "fecha_nacimiento"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["telefono"].widget.attrs.setdefault("placeholder", "Ej.: +56 9 1234 5678")


class PersonaRapidaForm(FichaRapidaForm):
    """Modo rápido de Personas → Nueva (IG-01): la ficha rápida y el «Tipo de registro»."""

    perfiles_en_lista = False

    class Meta(FichaRapidaForm.Meta):
        fields = [*FichaRapidaForm.Meta.fields, "perfiles"]  # perfiles: solo los «Tipo de registro»


class PersonaCrearRapidaForm(FichaRapidaForm):
    """Ventana «+ Crear persona» de los buscadores: la ficha rápida, sin salir del formulario de origen."""


def inicial_desde_texto(texto):
    """Lo escrito en el buscador prellena la ventana: un correo, un teléfono o un nombre («Nombre Apellido» o «Apellido, Nombre»)."""
    from apps.nucleo.utilidades import separar_nombre

    texto = (texto or "").strip()
    if not texto:
        return {}
    if "@" in texto:
        return {"correo": texto}
    if sum(c.isdigit() for c in texto) >= 8 and not any(c.isalpha() for c in texto):
        return {"telefono": texto}
    nombres, paterno, materno = separar_nombre(texto)
    return {"nombres": nombres, "apellido_paterno": paterno, "apellido_materno": materno}


class ContactoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Contacto
        fields = ["tipo", "valor", "proposito", "principal", "vigente"]
        labels = {"tipo": "Tipo de contacto", "valor": "Número, correo o enlace", "proposito": "¿Para qué se usa?",
                  "principal": "Usar como contacto principal"}
        help_texts = {"valor": "Ej.: +56 9 1234 5678 o nombre@ejemplo.cl.", "proposito": "Opcional. Ej.: cartas y oficios; donaciones.",
                      "principal": "Es el que se muestra primero en la ficha y en las listas."}

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.fields["tipo"].queryset = TipoContacto.objects.filter(activo=True)

    def clean(self):
        d = super().clean()
        tipo, valor = d.get("tipo"), d.get("valor", "")
        if tipo and valor:
            norm = Contacto.normalizar(tipo, valor)
            if tipo.codigo in ("telefono_movil", "telefono_fijo") and not telefono_normalizado_valido(norm):
                self.add_error("valor", "Teléfono no válido. Usa el formato +56 9 1234 5678.")
            if tipo.codigo == "correo":
                try:
                    forms.EmailField().clean(valor)
                except forms.ValidationError:
                    self.add_error("valor", "Correo no válido.")
        return d


class PersonaDireccionForm(DireccionForm):
    tipo = forms.ChoiceField(choices=PersonaDireccion.TIPOS, label="Tipo de dirección",
                             help_text="Residencia: donde vive hoy. Procedencia: de donde viene (p. ej. su ciudad de origen).")

    def __iter__(self):  # el bloque de dirección no repite «tipo»: se muestra aparte
        return (c for c in super().__iter__() if c.name != "tipo")

    def save_para(self, persona):
        direccion = super().save()
        return PersonaDireccion.objects.create(persona=persona, direccion=direccion, tipo=self.cleaned_data["tipo"])


def _mismo_nombre(qs, nombre):
    """El registro de `qs` que se llama igual, sin contar tildes, mayúsculas ni espacios de más (o None)."""
    return qs.filter(nombre__unaccent__iexact=" ".join(nombre.split())).first()


class FormacionForm(BootstrapMixin, forms.ModelForm):
    """Estudios de una persona. Institución → sede o casa matriz y carrera, en cascada: al elegir la institución se ofrecen
    sus sedes y carreras (personas/fichas/_estudios.html; con JavaScript la lista se renueva sola, sin JavaScript con
    «Actualizar listas»). Si falta la sede o la carrera, se escribe y se crea al guardar, en la misma transacción.
    Crear exige `usuario` con permiso (lugares.add_lugar, organizaciones.add_carrera); sin él, solo se elige."""

    organizacion = SelectorField(ORGANIZACIONES, filtros={"tipo": "institucion_educativa"}, label="Institución educativa",
                                 help_text="Ej.: un instituto profesional o una universidad. Si no está, créala desde aquí.")
    docente = selector_persona(required=False, label="Docente o tutor a cargo")
    nueva_sede = forms.CharField(required=False, max_length=200, label="Nombre de la sede o casa matriz",
                                 widget=forms.TextInput(attrs={"placeholder": "Ej.: Sede San Andrés", "autocomplete": "off"}))
    nueva_sede_tipo = forms.ChoiceField(required=False, label="Es", choices=[("sede", "Sede"), ("casa_matriz", "Casa matriz")], initial="sede")
    nueva_sede_comuna = forms.ModelChoiceField(queryset=None, required=False, label="Comuna de la sede")
    nueva_carrera = forms.CharField(required=False, max_length=200, label="Nombre de la carrera",
                                    widget=forms.TextInput(attrs={"placeholder": "Ej.: Técnico en Trabajo Social", "autocomplete": "off"}))
    CAMPOS_ESTUDIOS = ("organizacion", "sede_institucion", "carrera", "nueva_sede", "nueva_sede_tipo", "nueva_sede_comuna", "nueva_carrera")
    secciones = [
        ("Estudios", "", ["estudios", "estado", "sede", "jornada", "nivel_actual", "anio_inicio", "anio_termino"]),
        ("Vínculo con la Fundación", "Para coordinar con la institución y certificar las horas.", ["asignatura", "docente", "horas_comprometidas", "vigente"]),
    ]

    class Meta:
        model = PersonaFormacion
        fields = ["organizacion", "sede_institucion", "carrera", "estado", "sede", "jornada", "nivel_actual", "anio_inicio", "anio_termino", "asignatura", "docente",
                  "horas_comprometidas", "vigente"]
        labels = {"estado": "Situación", "anio_inicio": "Año de ingreso", "anio_termino": "Año de egreso o término",
                  "horas_comprometidas": "Horas comprometidas con la Fundación"}
        help_texts = {"estado": "Estudiante, egresado o titulado.", "jornada": "Ej.: Vespertina.", "nivel_actual": "Ej.: 3.er semestre; 2.º año.",
                      "anio_inicio": "Ej.: 2024.", "anio_termino": "Si ya terminó o se sabe cuándo termina. Ej.: 2027.",
                      "asignatura": "La asignatura o práctica por la que viene, si corresponde. Ej.: Práctica profesional I.",
                      "horas_comprometidas": "Las que pide la institución para certificar. Ej.: 120."}

    def __init__(self, *args, usuario=None, **kw):
        super().__init__(*args, **kw)
        from apps.territorio.models import Comuna

        self.usuario = usuario
        self.puede_crear_sede = bool(usuario and usuario.has_perm("lugares.add_lugar"))
        self.puede_crear_carrera = bool(usuario and usuario.has_perm("organizaciones.add_carrera"))
        if not self.puede_crear_sede:
            for n in ("nueva_sede", "nueva_sede_tipo", "nueva_sede_comuna"):
                self.fields.pop(n)
        if not self.puede_crear_carrera:
            self.fields.pop("nueva_carrera")
        org = self.institucion_elegida()
        sede, carrera = self.fields["sede_institucion"], self.fields["carrera"]
        sede.label, sede.required, carrera.required = "Sede o casa matriz", False, False
        sede.label_from_instance = carrera.label_from_instance = lambda o: o.nombre
        if org:
            sede.queryset = PersonaFormacion.sedes_de(org).filter(Q(activo=True) | Q(pk=self.instance.sede_institucion_id or 0)).order_by("nombre")
            carrera.queryset = Carrera.objects.filter(organizacion=org).filter(Q(activo=True) | Q(pk=self.instance.carrera_id or 0)).order_by("nombre")
            sede.help_text = "" if sede.queryset.exists() else f"{org.nombre} aún no tiene sedes registradas."
            carrera.help_text = "" if carrera.queryset.exists() else f"{org.nombre} aún no tiene carreras registradas."
        else:
            sede.queryset, carrera.queryset = sede.queryset.none(), Carrera.objects.none()
            for campo in (sede, carrera):
                campo.empty_label = "Primero elige la institución"
                campo.widget.attrs["disabled"] = True
        if "nueva_sede_comuna" in self.fields:
            from itertools import groupby

            campo = self.fields["nueva_sede_comuna"]
            campo.queryset = Comuna.objects.all()
            todas = Comuna.objects.select_related("provincia__region").order_by("provincia__region__codigo", "nombre") if org else []
            campo.choices = [("", "---------")] + [(r.nombre, [(c.pk, c.nombre) for c in lista]) for r, lista in groupby(todas, key=lambda c: c.provincia.region)]
            if org and not self.is_bound and org.direccion_id:
                self.initial.setdefault("nueva_sede_comuna", org.direccion.comuna_id)  # la comuna de la institución, como punto de partida
        if "sede" in self.fields:
            self.fields["sede"].label = "Sede escrita (texto anterior)"
            self.fields["sede"].help_text = "Se escribía antes de poder elegir la sede de la lista. Elige la sede arriba y luego borra este texto."
        self.organizacion_elegida = org
        # al elegir otra institución, se vuelven a dibujar su sede y su carrera (personas/fichas/_estudios.html)
        self.fields["organizacion"].widget.attrs.update({
            "hx-get": reverse("personas:estudios_dependientes"), "hx-trigger": "change", "hx-target": f"#{self.id_dependientes}",
            "hx-swap": "outerHTML", "hx-include": "closest .fche-estudios", "hx-vals": json.dumps({"_prefijo": self.prefix or ""}),
        })

    @property
    def id_dependientes(self):
        return f"estudios-{self.prefix or 'principal'}-dependientes"

    @property
    def nombre_actualizar(self):
        return self.add_prefix("_actualizar_estudios")

    @property
    def actualizando(self):
        """Sin JavaScript, «Actualizar listas» vuelve a dibujar el formulario con las sedes y carreras de la institución, sin guardar."""
        return self.is_bound and bool(self.data.get(self.nombre_actualizar))

    def full_clean(self):
        if self.actualizando:
            from apps.territorio.ubicacion import sin_errores

            sin_errores(self)
            return
        super().full_clean()

    def is_valid(self):
        return super().is_valid() and not self.actualizando

    def institucion_elegida(self):
        """La institución elegida (al volver a dibujar, la del formulario enviado), sin errores si el valor no sirve."""
        pk = pk_seguro(self.data.get(self.add_prefix("organizacion"))) if self.is_bound else pk_seguro(self.initial.get("organizacion") or self.instance.organizacion_id)
        if not pk:
            return None
        return Organizacion.objects.filter(pk=pk, tipo__codigo="institucion_educativa").select_related("direccion").first()

    @property
    def bloques_de_seccion(self):
        """En `secciones`, «estudios» dibuja juntos la institución, la sede y la carrera (con «+ Crear»)."""
        return {"estudios": BloqueDeSeccion(self, "personas/fichas/_estudios.html", self.CAMPOS_ESTUDIOS)}

    def clean(self):
        d = super().clean()
        org = d.get("organizacion")
        nueva_sede, nueva_carrera = (d.get("nueva_sede") or "").strip(), (d.get("nueva_carrera") or "").strip()
        if nueva_sede:
            if d.get("sede_institucion"):
                self.add_error("nueva_sede", "Elige una sede de la lista o escribe una nueva, no las dos.")
            elif not org:
                self.add_error("nueva_sede", "Primero elige la institución de la sede.")
            elif not d.get("nueva_sede_comuna"):
                self.add_error("nueva_sede_comuna", "Indica en qué comuna está la sede.")
            else:
                igual = _mismo_nombre(PersonaFormacion.sedes_de(org), nueva_sede)
                if igual:
                    self.add_error("nueva_sede", f"{org.nombre} ya tiene la sede «{igual.nombre}»: elígela en la lista.")
        if nueva_carrera:
            if d.get("carrera"):
                self.add_error("nueva_carrera", "Elige una carrera de la lista o escribe una nueva, no las dos.")
            elif not org:
                self.add_error("nueva_carrera", "Primero elige la institución de la carrera.")
            else:
                igual = _mismo_nombre(Carrera.objects.filter(organizacion=org), nueva_carrera)
                if igual:
                    self.add_error("nueva_carrera", f"{org.nombre} ya tiene la carrera «{igual.nombre}»: elígela en la lista.")
        # PersonaFormacion.clean() valida carrera y sede ↔ institución; ModelForm la llama con la instancia ya armada
        return d

    def crear_lo_escrito(self, obj):
        """Crea la sede y la carrera escritas (si las hay) y las deja elegidas. Se llama dentro de la transacción de guardar."""
        from apps.lugares.models import Lugar
        from apps.nucleo.models import TipoLugar
        from apps.territorio.models import Direccion

        d = self.cleaned_data
        org = d.get("organizacion")
        nombre = " ".join((d.get("nueva_sede") or "").split())
        if nombre and org and self.puede_crear_sede:
            tipo = TipoLugar.objects.get(codigo=d.get("nueva_sede_tipo") or "sede")
            obj.sede_institucion = Lugar.objects.create(nombre=nombre, tipo=tipo, direccion=Direccion.objects.create(comuna=d["nueva_sede_comuna"]),
                                                        organizacion_propietaria=org, creado_por=self.usuario)
        nombre = " ".join((d.get("nueva_carrera") or "").split())
        if nombre and org and self.puede_crear_carrera:
            obj.carrera = Carrera.objects.create(organizacion=org, nombre=nombre)

    def save(self, commit=True):
        obj = super().save(commit=False)
        if commit:
            self.crear_lo_escrito(obj)
            obj.save()
            self._save_m2m()
        return obj


class EstudianteForm(FormacionForm):
    """Sección «Estudiante» al registrar a una persona: lo principal de sus estudios (el resto, en la pestaña Formación)."""

    docente = None
    secciones = ()

    class Meta(FormacionForm.Meta):
        fields = ["organizacion", "sede_institucion", "carrera", "estado", "jornada", "nivel_actual", "anio_inicio"]


ETIQUETAS_VINCULO = {"organizacion": "Organización", "cargo": "Cargo", "fecha_inicio": "Desde", "fecha_termino": "Hasta (si ya dejó el cargo)"}
AYUDAS_VINCULO = {
    "cargo": "Ej.: Presidenta; Encargado de vinculación con el medio.",
    "tipo_cargo": "Directorio: presidencia, secretaría o tesorería. Funcional: quien trabaja o coordina. Autoridad: alcalde o director de liceo.",
    "fecha_termino": "Los cargos no se borran: al dejarlo, se indica hasta cuándo y queda en la historia.",
}


class VinculoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = PersonaOrganizacion
        fields = ["organizacion", "cargo", "tipo_cargo", "fecha_inicio", "fecha_termino"]
        labels = ETIQUETAS_VINCULO
        help_texts = AYUDAS_VINCULO

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.fields["organizacion"].queryset = Organizacion.objects.filter(activo=True)


class VinculoDesdeOrganizacionForm(BootstrapMixin, forms.ModelForm):
    """Agregar persona con cargo desde la ficha de la organización. Los cargos son históricos: se cierran con «hasta»."""

    persona = forms.ModelChoiceField(Persona.objects.none())

    class Meta:
        model = PersonaOrganizacion
        fields = ["persona", "cargo", "tipo_cargo", "fecha_inicio", "fecha_termino"]
        labels = ETIQUETAS_VINCULO
        help_texts = AYUDAS_VINCULO

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.nucleo.formularios import fijar_valores_selectores

        self.fields["persona"] = SelectorField(PERSONAS, label="Persona")
        self.fields["persona"].widget.attrs["class"] = "form-select"
        fijar_valores_selectores(self)


class ExperienciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Experiencia
        fields = ["descripcion", "lugar", "desde", "hasta", "vigente"]
        labels = {"descripcion": "¿Qué hizo?"}
        help_texts = {"descripcion": "Ej.: Monitora de taller de lectura.", "lugar": "Ej.: Biblioteca municipal de Hualpén."}


class DisponibilidadForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DisponibilidadPersona
        fields = ["dia", "hora_inicio", "hora_fin", "comentario", "vigente"]
        help_texts = {"comentario": "Ej.: solo la primera semana del mes."}


class EmergenciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ContactoEmergencia
        fields = ["nombre", "parentesco", "telefono", "vigente"]
        labels = {"nombre": "Nombre de la persona a quien avisar"}
        help_texts = {"parentesco": "Ej.: Madre.", "telefono": "Ej.: +56 9 1234 5678."}


class VerificacionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = VerificacionPersona
        fields = ["tipo", "fecha", "vigente_hasta", "observaciones", "vigente"]
        labels = {"tipo": "¿Qué se verificó?", "fecha": "Fecha de la verificación"}
        help_texts = {"tipo": "Ej.: Certificado de antecedentes.", "vigente_hasta": "Si el documento caduca. Ej.: 31-12-2026."}


class PerfilSensibleForm(BootstrapMixin, forms.ModelForm):
    """Datos sensibles. Exigen un consentimiento vigente de tipo «datos sensibles»; si no hay, se registra aquí mismo."""

    consentimiento = forms.BooleanField(required=False, label="La persona (o su apoderado) dio su consentimiento explícito para registrar estos datos")
    consentimiento_fecha = forms.DateField(required=False, label="Fecha del consentimiento", widget=forms.DateInput)
    consentimiento_medio = forms.ChoiceField(required=False, choices=Consentimiento.MEDIOS, label="Medio")
    secciones = [
        ("Género y origen", "Solo para estadísticas desagregadas. Siempre se puede responder «Prefiere no responder».", ["genero", "pueblo_originario"]),
        ("Salud y accesibilidad", "Para preparar el lugar y la actividad, y actuar en una emergencia.",
         ["discapacidad", "necesidades_apoyo", "condiciones_salud", "alergias", "prevision_salud"]),
        ("Hogar", "Para focalizar beneficios e informar a fondos. La jefatura y los integrantes del hogar van en la ficha de vecino o vecina "
                  "(pestaña Resumen).", ["tramo_rsh"]),
        ("Consentimiento", "", ["consentimiento", "consentimiento_fecha", "consentimiento_medio"]),
    ]

    class Meta:
        model = PerfilSensible
        # jefatura_hogar e integrantes_hogar pasaron a la ficha de vecino (FichaVecino); sus columnas se conservan sin uso
        fields = ["genero", "pueblo_originario", "discapacidad", "necesidades_apoyo", "condiciones_salud", "alergias", "prevision_salud", "tramo_rsh"]
        widgets = {"discapacidad": forms.Select(choices=[("", "Sin información"), (True, "Sí"), (False, "No")])}

    def __init__(self, *a, persona=None, **kw):
        super().__init__(*a, **kw)
        self.persona = persona
        self.consentimiento_previo = persona.consentimiento_vigente("sensibles") if persona else None
        if self.consentimiento_previo:
            for c in ("consentimiento", "consentimiento_fecha", "consentimiento_medio"):
                del self.fields[c]

    def clean(self):
        d = super().clean()
        hay_datos = any(d.get(c) not in (None, "") for c in self._meta.fields)
        if hay_datos and not self.consentimiento_previo and not d.get("consentimiento"):
            raise forms.ValidationError("Sin consentimiento explícito no se pueden registrar datos sensibles (Ley 21.719). Márcalo e indica la fecha y el medio.")
        if d.get("consentimiento") and not d.get("consentimiento_fecha"):
            self.add_error("consentimiento_fecha", "Indica la fecha del consentimiento.")
        return d


class ConsentimientoForm(BootstrapMixin, forms.ModelForm):
    otorgado_por = selector_persona(required=False, label="Otorgado por (apoderado)",
                                    help_text="Solo si lo dio el apoderado o apoderada, por ejemplo en el caso de un menor de edad.")

    class Meta:
        model = Consentimiento
        fields = ["tipo", "otorgado", "fecha", "medio", "otorgado_por", "documento", "revocado_en", "observaciones"]
        labels = {"tipo": "¿Para qué es el consentimiento?", "medio": "¿Cómo lo dio?", "revocado_en": "Revocado el"}
        help_texts = {"medio": "Ej.: Papel firmado.", "revocado_en": "Solo si la persona lo retiró. No se borra: queda registrado."}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        from apps.documentos.models import Documento

        persona = self.instance.persona if self.instance.persona_id else None
        docs = Documento.objects.filter(activo=True, persona=persona) if persona else Documento.objects.none()
        if self.instance.documento_id:
            docs = docs | Documento.objects.filter(pk=self.instance.documento_id)
        self.fields["documento"].queryset = docs
        self.fields["documento"].help_text = "Documentos ya subidos a la ficha de esta persona (pestaña Documentos)."


class ApoderadoForm(BootstrapMixin, forms.ModelForm):
    apoderado = selector_persona(label="Apoderado o apoderada")

    class Meta:
        model = Apoderado
        fields = ["apoderado", "parentesco", "tutor_legal", "vigente"]
        help_texts = {"parentesco": "Ej.: Madre.", "tutor_legal": "Márcalo si tiene la tutela legal (por ejemplo, por resolución del tribunal)."}

    def clean_apoderado(self):
        a = self.cleaned_data["apoderado"]
        if self.instance.persona_id and a.pk == self.instance.persona_id:
            raise forms.ValidationError("Una persona no puede ser su propio apoderado.")
        if Apoderado.objects.filter(persona_id=self.instance.persona_id, apoderado=a).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Esa persona ya está registrada como apoderado.")
        return a

    def validate_unique(self):
        pass


class PersonaLugarForm(BootstrapMixin, forms.ModelForm):
    """Vincula a la persona con un lugar ya registrado (un colegio, una sede, un centro comunitario)."""

    class Meta:
        model = PersonaLugar
        fields = ["lugar", "relacion", "desde", "hasta", "observaciones"]
        widgets = {"desde": forms.DateInput, "hasta": forms.DateInput}
        labels = {"lugar": "Lugar", "relacion": "¿Qué hace ahí?"}
        help_texts = {
            "lugar": "Un lugar ya registrado. Si no está, regístralo primero en Lugares. Ej.: Colegio Santa María, Hualpén.",
            "hasta": "Solo si ya no tiene ese vínculo: el registro se conserva.",
            "observaciones": "Ej.: apoderado del curso 3.º B.",
        }

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        from apps.lugares.campos import LugarChoiceField

        self.fields["lugar"] = LugarChoiceField(label="Lugar", help_text=self.fields["lugar"].help_text)

"""Tablas de personas: Persona (solo el nombre es obligatorio; RUT opcional y único si existe) y lo que se le vincula:
contactos, direcciones, formación, cargos históricos, experiencia y disponibilidad. Aparte, los datos restringidos
(contacto de emergencia, datos sensibles, consentimientos, apoderados, verificaciones), que exigen permiso propio."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Exists, OuterRef, Q
from django.urls import reverse
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.nucleo.models import AreaTematica, Canal, EstadoRegistro, OrigenPersona, PerfilPersona, TipoContacto
from apps.nucleo.utilidades import formatear_rut, normalizar_telefono


class PersonaQuerySet(models.QuerySet):
    def buscar(self, texto):
        """Por nombre (sin distinguir tildes ni mayúsculas), RUT, documento o teléfono en cualquier formato (PE-E8, BU-E1, BU-E2, BU-E3)."""
        texto = (texto or "").strip()
        if not texto:
            return self
        digitos_total = "".join(ch for ch in texto if ch.isdigit())
        if len(digitos_total) >= 8 and not any(ch.isalpha() and ch not in "kK" for ch in texto):
            # parece un teléfono o un RUT completo: se compara normalizado
            tel = normalizar_telefono(texto)
            cola = digitos_total[-8:]
            por_numero = Q(contactos__valor_normalizado__endswith=cola) | Q(rut_numero__icontains=digitos_total[:-1] or digitos_total) | Q(numero_documento__icontains=texto.replace(" ", ""))
            if tel.startswith("+"):
                por_numero |= Q(contactos__valor_normalizado=tel)
            return self.filter(por_numero).distinct()
        cond = Q()
        for palabra in texto.split():
            sub = (
                Q(nombres__unaccent__icontains=palabra) | Q(apellido_paterno__unaccent__icontains=palabra) | Q(apellido_materno__unaccent__icontains=palabra)
                | Q(numero_documento__icontains=palabra)
            )
            digitos = "".join(ch for ch in palabra if ch.isdigit())
            if len(digitos) >= 4:
                sub |= Q(rut_numero__icontains=digitos)
            cond &= sub
        return self.filter(cond)

    def cola_incompletos(self):
        """Personas con registro incompleto; primero las de actividades próximas (docs/CONTEXTO.md §11.2)."""
        from django.apps import apps

        hoy = timezone.localdate()
        Participacion = apps.get_model("actividades", "Participacion")
        proxima = Participacion.objects.filter(
            persona=OuterRef("pk"), actividad__agendas__vigente=True, actividad__agendas__fecha__gte=hoy
        )
        return (
            self.filter(activo=True, estado_registro__codigo="incompleto")
            .annotate(prioridad=Exists(proxima))
            .order_by("-prioridad", "-creado_en")
        )


class Persona(models.Model):
    nombres = models.CharField(max_length=150)
    apellido_paterno = models.CharField(max_length=100, blank=True)
    apellido_materno = models.CharField(max_length=100, blank=True)
    rut_numero = models.PositiveIntegerField("RUT (número)", null=True, blank=True)
    rut_dv = models.CharField("RUT (dígito)", max_length=1, null=True, blank=True)
    TIPOS_DOCUMENTO = [("pasaporte", "Pasaporte"), ("extranjero", "Documento de identidad extranjero"), ("otro", "Otro")]
    tipo_documento = models.CharField("otro documento (tipo)", max_length=12, choices=TIPOS_DOCUMENTO, blank=True,
                                      help_text="Para quien no tiene RUT, por ejemplo personas extranjeras (PE-E4).")
    numero_documento = models.CharField("otro documento (número)", max_length=40, blank=True)
    origen = models.ForeignKey(OrigenPersona, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    estado_registro = models.ForeignKey(EstadoRegistro, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="estado del registro")
    profesion = models.CharField("profesión u oficio", max_length=120, blank=True)
    sitio_web = models.URLField("sitio web / LinkedIn", blank=True)
    # F22: identificación y perfil (todo opcional; crear nunca se bloquea)
    nombre_social = models.CharField("nombre social", max_length=100, blank=True, help_text="Cómo prefiere que la llamen, si es distinto de su nombre legal.")
    fecha_nacimiento = models.DateField("fecha de nacimiento", null=True, blank=True)
    nacionalidad = models.CharField(max_length=60, blank=True)
    NIVELES_EDUCACIONALES = [
        ("sin_estudios", "Sin estudios formales"), ("basica_incompleta", "Básica incompleta"), ("basica_completa", "Básica completa"),
        ("media_incompleta", "Media incompleta"), ("media_completa", "Media completa"), ("tecnica_incompleta", "Técnica superior incompleta"),
        ("tecnica_completa", "Técnica superior completa"), ("universitaria_incompleta", "Universitaria incompleta"),
        ("universitaria_completa", "Universitaria completa"), ("postgrado", "Postgrado"),
    ]
    nivel_educacional = models.CharField("nivel educacional", max_length=24, choices=NIVELES_EDUCACIONALES, blank=True)
    SITUACIONES = [
        ("estudia", "Estudia"), ("trabaja", "Trabaja"), ("trabaja_estudia", "Trabaja y estudia"), ("busca_trabajo", "Busca trabajo"),
        ("cuidados", "Labores de cuidado o del hogar"), ("jubilado", "Jubilado/a o pensionado/a"), ("otra", "Otra"),
    ]
    situacion_ocupacional = models.CharField("situación ocupacional", max_length=16, choices=SITUACIONES, blank=True)
    perfiles = models.ManyToManyField(PerfilPersona, blank=True, related_name="+", help_text="Qué es esta persona para la Fundación. Puede tener varios.")
    areas_interes = models.ManyToManyField(AreaTematica, blank=True, related_name="+", verbose_name="áreas de interés")
    habilidades = models.TextField("habilidades y conocimientos", blank=True, help_text="Lo que sabe hacer y podría enseñar o aportar.")
    idiomas = models.CharField(max_length=150, blank=True)
    canal_preferido = models.ForeignKey(Canal, null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="canal de contacto preferido")
    observaciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()
    objects = PersonaQuerySet.as_manager()

    class Meta:
        ordering = ["apellido_paterno", "apellido_materno", "nombres"]
        verbose_name = "persona"
        verbose_name_plural = "personas"
        permissions = [
            ("exportar_persona", "Puede exportar personas"),
            ("ver_sensibles", "Puede ver datos sensibles de personas"),
            ("fusionar_persona", "Puede fusionar fichas duplicadas de personas"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["rut_numero"], condition=Q(rut_numero__isnull=False), name="persona_rut_unico"),
            models.CheckConstraint(condition=Q(rut_numero__isnull=True) | Q(rut_dv__isnull=False), name="persona_rut_con_dv"),
            models.UniqueConstraint(fields=["tipo_documento", "numero_documento"], condition=~Q(numero_documento=""), name="persona_documento_unico"),
        ]

    def __str__(self):
        return self.nombre_completo

    @property
    def nombre_completo(self):
        return " ".join(p for p in [self.nombres, self.apellido_paterno, self.apellido_materno] if p)

    @property
    def rut(self):
        return formatear_rut(self.rut_numero, self.rut_dv)

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.localdate()
        n = self.fecha_nacimiento
        return hoy.year - n.year - ((hoy.month, hoy.day) < (n.month, n.day))

    @property
    def es_menor(self):
        return self.edad is not None and self.edad < 18

    def consentimiento_vigente(self, tipo):
        """El último consentimiento de ese tipo, si está otorgado y no revocado."""
        c = self.consentimientos.filter(tipo=tipo).order_by("-fecha", "-pk").first()
        return c if c and c.otorgado and not c.revocado_en else None

    def avisos_consentimiento(self):
        """Lo que falta registrar para tratar los datos de esta persona (Ley 21.719)."""
        avisos = []
        if self.es_menor:
            if not self.apoderados.filter(vigente=True).exists():
                avisos.append("Es menor de edad y no tiene apoderado registrado.")
            if not self.consentimiento_vigente("apoderado"):
                avisos.append("Es menor de edad y falta la autorización del apoderado.")
        if not self.consentimiento_vigente("datos"):
            avisos.append("Falta registrar el consentimiento para el tratamiento de sus datos.")
        return avisos

    def get_absolute_url(self):
        return reverse("personas:ficha", args=[self.pk])

    def clean(self):
        if self.fecha_nacimiento:
            hoy = timezone.localdate()
            if self.fecha_nacimiento > hoy:
                raise ValidationError({"fecha_nacimiento": "La fecha de nacimiento no puede ser futura."})
            if hoy.year - self.fecha_nacimiento.year > 120:
                raise ValidationError({"fecha_nacimiento": "Revisa el año: la edad supera los 120 años."})

    def save(self, *args, **kwargs):
        if self.rut_dv:
            self.rut_dv = self.rut_dv.upper()
        super().save(*args, **kwargs)


class Contacto(models.Model):
    """Pertenece a una persona, a una organización o a un cargo (exactamente uno)."""

    tipo = models.ForeignKey(TipoContacto, on_delete=models.PROTECT, related_name="+")
    valor = models.CharField(max_length=200)
    valor_normalizado = models.CharField(max_length=200, blank=True, db_index=True)
    principal = models.BooleanField(default=False)
    vigente = models.BooleanField(default=True)
    proposito = models.CharField("propósito", max_length=60, blank=True, help_text="Ej.: institucional, cartas, donaciones.")
    persona = models.ForeignKey(Persona, null=True, blank=True, on_delete=models.PROTECT, related_name="contactos")
    organizacion = models.ForeignKey("organizaciones.Organizacion", null=True, blank=True, on_delete=models.PROTECT, related_name="contactos")
    cargo = models.ForeignKey("PersonaOrganizacion", null=True, blank=True, on_delete=models.PROTECT, related_name="contactos")

    class Meta:
        ordering = ["-principal", "-vigente", "tipo__orden", "id"]
        verbose_name = "contacto"
        verbose_name_plural = "contactos"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(persona__isnull=False, organizacion__isnull=True, cargo__isnull=True)
                    | Q(persona__isnull=True, organizacion__isnull=False, cargo__isnull=True)
                    | Q(persona__isnull=True, organizacion__isnull=True, cargo__isnull=False)
                ),
                name="contacto_un_solo_dueno",
            )
        ]

    def __str__(self):
        return f"{self.tipo}: {self.valor}"

    @staticmethod
    def normalizar(tipo, valor):
        valor = (valor or "").strip()
        if tipo.codigo in ("telefono_movil", "telefono_fijo"):
            return normalizar_telefono(valor)
        if tipo.codigo == "correo":
            return valor.lower()
        return valor

    def save(self, *args, **kwargs):
        self.valor_normalizado = self.normalizar(self.tipo, self.valor)
        super().save(*args, **kwargs)


class PersonaDireccion(models.Model):
    TIPOS = [("residencia", "Residencia"), ("procedencia", "Procedencia")]
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="direcciones")
    direccion = models.ForeignKey("territorio.Direccion", on_delete=models.PROTECT, related_name="+")
    tipo = models.CharField(max_length=12, choices=TIPOS, default="residencia")
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "dirección de persona"
        verbose_name_plural = "direcciones de personas"

    def __str__(self):
        return f"{self.get_tipo_display()}: {self.direccion}"


class PersonaFormacion(models.Model):
    ESTADOS = [("estudiante", "Estudiante"), ("egresado", "Egresado"), ("titulado", "Titulado")]
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="formaciones")
    organizacion = models.ForeignKey("organizaciones.Organizacion", on_delete=models.PROTECT, related_name="formaciones", verbose_name="institución educativa")
    carrera = models.ForeignKey("organizaciones.Carrera", null=True, blank=True, on_delete=models.PROTECT, related_name="formaciones")
    estado = models.CharField(max_length=12, choices=ESTADOS, default="estudiante")
    anio_inicio = models.PositiveSmallIntegerField("año de inicio", null=True, blank=True)
    anio_termino = models.PositiveSmallIntegerField("año de término", null=True, blank=True)
    # F22: datos del estudiante que la institución y la Fundación necesitan para coordinar y certificar
    sede = models.CharField("sede o campus", max_length=120, blank=True)
    JORNADAS = [("diurna", "Diurna"), ("vespertina", "Vespertina"), ("en_linea", "En línea"), ("otra", "Otra")]
    jornada = models.CharField(max_length=12, choices=JORNADAS, blank=True)
    nivel_actual = models.PositiveSmallIntegerField("año o nivel que cursa", null=True, blank=True)
    asignatura = models.CharField("asignatura, programa o práctica vinculada", max_length=200, blank=True,
                                  help_text="Ej.: vinculación con el medio, aprendizaje + servicio, práctica profesional.")
    docente = models.ForeignKey(Persona, null=True, blank=True, on_delete=models.PROTECT, related_name="estudiantes_a_cargo", verbose_name="docente o tutor a cargo")
    horas_comprometidas = models.PositiveSmallIntegerField("horas comprometidas", null=True, blank=True, help_text="Horas que debe cumplir con la Fundación.")
    vigente = models.BooleanField(default=True)

    class Meta:
        ordering = ["-vigente", "-anio_inicio"]
        verbose_name = "formación"
        verbose_name_plural = "formaciones"

    def __str__(self):
        return f"{self.carrera or 'Sin carrera'} · {self.organizacion}"

    def clean(self):
        if self.carrera_id and self.organizacion_id and self.carrera.organizacion_id != self.organizacion_id:
            raise ValidationError({"carrera": "La carrera debe pertenecer a la institución elegida."})
        if self.organizacion_id and not self.organizacion.es_educativa:
            raise ValidationError({"organizacion": "Debe ser una institución educativa."})
        if self.anio_inicio and self.anio_termino and self.anio_termino < self.anio_inicio:
            raise ValidationError({"anio_termino": "El año de término no puede ser anterior al de inicio."})


class PersonaOrganizacion(models.Model):
    """Cargo o vínculo de una persona con una organización. Los cargos son históricos."""

    TIPOS_CARGO = [("directorio", "Directorio"), ("funcional", "Funcional"), ("autoridad", "Autoridad")]
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="vinculos")
    organizacion = models.ForeignKey("organizaciones.Organizacion", on_delete=models.PROTECT, related_name="vinculos")
    cargo = models.CharField(max_length=120, blank=True)
    tipo_cargo = models.CharField("tipo de cargo", max_length=12, choices=TIPOS_CARGO, default="funcional")
    fecha_inicio = models.DateField("desde", null=True, blank=True)
    fecha_termino = models.DateField("hasta", null=True, blank=True)

    class Meta:
        ordering = ["-fecha_termino", "-fecha_inicio"]
        verbose_name = "vínculo persona-organización"
        verbose_name_plural = "vínculos persona-organización"

    def __str__(self):
        return f"{self.persona} · {self.cargo or 'vínculo'} · {self.organizacion}"

    @property
    def vigente(self):
        return self.fecha_termino is None or self.fecha_termino >= timezone.localdate()

    def clean(self):
        if self.fecha_inicio and self.fecha_termino and self.fecha_termino < self.fecha_inicio:
            raise ValidationError({"fecha_termino": "El término no puede ser anterior al inicio."})


class Experiencia(models.Model):
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="experiencias")
    descripcion = models.CharField("experiencia", max_length=250)
    lugar = models.CharField("institución o lugar", max_length=150, blank=True)
    desde = models.DateField(null=True, blank=True)
    hasta = models.DateField(null=True, blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        ordering = ["-desde"]
        verbose_name = "experiencia"
        verbose_name_plural = "experiencias"

    def __str__(self):
        return self.descripcion


class DisponibilidadPersona(models.Model):
    DIAS = [(0, "Lunes"), (1, "Martes"), (2, "Miércoles"), (3, "Jueves"), (4, "Viernes"), (5, "Sábado"), (6, "Domingo")]
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="disponibilidades")
    dia = models.PositiveSmallIntegerField("día", choices=DIAS)
    hora_inicio = models.TimeField("desde")
    hora_fin = models.TimeField("hasta")
    comentario = models.CharField(max_length=200, blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        ordering = ["dia", "hora_inicio"]
        verbose_name = "disponibilidad"
        verbose_name_plural = "disponibilidades"

    def __str__(self):
        return f"{self.get_dia_display()} {self.hora_inicio:%H:%M}–{self.hora_fin:%H:%M}"

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({"hora_fin": "La hora de término debe ser posterior a la de inicio."})


class ContactoEmergencia(models.Model):
    """Dato sensible: solo con permiso `ver_sensibles`."""

    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="contactos_emergencia")
    nombre = models.CharField(max_length=150)
    parentesco = models.CharField(max_length=60, blank=True)
    telefono = models.CharField("teléfono", max_length=40)
    telefono_normalizado = models.CharField(max_length=40, blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "contacto de emergencia"
        verbose_name_plural = "contactos de emergencia"

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        self.telefono_normalizado = normalizar_telefono(self.telefono)
        super().save(*args, **kwargs)


class VerificacionPersona(models.Model):
    """Dato sensible y con vigencia (p. ej. antecedentes). El respaldo documental se vincula en Documentos."""

    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="verificaciones")
    tipo = models.CharField(max_length=120)
    fecha = models.DateField()
    vigente_hasta = models.DateField("vigente hasta", null=True, blank=True)
    observaciones = models.CharField(max_length=250, blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "verificación"
        verbose_name_plural = "verificaciones"

    def __str__(self):
        return f"{self.tipo} ({self.fecha:%d-%m-%Y})"

    @property
    def vencida(self):
        return bool(self.vigente_hasta and self.vigente_hasta < timezone.localdate())


class PerfilSensible(models.Model):
    """Datos sensibles (Ley 21.719): solo con permiso `ver_sensibles`, con consentimiento vigente y si DATOS_SENSIBLES está activo."""

    persona = models.OneToOneField(Persona, on_delete=models.PROTECT, related_name="perfil_sensible")
    GENEROS = [("femenino", "Femenino"), ("masculino", "Masculino"), ("no_binario", "No binario"), ("otro", "Otro"), ("no_responde", "Prefiere no responder")]
    genero = models.CharField("género", max_length=12, choices=GENEROS, blank=True)
    PUEBLOS = [
        ("ninguno", "No pertenece"), ("aymara", "Aymara"), ("lickanantay", "Atacameño o Lickanantay"), ("chango", "Chango"), ("colla", "Colla"),
        ("diaguita", "Diaguita"), ("kawesqar", "Kawésqar"), ("mapuche", "Mapuche"), ("quechua", "Quechua"), ("rapa_nui", "Rapa Nui"),
        ("selknam", "Selk'nam"), ("yagan", "Yagán"), ("otro", "Otro"), ("no_responde", "Prefiere no responder"),
    ]
    pueblo_originario = models.CharField("pueblo originario", max_length=12, choices=PUEBLOS, blank=True)
    discapacidad = models.BooleanField("tiene alguna discapacidad", null=True, blank=True)
    necesidades_apoyo = models.TextField("necesidades de apoyo o accesibilidad", blank=True, help_text="Para preparar el lugar y la actividad (acceso, intérprete, material adaptado…).")
    condiciones_salud = models.TextField("condiciones de salud relevantes para las actividades", blank=True)
    alergias = models.CharField("alergias y restricciones alimentarias", max_length=250, blank=True)
    PREVISIONES = [("fonasa", "FONASA"), ("isapre", "ISAPRE"), ("capredena_dipreca", "CAPREDENA o DIPRECA"), ("otra", "Otra"), ("ninguna", "Ninguna")]
    prevision_salud = models.CharField("previsión de salud", max_length=18, choices=PREVISIONES, blank=True)
    jefatura_hogar = models.BooleanField("es jefe o jefa de hogar", null=True, blank=True)
    integrantes_hogar = models.PositiveSmallIntegerField("integrantes del hogar", null=True, blank=True)
    TRAMOS_RSH = [("40", "40 %"), ("50", "50 %"), ("60", "60 %"), ("70", "70 %"), ("80", "80 %"), ("90", "90 %"), ("100", "100 %"), ("sin_rsh", "No tiene Registro Social de Hogares")]
    tramo_rsh = models.CharField("tramo del Registro Social de Hogares", max_length=8, choices=TRAMOS_RSH, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "datos sensibles"
        verbose_name_plural = "datos sensibles"

    def __str__(self):
        return f"Datos sensibles de {self.persona}"


class Consentimiento(models.Model):
    """Consentimientos y autorizaciones. Nunca se borran: se revocan con fecha."""

    TIPOS = [
        ("datos", "Tratamiento de datos personales"), ("sensibles", "Datos sensibles"), ("imagen", "Uso de imagen (fotos y videos)"),
        ("contacto", "Contacto para futuras actividades"), ("apoderado", "Autorización del apoderado (menor de edad)"),
    ]
    MEDIOS = [("papel", "Formulario en papel"), ("digital", "Formulario digital"), ("correo", "Correo electrónico"), ("verbal", "Verbal, registrado por el equipo"), ("otro", "Otro")]
    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="consentimientos")
    tipo = models.CharField(max_length=10, choices=TIPOS)
    otorgado = models.BooleanField("otorgado", default=True, help_text="Desmarca si la persona lo rechazó.")
    fecha = models.DateField(default=timezone.localdate)
    medio = models.CharField(max_length=8, choices=MEDIOS, default="papel")
    otorgado_por = models.ForeignKey(Persona, null=True, blank=True, on_delete=models.PROTECT, related_name="consentimientos_otorgados",
                                     verbose_name="otorgado por (apoderado)", help_text="Solo si lo firma otra persona, por ejemplo el apoderado de un menor.")
    documento = models.ForeignKey("documentos.Documento", null=True, blank=True, on_delete=models.PROTECT, related_name="+", verbose_name="documento de respaldo")
    revocado_en = models.DateField("revocado el", null=True, blank=True)
    observaciones = models.CharField(max_length=250, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creado_en = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["tipo", "-fecha", "-pk"]
        verbose_name = "consentimiento"
        verbose_name_plural = "consentimientos"

    def __str__(self):
        return f"{self.get_tipo_display()} · {'otorgado' if self.otorgado else 'rechazado'} el {self.fecha:%d-%m-%Y}"

    @property
    def vigente(self):
        return self.otorgado and not self.revocado_en

    def clean(self):
        if self.otorgado_por_id and self.otorgado_por_id == self.persona_id:
            raise ValidationError({"otorgado_por": "Déjalo vacío si lo otorga la misma persona."})
        if self.revocado_en and self.fecha and self.revocado_en < self.fecha:
            raise ValidationError({"revocado_en": "La revocación no puede ser anterior al consentimiento."})


class Apoderado(models.Model):
    """Apoderado o tutor legal de una persona (normalmente menor de edad). Dato sensible."""

    persona = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="apoderados")
    apoderado = models.ForeignKey(Persona, on_delete=models.PROTECT, related_name="representados", verbose_name="apoderado o apoderada")
    parentesco = models.CharField(max_length=60, blank=True)
    tutor_legal = models.BooleanField("es tutor legal", default=False)
    vigente = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "apoderado"
        verbose_name_plural = "apoderados"
        constraints = [models.UniqueConstraint(fields=["persona", "apoderado"], name="apoderado_unico")]

    def __str__(self):
        return f"{self.apoderado} ({self.parentesco or 'apoderado'})"

    def clean(self):
        if self.apoderado_id and self.apoderado_id == self.persona_id:
            raise ValidationError({"apoderado": "Una persona no puede ser su propio apoderado."})

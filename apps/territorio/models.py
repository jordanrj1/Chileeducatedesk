"""Tablas del territorio: Region, Provincia y Comuna (se cargan desde la fuente oficial CUT), Sector (villa, población,
etapa o barrio; puede estar dentro de otro sector; se desactiva, no se borra), SectorAlias (nombres escritos distinto)
y Direccion (calle, número, comuna y sector; el sector debe pertenecer a la comuna)."""
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords

REGIONES_OFICIALES = frozenset(f"{n:02d}" for n in range(1, 17))  # 01 Tarapacá … 16 Ñuble (CUT 2018)


def es_codigo_oficial(codigo):
    """Si un código CUT es de una de las 16 regiones de Chile. La Región Demo y las de prueba usan 97, 98 o 99."""
    codigo = codigo or ""
    return codigo.isascii() and codigo.isdigit() and codigo[:2] in REGIONES_OFICIALES


# Región, provincia y comuna: si vienen de la lista oficial de Chile (si no, son de demostración o de prueba). Sin consultas.
ES_OFICIAL = property(lambda self: es_codigo_oficial(self.codigo), doc="Viene de la lista oficial de Chile (por su código).")


class Region(models.Model):
    codigo = models.CharField("código CUT", max_length=3, unique=True)
    nombre = models.CharField(max_length=120)
    es_oficial = ES_OFICIAL

    class Meta:
        ordering = ["codigo"]
        verbose_name = "región"
        verbose_name_plural = "regiones"

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("territorio:region", args=[self.pk])


class Provincia(models.Model):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="provincias")
    codigo = models.CharField("código CUT", max_length=3, unique=True)
    nombre = models.CharField(max_length=120)
    es_oficial = ES_OFICIAL

    class Meta:
        ordering = ["codigo"]
        verbose_name = "provincia"
        verbose_name_plural = "provincias"

    def __str__(self):
        return self.nombre


class Comuna(models.Model):
    provincia = models.ForeignKey(Provincia, on_delete=models.PROTECT, related_name="comunas")
    codigo = models.CharField("código CUT", max_length=5, unique=True)
    nombre = models.CharField(max_length=120)
    es_oficial = ES_OFICIAL

    class Meta:
        ordering = ["nombre"]
        verbose_name = "comuna"
        verbose_name_plural = "comunas"
        permissions = [("exportar_territorio", "Puede exportar resúmenes territoriales")]  # F23: Excel de una comuna o sector

    def __str__(self):
        return self.nombre

    @property
    def region(self):
        return self.provincia.region

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("territorio:comuna", args=[self.pk])


class Sector(models.Model):
    """Jerárquico: San Pedro de la Costa contiene Etapa 1 a 4; existen villas y poblaciones.

    Nunca se borra: se desactiva. Un sector desactivado deja de ofrecerse para elegir (ver `para_elegir`), pero lo que ya está
    registrado en él lo conserva.
    """

    TIPOS = [("sector", "Sector"), ("etapa", "Etapa"), ("villa", "Villa"), ("poblacion", "Población"), ("barrio", "Barrio")]
    comuna = models.ForeignKey(Comuna, on_delete=models.PROTECT, related_name="sectores")
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=10, choices=TIPOS, default="sector")
    sector_padre = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="hijos")
    activo = models.BooleanField(default=True, help_text="Un sector desactivado ya no se ofrece para elegir; lo registrado en él se conserva.")
    history = HistoricalRecords()

    class Meta:
        ordering = ["nombre"]
        verbose_name = "sector"
        verbose_name_plural = "sectores"
        constraints = [
            models.UniqueConstraint(fields=["comuna", "sector_padre", "nombre"], name="sector_unico_por_padre"),
            models.UniqueConstraint(fields=["comuna", "nombre"], condition=models.Q(sector_padre__isnull=True), name="sector_raiz_unico"),
        ]

    def __str__(self):
        return f"{self.sector_padre} › {self.nombre}" if self.sector_padre_id else self.nombre

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("territorio:sector", args=[self.pk])

    @classmethod
    def para_elegir(cls, conservar=None):
        """Sectores que se ofrecen en una lista para elegir: los activos y, al editar, el que el registro ya tiene (`conservar`,
        un id) aunque esté desactivado, para no perderlo al guardar."""
        filtro = models.Q(activo=True)
        if conservar:
            filtro |= models.Q(pk=conservar)
        return cls.objects.filter(filtro)

    def etiqueta(self, con_comuna=False):
        """Texto de la opción en una lista: «Villa X» o «Villa X (Hualpén)», con «(desactivado)» si ya no está activo."""
        texto = f"{self.nombre} ({self.comuna})" if con_comuna else str(self)
        return texto if self.activo else f"{texto} (desactivado)"

    def descendientes_ids(self):
        """Ids de este sector y de todos los que contiene (etapas dentro de un sector, etc.)."""
        ids, frontera = [self.pk], [self.pk]
        while frontera:
            frontera = list(Sector.objects.filter(sector_padre_id__in=frontera).values_list("pk", flat=True))
            ids += frontera
        return ids

    def clean(self):
        if self.sector_padre_id and self.sector_padre.comuna_id != self.comuna_id:
            raise ValidationError({"sector_padre": "El sector padre debe pertenecer a la misma comuna."})
        if self.sector_padre_id and self.sector_padre_id == self.pk:
            raise ValidationError({"sector_padre": "Un sector no puede ser su propio padre."})


class SectorAlias(models.Model):
    """Nombre alternativo de un sector («Pobl. San Pedro», «SPC Etapa 2»), para reconocerlo aunque se escriba distinto (TE-06)."""

    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="alias")
    nombre = models.CharField(max_length=120)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "nombre alternativo de sector"
        verbose_name_plural = "nombres alternativos de sectores"
        constraints = [models.UniqueConstraint(fields=["sector", "nombre"], name="alias_unico_por_sector")]

    def __str__(self):
        return self.nombre


class Direccion(models.Model):
    """Compartida por personas, organizaciones y lugares. Región y provincia se deducen de la comuna."""

    calle = models.CharField(max_length=160, blank=True)
    numero = models.CharField("número", max_length=20, blank=True)
    block = models.CharField(max_length=20, blank=True)
    depto = models.CharField(max_length=20, blank=True)
    referencia = models.CharField(max_length=200, blank=True)
    comuna = models.ForeignKey(Comuna, on_delete=models.PROTECT, related_name="direcciones")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.PROTECT, related_name="direcciones")

    class Meta:
        verbose_name = "dirección"
        verbose_name_plural = "direcciones"

    def __str__(self):
        partes = [" ".join(p for p in [self.calle, self.numero] if p)]
        if self.block:
            partes.append(f"block {self.block}")
        if self.depto:
            partes.append(f"depto {self.depto}")
        if self.sector_id:
            partes.append(str(self.sector))
        partes.append(self.comuna.nombre)
        return ", ".join(p for p in partes if p)

    def clean(self):
        if self.sector_id and self.comuna_id and self.sector.comuna_id != self.comuna_id:
            raise ValidationError({"sector": "El sector debe pertenecer a la comuna de la dirección."})

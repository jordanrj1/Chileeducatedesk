"""«¿Dónde se realiza o a quién va dirigida?»: una o más filas región → comuna → sector dentro del formulario de una actividad
o de un proyecto. Cada fila es la ubicación en cascada (ubicacion.py, modo «destino») y guarda solo el nivel más preciso.
Lo ya indicado se quita (deja de estar vigente, no se borra) y un territorio repetido no se duplica. Lo dibuja
territorio/_destinos.html; sin JavaScript, «+ Otro territorio» y «Actualizar listas» vuelven a dibujar sin guardar."""
from django import forms
from django.forms import formset_factory

from apps.nucleo.formularios import BloqueDeSeccion, BootstrapMixin
from apps.nucleo.selector import pk_seguro

from .ubicacion import UbicacionMixin, sin_errores

PREFIJO = "donde"
MAXIMO = 20  # filas por envío
NIVEL_TEXTO = {"sector": "Sector", "comuna": "Comuna", "provincia": "Provincia", "region": "Región"}


class DestinoForm(UbicacionMixin, BootstrapMixin, forms.Form):
    """Una fila de «¿Dónde?»: todo es opcional y se guarda el nivel más preciso elegido (`ubicacion_elegida`)."""

    ubicacion_modo = "destino"


DestinosFormSet = formset_factory(DestinoForm, extra=1, max_num=MAXIMO, validate_max=True)


def fila_inicial(territorio=None, comuna=None, sector=None):
    """Valores con que parte una fila: desde un territorio ya guardado (p. ej. el de la jornada) o desde una comuna y sector."""
    if territorio is not None:
        if territorio.sector_id:
            return {"comuna": territorio.sector.comuna_id, "sector": territorio.sector_id}
        if territorio.provincia_id:
            return {"region": territorio.provincia.region_id, "provincia": territorio.provincia_id}
        return {n: getattr(territorio, f"{n}_id") for n in ("comuna", "region") if getattr(territorio, f"{n}_id")}
    if comuna is None:
        return {}
    return {"comuna": comuna.pk, **({"sector": sector.pk} if sector else {})}


def texto_destino(t):
    """«Comuna: Hualpén» o «Sector: Villa Los Aromos (Hualpén)». El sector necesita `select_related("sector__comuna")`."""
    texto = f"{NIVEL_TEXTO.get(t.nivel, '')}: {t}"
    return f"{texto} ({t.sector.comuna})" if t.sector_id else texto


class DestinosMixin:
    """Agrega a un ModelForm (cuyo modelo tiene `territorios`, p. ej. Actividad o Proyecto) la sección «¿Dónde?».

    En `secciones`, el nombre «donde» la dibuja. Las filas se guardan junto con el registro (en `save()` o `save_m2m()`),
    dentro de la transacción de la vista. Si lo enviado no trae la sección (otra pantalla, una prueba antigua), no se toca
    nada: `destinos_enviados` es falso y la vista puede usar lo que trae la dirección (`?comuna=`).
    """

    def __init__(self, *args, destinos_inicial=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.destinos_enviados = self.is_bound and f"{PREFIJO}-TOTAL_FORMS" in self.data
        self.destinos_actuales = []
        if self.instance.pk:
            self.destinos_actuales = list(
                self.instance.territorios.filter(vigente=True).select_related("region", "provincia", "comuna", "sector__comuna", "sector__sector_padre").order_by("pk")
            )
        datos = self._datos_destinos() if self.destinos_enviados else None
        self.destinos = DestinosFormSet(datos, prefix=PREFIJO, initial=None if datos is not None else (destinos_inicial or None))

    # --- volver a dibujar sin guardar (sin JavaScript) --------------------------------
    @property
    def actualizando_destinos(self):
        """«+ Otro territorio» o «Actualizar listas» sin JavaScript: se vuelve a dibujar el formulario sin guardar."""
        if not self.destinos_enviados:
            return False
        return bool(self.data.get(f"{PREFIJO}-_otra_fila")) or any(
            k.startswith(f"{PREFIJO}-") and k.endswith("-_actualizar_ubicacion") and v for k, v in self.data.items()
        )

    def _datos_destinos(self):
        if not self.actualizando_destinos:
            return self.data
        datos = self.data.copy()
        total = min(pk_seguro(datos.get(f"{PREFIJO}-TOTAL_FORMS")) or 0, MAXIMO)
        for i in range(total):  # todas las filas se ordenan (lo que no calza se suelta) y no muestran errores
            datos[f"{PREFIJO}-{i}-_actualizar_ubicacion"] = "1"
        if datos.get(f"{PREFIJO}-_otra_fila") and total < MAXIMO:
            datos[f"{PREFIJO}-TOTAL_FORMS"] = str(total + 1)
        return datos

    def full_clean(self):
        if self.actualizando_destinos:
            sin_errores(self)
            return
        super().full_clean()

    def is_valid(self):
        return super().is_valid() and not self.actualizando_destinos

    def clean(self):
        d = super().clean()
        if self.destinos_enviados and not self.destinos.is_valid():
            errores = list(self.destinos.non_form_errors())
            self.add_error(None, errores[0] if errores else "Revisa la sección «¿Dónde?»: hay una fila con un error.")
        return d

    # --- guardar ----------------------------------------------------------------------
    def quitar_elegidos(self):
        vigentes = {t.pk for t in self.destinos_actuales}
        return {pk_seguro(v) for v in self.data.getlist(f"{PREFIJO}-quitar")} & vigentes if self.is_bound else set()

    def guardar_destinos(self, obj):
        """Quita lo marcado y agrega cada fila elegida: un territorio que ya estaba se reactiva en vez de repetirse."""
        if not self.destinos_enviados:
            return
        relacion = obj.territorios
        quitar = self.quitar_elegidos()
        if quitar:
            relacion.filter(pk__in=quitar).update(vigente=False)
        existentes = {t.clave: t for t in relacion.all()}
        for fila in self.destinos.forms:
            elegido = fila.ubicacion_elegida()
            if not elegido:
                continue  # fila vacía: no se guarda
            ((nivel, valor),) = elegido.items()
            t = existentes.get((nivel, valor.pk))
            if t is None:
                existentes[(nivel, valor.pk)] = relacion.create(**{nivel: valor})
            elif not t.vigente:
                t.vigente = True
                t.save(update_fields=["vigente"])

    def _save_m2m(self):
        super()._save_m2m()  # lo llaman save() y save_m2m(): el registro ya tiene id
        self.guardar_destinos(self.instance)

    # --- para dibujar ------------------------------------------------------------------
    @property
    def bloques_de_seccion(self):
        return {**super().bloques_de_seccion, "donde": BloqueDeSeccion(self, "territorio/_destinos.html", ())}

    def destinos_ui(self):
        quitar = self.quitar_elegidos()
        return {
            "actuales": [{"pk": t.pk, "texto": texto_destino(t), "quitar": t.pk in quitar} for t in self.destinos_actuales],
            "formset": self.destinos, "prefijo": PREFIJO,
        }

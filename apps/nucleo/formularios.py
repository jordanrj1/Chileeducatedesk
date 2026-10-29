"""Piezas comunes de formularios: BootstrapMixin da el estilo y agrupa los campos por secciones;
SelectorField es un campo con buscador (se abre, se escribe y se elige) para listas largas como personas u organizaciones;
SelectorMultiple es la selección múltiple desplegable (botón, buscador y etiquetas) en vez de casillas a la vista."""
from collections import namedtuple

from django import forms
from django.db.models import Q
from django.utils.functional import lazy

from . import memo
from .selector import TOPE, pk_seguro


class SelectorMultiple(forms.CheckboxSelectMultiple):
    """Selección múltiple desplegable: un botón con el resumen de lo elegido que despliega la lista con un buscador.
    Lo dibuja generico/_selector_multiple.html (desde generico/_campo.html) y static/js/selector.js muestra lo elegido
    como etiquetas con × para quitarlas. Sin JavaScript son casillas nativas dentro de un bloque plegable (<details>).
    Lo que se envía no cambia (perfiles=3&perfiles=7), así que las vistas y la validación siguen iguales."""


def a_desplegable(campo):
    """Cambia las casillas a la vista (o la lista de selección múltiple) de un campo por el SelectorMultiple.
    Se conservan sus opciones y atributos; si el formulario cambia después la consulta del campo, el nuevo
    control recibe las opciones nuevas (Django las asigna al widget del campo)."""
    w = campo.widget
    if isinstance(w, SelectorMultiple) or not isinstance(w, (forms.CheckboxSelectMultiple, forms.SelectMultiple)):
        return
    attrs = {k: v for k, v in w.attrs.items() if k != "class"}
    attrs["class"] = "form-check-input"
    nuevo = SelectorMultiple(attrs=attrs)
    nuevo.choices = w.choices
    nuevo.is_required, nuevo.is_localized = w.is_required, w.is_localized
    campo.widget = nuevo


class IteradorCompartido(forms.models.ModelChoiceIterator):
    """F26 Rb: las opciones de un catálogo se leen una vez por petición aunque las pidan varios campos o filas."""

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        for obj in memo.lista(self.queryset):
            yield self.choice(obj)


def compartir_opciones(campo):
    """Un ModelChoiceField (no los buscadores, que tienen su propio iterador) pasa a leer sus opciones con
    IteradorCompartido. Si el formulario cambia después la consulta, el campo sigue usando este iterador."""
    if isinstance(campo, forms.ModelChoiceField) and campo.iterator is forms.models.ModelChoiceIterator:
        campo.iterator = IteradorCompartido
        if not hasattr(campo, "_choices"):
            campo.widget.choices = campo.choices


class BootstrapMixin:
    """Aplica clases de Bootstrap a todos los campos. Toda selección múltiple pasa a ser desplegable (SelectorMultiple)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instancia = getattr(self, "instance", None)
        if instancia is not None and instancia._state.adding and "vigente" in self.fields:
            # Al agregar un registro nunca se crea «no vigente» (el modelo parte en vigente); se da de baja después
            # con «Marcar no vigente» o al editarlo.
            del self.fields["vigente"]
        elif "vigente" in self.fields and not self.fields["vigente"].help_text:
            self.fields["vigente"].help_text = "Desmárcala para dar de baja este dato sin borrarlo: queda en el historial."
        fijar_valores_selectores(self)
        for campo in self.fields.values():
            compartir_opciones(campo)
            a_desplegable(campo)
            w = campo.widget
            if isinstance(w, forms.CheckboxSelectMultiple):
                continue  # la clase de cada casilla la pone a_desplegable (Django la pondría también en el contenedor)
            if isinstance(w, forms.CheckboxInput):
                clase = "form-check-input"
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                clase = "form-select"
            else:
                clase = "form-control"
            w.attrs["class"] = (w.attrs.get("class", "") + " " + clase).strip()
            if isinstance(w, forms.Textarea):
                # F26 Ia: Django trae rows="10" (texto) por defecto; un form que pide otro número lo conserva.
                if w.attrs.get("rows") in (None, "10"):
                    w.attrs["rows"] = 3
                w.attrs.setdefault("data-crecer", "")  # fche.js la hace crecer al escribir; sin JS queda de 3 filas
            if isinstance(w, forms.DateInput):
                w.input_type = "date"
                w.format = "%Y-%m-%d"
            if isinstance(w, forms.TimeInput):
                w.input_type = "time"
                w.format = "%H:%M"

    # [(título, ayuda, [nombres de campos])]: el formulario se dibuja por bloques. Un 4.º elemento opcional
    # {"plegada": True} dibuja la sección plegada (<details>); se abre sola si uno de sus campos tiene valor o error.
    secciones = ()
    bloques_de_seccion = {}  # {nombre: BloqueDeSeccion}: un nombre en `secciones` que dibuja varios campos juntos

    def secciones_ui(self):
        """Secciones (`Seccion`) con sus campos visibles; lo que no está en ninguna va al final en «Otros datos».
        Un nombre de `bloques_de_seccion` (p. ej. «ubicacion») dibuja sus campos juntos con la plantilla del bloque."""
        if not self.secciones:
            return None
        bloques = self.bloques_de_seccion or {}
        usados, res = set(), []
        for titulo, ayuda, nombres, *opciones in self.secciones:
            plegada = bool(opciones and opciones[0].get("plegada"))
            campos = []
            for n in nombres:
                if n in bloques:
                    campos.append(bloques[n])
                    usados.update(bloques[n].campos)
                elif n in self.fields:
                    campos.append(self[n])
            usados.update(nombres)
            if campos:
                res.append(Seccion(titulo, ayuda, campos, plegada, not plegada or any(_con_dato(c) for c in campos)))
        resto = []
        for n in self.fields:
            if n in usados:
                continue
            bloque = next((b for b in bloques.values() if n in b.campos), None)
            if bloque is None:
                resto.append(self[n])
            elif bloque not in resto:
                resto.append(bloque)
        if resto:
            res.append(Seccion("Otros datos", "", resto, False, True))
        return res


Seccion = namedtuple("Seccion", "titulo ayuda campos plegada abierta")


def _con_dato(campo):
    """Si un campo de una sección plegada tiene valor o error (entonces la sección se dibuja abierta)."""
    if getattr(campo, "es_bloque", False):
        return False
    return bool(campo.errors) or campo.value() not in (None, "", [], (), False)


class BloqueDeSeccion:
    """Varios campos que se dibujan juntos con su propia plantilla dentro de una sección (p. ej. la ubicación en cascada)."""

    es_bloque = True

    def __init__(self, form, plantilla, campos):
        self.form, self.plantilla, self.campos = form, plantilla, tuple(campos)


def preparar_tramos(form, etiqueta_texto="Rango etario (texto anterior)"):
    """Campo «tramos_etarios» con los tramos activos (más los que el registro ya tenía) y su rango de edad a la vista.
    El texto antiguo «rango_etario» solo se muestra si tiene algo, para revisarlo y borrarlo; si está vacío, sale del formulario."""
    from .models import TramoEtario

    campo = form.fields["tramos_etarios"]
    campo.queryset = TramoEtario.para_elegir(conservar=form.instance.tramos_etarios.all() if form.instance.pk else None)
    campo.label_from_instance = lambda t: t.etiqueta
    if not form.instance.rango_etario:
        form.fields.pop("rango_etario", None)
    elif "rango_etario" in form.fields:
        form.fields["rango_etario"].label = etiqueta_texto
        form.fields["rango_etario"].help_text = ("Se escribió antes de que existieran los tramos de edad. "
                                                 "Revisa que los tramos marcados digan lo mismo y luego borra este texto.")


class _IteradorLimitado(forms.models.ModelChoiceIterator):
    """Opciones del <select> sin JavaScript: la vacía, la elegida y las primeras de la fuente (no la lista entera)."""

    def __iter__(self):
        campo = self.field
        if campo.empty_label is not None:
            yield ("", campo.empty_label)
        fuente, pk = campo.fuente, campo.valor_actual
        if pk:
            actual = next(iter(memo.lista(fuente.con_relaciones(self.queryset.filter(pk=pk))[:1])), None)
            if actual is not None:
                yield self.choice(actual)
        qs = fuente.base(**campo.filtros)
        if pk:
            qs = qs.exclude(pk=pk)
        # F26 Rb: varios buscadores iguales en la página (p. ej. las filas de «Relaciones») leen sus opciones una sola vez
        for grupo, objs in fuente.agrupar(memo.lista(fuente.con_relaciones(fuente.ordenar(qs))[:TOPE])):
            if grupo and objs:
                yield (grupo, [self.choice(o) for o in objs])
            else:
                yield from (self.choice(o) for o in objs)


class SelectorWidget(forms.Select):
    """<select> que static/js/selector.js convierte en un buscador. Cada opción lleva su nombre corto (data-texto)."""

    fuente = None

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        opcion = super().create_option(name, value, label, selected, index, subindex, attrs)
        obj = getattr(value, "instance", None)
        if obj is not None and self.fuente is not None:
            opcion["attrs"]["data-texto"] = self.fuente.texto(obj)
        return opcion


_url_lista = lazy(lambda fuente, filtros, crear: fuente.url_lista(filtros, crear), str)


class SelectorField(forms.ModelChoiceField):
    """Campo para elegir un registro de una lista larga, con buscador. Usa la «fuente» del tipo de registro
    (apps/<app>/selector.py) tanto para ofrecer como para validar. Un valor ya guardado que dejó de ofrecerse
    (por ejemplo, una persona desactivada) se conserva al editar y se marca «(desactivada)»."""

    widget = SelectorWidget
    iterator = _IteradorLimitado

    def __init__(self, fuente, filtros=None, crear=True, **kwargs):
        self.fuente = fuente
        self.filtros = {k: str(v) for k, v in (filtros or {}).items() if v not in (None, "")}
        self.crear = crear
        super().__init__(fuente.base(**self.filtros), **kwargs)
        self.valor_actual = None
        self.inactivos = set()
        self._fijar_atributos()

    def _fijar_atributos(self):
        self.widget.fuente = self.fuente
        self.widget.attrs.update({
            "data-selector": "1",
            "data-opciones-url": _url_lista(self.fuente, dict(self.filtros), self.crear),
            "data-placeholder": self.fuente.placeholder,
        })

    def __deepcopy__(self, memo):
        result = super().__deepcopy__(memo)
        # Cada formulario lleva su propia copia de los filtros: excluir un registro en uno no afecta a los demás.
        result.filtros = dict(self.filtros)
        result.queryset = self.fuente.base(**result.filtros)  # consulta nueva en cada formulario (ajustes y fechas al día)
        result.valor_actual = None
        result.inactivos = set()
        return result

    def con_filtros(self, **extra):
        """Agrega filtros (p. ej. excluir el propio registro) a lo que se ofrece y se valida."""
        # Se reemplaza el diccionario (no se modifica): así nunca se toca el del campo declarado en la clase.
        self.filtros = {**self.filtros, **{k: str(v) for k, v in extra.items() if v not in (None, "")}}
        self.queryset = self.fuente.base(**self.filtros)
        self.inactivos = set()
        self._fijar_atributos()

    def label_from_instance(self, obj):
        etiqueta = self.fuente.etiqueta(obj)
        marca = self.fuente.marca(obj) if obj.pk in self.inactivos else ""
        return f"{etiqueta} {marca}" if marca else etiqueta


def fijar_valores_selectores(form):
    """Para cada buscador: conserva el valor ya guardado aunque haya dejado de ofrecerse, y anota el valor
    elegido para dibujarlo. Un valor que no es un número no provoca un error 500: queda como error del campo."""
    instancia = getattr(form, "instance", None)
    for nombre, campo in form.fields.items():
        if not isinstance(campo, SelectorField):
            continue
        guardado = pk_seguro(form.initial.get(nombre)) or pk_seguro(getattr(instancia, f"{nombre}_id", None))
        if guardado and guardado not in campo.inactivos and not campo.queryset.filter(pk=guardado).exists():
            modelo = campo.queryset.model
            if modelo._default_manager.filter(pk=guardado).exists():
                campo.queryset = modelo._default_manager.filter(Q(pk__in=campo.queryset.values("pk")) | Q(pk=guardado))
                campo.inactivos.add(guardado)
        valor = form.data.get(form.add_prefix(nombre)) if form.is_bound else guardado
        campo.valor_actual = pk_seguro(valor)

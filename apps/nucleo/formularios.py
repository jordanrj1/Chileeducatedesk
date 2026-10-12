from django import forms


class BootstrapMixin:
    """Aplica clases de Bootstrap a todos los campos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        fijar_valores_selectores(self)
        for campo in self.fields.values():
            w = campo.widget
            if isinstance(w, forms.CheckboxInput):
                clase = "form-check-input"
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                clase = "form-select"
            else:
                clase = "form-control"
            w.attrs["class"] = (w.attrs.get("class", "") + " " + clase).strip()
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("rows", 3)
            if isinstance(w, forms.DateInput):
                w.input_type = "date"
                w.format = "%Y-%m-%d"
            if isinstance(w, forms.TimeInput):
                w.input_type = "time"
                w.format = "%H:%M"


class _IteradorLimitado(forms.models.ModelChoiceIterator):
    """Solo ofrece la opción vacía y la seleccionada; el resto se busca por HTMX (listas muy grandes)."""

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        pk = getattr(self.field, "valor_actual", None)
        if pk:
            obj = self.queryset.filter(pk=pk).first()
            if obj:
                yield self.choice(obj)


class SelectorField(forms.ModelChoiceField):
    """Campo de selección con búsqueda: escribe, elige. La validación sigue usando el queryset completo."""

    iterator = _IteradorLimitado

    def __init__(self, queryset, url, **kwargs):
        super().__init__(queryset, **kwargs)
        self.widget.attrs["selector_url"] = url
        self.valor_actual = None


def fijar_valores_selectores(form):
    for nombre, campo in form.fields.items():
        if isinstance(campo, SelectorField):
            if form.is_bound:
                v = form.data.get(form.add_prefix(nombre))
            else:
                v = form.initial.get(nombre) or getattr(getattr(form, "instance", None), f"{nombre}_id", None)
            campo.valor_actual = getattr(v, "pk", v) or None

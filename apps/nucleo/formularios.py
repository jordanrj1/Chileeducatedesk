from django import forms


class BootstrapMixin:
    """Aplica clases de Bootstrap a todos los campos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

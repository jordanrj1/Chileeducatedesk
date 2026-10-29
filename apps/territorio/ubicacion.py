"""Ubicación en cascada para cualquier formulario: región → comuna → sector (la provincia es opcional y solo acota),
con «+ Crear sector» y, si se pide, la comunidad. El bloque lo dibuja territorio/_ubicacion.html y la ruta
/territorio/ubicacion lo vuelve a dibujar cada vez que cambia una lista. Sin JavaScript, «Actualizar listas» hace lo mismo
sin guardar. En el formulario de lugar, el bloque muestra además lo que ya hay en la comuna elegida."""
import json
import re
from itertools import groupby

from django import forms
from django.db.models import Q
from django.forms.utils import ErrorDict
from django.urls import reverse

from apps.nucleo import memo
from apps.nucleo.formularios import BloqueDeSeccion, BootstrapMixin
from apps.nucleo.selector import pk_seguro

from .models import Comuna, Provincia, Region, Sector

CAMPOS = ("region", "provincia", "comuna", "sector")
MODOS = ("direccion", "comunidad", "destino")  # dirección y comunidad exigen comuna; destino (actividad, proyecto) no exige nada
CONTEXTOS = ("", "lugar")  # «lugar»: muestra lo que ya hay en la comuna elegida
VACIO = ("", "---------")
PANEL_TOPE = 6  # registros por grupo en «En <comuna> ya hay…»


def prefijo_seguro(valor):
    """Prefijo de formulario que llega desde la página («dir», «territorios-0»); cualquier otra cosa se descarta."""
    valor = str(valor or "")
    return valor if re.fullmatch(r"[A-Za-z][\w-]{0,59}", valor) else ""


def sin_errores(form):
    """Deja un formulario enviado sin errores a la vista: se usa cuando solo se pidió «Actualizar listas»."""
    form._errors, form.cleaned_data = ErrorDict(), {}


class UbicacionMixin:
    """Agrega región, provincia, comuna y sector (y la comunidad, si se pide) con listas en cascada.

    Atributos (o argumentos al crear el formulario con el mismo nombre):
    - `ubicacion_modo`: «direccion» o «comunidad» (comuna obligatoria) o «destino» (todo opcional; ver `ubicacion_elegida`);
    - `ubicacion_crear_sector`: ofrece «+ Crear sector» a quien puede crearlos;
    - `ubicacion_contexto`: «lugar» muestra lo que ya hay en la comuna (para no duplicar);
    - `ubicacion_comunidad`: agrega la comunidad (de la comuna elegida) después del sector.
    Si el modelo ya tiene `comuna` y `sector`, se usan esos campos; si no, se agregan.
    Un sector desactivado no se ofrece, salvo el que el registro ya tenía (se ve «(desactivado)»).
    En `secciones`, el nombre «ubicacion» dibuja el bloque completo.
    """

    ubicacion_modo = "direccion"
    ubicacion_crear_sector = True
    ubicacion_contexto = ""
    ubicacion_comunidad = False

    def __init__(self, *args, ubicacion_cambio=None, ubicacion_conservar=None, **kw):
        for nombre in ("ubicacion_modo", "ubicacion_crear_sector", "ubicacion_contexto", "ubicacion_comunidad"):
            if nombre in kw:
                setattr(self, nombre, kw.pop(nombre))
        super().__init__(*args, **kw)
        self.ubicacion_cambio = ubicacion_cambio  # None: primer dibujo; si no, qué lista cambió al volver a dibujar
        self._conservar = ubicacion_conservar or pk_seguro(getattr(getattr(self, "instance", None), "sector_id", None))
        self.ubicacion_estado = {}  # lo escrito en «+ Crear sector», el mensaje y el foco (lo llena la vista)
        self._agregar_campos()
        self._armar_listas()

    # --- campos -------------------------------------------------------------
    @property
    def campos_ubicacion(self):
        return CAMPOS + (("comunidad",) if self.ubicacion_comunidad else ())

    def _agregar_campos(self):
        obligatoria = self.ubicacion_modo in ("direccion", "comunidad")
        nuevos = {
            "region": forms.ModelChoiceField(Region.objects.all(), required=False),
            "provincia": forms.ModelChoiceField(Provincia.objects.all(), required=False),
            "comuna": forms.ModelChoiceField(Comuna.objects.all()),
            "sector": forms.ModelChoiceField(Sector.objects.all(), required=False),
        }
        if self.ubicacion_comunidad:
            from apps.comunidades.models import Comunidad

            nuevos["comunidad"] = forms.ModelChoiceField(Comunidad.objects.filter(activo=True), required=False, label="Comunidad")
        campos = {}
        for nombre, campo in self.fields.items():
            if nombre == "comuna":  # región y provincia van justo antes de la comuna
                campos.update({n: self.fields.get(n) or nuevos[n] for n in ("region", "provincia")})
            if nombre not in ("region", "provincia"):
                campos[nombre] = campo
        for nombre in self.campos_ubicacion:
            campos.setdefault(nombre, nuevos[nombre])
        self.fields = campos
        f = self.fields
        f["region"].label, f["region"].help_text = "Región", ""
        f["provincia"].label, f["provincia"].help_text = "Provincia", "Opcional: deja solo las comunas de esa provincia."
        f["comuna"].queryset = Comuna.objects.select_related("provincia__region")
        f["comuna"].required, f["comuna"].label, f["comuna"].help_text = obligatoria, "Comuna", ""
        f["sector"].required, f["sector"].label, f["sector"].help_text = False, "Sector, villa o población", ""
        f["sector"].error_messages["invalid_choice"] = "Ese sector no está disponible en la comuna elegida (puede estar desactivado): elige otro."
        url = reverse("territorio:ubicacion")
        cambian = ("region", "provincia", "comuna") + (("sector",) if self.ubicacion_comunidad else ())
        for nombre in self.campos_ubicacion:
            w = f[nombre].widget
            w.attrs["class"] = "form-select"
            if nombre in cambian:  # al cambiar, el bloque se vuelve a dibujar (ver territorio/_ubicacion.html)
                w.attrs.update({"hx-get": url, "hx-trigger": "change"})

    # --- valores elegidos -----------------------------------------------------
    def _crudo(self, nombre):
        if self.is_bound:
            return pk_seguro(self.data.get(self.add_prefix(nombre)))
        return pk_seguro(self.initial.get(nombre))

    def _resolver(self):
        """(región, provincia, comuna, sector, comunidad) elegidos. Al volver a dibujar, se ordenan para que nada quede
        incoherente: la lista que cambió manda y lo que no calza con ella se suelta."""
        v = {n: self._crudo(n) for n in self.campos_ubicacion}
        R = Region.objects.filter(pk=v["region"]).first() if v["region"] else None
        P = Provincia.objects.filter(pk=v["provincia"]).first() if v["provincia"] else None
        C = Comuna.objects.select_related("provincia__region").filter(pk=v["comuna"]).first() if v["comuna"] else None
        S = Sector.objects.filter(pk=v["sector"]).first() if v["sector"] else None
        CM = None
        if self.ubicacion_comunidad and v["comunidad"]:
            CM = self.fields["comunidad"].queryset.model.objects.filter(pk=v["comunidad"]).first()
        if self.is_bound and not self.actualizando_ubicacion:
            return R, P, C, S, CM  # al guardar se valida tal cual en clean()
        cambio = "" if self.is_bound else self.ubicacion_cambio
        if cambio is None:  # primer dibujo: la región y la provincia salen de la comuna
            if C:
                R, P = C.provincia.region, C.provincia
        else:
            if cambio == "comuna" and C:
                R = C.provincia.region
                P = P if P and P.pk == C.provincia_id else None
            if cambio == "provincia" and P:
                R = Region.objects.filter(pk=P.region_id).first()
            if P and R and P.region_id != R.pk:
                P = None
            if C and ((P and C.provincia_id != P.pk) or (R and C.provincia.region_id != R.pk)):
                C = None
            if C and not R:
                R = C.provincia.region
            if P and not R:
                R = Region.objects.filter(pk=P.region_id).first()
        if S and (not C or S.comuna_id != C.pk):
            S = None
        if CM and (not C or CM.comuna_id != C.pk):
            CM = None
        if self.is_bound:
            return R, P, C, S, CM
        for nombre, obj in (("region", R), ("provincia", P)):
            if obj:
                self.initial[nombre] = obj.pk
            else:
                self.initial.pop(nombre, None)
        for nombre, obj in (("comuna", C), ("sector", S), ("comunidad", CM)):
            if obj is None:
                self.initial.pop(nombre, None)  # un valor que no existe o no calza se ignora
            elif cambio is not None:
                self.initial[nombre] = obj.pk
        return R, P, C, S, CM

    def _armar_listas(self):
        # F26 Rb: con dos ubicaciones en la misma página (p. ej. actividad y su lugar) las listas se leen una vez (memo.lista)
        R, P, C, S, CM = self._resolver()
        self._elegidos = {"region": R, "provincia": P, "comuna": C, "sector": S, "comunidad": CM}
        f = self.fields
        f["region"].choices = [VACIO] + [(r.pk, r.nombre) for r in memo.lista(Region.objects.order_by("codigo"))]
        f["provincia"].choices = [VACIO] + [(p.pk, p.nombre) for p in memo.lista((Provincia.objects.filter(region=R) if R else Provincia.objects.all()).order_by("nombre"))]
        if P or R:
            comunas = Comuna.objects.filter(**({"provincia": P} if P else {"provincia__region": R})).order_by("nombre")
            f["comuna"].choices = [VACIO] + [(c.pk, c.nombre) for c in memo.lista(comunas)]
        else:  # sin región: todas, agrupadas por región
            todas = Comuna.objects.select_related("provincia__region").order_by("provincia__region__codigo", "nombre")
            f["comuna"].choices = [VACIO] + [(r.nombre, [(c.pk, c.nombre) for c in lista]) for r, lista in groupby(memo.lista(todas), key=lambda c: c.provincia.region)]
        sector = f["sector"]
        if C:
            sector.queryset = Sector.para_elegir(conservar=self._conservar).filter(comuna=C)
            self._sectores = sorted(sector.queryset.select_related("sector_padre__sector_padre"), key=lambda s: str(s).lower())
            sector.choices = [VACIO] + [(s.pk, s.etiqueta()) for s in self._sectores]
            if not self._sectores:
                sector.help_text = f"Aún no hay sectores en {C.nombre}."
        else:
            sector.queryset = Sector.para_elegir(conservar=self._conservar)  # se valida contra la comuna en clean()
            self._sectores = []
            sector.choices = [("", "Primero elige la comuna")]
            sector.widget.attrs["disabled"] = True
            sector.help_text = "Elige la comuna para ver o crear sus sectores."
        if self.ubicacion_comunidad:
            self._armar_comunidades(C, S)

    def _armar_comunidades(self, C, S):
        campo = self.fields["comunidad"]
        if not C:
            campo.choices = [("", "Primero elige la comuna")]
            campo.widget.attrs["disabled"] = True
            campo.help_text = "Elige la comuna para ver sus comunidades."
            return
        qs = campo.queryset.filter(comuna=C)
        if S:  # las del sector, las del sector que lo contiene y las de toda la comuna
            qs = qs.filter(Q(sector__isnull=True) | Q(sector=S) | Q(sector_id=S.sector_padre_id))
        campo.queryset = qs
        campo.choices = [VACIO] + [(c.pk, c.nombre) for c in qs.order_by("nombre")]

    # --- validación -------------------------------------------------------------
    @property
    def actualizando_ubicacion(self):
        """Sin JavaScript, «Actualizar listas» vuelve a dibujar el formulario con las listas al día y sin guardar."""
        return self.is_bound and bool(self.data.get(self.add_prefix("_actualizar_ubicacion")))

    def full_clean(self):
        if self.actualizando_ubicacion:
            sin_errores(self)
            return
        super().full_clean()

    def is_valid(self):
        return super().is_valid() and not self.actualizando_ubicacion

    def clean(self):
        d = super().clean()
        R, P, C, S = (d.get(n) for n in CAMPOS)
        if P and R and P.region_id != R.pk:
            self.add_error("provincia", "La provincia no pertenece a la región elegida.")
        if C and P and C.provincia_id != P.pk:
            self.add_error("comuna", "La comuna no pertenece a la provincia elegida.")
        elif C and R and C.provincia.region_id != R.pk:
            self.add_error("comuna", "La comuna no pertenece a la región elegida.")
        if S and not C and "comuna" not in self.errors:
            self.add_error("sector", "Elige también la comuna del sector.")
        elif S and C and S.comuna_id != C.pk:
            self.add_error("sector", "El sector debe pertenecer a la comuna elegida.")
        cm = d.get("comunidad") if self.ubicacion_comunidad else None
        if cm and C and cm.comuna_id != C.pk:
            self.add_error("comunidad", "La comunidad debe ser de la comuna elegida.")
        escrito = (self.data.get(self.add_prefix("nuevo_sector_nombre")) or "").strip()
        if escrito and not S and "sector" not in self.errors:
            self.add_error("sector", f"Escribiste el sector «{escrito}» pero no lo creaste: pulsa «+ Crear sector» o borra el texto.")
        return d

    def ubicacion_elegida(self):
        """El nivel más preciso elegido, para guardar un solo nivel (modo «destino»): {"sector": …}, {"comuna": …},
        {"provincia": …}, {"region": …} o {} si no se eligió nada."""
        d = getattr(self, "cleaned_data", {})
        for nombre in ("sector", "comuna", "provincia", "region"):
            if d.get(nombre):
                return {nombre: d[nombre]}
        return {}

    # --- para dibujar ------------------------------------------------------------
    @property
    def bloques_de_seccion(self):
        """En `secciones`, el nombre «ubicacion» dibuja el bloque completo en vez de cada lista por separado."""
        return {"ubicacion": BloqueDeSeccion(self, "territorio/_ubicacion.html", self.campos_ubicacion)}

    def campos_sin_ubicacion(self):
        """Los demás campos (calle, número…), en el orden del formulario."""
        return [c for c in self if c.name not in self.campos_ubicacion]

    def _vals_crear(self, confirmar=False):
        C = self._elegidos["comuna"]
        vals = {"comuna_del_sector": str(C.pk) if C else "", "_formato": "bloque"}
        if confirmar:
            vals["confirmar_sector"] = "1"
        return json.dumps(vals)

    def ubicacion_ui(self):
        """Todo lo que necesita territorio/_ubicacion.html para dibujar el bloque."""
        p = self.add_prefix
        C = self._elegidos["comuna"]
        valores = {"_prefijo": self.prefix or "", "_modo": self.ubicacion_modo, "_contexto": self.ubicacion_contexto,
                   "_crear": "1" if self.ubicacion_crear_sector else "0", "_comunidad": "1" if self.ubicacion_comunidad else "0"}
        if self._conservar:
            valores["_conservar"] = str(self._conservar)
        estado = self.ubicacion_estado
        if estado.get("enfocar") == "sector":  # tras crear el sector, el foco queda en la lista con el sector elegido
            self.fields["sector"].widget.attrs["autofocus"] = True
        dato =(lambda n: (self.data.get(p(n)) or "")) if self.is_bound else (lambda n: estado.get(n, ""))
        escrito = dato("nuevo_sector_nombre")
        return {
            "id": "ubicacion-" + (self.prefix or "principal"), "vals": json.dumps(valores), "comuna": C,
            "region": self["region"], "provincia": self["provincia"], "campo_comuna": self["comuna"], "sector": self["sector"],
            "comunidad": self["comunidad"] if self.ubicacion_comunidad else None,
            "provincia_abierta": bool(self._elegidos["provincia"]) or bool(self.is_bound and self.errors.get("provincia")),
            "crear": self.ubicacion_crear_sector, "padres": [s for s in self._sectores if s.activo], "tipos": Sector.TIPOS,
            "nombre_sector": p("nuevo_sector_nombre"), "nombre_tipo": p("nuevo_sector_tipo"), "nombre_padre": p("nuevo_sector_padre"),
            "nombre_actualizar": p("_actualizar_ubicacion"),
            "escrito": escrito, "tipo_escrito": dato("nuevo_sector_tipo") or "sector", "padre_escrito": str(dato("nuevo_sector_padre")),
            "vals_crear": self._vals_crear(), "vals_confirmar": self._vals_crear(confirmar=True),
            "mensaje": estado.get("mensaje", ""), "nivel": estado.get("nivel", "secondary"), "confirmar": estado.get("confirmar", False),
            "abierto": bool(escrito) or estado.get("abierto", False) or bool(self.is_bound and self.errors.get("sector")),
            "enfocar": estado.get("enfocar", ""),
            "panel": lo_que_hay_en(C, self._sectores) if C and self.ubicacion_contexto == "lugar" else None,
        }


class UbicacionForm(UbicacionMixin, BootstrapMixin, forms.Form):
    """Solo la ubicación: la usa /territorio/ubicacion para volver a dibujar el bloque de cualquier formulario."""


def formulario_desde_peticion(datos, cambio="", elegir=None):
    """Arma el bloque que se vuelve a dibujar con lo que manda la página: el prefijo y las opciones del formulario de origen
    (`_prefijo`, `_modo`, `_contexto`, `_crear`, `_comunidad`, `_conservar`), lo elegido en cada lista y lo escrito en
    «+ Crear sector». `elegir` cambia una elección (p. ej. el sector recién creado)."""
    prefijo = prefijo_seguro(datos.get("_prefijo"))
    nombre = (lambda n: f"{prefijo}-{n}") if prefijo else (lambda n: n)
    con_comunidad = datos.get("_comunidad") == "1"
    campos = CAMPOS + (("comunidad",) if con_comunidad else ())
    inicial = {n: datos.get(nombre(n), "") for n in campos}
    inicial.update(elegir or {})
    form = UbicacionForm(
        prefix=prefijo or None, initial=inicial, ubicacion_cambio=cambio,
        ubicacion_modo=datos.get("_modo") if datos.get("_modo") in MODOS else "direccion",
        ubicacion_contexto=datos.get("_contexto") if datos.get("_contexto") in CONTEXTOS else "",
        ubicacion_crear_sector=datos.get("_crear") != "0", ubicacion_comunidad=con_comunidad,
        ubicacion_conservar=pk_seguro(datos.get("_conservar")),
    )
    form.ubicacion_estado = {n: (datos.get(nombre(n)) or "").strip() for n in ("nuevo_sector_nombre", "nuevo_sector_tipo", "nuevo_sector_padre")}
    return form


def lo_que_hay_en(comuna, sectores):
    """«En <comuna> ya hay…»: sectores, comunidades, lugares y organizaciones activos de la comuna, para reutilizarlos en vez
    de crearlos de nuevo. Usa un número fijo de consultas: una lista corta y un total por grupo."""
    from apps.comunidades.models import Comunidad

    from .consultas import lugares_de, organizaciones_de

    url = comuna.get_absolute_url()
    activos = [s for s in sectores if s.activo]
    comunidades = Comunidad.objects.filter(comuna=comuna, activo=True).select_related("sector").order_by("nombre")
    lugares = lugares_de(comuna=comuna).filter(activo=True).order_by("nombre")
    organizaciones = organizaciones_de(comuna=comuna).filter(activo=True).order_by("nombre")
    grupos = [
        ("Sectores", "sector", "sectores", "sectores", len(activos), [(str(s), s.get_absolute_url(), s.get_tipo_display()) for s in activos[:PANEL_TOPE]]),
        ("Comunidades", "comunidad", "comunidades", "comunidades", comunidades.count(),
         [(c.nombre, c.get_absolute_url(), c.sector.nombre if c.sector_id else "") for c in comunidades[:PANEL_TOPE]]),
        ("Lugares", "lugar", "lugares", "lugares", lugares.count(), [(l.nombre, l.get_absolute_url(), str(l.tipo)) for l in lugares[:PANEL_TOPE]]),
        ("Organizaciones", "organización", "organizaciones", "organizaciones", organizaciones.count(),
         [(o.nombre, o.get_absolute_url(), str(o.tipo)) for o in organizaciones[:PANEL_TOPE]]),
    ]
    grupos = [{"titulo": t, "total": n, "filas": filas, "mas": f"{url}?tab={pestana}", "texto": f"{n} {uno if n == 1 else varios}"}
              for t, uno, varios, pestana, n, filas in grupos]
    return {"grupos": grupos, "total": sum(g["total"] for g in grupos), "resumen": " · ".join(g["texto"] for g in grupos)}

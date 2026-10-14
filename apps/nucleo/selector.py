"""Buscadores para elegir un registro (persona, organización, actividad…) dentro de un formulario.
Cada tipo de registro tiene una «fuente» que dice qué se ofrece, cómo se busca, se ordena y se muestra.
El campo del formulario y la lista que se despliega usan la misma consulta: lo que se ofrece es lo que se acepta.
La lista la arma el servidor (con format_html, que escapa todo) y static/js/selector.js la muestra."""
import json
import re
from urllib.parse import urlencode

from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.views import View

from .vistas_base import Permiso403Mixin

TOPE = 25  # opciones que se muestran al abrir la lista
TOPE_MAXIMO = 100


def pk_seguro(valor):
    """Un identificador válido (entero positivo) o None. Un texto como «abc» no provoca errores."""
    v = getattr(valor, "pk", valor)
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if v > 0 else None
    texto = str(v if v is not None else "").strip()
    if texto.isdigit() and len(texto) <= 12 and int(texto) > 0:
        return int(texto)
    return None


def campo_seguro(valor):
    """El id del campo que pidió crear (p. ej. «id_responsable»); cualquier otra cosa se descarta."""
    valor = str(valor or "")
    return valor if re.fullmatch(r"[A-Za-z][\w-]{0,99}", valor) else ""


def respuesta_elegido(campo, valor, texto, aviso=""):
    """Respuesta de la ventana «+ Crear…»: no reemplaza nada en la página y avisa al buscador (evento
    «fche:elegido») qué registro quedó elegido. json.dumps escapa las tildes, así el encabezado es seguro."""
    from django.http import HttpResponse

    r = HttpResponse("")
    r["HX-Reswap"] = "none"
    r["HX-Trigger"] = json.dumps({"fche:elegido": {"campo": campo_seguro(campo), "valor": valor, "texto": texto, "aviso": aviso}})
    return r


class Fuente:
    """Qué registros se ofrecen y cómo se muestran. Cada app define la suya (apps/<app>/selector.py)."""

    modelo = None
    permiso_ver = ""
    url_opciones = ""  # nombre de la ruta que entrega la lista
    url_crear = ""  # nombre de la ruta de «+ Crear…» ('' = no se crea desde el buscador)
    permiso_crear = ""
    etiqueta_crear = ""  # «persona», «organización»
    placeholder = "Escribe para buscar…"
    texto_vacio = "Aún no hay registros."
    filtros_permitidos = ()  # filtros que acepta la dirección de la lista (p. ej. tipo, excluir)

    # --- consulta ---------------------------------------------------------
    def base(self, **filtros):
        """Consulta para listar y para validar."""
        return self.modelo.objects.all()

    def buscar(self, qs, q):
        return qs

    def ordenar(self, qs):
        return qs.order_by("pk")

    def con_relaciones(self, qs):
        """select_related / prefetch_related para mostrar el detalle sin consultas en bucle."""
        return qs

    # --- presentación -----------------------------------------------------
    def texto(self, obj):
        return str(obj)

    def detalle(self, obj):
        return ""

    def marca(self, obj):
        """Se agrega al texto cuando el valor ya guardado ya no se ofrece (p. ej. «(desactivada)»)."""
        return "(desactivada)" if getattr(obj, "activo", True) is False else "(no disponible)"

    def agrupar(self, objs):
        """[(título del grupo o None, [objetos])]."""
        return [(None, list(objs))]

    def aviso(self, filtros):
        """Una frase extra para el pie de la lista (o '')."""
        return ""

    def puede_crear(self, usuario, filtros):
        return bool(self.url_crear) and usuario.has_perm(self.permiso_crear)

    # --- utilidades -------------------------------------------------------
    def limpiar_filtros(self, datos):
        """Solo los filtros declarados, como texto, y «excluir» solo si es un número."""
        res = {}
        for nombre in self.filtros_permitidos:
            valor = str(datos.get(nombre, "") or "").strip()[:60]
            if nombre == "excluir":
                valor = str(pk_seguro(valor) or "")
            if valor:
                res[nombre] = valor
        return res

    def url_lista(self, filtros=None, crear=False):
        params = dict(filtros or {})
        if crear and self.url_crear:
            params["crear"] = "1"
        return reverse(self.url_opciones) + (f"?{urlencode(params)}" if params else "")

    def etiqueta(self, obj):
        """Texto de la opción en el <select> sin JavaScript: nombre y, si hay, el detalle para distinguir homónimos."""
        d = self.detalle(obj)
        return f"{self.texto(obj)} · {d}" if d else self.texto(obj)

    def opciones(self, q="", actual=None, limite=TOPE, **filtros):
        """Primeras opciones que calzan con `q` y el total. Con `q` vacío, la opción actual va primero."""
        base = self.base(**filtros)
        qs = self.buscar(base, q) if q else base
        total = qs.count()
        objs = list(self.con_relaciones(self.ordenar(qs))[:limite])
        pk = pk_seguro(actual)
        elegida, fuera = None, False
        if pk and not q:
            elegida = next((o for o in objs if o.pk == pk), None)
            if elegida is not None:
                objs = [o for o in objs if o.pk != pk]
            else:
                elegida = self.con_relaciones(self.modelo.objects.filter(pk=pk)).first()
                fuera = elegida is not None and not base.filter(pk=pk).exists()
        return {"objs": objs, "total": total, "mostradas": len(objs) + (1 if elegida is not None and not fuera else 0),
                "elegida": elegida, "elegida_fuera": fuera, "actual": pk}


def _opcion_html(fuente, obj, seleccionada=False, marca=""):
    texto = fuente.texto(obj)
    detalle = fuente.detalle(obj)
    return format_html(
        '<div class="fche-selector__opcion" role="option" aria-selected="{}" data-valor="{}" data-texto="{}">'
        "<span>{}{}</span>{}</div>",
        "true" if seleccionada else "false", obj.pk, texto, texto, format_html(" <em>{}</em>", marca) if marca else "",
        format_html("<small>{}</small>", detalle) if detalle else "",
    )


def panel_html(fuente, datos, q="", url_crear=""):
    """HTML de la lista desplegable. Todo pasa por format_html: los nombres no pueden inyectar marcado."""
    partes = []
    actual = datos["actual"]
    if datos["elegida"] is not None:
        partes.append(_opcion_html(fuente, datos["elegida"], True, fuente.marca(datos["elegida"]) if datos["elegida_fuera"] else ""))
    for grupo, objs in fuente.agrupar(datos["objs"]):
        if not objs:
            continue
        opciones = format_html_join("", "{}", ((_opcion_html(fuente, o, o.pk == actual),) for o in objs))
        if grupo:
            partes.append(format_html(
                '<div role="group" aria-label="{}"><div class="fche-selector__grupo" aria-hidden="true">{}</div>{}</div>', grupo, grupo, opciones,
            ))
        else:
            partes.append(opciones)
    if url_crear:
        texto = f"+ Crear {fuente.etiqueta_crear} “{q}”" if q else f"+ Crear {fuente.etiqueta_crear} nueva"
        partes.append(format_html(
            '<div class="fche-selector__crear" role="option" aria-selected="false" data-crear="{}">{}</div>', url_crear, texto,
        ))
    total, mostradas = datos["total"], datos["mostradas"]
    if total == 0 and q:
        pie = format_html("Sin resultados para «{}».", q)
    elif total == 0:
        pie = fuente.texto_vacio
    elif total > mostradas:
        pie = f"Mostrando {mostradas} de {total}. Escribe para filtrar si no ves a quien buscas."
    else:
        pie = f"Mostrando {mostradas} de {total}."
    aviso = fuente.aviso(datos.get("filtros", {}))
    return format_html(
        '<div class="fche-selector__lista" role="listbox">{}</div><div class="fche-selector__pie">{}{}</div>',
        mark_safe("".join(str(p) for p in partes)), pie, format_html(" {}", aviso) if aviso else "",
    )


class OpcionesVista(Permiso403Mixin, View):
    """Lista de opciones para un buscador: acepta `q` (texto), `actual` (valor elegido), `limite` y los filtros de la fuente."""

    fuente = None

    def get_permission_required(self):
        return (self.fuente.permiso_ver,)

    def get(self, request):
        from django.http import HttpResponse

        q = request.GET.get("q", "").strip()[:100]
        try:
            limite = max(1, min(int(request.GET.get("limite") or TOPE), TOPE_MAXIMO))
        except ValueError:
            limite = TOPE
        filtros = self.fuente.limpiar_filtros(request.GET)
        datos = self.fuente.opciones(q, request.GET.get("actual"), limite, **filtros)
        datos["filtros"] = filtros
        url_crear = ""
        if request.GET.get("crear") == "1" and self.fuente.puede_crear(request.user, filtros):
            url_crear = reverse(self.fuente.url_crear) + "?" + urlencode({"q": q, **filtros})
        return HttpResponse(panel_html(self.fuente, datos, q, url_crear))

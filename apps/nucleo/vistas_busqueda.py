"""Pantalla de resultados del buscador general (/buscar), agrupados por tipo y con filtros.
La búsqueda en sí está en busqueda.py."""
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.http import QueryDict
from django.views.generic import TemplateView

from . import busqueda
from .models import EstadoActividad, EstadoRegistro, TipoActividad
from .vistas_base import Permiso403Mixin


POR_GRUPO = 5  # F26 P: sin elegir tipo, cada grupo muestra hasta 5 y «Ver todos (n)»

# Lista de cada módulo para «Ver todos (n)» y cómo se llaman allí los filtros de /buscar (param de /buscar -> param de la lista).
# Sin lista propia (minutas), «Ver todos» abre /buscar con ese tipo.
LISTAS = {
    "persona": ("/personas", {"zona": "comuna", "registro": "registro"}),
    "organizacion": ("/organizaciones", {}),
    "comunidad": ("/comunidades", {"zona": "comuna"}),
    "proyecto": ("/proyectos", {}),
    "actividad": ("/actividades", {"zona": "comuna", "tipo_actividad": "tipo", "desde": "desde", "hasta": "hasta"}),
    "lugar": ("/lugares", {"zona": "comuna"}),
    "reunion": ("/reuniones", {"desde": "desde", "hasta": "hasta"}),
    "documento": ("/documentos", {"desde": "desde", "hasta": "hasta"}),
}


def url_ver_todos(tipo, g, estados_pk):
    """Dirección de «Ver todos»: la lista del módulo con ?q= y los filtros equivalentes que existan."""
    if tipo not in LISTAS:
        params = QueryDict(mutable=True)
        params.update({k: v for k, v in g.items() if v and k != "page"})
        params["tipo"] = tipo
        return f"/buscar?{params.urlencode()}"
    ruta, equivalentes = LISTAS[tipo]
    params = {}
    if g.get("q", "").strip():
        params["q"] = g["q"].strip()
    for origen, destino in equivalentes.items():
        if g.get(origen):
            params[destino] = g[origen]
    if tipo == "actividad" and g.get("estado") in estados_pk:  # la lista filtra el estado por su número, /buscar por su código
        params["estado"] = estados_pk[g["estado"]]
    return ruta + (f"?{urlencode(params)}" if params else "")


def _sin(g, *quitar):
    params = g.copy()
    for k in (*quitar, "page"):
        params.pop(k, None)
    return params.urlencode()


class Buscar(Permiso403Mixin, TemplateView):
    template_name = "nucleo/buscar.html"

    def has_permission(self):
        u = self.request.user
        return u.is_authenticated and u.groups.exists()

    def _barra(self, g, estados, comunas, tipos_actividad, registros):
        """Filtros con la forma que usa la barra común (generico/_filtros.html)."""
        from .fases import modulo_activo

        tipos = [(v, n, "") for v, n in busqueda.TIPOS if v != "reunion" or modulo_activo("reuniones")]
        defs = [
            # (param, etiqueta, opciones, entrada, principal, grupo, todos, texto_casilla)
            ("tipo", "Tipo", tipos, "select", True, "", "Todos", ""),
            ("zona", "Zona", [(str(c.pk), c.nombre, "") for c in comunas], "select", True, "", "Todas", ""),
            ("desde", "Desde", [], "date", True, "", "", ""),
            ("hasta", "Hasta", [], "date", True, "", "", ""),
            ("estado", "Estado de la actividad", [(e.codigo, e.nombre, "") for e in estados], "select", False, "Actividades", "Todos", ""),
            ("tipo_actividad", "Tipo de actividad", [(str(t.pk), t.nombre, "") for t in tipos_actividad], "select", False, "Actividades", "Todos", ""),
            ("registro", "Estado del registro", [(r.codigo, r.nombre, "") for r in registros], "select", False, "Personas", "Todos", ""),
            ("con_actividades", "Con actividades", [], "casilla", False, "Organizaciones", "", "Solo organizaciones con actividades"),
        ]
        ui, activos = [], []
        for param, etiqueta, opciones, entrada, principal, grupo, todos, casilla in defs:
            valor = g.get(param, "")
            ui.append({"param": param, "etiqueta": etiqueta, "opciones": opciones, "valor": valor, "entrada": entrada, "todos": todos,
                       "grupo": grupo, "por_defecto": "", "texto_casilla": casilla or etiqueta, "aviso": "", "principal": principal})
            if valor:
                if entrada == "select":
                    texto = next((o[1] for o in opciones if o[0] == valor), valor)
                elif entrada == "date":
                    texto = "-".join(reversed(valor.split("-")))
                else:
                    texto = "Sí"
                activos.append({"param": param, "etiqueta": etiqueta, "texto": texto, "url_quitar": _sin(g, param), "en_mas": not principal})
        if g.get("q", "").strip():
            activos.insert(0, {"param": "q", "etiqueta": "Texto", "texto": f"«{g['q'].strip()}»", "url_quitar": _sin(g, "q"), "en_mas": False})
        return {
            "filtros_ui": ui, "filtros_principales": [u for u in ui if u["principal"]], "filtros_mas": [u for u in ui if not u["principal"]],
            "filtros_activos": activos, "n_mas_activos": sum(1 for a in activos if a["en_mas"]), "url_limpiar": "", "buscable": True,
            "q": g.get("q", ""), "texto_busqueda": "Nombre, RUT, correo, teléfono, actividad…", "etiqueta_busqueda": "Texto a buscar",
        }

    def get_context_data(self, **kw):
        from apps.territorio.models import Comuna

        ctx = super().get_context_data(**kw)
        g = self.request.GET
        hay_criterio = any(g.get(k) for k in ("q", "tipo", "estado", "zona", "desde", "hasta", "tipo_actividad", "registro", "con_actividades"))
        resultados = busqueda.buscar(self.request.user, g) if hay_criterio else []
        estados, comunas = list(EstadoActividad.objects.all()), list(Comuna.objects.all())
        tipos_actividad, registros = list(TipoActividad.objects.all()), list(EstadoRegistro.objects.all())
        nombres = dict(busqueda.TIPOS)
        conteo = {}
        for r in resultados:
            conteo[r.tipo] = conteo.get(r.tipo, 0) + 1
        un_tipo = bool(g.get("tipo"))
        # Con un tipo elegido se ve todo, por páginas; sin tipo, hasta 5 por grupo con «Ver todos (n)»
        pagina = Paginator(resultados, 50).get_page(g.get("page")) if un_tipo else None
        grupos = {}
        for r in (pagina if un_tipo else resultados):
            items = grupos.setdefault(r.tipo, [])
            if un_tipo or len(items) < POR_GRUPO:
                items.append(r)
        estados_pk = {e.codigo: str(e.pk) for e in estados}
        agrupados = [
            {"nombre": nombres[t], "clave": t, "total": conteo[t], "items": grupos[t],
             "ver_todos": url_ver_todos(t, g, estados_pk) if not un_tipo and conteo[t] > POR_GRUPO else ""}
            for t, _ in busqueda.TIPOS if t in grupos
        ]
        hay_tope = any(n >= busqueda.LIMITE_POR_TIPO for n in conteo.values())
        total = len(resultados)
        ctx.update(
            titulo="Búsqueda", termino=g.get("q", "").strip(), pagina=pagina, agrupados=agrupados, hay_tope=hay_tope, limite=busqueda.LIMITE_POR_TIPO,
            total=total, hay_criterio=hay_criterio, querystring=_sin(g), paginator={"count": total}, datos=g,
            **self._barra(g, estados, comunas, tipos_actividad, registros),
        )
        return ctx

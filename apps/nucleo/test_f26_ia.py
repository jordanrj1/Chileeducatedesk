"""Pruebas de F26 Ia (specs/f26/spec.md, «Paquete I · Interfaz por módulo → Ia. Piezas comunes»): un solo botón «Filtros»,
solicitudes sin selector de estado, áreas de texto de 3 filas, «Desactivar» en «Más acciones», campos vacíos plegados,
«Origen» dentro del Historial, «Tareas» en proyectos, «Historial de cargas», dirección con «Más datos» y «Es la Fundación»
en «Datos legales». Todos los datos son ficticios."""
import re

import pytest
from django import forms

from apps.comunidades.models import Comunidad
from apps.nucleo.formularios import BootstrapMixin
from apps.organizaciones.forms import OrganizacionForm
from apps.organizaciones.models import Organizacion
from apps.proyectos.models import Proyecto
from apps.territorio.forms import DireccionForm

pytestmark = pytest.mark.django_db


def _html(cliente, url):
    r = cliente.get(url)
    assert r.status_code == 200, url
    return r.content.decode()


@pytest.mark.parametrize("url", ["/personas", "/actividades", "/organizaciones", "/lugares", "/proyectos", "/solicitudes", "/importaciones"])
def test_boton_de_filtros_unico(cg, url):
    html = _html(cg, url)
    barra = html.split('class="fche-filtros"', 1)[1].split("</form>", 1)[0]
    assert "Filtros" in barra
    # ya no hay un «Filtrar» azul visible: solo el botón oculto que aplica con Enter cuando los demás filtros están plegados
    assert "btn-outline-primary" not in barra
    for boton in re.findall(r"<button[^>]*>[^<]*Filtrar</button>", barra):
        assert "visually-hidden" in boton


def test_solicitudes_sin_selector_de_estado_pero_filtra_por_pestana(cg):
    html = _html(cg, "/solicitudes")
    assert 'name="estado"' not in html
    assert 'aria-label="Solicitudes por estado"' in html
    assert _html(cg, "/solicitudes?estado=pendiente").count('aria-current="page"') >= 1


class _FormTexto(BootstrapMixin, forms.Form):
    corto = forms.CharField(widget=forms.Textarea)
    largo = forms.CharField(widget=forms.Textarea(attrs={"rows": 6}))


def test_areas_de_texto_de_3_filas_que_crecen():
    f = _FormTexto()
    assert f.fields["corto"].widget.attrs["rows"] == 3
    assert "data-crecer" in f.fields["corto"].widget.attrs
    assert f.fields["largo"].widget.attrs["rows"] == 6  # el formulario que pide otro número lo conserva
    assert 'rows="3"' in str(f["corto"])


def test_ayuda_corta_del_responsable():
    from apps.actividades.forms import TareaForm
    from apps.proyectos.forms import ProyectoForm

    for form in (TareaForm, ProyectoForm):
        assert form.base_fields["responsable"].help_text == "Queda en el equipo automáticamente."


def _org(tipo_org, **kw):
    return Organizacion.objects.create(nombre="Junta Ficticia Norte", tipo=tipo_org("junta_de_vecinos_o_comite"), **kw)


@pytest.mark.parametrize("cual", ["organizacion", "comunidad", "lugar"])
def test_desactivar_en_mas_acciones_y_el_post_sigue_funcionando(cg, cual, tipo_org, comuna, lugar):
    if cual == "organizacion":
        obj, ruta = _org(tipo_org), "organizaciones"
    elif cual == "comunidad":
        obj, ruta = Comunidad.objects.create(nombre="Vecinos Ficticios", comuna=comuna, tipo="vecinal"), "comunidades"
    else:
        obj, ruta = lugar, "lugares"
    html = _html(cg, obj.get_absolute_url())
    menu = html.split('class="fche-menu__panel"', 1)[1].split("</details>", 1)[0]
    assert f'action="/{ruta}/{obj.pk}/' in menu and "Desactivar" in menu
    cuerpo = html.split('id="pestana"', 1)[1]
    assert "Desactivar" not in cuerpo  # ya no hay botón suelto al pie de Información
    accion = re.search(rf'action="(/{ruta}/{obj.pk}/[^"]+)"', menu).group(1)
    assert cg.post(accion).status_code == 302
    obj.refresh_from_db()
    assert obj.activo is False


def test_campos_vacios_plegados_e_insignia_unica(cg, tipo_org):
    o = _org(tipo_org)
    html = _html(cg, o.get_absolute_url())
    cuerpo = html.split('id="pestana"', 1)[1]
    assert re.search(r"Sin completar \(\d+\)", cuerpo)
    assert "<dd>—</dd>" not in cuerpo
    assert "Activa" not in cuerpo and "Inactiva" not in html  # «Inactiva» solo si lo está
    o.activo = False
    o.save()
    assert "Inactiva" in _html(cg, o.get_absolute_url())


@pytest.mark.parametrize("cual", ["proyecto", "organizacion", "lugar"])
def test_origen_dentro_del_historial(cg, cual, tipo_org, lugar):
    obj = {"proyecto": lambda: Proyecto.objects.create(nombre="Proyecto Ficticio"), "organizacion": lambda: _org(tipo_org), "lugar": lambda: lugar}[cual]()
    html = _html(cg, f"{obj.get_absolute_url()}?tab=origen")
    assert 'href="?tab=origen"' not in html
    assert re.search(r'class="nav-link active" href="\?tab=historial"', html)
    assert "Origen de la información" in html


def test_tareas_en_proyectos(cg):
    p = Proyecto.objects.create(nombre="Proyecto Ficticio")
    assert "<th" in (lista := _html(cg, "/proyectos")) and re.search(r"<th[^>]*>(<a[^>]*>)?Tareas", lista)
    resumen = _html(cg, p.get_absolute_url())
    assert "<dt>Tareas</dt>" in resumen and "<dt>Actividades</dt>" not in resumen


def test_historial_de_cargas(cg):
    html = _html(cg, "/importaciones")
    assert "Historial de cargas" in html and "+ Cargar planilla" in html
    assert "Importaciones" not in html.split("<main", 1)[-1] and "Nueva importación" not in html
    nueva = _html(cg, "/importaciones/nueva")
    assert "Cargar planilla" in nueva and "Historial de cargas" in nueva


def test_direccion_con_mas_datos_plegados(comuna):
    f = DireccionForm()
    assert [c.name for c in f.campos_mas()] == ["block", "depto", "referencia"]
    assert not f.mas_abierto()
    f = DireccionForm(initial={"depto": "12"})
    assert f.mas_abierto()


def test_es_la_fundacion_en_datos_legales():
    legales = next(s for s in OrganizacionForm.secciones if s[0] == "Datos legales")
    assert "es_propia" in legales[2] and legales[3].get("plegada")
    assert all("es_propia" not in s[2] for s in OrganizacionForm.secciones if s[0] != "Datos legales")

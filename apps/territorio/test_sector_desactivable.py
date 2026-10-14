"""Pruebas automáticas del sector que se desactiva en vez de borrarse: deja de ofrecerse para elegir, lo registrado en él
se conserva al editar, no se duplica al crear uno con su nombre, queda en el historial y su ficha lo explica.
También revisa el bloque «Cómo funciona el territorio». Los nombres son ficticios."""
import pytest

from apps.comunidades.forms import ComunidadForm
from apps.comunidades.models import Comunidad
from apps.territorio.forms import DireccionForm
from apps.territorio.models import Direccion, Sector

pytestmark = pytest.mark.django_db


@pytest.fixture
def sectores(comuna):
    activo = Sector.objects.create(comuna=comuna, nombre="Villa Ficticia Activa", tipo="villa")
    viejo = Sector.objects.create(comuna=comuna, nombre="Población Ficticia Antigua", tipo="poblacion", activo=False)
    return activo, viejo


def test_sector_desactivado_no_se_ofrece_pero_se_conserva_al_editar(cg, comuna, sectores):
    activo, viejo = sectores
    # la cascada de la dirección y el formulario nuevo solo ofrecen los activos
    html = cg.get(f"/territorio/sectores?comuna={comuna.pk}").content.decode()
    assert activo.nombre in html and viejo.nombre not in html
    nuevo = DireccionForm({"calle": "Calle Inventada", "comuna": comuna.pk, "sector": viejo.pk})
    assert not nuevo.is_valid() and "sector" in nuevo.errors
    assert list(ComunidadForm().fields["sector"].queryset) == [activo]

    # lo que ya estaba en el sector desactivado lo conserva: se ve marcado y se guarda sin cambios
    direccion = Direccion.objects.create(calle="Calle Inventada", comuna=comuna, sector=viejo)
    editar = DireccionForm(instance=direccion)
    etiquetas = [etiqueta for _, etiqueta in editar.fields["sector"].choices]
    assert f"{viejo.nombre} (desactivado)" in etiquetas and activo.nombre in etiquetas
    editar = DireccionForm({"calle": "Calle Cambiada", "comuna": comuna.pk, "sector": viejo.pk}, instance=direccion)
    assert editar.is_valid(), editar.errors
    assert editar.save().sector == viejo
    comunidad = Comunidad.objects.create(nombre="Comunidad Ficticia", comuna=comuna, sector=viejo)
    assert viejo in ComunidadForm(instance=comunidad).fields["sector"].queryset


def test_desactivar_y_reactivar_desde_la_ficha_con_historial(cg, ca, comuna, sectores):
    activo, _ = sectores
    url = f"/territorio/sector/{activo.pk}"
    html = cg.get(url).content.decode()
    assert "Desactivar sector" in html and f"/comunidades/nueva?comuna={comuna.pk}&amp;sector={activo.pk}" in html

    assert ca.post(f"{url}/alternar").status_code == 403  # el Administrador no edita sectores
    assert cg.post(f"{url}/alternar").status_code == 302
    activo.refresh_from_db()
    assert not activo.activo

    html = cg.get(url).content.decode()
    assert "Reactivar sector" in html and "Ya no se ofrece para elegir" in html
    assert "/comunidades/nueva?" not in html and "/actividades/nueva?" not in html  # ya no es punto de partida
    # tampoco recibe sectores nuevos dentro
    r = cg.post(f"/territorio/comuna/{comuna.pk}/sectores/nuevo", {"nombre": "Etapa Ficticia 1", "tipo": "etapa", "sector_padre": activo.pk}, follow=True)
    assert not Sector.objects.filter(nombre="Etapa Ficticia 1").exists() and "desactivado" in r.content.decode()

    historial = cg.get(f"{url}?tab=historial").content.decode()
    assert "Modificación" in historial and activo.history.count() == 2

    cg.post(f"{url}/alternar")
    activo.refresh_from_db()
    assert activo.activo


def test_crear_sector_con_el_nombre_de_uno_desactivado_avisa_y_no_duplica(cg, comuna, sectores):
    _, viejo = sectores
    r = cg.post("/territorio/sectores/crear", {"dir-comuna": comuna.pk, "nuevo_sector_nombre": "poblacion ficticia antigua"})
    html = r.content.decode()
    assert "está desactivado" in html and viejo.get_absolute_url() in html
    assert f'value="{viejo.pk}"' not in html  # no queda elegido
    assert Sector.objects.filter(comuna=comuna).count() == 2
    r = cg.post(f"/territorio/comuna/{comuna.pk}/sectores/nuevo", {"nombre": "Población Ficticia Antigua", "tipo": "poblacion"}, follow=True)
    assert "Reactívalo" in r.content.decode() and Sector.objects.filter(comuna=comuna).count() == 2


def test_bloque_como_funciona_en_el_indice_y_en_las_fichas(cg, comuna, sectores):
    activo, _ = sectores
    for url in ("/territorio", comuna.get_absolute_url(), activo.get_absolute_url()):
        html = cg.get(url).content.decode()
        assert "Cómo funciona el territorio" in html and "De dónde sale" in html and "Qué reúne cada comuna o sector" in html, url
    # en una comuna sin nada registrado se muestra desplegado
    assert '<details class="fche-tarjeta mb-4" open>' in cg.get(comuna.get_absolute_url()).content.decode()

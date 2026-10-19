"""Pruebas de la ubicación en cascada (región → comuna → sector): la región acota las comunas, «+ Crear sector» explica
que falta la comuna y, con comuna, crea y deja elegido; el panel «En <comuna> ya hay…» del lugar; y los formularios que
la usan siguen guardando (sin JavaScript, «Actualizar listas» no guarda). Todos los nombres son ficticios."""
import pytest

from apps.comunidades.models import Comunidad
from apps.lugares.models import Lugar
from apps.territorio.models import Comuna, Provincia, Region, Sector

pytestmark = pytest.mark.django_db


@pytest.fixture
def otra_region(comuna):
    r = Region.objects.create(codigo="98", nombre="Región Inventada")
    p = Provincia.objects.create(region=r, codigo="980", nombre="Provincia Inventada")
    return Comuna.objects.create(provincia=p, codigo="98001", nombre="Comuna Lejana")


def test_la_region_acota_las_comunas_y_suelta_lo_que_no_calza(cg, comuna, otra_region):
    villa = Sector.objects.create(comuna=comuna, nombre="Villa Ficticia Uno", tipo="villa")
    base = {"_prefijo": "dir", "dir-comuna": comuna.pk, "dir-sector": villa.pk}
    # se cambia a otra región: solo sus comunas, y la comuna y el sector anteriores se sueltan
    html = cg.get("/territorio/ubicacion", {**base, "dir-region": otra_region.provincia.region_id}, HTTP_HX_TRIGGER_NAME="dir-region").content.decode()
    assert "Comuna Lejana" in html and "Comuna Ficticia" not in html
    assert "Villa Ficticia Uno" not in html and "Primero elige la comuna" in html
    # se elige la comuna: la región se deduce y aparecen sus sectores
    html = cg.get("/territorio/ubicacion", {**base, "dir-region": ""}, HTTP_HX_TRIGGER_NAME="dir-comuna").content.decode()
    assert f'value="{comuna.provincia.region_id}" selected' in html and f'value="{villa.pk}" selected' in html
    assert "+ Crear sector en Comuna Ficticia" in html


def test_crear_sector_sin_comuna_explica_y_con_comuna_crea_y_deja_elegido(cg, comuna):
    html = cg.get("/lugares/nuevo").content.decode()
    assert "Primero elige la comuna: cada sector pertenece a una comuna." in html and 'aria-describedby="ubicacion-dir-sin-comuna"' in html
    assert 'data-enter-dispara' not in html  # sin comuna no hay cuadro para escribir el sector

    previo = Sector.objects.create(comuna=comuna, nombre="Población Ficticia Previa", tipo="poblacion")
    datos = {"_prefijo": "dir", "_formato": "bloque", "comuna_del_sector": comuna.pk, "dir-comuna": comuna.pk, "dir-sector": previo.pk}
    # sin nombre: lo explica y conserva el sector que ya estaba elegido
    html = cg.post("/territorio/sectores/crear", {**datos, "dir-nuevo_sector_nombre": ""}).content.decode()
    assert "Escribe el nombre del sector nuevo." in html and f'value="{previo.pk}" selected' in html
    # sin comuna explícita: no crea y lo explica
    html = cg.post("/territorio/sectores/crear", {**datos, "comuna_del_sector": "", "dir-nuevo_sector_nombre": "Villa Nueva"}).content.decode()
    assert "Elige la comuna primero" in html and not Sector.objects.filter(nombre="Villa Nueva").exists()
    # con comuna: crea dentro del sector elegido como padre y queda seleccionado, con el foco en la lista
    html = cg.post("/territorio/sectores/crear", {**datos, "dir-nuevo_sector_nombre": "Etapa Ficticia 1", "dir-nuevo_sector_tipo": "etapa",
                                                  "dir-nuevo_sector_padre": previo.pk}).content.decode()
    nuevo = Sector.objects.get(nombre="Etapa Ficticia 1")
    assert nuevo.comuna == comuna and nuevo.sector_padre == previo and nuevo.tipo == "etapa"
    assert f'value="{nuevo.pk}" selected' in html and "creado y seleccionado" in html and "autofocus" in html
    assert 'id="ubicacion-dir"' in html and 'hx-swap="outerHTML"' in html


def test_sector_escrito_sin_crear_no_se_pierde_en_silencio(cg, comuna):
    from apps.nucleo.models import TipoLugar

    r = cg.post("/lugares/nuevo", {"nombre": "Sede Ficticia", "tipo": TipoLugar.objects.get(codigo="sala").pk, "dir-comuna": comuna.pk, "dir-calle": "Calle Inventada",
                                   "dir-nuevo_sector_nombre": "Villa Escrita"})
    assert r.status_code == 200 and "Escribiste el sector «Villa Escrita» pero no lo creaste" in r.content.decode()
    assert not Lugar.objects.filter(nombre="Sede Ficticia").exists()


def test_panel_del_lugar_muestra_lo_que_ya_hay_en_la_comuna(cg, comuna, lugar, universidad, django_assert_max_num_queries):
    from apps.territorio.models import Direccion

    universidad.direccion = Direccion.objects.create(calle="Calle Inventada", numero="5", comuna=comuna)
    universidad.save()
    Sector.objects.create(comuna=comuna, nombre="Villa Ficticia Dos", tipo="villa")
    Comunidad.objects.create(nombre="Comunidad Ficticia Norte", comuna=comuna)
    with django_assert_max_num_queries(20):
        html = cg.get("/territorio/ubicacion", {"_prefijo": "dir", "_contexto": "lugar", "dir-comuna": comuna.pk},
                      HTTP_HX_TRIGGER_NAME="dir-comuna").content.decode()
    assert "En Comuna Ficticia ya hay: 1 sector · 1 comunidad · 1 lugar · 1 organización" in html
    for nombre in ("Villa Ficticia Dos", "Comunidad Ficticia Norte", "Sala Ficticia", "Universidad Ficticia"):
        assert nombre in html, nombre
    # el formulario de lugar lo muestra al editar (ya tiene comuna); el de organización no
    assert "ya hay:" in cg.get(f"/lugares/{lugar.pk}/editar").content.decode()
    assert "ya hay:" not in cg.get("/organizaciones/nueva?comuna=%d" % comuna.pk).content.decode()


def test_formularios_con_cascada_siguen_guardando_y_actualizar_listas_no_guarda(cg, comuna, persona):
    villa = Sector.objects.create(comuna=comuna, nombre="Villa Ficticia Tres", tipo="villa")
    # comunidad: comuna y sector en el bloque «ubicacion» de su sección Territorio
    html = cg.get(f"/comunidades/nueva?comuna={comuna.pk}").content.decode()
    assert 'id="ubicacion-principal"' in html and f'value="{villa.pk}"' in html
    r = cg.post("/comunidades/nueva", {"nombre": "Comunidad Ficticia Sur", "tipo": "vecinal", "comuna": comuna.pk, "sector": villa.pk})
    assert r.status_code == 302 and Comunidad.objects.get(nombre="Comunidad Ficticia Sur").sector == villa
    # dirección de persona
    r = cg.post(f"/personas/{persona.pk}/direcciones/nuevo", {"tipo": "residencia", "comuna": comuna.pk, "sector": villa.pk, "calle": "Pasaje Inventado"})
    assert r.status_code == 302 and persona.direcciones.get().direccion.sector == villa
    # sin JavaScript: «Actualizar listas» vuelve a dibujar con los sectores de la comuna, sin guardar ni marcar errores
    r = cg.post("/lugares/nuevo", {"dir-comuna": comuna.pk, "dir-_actualizar_ubicacion": "1"})
    html = r.content.decode()
    assert r.status_code == 200 and "Villa Ficticia Tres" in html and "fche-campo--error" not in html and "en rojo" not in html and not Lugar.objects.exists()

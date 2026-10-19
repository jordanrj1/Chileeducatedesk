"""Pruebas de «¿Dónde?» en actividad y proyecto: varias filas región → comuna → sector que guardan el nivel más preciso,
editar sin tocar conserva, «Quitar» deja la zona no vigente y volver a elegirla la reactiva, el prellenado desde la jornada,
el proyecto con sus territorios y el enlace de la zona escrita antes. Todos los nombres son ficticios."""
import pytest

from apps.actividades.models import Actividad, ActividadTerritorio
from apps.proyectos.models import Proyecto, ProyectoTerritorio
from apps.proyectos.zona import vincular_zonas
from apps.territorio.models import Comuna, Sector, SectorAlias

pytestmark = pytest.mark.django_db


@pytest.fixture
def otra(comuna):
    return Comuna.objects.create(provincia=comuna.provincia, codigo="99002", nombre="Comuna Inventada")


def filas(*elegidas, inicial=0):
    """Datos de la sección «¿Dónde?»: una fila por diccionario ({"region": …, "comuna": …, "sector": …})."""
    datos = {"donde-TOTAL_FORMS": str(len(elegidas)), "donde-INITIAL_FORMS": str(inicial), "donde-MIN_NUM_FORMS": "0", "donde-MAX_NUM_FORMS": "20"}
    for i, fila in enumerate(elegidas):
        datos.update({f"donde-{i}-{k}": v.pk for k, v in fila.items()})
    return datos


def zonas(registro):
    return {(t.nivel, t.territorio.pk, t.vigente) for t in registro.territorios.all()}


def test_crear_actividad_con_dos_comunas_y_un_sector(cg, comuna, otra):
    villa = Sector.objects.create(comuna=comuna, nombre="Villa Ficticia", tipo="villa")
    html = cg.get("/actividades/nueva").content.decode()
    assert "¿Dónde se realiza o a quién va dirigida?" in html and 'name="donde-TOTAL_FORMS"' in html and "data-agregar-fila" in html
    assert '<details class="fche-bloque fche-bloque--plegable">' in html and "<summary class=\"fche-bloque__titulo\">Detalles</summary>" in html
    region = comuna.provincia.region
    datos = {"nombre": "Taller en tres lugares", **filas({"region": region, "comuna": comuna}, {"comuna": otra}, {"region": region, "comuna": comuna, "sector": villa},
                                                          {"comuna": otra}, {})}
    r = cg.post("/actividades/nueva", datos)
    assert r.status_code == 302
    a = Actividad.objects.get(nombre="Taller en tres lugares")
    # se guarda el nivel más preciso de cada fila; la comuna repetida y la fila vacía no suman filas
    assert zonas(a) == {("comuna", comuna.pk, True), ("comuna", otra.pk, True), ("sector", villa.pk, True)}
    # y aparece al filtrar el listado por la comuna del sector
    assert "Taller en tres lugares" in cg.get(f"/actividades?comuna={comuna.pk}").content.decode()


def test_editar_sin_tocar_conserva_y_quitar_deja_no_vigente(cg, actividad, comuna, otra):
    t1 = ActividadTerritorio.objects.create(actividad=actividad, comuna=comuna)
    ActividadTerritorio.objects.create(actividad=actividad, comuna=otra)
    html = cg.get(f"/actividades/{actividad.pk}/editar").content.decode()
    assert "Ya indicado" in html and "Comuna: Comuna Inventada" in html and 'name="donde-quitar"' in html
    base = {"nombre": actividad.nombre, **filas({})}
    assert cg.post(f"/actividades/{actividad.pk}/editar", base).status_code == 302
    assert zonas(actividad) == {("comuna", comuna.pk, True), ("comuna", otra.pk, True)}
    # «Quitar» la deja no vigente (no se borra); volver a elegirla la reactiva sin repetirla
    cg.post(f"/actividades/{actividad.pk}/editar", {**base, "donde-quitar": t1.pk})
    assert zonas(actividad) == {("comuna", comuna.pk, False), ("comuna", otra.pk, True)}
    cg.post(f"/actividades/{actividad.pk}/editar", {"nombre": actividad.nombre, **filas({"comuna": comuna})})
    assert zonas(actividad) == {("comuna", comuna.pk, True), ("comuna", otra.pk, True)} and actividad.territorios.count() == 2


def test_sin_javascript_otro_territorio_no_guarda_y_la_jornada_prellena(cg, crear_actividad, comuna, otra):
    jornada = crear_actividad("Jornada ficticia")
    ActividadTerritorio.objects.create(actividad=jornada, comuna=comuna)
    ActividadTerritorio.objects.create(actividad=jornada, comuna=otra)
    r = cg.get(f"/actividades/nueva?padre={jornada.pk}")
    filas_iniciales = r.context["form"].destinos.forms
    assert [f.initial.get("comuna") for f in filas_iniciales[:2]] == [comuna.pk, otra.pk] and len(filas_iniciales) == 3
    r = cg.post("/actividades/nueva", {"nombre": "Charla de la jornada", **filas({"comuna": comuna}), "donde-_otra_fila": "1"})
    assert r.status_code == 200 and not Actividad.objects.filter(nombre="Charla de la jornada").exists()
    assert len(r.context["form"].destinos.forms) == 2 and 'name="donde-1-comuna"' in r.content.decode()


def test_editar_es_atomico(cg, actividad, comuna, monkeypatch):
    def falla(*a, **kw):
        raise RuntimeError("falla simulada al guardar los territorios")

    monkeypatch.setattr("apps.territorio.destinos.DestinosMixin.guardar_destinos", falla)
    with pytest.raises(RuntimeError):
        cg.post(f"/actividades/{actividad.pk}/editar", {"nombre": "Nombre a medias", **filas({"comuna": comuna})})
    actividad.refresh_from_db()
    assert actividad.nombre != "Nombre a medias"


def test_proyecto_con_territorios_y_su_resumen(cg, comuna, otra):
    villa = Sector.objects.create(comuna=otra, nombre="Villa Inventada", tipo="villa")
    html = cg.get("/proyectos/nuevo").content.decode()
    assert "¿Dónde se desarrolla o a quién va dirigido?" in html and "Zona (texto anterior)" not in html
    r = cg.post("/proyectos/nuevo", {"nombre": "Proyecto ficticio", "estado": "preparacion", **filas({"comuna": comuna}, {"comuna": otra, "sector": villa})})
    assert r.status_code == 302
    p = Proyecto.objects.get(nombre="Proyecto ficticio")
    assert zonas(p) == {("comuna", comuna.pk, True), ("sector", villa.pk, True)}
    resumen = cg.get(f"{p.get_absolute_url()}?tab=resumen").content.decode()
    assert f'href="{comuna.get_absolute_url()}">Comuna: Comuna Ficticia</a>' in resumen and "Sector: Villa Inventada (Comuna Inventada)" in resumen
    assert "Comuna Ficticia · Villa Inventada" in cg.get("/proyectos").content.decode()
    assert "Proyecto ficticio" in cg.get(f"/buscar?tipo=proyecto&zona={otra.pk}").content.decode()  # por el sector de la comuna


def test_zona_escrita_se_enlaza_solo_si_coincide_con_uno(comuna, otra):
    Sector.objects.create(comuna=comuna, nombre="Centro", tipo="sector")
    Sector.objects.create(comuna=otra, nombre="Centro", tipo="sector")
    aromos = Sector.objects.create(comuna=otra, nombre="Villa Los Aromos", tipo="villa")
    SectorAlias.objects.create(sector=aromos, nombre="Los Aromos")
    unico = Proyecto.objects.create(nombre="Uno", zona="  comuna ficticía ")
    alias = Proyecto.objects.create(nombre="Dos", zona="LOS AROMOS")
    ambiguo = Proyecto.objects.create(nombre="Tres", zona="Centro")
    sin = Proyecto.objects.create(nombre="Cuatro", zona="Comuna Ficticia, Centro")
    args = (Proyecto, ProyectoTerritorio, Comuna, Sector, SectorAlias)
    assert len(vincular_zonas(*args)) == 2
    assert zonas(unico) == {("comuna", comuna.pk, True)} and zonas(alias) == {("sector", aromos.pk, True)}
    assert not ambiguo.territorios.exists() and not sin.territorios.exists()
    unico.refresh_from_db()
    assert unico.zona == "  comuna ficticía "  # el texto no se borra
    assert vincular_zonas(*args) == [] and ProyectoTerritorio.objects.count() == 2  # se puede repetir sin duplicar
    assert Proyecto.objects.get(pk=unico.pk).zona_resumen == "Comuna Ficticia"  # con territorio, se muestra el territorio

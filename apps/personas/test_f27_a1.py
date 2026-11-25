"""F27 A1: catálogos con descripción, vínculo con o sin cargo y relación precisa con un lugar. Datos ficticios."""
import importlib
import json
import re

import pytest
from django.apps import apps as django_apps

from apps.lugares.models import Lugar
from apps.nucleo.models import RelacionLugar, RolOrganizacion
from apps.organizaciones.models import Organizacion
from apps.personas.models import PersonaLugar, PersonaOrganizacion
from apps.personas.vinculos import cargos_y_vinculos, vincular

pytestmark = pytest.mark.django_db
MIGRACION = importlib.import_module("apps.personas.migrations.0009_f27_tipo_cargo_y_relacion_lugar")


@pytest.fixture
def junta(tipo_org):
    return Organizacion.objects.create(nombre="Junta Ficticia F27", tipo=tipo_org("junta_de_vecinos_o_comite"))


def rol(codigo):
    return RolOrganizacion.objects.get(codigo=codigo)


def relacion(codigo):
    return RelacionLugar.objects.get(codigo=codigo)


# --- 1. Descripción en los catálogos ------------------------------------------------------------------
def test_descripcion_visible_bajo_la_lista_y_ayuda_plegable(cg, persona):
    html = cg.get(f"/personas/{persona.pk}/vinculos/nuevo").content.decode()
    dirigente = rol("dirigente")
    # cada opción lleva su descripción y bajo la lista está el bloque que la muestra (con JavaScript)
    assert re.search(rf'<option value="{dirigente.pk}" data-descripcion="Integra la directiva', html)
    assert 'data-descripcion-de="id_rol"' in html
    # sin JavaScript: todas las descripciones en una ayuda plegable
    assert '<details class="fche-descripciones"><summary>¿Qué significa cada opción?</summary>' in html
    assert "<dt>Vecino o vecina</dt><dd>Vive en el territorio de la organización" in html


def test_descripcion_se_edita_y_se_ve_en_catalogos(cg):
    r = cg.get("/administracion/catalogos/rol-organizacion/")
    html = r.content.decode()
    assert 'name="descripcion"' in html and "Representa legalmente a la organización" in html and "Admite cargo" in html
    tipo = django_apps.get_model("nucleo", "TipoActividad").objects.first()
    r = cg.post(f"/administracion/catalogos/tipo-actividad/{tipo.pk}/editar",
                {"nombre": tipo.nombre, "descripcion": "Encuentro breve de prueba.", "orden": tipo.orden, "activo": "on"})
    assert r.status_code == 302
    tipo.refresh_from_db()
    assert tipo.descripcion == "Encuentro breve de prueba."
    assert "Encuentro breve de prueba." in cg.get("/administracion/catalogos/tipo-actividad/").content.decode()


def test_catalogo_relacion_lugar_en_catalogos(cg):
    html = cg.get("/administracion/catalogos/").content.decode()
    assert "Relaciones con un lugar" in html
    html = cg.get("/administracion/catalogos/relacion-lugar/").content.decode()
    assert "Hace su práctica ahí" in html and "Ámbito" in html and "Estudio" in html


# --- 2. Vínculo con o sin cargo --------------------------------------------------------------------------
def test_roles_ampliados_con_y_sin_cargo():
    sin = set(RolOrganizacion.objects.filter(con_cargo=False).values_list("codigo", flat=True))
    assert sin == {"estudiante", "egresado", "practicante", "vecino", "apoderado", "beneficiario"}
    for codigo in ("dirigente", "autoridad", "representante_legal", "docente", "funcionario", "socio", "voluntario", "contacto", "otro"):
        assert rol(codigo).con_cargo and rol(codigo).descripcion


def test_tipo_de_cargo_opcional_condicionado_y_explicado(cg, junta):
    html = cg.get(f"/organizaciones/{junta.pk}/personas/nuevo").content.decode()
    select = re.search(r'<select name="tipo_cargo"[^>]*>', html).group(0)
    assert 'data-mostrar-si-campo="rol"' in select and 'data-mostrar-si-con-dato="cargo"' in select and "required" not in select
    valores = re.search(r'data-mostrar-si-valor="([0-9 ]+)"', select).group(1).split()
    assert str(rol("dirigente").pk) in valores and str(rol("vecino").pk) not in valores
    assert '<option value="" selected>Sin cargo</option>' in html  # ya no viene «Funcional» por defecto
    assert "<dt>Funcional</dt><dd>Trabaja, coordina o tiene una responsabilidad en un área" in html


def test_rol_sin_cargo_deja_tipo_vacio_aunque_llegue_funcional(cg, persona, junta):
    r = cg.post(f"/organizaciones/{junta.pk}/personas/nuevo", {"persona": persona.pk, "rol": rol("vecino").pk, "tipo_cargo": "funcional"})
    assert r.status_code == 302
    v = PersonaOrganizacion.objects.get(persona=persona, organizacion=junta)
    assert v.tipo_cargo == "" and v.rol.codigo == "vecino"
    # con un cargo escrito, el tipo se conserva aunque el rol no admita cargo
    r = cg.post(f"/personas/{persona.pk}/vinculos/{v.pk}/editar", {"organizacion": junta.pk, "rol": rol("vecino").pk, "cargo": "Delegada de pasaje",
                                                                     "tipo_cargo": "funcional"})
    assert r.status_code == 302
    v.refresh_from_db()
    assert v.tipo_cargo == "funcional"


def test_rol_con_cargo_permite_tipo_y_no_lo_exige(cg, persona, junta):
    r = cg.post(f"/personas/{persona.pk}/vinculos/nuevo", {"organizacion": junta.pk, "rol": rol("dirigente").pk, "cargo": "Presidenta",
                                                            "tipo_cargo": "directorio"})
    assert r.status_code == 302
    assert PersonaOrganizacion.objects.get(cargo="Presidenta").tipo_cargo == "directorio"
    r = cg.post(f"/personas/{persona.pk}/vinculos/nuevo", {"organizacion": junta.pk, "rol": rol("autoridad").pk, "tipo_cargo": "autoridad",
                                                            "fecha_inicio": "2020-01-01", "fecha_termino": "2020-12-31"})
    assert r.status_code == 302  # sin cargo escrito, pero el rol admite cargo: el tipo se conserva
    assert PersonaOrganizacion.objects.get(rol__codigo="autoridad").tipo_cargo == "autoridad"
    r = cg.post(f"/personas/{persona.pk}/vinculos/nuevo", {"organizacion": junta.pk, "rol": rol("funcionario").pk, "cargo": "Encargada"})
    assert r.status_code == 302  # «Sin cargo» es válido: no es obligatorio
    assert PersonaOrganizacion.objects.get(cargo="Encargada").tipo_cargo == ""


def test_migracion_limpia_solo_rol_sin_cargo_y_sin_cargo_escrito(persona, junta):
    crear = PersonaOrganizacion.objects.create
    a = crear(persona=persona, organizacion=junta, rol=rol("estudiante"))
    b = crear(persona=persona, organizacion=junta, rol=rol("vecino"), cargo="Delegada", tipo_cargo="funcional")
    c = crear(persona=persona, organizacion=junta, rol=rol("dirigente"), tipo_cargo="directorio")
    d = crear(persona=persona, organizacion=junta)
    # datos anteriores a F27: «Funcional» por defecto (se escribe sin pasar por save, como estaban en la base)
    PersonaOrganizacion.objects.filter(pk__in=[a.pk, d.pk]).update(tipo_cargo="funcional")
    assert MIGRACION.limpiar_tipo_cargo(django_apps, None) == 1
    tipos = dict(PersonaOrganizacion.objects.values_list("pk", "tipo_cargo"))
    assert tipos == {a.pk: "", b.pk: "funcional", c.pk: "directorio", d.pk: "funcional"}


def test_vincular_sigue_sin_duplicar_y_sin_funcional_por_defecto(persona, junta):
    v1 = vincular(persona, organizacion=junta, rol="vecino")["vinculo"]
    v2 = vincular(persona, organizacion=junta, rol=rol("vecino"))["vinculo"]
    assert v1.pk == v2.pk and PersonaOrganizacion.objects.filter(persona=persona).count() == 1
    assert v1.tipo_cargo == ""
    v3 = vincular(persona, organizacion=junta, cargo="Presidenta", rol="dirigente")["vinculo"]
    assert v3.tipo_cargo == "directorio"
    assert vincular(persona, organizacion=junta, rol="vecino", tipo_cargo="funcional")["vinculo"].tipo_cargo == ""


# --- 3. Relación con un lugar ------------------------------------------------------------------------------
def test_catalogo_relacion_lugar_sembrado_por_ambito():
    por_ambito = {}
    for r in RelacionLugar.objects.all():
        por_ambito.setdefault(r.ambito, []).append(r.codigo)
        assert r.descripcion
    assert por_ambito["estudio"] == ["estudia", "practica"]
    assert set(por_ambito["trabajo"]) == {"trabaja", "presta_servicios", "dirige"}
    assert set(por_ambito["residencia"]) == {"vive", "vive_cerca"}
    assert len(por_ambito["comunidad"]) == 4 and len(por_ambito["otra"]) == 3


def test_migracion_rellena_relacion_desde_el_texto(persona, lugar):
    pl = PersonaLugar.objects.create(persona=persona, lugar=lugar, relacion="trabaja")
    assert pl.tipo_relacion_id is None
    assert MIGRACION.rellenar_tipo_relacion(django_apps, None) == 1
    pl.refresh_from_db()
    assert pl.tipo_relacion.codigo == "trabaja" and pl.relacion_texto == "Trabaja ahí"


def test_formulario_de_lugar_con_buscador_y_grupos(cg, persona):
    html = cg.get(f"/personas/{persona.pk}/lugares/nuevo").content.decode()
    select = re.search(r'<select name="lugar"[^>]*>', html).group(0)
    assert 'data-selector="1"' in select and "/lugares/opciones" in select and "crear=1" in select
    assert 'class="form-select"' in select  # mismo ancho y alto que los demás campos
    assert '<div class="fche-selector">' in html
    assert '<optgroup label="Estudio">' in html and '<optgroup label="Residencia">' in html
    assert 'name="relacion"' not in html and 'data-descripcion="Hace su práctica profesional' in html


def test_opciones_y_crear_lugar_desde_el_buscador(cg, lugar, comuna):
    html = cg.get("/lugares/opciones?crear=1&q=Sala").content.decode()
    assert "Sala Ficticia" in html and "+ Crear lugar" in html
    tipo = lugar.tipo
    # mismo nombre en la misma comuna: se avisa antes de crear
    r = cg.post("/lugares/crear-desde-buscador", {"campo": "id_lugar", "rapida-nombre": "Sala Ficticia", "rapida-tipo": tipo.pk, "rapida-comuna": comuna.pk})
    assert "Este lugar podría ya existir." in r.content.decode() and Lugar.objects.count() == 1
    r = cg.post("/lugares/crear-desde-buscador", {"campo": "id_lugar", "rapida-nombre": "Gimnasio Inventado", "rapida-tipo": tipo.pk,
                                                  "rapida-comuna": comuna.pk})
    nuevo = Lugar.objects.get(nombre="Gimnasio Inventado")
    assert json.loads(r["HX-Trigger"])["fche:elegido"] == {"campo": "id_lugar", "valor": nuevo.pk, "texto": "Gimnasio Inventado",
                                                           "aviso": "Lugar creado y elegido. Completa su dirección y condiciones en su ficha cuando puedas."}
    assert nuevo.direccion.comuna == comuna


def test_guardar_relacion_del_catalogo_y_mostrarla(cg, persona, lugar):
    for codigo in ("trabaja", "dirige"):  # dos relaciones del mismo ámbito con el mismo lugar ya no chocan
        r = cg.post(f"/personas/{persona.pk}/lugares/nuevo", {"lugar": lugar.pk, "tipo_relacion": relacion(codigo).pk})
        assert r.status_code == 302
    filas = PersonaLugar.objects.filter(persona=persona).order_by("pk")
    assert [(f.tipo_relacion.codigo, f.relacion) for f in filas] == [("trabaja", "trabaja"), ("dirige", "trabaja")]
    lugares = dict(cargos_y_vinculos(persona))["Lugares"]
    assert {f["rol"] for f in lugares} == {"Trabaja ahí", "Dirige o administra el lugar"}
    assert "Dirige o administra el lugar" in cg.get(f"/lugares/{lugar.pk}?tab=personas").content.decode()
    # la misma relación dos veces sí se rechaza
    r = cg.post(f"/personas/{persona.pk}/lugares/nuevo", {"lugar": lugar.pk, "tipo_relacion": relacion("dirige").pk})
    assert r.status_code == 200 and PersonaLugar.objects.filter(persona=persona).count() == 2


def test_relacion_es_obligatoria(cg, persona, lugar):
    r = cg.post(f"/personas/{persona.pk}/lugares/nuevo", {"lugar": lugar.pk})
    assert r.status_code == 200 and not PersonaLugar.objects.exists()

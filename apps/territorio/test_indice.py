"""F23, Task 4: índice «Dónde trabajamos» y página de región. Todos los datos son ficticios."""
import re
from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.actividades.servicios import programar
from apps.comunidades.models import Comunidad
from apps.lugares.models import Lugar
from apps.nucleo.models import TipoLugar, TipoOrganizacion
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona, PersonaDireccion
from apps.territorio.models import Comuna, Direccion, Provincia, Region

pytestmark = pytest.mark.django_db

HOY = timezone.localdate()


# ---------- ayudas ----------

def _otra_comuna(comuna, codigo="99002", nombre="Otra Comuna"):
    return Comuna.objects.create(provincia=comuna.provincia, codigo=codigo, nombre=nombre)


def _dir(comuna):
    return Direccion.objects.create(calle="Calle Inventada", numero="1", comuna=comuna)


def _sala(comuna, nombre="Sala Ficticia"):
    return Lugar.objects.create(nombre=nombre, tipo=TipoLugar.objects.get(codigo="sala"), direccion=_dir(comuna), capacidad=20)


def _org(nombre, comuna, tipo="junta_de_vecinos_o_comite"):
    return Organizacion.objects.create(nombre=nombre, tipo=TipoOrganizacion.objects.get(codigo=tipo), direccion=_dir(comuna))


def _reside(comuna, nombres="Vecino"):
    persona = Persona.objects.create(nombres=nombres, apellido_paterno="Ficticio")
    return PersonaDireccion.objects.create(persona=persona, direccion=_dir(comuna), tipo="residencia", vigente=True)


def _con_actividad(crear_actividad, gestor, comuna, dias=-10, nombre="Taller ficticio"):
    a = crear_actividad(nombre)
    programar(a, gestor, HOY + timedelta(days=dias), None, None, _sala(comuna, f"Sala de {nombre}"), None)
    return a


def _tarjetas(html):
    """`{nombre de comuna: html de su tarjeta}` dentro de la sección «Comunas con presencia»."""
    seccion = html.split("Comunas con presencia", 1)[1].split("Todas las regiones", 1)[0]
    return re.findall(r'<a class="fche-mosaico__item[^"]*" href="(/territorio/comuna/[^"]+)">(.*?)</a>', seccion, flags=re.S)


def _texto(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _usuario_con(*permisos):
    u = User.objects.create_user("lector_territorio", password="clave-ficticia-123")
    for p in permisos:
        app, codigo = p.split(".")
        u.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codigo))
    c = Client()
    c.force_login(u)
    return c


# ---------- índice ----------

def test_indice_muestra_comunas_con_presencia_primero(cg, comuna, crear_actividad, gestor):
    con_actividad = _otra_comuna(comuna, "99002", "Aldea Activa Ficticia")
    sin_nada = _otra_comuna(comuna, "99003", "Caleta Vacía Ficticia")
    Comunidad.objects.create(nombre="Comunidad uno", comuna=comuna)
    Comunidad.objects.create(nombre="Comunidad dos", comuna=comuna)
    _org("Junta ficticia", comuna)
    _reside(comuna)
    _con_actividad(crear_actividad, gestor, con_actividad)

    r = cg.get("/territorio")
    html = r.content.decode()
    assert r.status_code == 200
    # la sección va antes del mosaico de regiones, y la comuna con actividad reciente antes que la que solo tiene registros
    assert html.index("Comunas con presencia") < html.index("Todas las regiones")
    tarjetas = _tarjetas(html)
    assert [t[0] for t in tarjetas] == [con_actividad.get_absolute_url(), comuna.get_absolute_url()]
    assert "Caleta Vacía Ficticia" not in html.split("Todas las regiones", 1)[0]  # sin nada, no aparece
    assert sin_nada.get_absolute_url() not in html

    activa, registros = (_texto(t[1]) for t in tarjetas)
    assert "Aldea Activa Ficticia" in activa and "Región de Prueba" in activa and "1 actividad" in activa
    assert "comunidad" not in activa  # los ceros no se muestran
    assert "2 comunidades" in registros and "1 organización" in registros and "1 residente" in registros
    assert "actividad" not in registros
    # el mosaico de regiones se mantiene
    assert "Región de Prueba" in html.split("Todas las regiones", 1)[1] and "/territorio/region/" in html


def test_tarjeta_dice_en_total_cuando_la_actividad_no_es_de_los_ultimos_12_meses(cg, comuna, crear_actividad, gestor):
    """Una actividad futura (la que queda tras «+ Actividad») o una muy antigua no se presentan como «fuera de los últimos 12 meses»."""
    futura, antigua = _otra_comuna(comuna, "99002", "Aldea Futura Ficticia"), _otra_comuna(comuna, "99003", "Aldea Antigua Ficticia")
    _con_actividad(crear_actividad, gestor, futura, 20, "Taller futuro")
    _con_actividad(crear_actividad, gestor, antigua, -400, "Taller antiguo")
    tarjetas = {url: _texto(contenido) for url, contenido in _tarjetas(cg.get("/territorio").content.decode())}
    for comuna_con_actividad in (futura, antigua):
        texto = tarjetas[comuna_con_actividad.get_absolute_url()]
        assert "1 actividad en total" in texto and "fuera de los últimos" not in texto, texto


def test_indice_busqueda_de_comuna_se_mantiene(cg, comuna):
    Comunidad.objects.create(nombre="Comunidad uno", comuna=comuna)
    html = cg.get("/territorio?q=ficticia").content.decode()
    assert "Comuna Ficticia" in html and "Comunas con presencia" not in html and "Todas las regiones" not in html
    assert "Sin resultados" in cg.get("/territorio?q=zzzz").content.decode()


def test_indice_vacio_ofrece_acciones(cg, comuna):
    html = cg.get("/territorio").content.decode()
    assert "Aún no hay trabajo registrado" in html
    assert 'href="/comunidades/nueva"' in html and 'href="/organizaciones/nueva"' in html
    assert "+ Comunidad" in html and "+ Organización" in html
    assert "Todas las regiones" in html and "Región de Prueba" in html  # el mosaico sigue

    # sin permiso de crear, el vacío explica pero no ofrece
    solo_lectura = _usuario_con("territorio.view_comuna")
    html = solo_lectura.get("/territorio").content.decode()
    assert "Aún no hay trabajo registrado" in html
    assert "/comunidades/nueva" not in html and "/organizaciones/nueva" not in html


def test_indice_sin_territorio_cargado_mantiene_su_mensaje(cg):
    html = cg.get("/territorio").content.decode()
    assert "El territorio aún no se ha cargado" in html
    assert "Aún no hay trabajo registrado" not in html and "Comunas con presencia" not in html


def test_indice_consultas_no_crecen_con_las_comunas(cg, comuna, crear_actividad, gestor):
    def medir():
        with CaptureQueriesContext(connection) as ctx:
            r = cg.get("/territorio")
        assert r.status_code == 200
        return len(ctx), len(r.context["presencia"])

    Comunidad.objects.create(nombre="Comunidad base", comuna=comuna)
    cg.get("/territorio")  # calienta la sesión y los catálogos
    uno, filas_uno = medir()
    for i in range(24):
        otra = _otra_comuna(comuna, f"98{i:03d}", f"Comuna {i:02d} Ficticia")
        Comunidad.objects.create(nombre=f"Comunidad {i}", comuna=otra)
        _org(f"Junta {i}", otra)
        _reside(otra, f"Vecino{i}")
        _con_actividad(crear_actividad, gestor, otra, -i, f"Taller {i}")
    veinticinco, filas_25 = medir()
    assert (filas_uno, filas_25) == (1, 25)
    assert veinticinco - uno <= 2, (uno, veinticinco)


# ---------- región ----------

def _otra_region(codigo, nombre):
    region = Region.objects.create(codigo=codigo, nombre=nombre)
    provincia = Provincia.objects.create(region=region, codigo=f"{codigo}0", nombre=f"Provincia de {nombre}")
    return region, Comuna.objects.create(provincia=provincia, codigo=f"{codigo}001", nombre=f"Comuna de {nombre}")


def test_region_lista_sus_comunas_con_presencia(cg, comuna):
    vecina = _otra_comuna(comuna, "99002", "Vecina Sin Nada Ficticia")
    _, ajena = _otra_region("98", "Región Ajena")
    Comunidad.objects.create(nombre="Comunidad uno", comuna=comuna)
    Comunidad.objects.create(nombre="Comunidad ajena", comuna=ajena)

    html = cg.get(comuna.provincia.region.get_absolute_url()).content.decode()
    assert "Comunas con presencia" in html
    assert html.index("Comunas con presencia") < html.index("Provincia de Prueba")  # las tarjetas van antes de la lista por provincia
    tarjetas = re.findall(r'<a class="fche-mosaico__item[^"]*" href="(/territorio/comuna/[^"]+)">(.*?)</a>', html, flags=re.S)
    assert [t[0] for t in tarjetas] == [comuna.get_absolute_url()]  # ni la comuna sin nada ni la de otra región
    assert "1 comunidad" in _texto(tarjetas[0][1])
    assert vecina.nombre in html  # la lista por provincia sigue mostrando todas las comunas de la región


def test_region_sin_presencia_solo_muestra_sus_provincias(cg, comuna):
    Comunidad.objects.create(nombre="Comunidad uno", comuna=comuna)  # presencia en otra región
    quieta, comuna_quieta = _otra_region("97", "Región Quieta")
    html = cg.get(quieta.get_absolute_url()).content.decode()
    assert "Comunas con presencia" not in html and "Aún no hay trabajo registrado" not in html
    assert "Provincia de Región Quieta" in html and comuna_quieta.nombre in html

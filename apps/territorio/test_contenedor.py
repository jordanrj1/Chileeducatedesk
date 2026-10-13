"""Ficha de comuna y de sector como contenedor (F23): resumen, personas, alcance y consultas acotadas. Datos ficticios."""
import re
from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.actividades.alcance import alcance
from apps.actividades.models import ActividadTerritorio, Participacion, SesionActividad
from apps.actividades.servicios import programar
from apps.comunidades.models import Comunidad, ComunidadMiembro
from apps.lugares.models import Lugar
from apps.nucleo.models import EstadoParticipacion, PerfilPersona, RolParticipacion, TipoContacto, TipoLugar, TipoOrganizacion
from apps.nucleo.utilidades import calcular_dv, formatear_rut
from apps.organizaciones.models import Organizacion
from apps.personas.models import ContactoEmergencia, Contacto, PerfilSensible, Persona, PersonaDireccion
from apps.territorio import consultas
from apps.territorio.models import Comuna, Direccion, Sector

pytestmark = pytest.mark.django_db

HOY = timezone.localdate()
INDICADORES = {"comunidades", "organizaciones", "personas", "lugares", "actividades", "alcance"}
PESTANAS_COMUNA = ["resumen", "sectores", "comunidades", "organizaciones", "personas", "lugares", "actividades", "alcance"]


# ---------- ayudas ----------

def _otra_comuna(comuna, codigo="99002", nombre="Otra Comuna"):
    return Comuna.objects.create(provincia=comuna.provincia, codigo=codigo, nombre=nombre)


def _dir(comuna, sector=None):
    return Direccion.objects.create(calle="Calle Inventada", numero="1", comuna=comuna, sector=sector)


def _sector(comuna, nombre, padre=None, tipo="sector"):
    return Sector.objects.create(comuna=comuna, nombre=nombre, tipo=tipo, sector_padre=padre)


def _org(nombre, tipo, direccion=None, **kw):
    return Organizacion.objects.create(nombre=nombre, tipo=TipoOrganizacion.objects.get(codigo=tipo), direccion=direccion, **kw)


def _lugar(nombre, direccion, **kw):
    return Lugar.objects.create(nombre=nombre, tipo=TipoLugar.objects.get(codigo="sala"), direccion=direccion, capacidad=20, **kw)


def _reside(persona, direccion):
    return PersonaDireccion.objects.create(persona=persona, direccion=direccion, tipo="residencia", vigente=True)


def _programada(crear_actividad, gestor, lugar, dias, nombre):
    a = crear_actividad(nombre)
    programar(a, gestor, HOY + timedelta(days=dias), None, None, lugar, None)
    return a


def _participa(actividad, persona, rol="participante", asistencia=True):
    return Participacion.objects.create(
        actividad=actividad, persona=persona, rol=RolParticipacion.objects.get(codigo=rol),
        estado=EstadoParticipacion.objects.get(codigo="asistio" if asistencia else "confirmado"), asistencia=asistencia,
    )


def _enlaces_de_indicadores(html):
    return re.findall(r'<a class="fche-kpi[^"]*" href="\?tab=(\w+)"', html)


# ---------- resumen ----------

def test_comuna_abre_en_resumen_con_indicadores_clicables(cg, comuna, lugar, crear_actividad, crear_persona, gestor):
    sector = _sector(comuna, "Villa Las Araucarias Ficticia", tipo="villa")
    Comunidad.objects.create(nombre="Comunidad Los Aromos Ficticia", comuna=comuna, sector=sector)
    _org("Junta Vecinal Ficticia N° 1", "junta_de_vecinos_o_comite", _dir(comuna, sector))
    vecina = crear_persona("Rosa Ficticia")
    _reside(vecina, _dir(comuna, sector))
    pasada = _programada(crear_actividad, gestor, lugar, -10, "Taller de huertos Ficticio")
    _participa(pasada, vecina)
    SesionActividad.objects.create(actividad=pasada, numero=1, fecha=HOY - timedelta(days=10), asistentes_sin_registro=12)
    _programada(crear_actividad, gestor, lugar, 5, "Charla de reciclaje Ficticia")

    r = cg.get(comuna.get_absolute_url())
    assert r.status_code == 200
    html = r.content.decode()
    assert r.context["pestana"] == "resumen"
    assert [c for c, _ in r.context["pestanas"]] == PESTANAS_COMUNA

    # cada indicador lleva a su pestaña
    assert set(_enlaces_de_indicadores(html)) == INDICADORES
    resumen = r.context["resumen"]
    assert (resumen["comunidades"], resumen["organizaciones"], resumen["personas"], resumen["lugares"]) == (1, 1, 1, 1)
    assert (resumen["actividades_12m"], resumen["actividades_total"]) == (1, 2)
    assert r.context["total_alcanzado"] == 13  # 1 asistente registrada + 12 sin registro
    assert ">13<" in html

    # organizaciones por tipo, tabla por sector con «Sin sector», próximas y minutas
    assert "Junta de vecinos o comité" in html and "Junta Vecinal Ficticia N° 1" in html
    assert "Villa Las Araucarias Ficticia" in html and "Sin sector" in html
    assert "Charla de reciclaje Ficticia" in html  # próxima (en 5 días)
    assert "Sesión 1" in html and "Taller de huertos Ficticio" in html  # última minuta

    # cabecera: región › provincia, municipalidad por registrar y acciones con la comuna elegida
    assert "Región de Prueba" in html and "Provincia de Prueba" in html
    assert f"/organizaciones/nueva?comuna={comuna.pk}&amp;tipo=municipalidad" in html
    for url in ("/comunidades/nueva", "/organizaciones/nueva", "/lugares/nuevo", "/actividades/nueva"):
        assert f'href="{url}?comuna={comuna.pk}"' in html, url

    # con municipalidad registrada, la cabecera enlaza a ella en vez de ofrecer registrarla
    muni = _org("Municipalidad Ficticia", "municipalidad", comuna_municipal=comuna)
    html = cg.get(comuna.get_absolute_url()).content.decode()
    assert muni.get_absolute_url() in html and "tipo=municipalidad" not in html


def test_comuna_vacia_ensena_que_hacer(cg, comuna):
    r = cg.get(comuna.get_absolute_url())
    html = r.content.decode()
    assert r.status_code == 200 and r.context["pestana"] == "resumen"
    assert "Aún no hay trabajo registrado" in html
    assert f'href="/comunidades/nueva?comuna={comuna.pk}"' in html


# ---------- personas ----------

def test_pestana_personas_separa_residentes_y_no_muestra_sensibles(cg, comuna, crear_persona):
    otra = _otra_comuna(comuna)
    vecino = PerfilPersona.objects.get(codigo="vecino_o_vecina_de_la_comunidad")
    comunidad = Comunidad.objects.create(nombre="Comunidad El Litre Ficticia", comuna=comuna)
    inactiva = Comunidad.objects.create(nombre="Comunidad Inactiva Ficticia", comuna=comuna, activo=False)
    ajena = Comunidad.objects.create(nombre="Comunidad de Otra Comuna", comuna=otra)

    residente = crear_persona("Marta Residente", rut_numero=12345678, rut_dv=calcular_dv(12345678))
    residente.perfiles.add(vecino)
    _reside(residente, _dir(comuna))
    ComunidadMiembro.objects.create(comunidad=comunidad, persona=residente)
    Contacto.objects.create(persona=residente, tipo=TipoContacto.objects.get(codigo="correo"), valor="marta.residente@ejemplo.invalid")
    PerfilSensible.objects.create(persona=residente, alergias="Alergia ficticia reservada", condiciones_salud="Condición ficticia reservada")
    ContactoEmergencia.objects.create(persona=residente, nombre="Contacto Emergencia Ficticio", telefono="+56 9 0000 0000")

    visitante = crear_persona("Pedro Visitante")
    _reside(visitante, _dir(otra))
    ComunidadMiembro.objects.create(comunidad=comunidad, persona=visitante)
    ex_integrante = crear_persona("Luis Exintegrante")
    ComunidadMiembro.objects.create(comunidad=comunidad, persona=ex_integrante, vigente=False)
    de_inactiva = crear_persona("Elena Deinactiva")
    ComunidadMiembro.objects.create(comunidad=inactiva, persona=de_inactiva)
    de_ajena = crear_persona("Jorge Deajena")
    ComunidadMiembro.objects.create(comunidad=ajena, persona=de_ajena)

    r = cg.get(f"{comuna.get_absolute_url()}?tab=personas")
    assert r.status_code == 200 and r.context["pestana"] == "personas"
    assert list(r.context["residentes"]) == [residente]
    assert list(r.context["integrantes_no_residentes"]) == [visitante]

    html = r.content.decode()
    assert html.index("Marta Residente") < html.index("no residen") < html.index("Pedro Visitante")
    assert "Vecino o vecina de la comunidad" in html and "Comunidad El Litre Ficticia" in html
    for ausente in ("Luis Exintegrante", "Elena Deinactiva", "Jorge Deajena"):
        assert ausente not in html
    # nada sensible ni de contacto
    for sensible in ("Alergia ficticia reservada", "Condición ficticia reservada", "Contacto Emergencia Ficticio", "marta.residente@ejemplo.invalid",
                     formatear_rut(12345678, calcular_dv(12345678)), "12345678"):
        assert sensible not in html, sensible
    assert f'href="/personas?comuna={comuna.pk}"' in html


def test_pestana_personas_oculta_sin_permiso(comuna, crear_persona):
    u = User.objects.create_user("lector_territorio", email="lector@ejemplo.invalid", password="clave-ficticia-123")
    for codigo in ("view_comuna", "view_sector", "view_comunidad", "view_organizacion", "view_lugar", "view_actividad", "view_participacion"):
        u.user_permissions.add(Permission.objects.get(codename=codigo))
    cliente = Client()
    cliente.force_login(u)
    sector = _sector(comuna, "Villa Oculta Ficticia", tipo="villa")
    _reside(crear_persona("Residente Oculta"), _dir(comuna, sector))

    for ficha in (comuna, sector):
        r = cliente.get(ficha.get_absolute_url())
        html = r.content.decode()
        assert r.status_code == 200
        assert "personas" not in [c for c, _ in r.context["pestanas"]]
        assert "?tab=personas" not in html and "Residente Oculta" not in html
        forzada = cliente.get(f"{ficha.get_absolute_url()}?tab=personas")
        assert forzada.status_code == 200 and forzada.context["pestana"] == "resumen"
        assert "Residente Oculta" not in forzada.content.decode()


# ---------- alcance ----------

def test_alcance_de_la_comuna_coincide_con_servicio(cg, comuna, lugar, crear_actividad, crear_persona, gestor):
    otra = _otra_comuna(comuna)
    sala_otra = _lugar("Sala de Otra Comuna", _dir(otra))
    en_la_sala = _programada(crear_actividad, gestor, lugar, -3, "Taller en la sala")
    _participa(en_la_sala, crear_persona("Tallerista Ficticia"), rol="tallerista")
    _participa(en_la_sala, crear_persona("Vecina Asistente"))
    _participa(en_la_sala, crear_persona("Vecino Ausente"), asistencia=False)
    SesionActividad.objects.create(actividad=en_la_sala, numero=1, fecha=HOY - timedelta(days=3), asistentes_sin_registro=7)
    dirigida = crear_actividad("Operativo dirigido a la comuna")
    ActividadTerritorio.objects.create(actividad=dirigida, comuna=comuna)
    _participa(dirigida, crear_persona("Vecina Dirigida"))
    fuera = _programada(crear_actividad, gestor, sala_otra, -2, "Taller de otra comuna")
    _participa(fuera, crear_persona("Persona de Afuera"))

    r = cg.get(f"{comuna.get_absolute_url()}?tab=alcance")
    assert r.status_code == 200 and r.context["pestana"] == "alcance"
    esperado = alcance(consultas.actividades_de(comuna=comuna))
    assert r.context["alcance"] == esperado
    assert esperado["actividades"] == 2 and esperado["total_alcanzado"] == 3 + 7  # tallerista, vecina y vecina dirigida + 7 sin registro
    assert "Total alcanzado" in r.content.decode()


# ---------- sector ----------

def test_sector_incluye_hijos(cg, comuna, crear_actividad, crear_persona, gestor):
    padre = _sector(comuna, "San Pedro de la Costa Ficticio")
    etapa = _sector(comuna, "Etapa 2", padre, "etapa")
    nieto = _sector(comuna, "Pasaje Interior", etapa, "villa")
    aparte = _sector(comuna, "Villa Aparte Ficticia", tipo="villa")

    Comunidad.objects.create(nombre="Comunidad de la Etapa", comuna=comuna, sector=etapa)
    Comunidad.objects.create(nombre="Comunidad Aparte", comuna=comuna, sector=aparte)
    _org("Junta del Pasaje", "junta_de_vecinos_o_comite", _dir(comuna, nieto))
    _org("Junta Aparte", "junta_de_vecinos_o_comite", _dir(comuna, aparte))
    sala = _lugar("Sede de la Etapa", _dir(comuna, etapa))
    _lugar("Sede Aparte", _dir(comuna, aparte))
    _reside(crear_persona("Nieta Residente"), _dir(comuna, nieto))
    _reside(crear_persona("Vecina Aparte"), _dir(comuna, aparte))
    en_etapa = _programada(crear_actividad, gestor, sala, -4, "Taller en la etapa")
    _participa(en_etapa, crear_persona("Asistente de la Etapa"))
    al_pasaje = crear_actividad("Operativo al pasaje")
    ActividadTerritorio.objects.create(actividad=al_pasaje, sector=nieto)
    ActividadTerritorio.objects.create(actividad=crear_actividad("Operativo aparte"), sector=aparte)

    url = padre.get_absolute_url()
    r = cg.get(url)
    assert r.status_code == 200 and r.context["pestana"] == "resumen"
    claves = [c for c, _ in r.context["pestanas"]]
    assert claves[0] == "resumen" and claves.index("nombres") == claves.index("sectores") + 1
    assert "personas" in claves and "alcance" in claves
    resumen = r.context["resumen"]
    assert (resumen["comunidades"], resumen["organizaciones"], resumen["lugares"], resumen["personas"], resumen["actividades_total"]) == (1, 1, 1, 1, 2)
    assert [f["sector"] for f in resumen["sectores"]] == [padre, etapa, nieto]
    html = r.content.decode()
    assert set(_enlaces_de_indicadores(html)) == INDICADORES
    assert f'href="/actividades/nueva?comuna={comuna.pk}"' in html  # las acciones usan la comuna del sector

    personas = cg.get(f"{url}?tab=personas").content.decode()
    assert "Nieta Residente" in personas and "Vecina Aparte" not in personas
    assert "Junta del Pasaje" in cg.get(f"{url}?tab=organizaciones").content.decode()
    assert "Junta Aparte" not in cg.get(f"{url}?tab=organizaciones").content.decode()
    actividades = cg.get(f"{url}?tab=actividades").content.decode()
    assert "Taller en la etapa" in actividades and "Operativo al pasaje" in actividades and "Operativo aparte" not in actividades
    r = cg.get(f"{url}?tab=alcance")
    assert r.context["alcance"]["actividades"] == 2 and r.context["alcance"]["total_alcanzado"] == 1


# ---------- organizaciones agrupadas ----------

def test_pestana_organizaciones_agrupada_por_tipo(cg, comuna):
    d = _dir(comuna)
    for i in range(3):
        _org(f"Junta {i} Ficticia", "junta_de_vecinos_o_comite", d)
    _org("Colegio Ficticio", "institucion_educativa", d)
    _org("Junta Desactivada Ficticia", "junta_de_vecinos_o_comite", d, activo=False)
    r = cg.get(f"{comuna.get_absolute_url()}?tab=organizaciones")
    grupos = [(tipo.codigo, total, [o.nombre for o in orgs]) for tipo, total, orgs in r.context["grupos_organizaciones"]]
    assert grupos == [("institucion_educativa", 1, ["Colegio Ficticio"]), ("junta_de_vecinos_o_comite", 3, ["Junta 0 Ficticia", "Junta 1 Ficticia", "Junta 2 Ficticia"])]
    assert [o.nombre for o in r.context["organizaciones_inactivas"]] == ["Junta Desactivada Ficticia"]
    html = r.content.decode()
    assert 'id="tipo-junta_de_vecinos_o_comite"' in html
    assert "Organizaciones (4)" in html  # el contador de la pestaña cuenta solo las activas, como el indicador del resumen
    # la desactivada sigue a la vista, aparte y al final: después del último grupo de activas, dentro del grupo atenuado
    assert html.index("Junta 2 Ficticia") < html.index("Organizaciones inactivas (1)") < html.index("Junta Desactivada Ficticia")
    assert html.count("Junta Desactivada Ficticia") == 1


def test_pestana_lugares_con_inactivos_aparte(cg, comuna, lugar):
    _lugar("Sede Desactivada Ficticia", _dir(comuna), activo=False)
    r = cg.get(f"{comuna.get_absolute_url()}?tab=lugares")
    assert [l.nombre for l in r.context["lugares"]] == ["Sala Ficticia"]
    assert [l.nombre for l in r.context["lugares_inactivos"]] == ["Sede Desactivada Ficticia"]
    html = r.content.decode()
    assert "Lugares (1)" in html  # contador = activos
    assert html.index("Sala Ficticia") < html.index("Lugares inactivos (1)") < html.index("Sede Desactivada Ficticia")
    assert html.count("Sede Desactivada Ficticia") == 1


def test_nota_de_lugares_visible_sin_permiso_de_crear(comuna, lugar):
    u = User.objects.create_user("lector_lugares", email="lector.lugares@ejemplo.invalid", password="clave-ficticia-123")
    for codigo in ("view_comuna", "view_lugar"):
        u.user_permissions.add(Permission.objects.get(codename=codigo))
    cliente = Client()
    cliente.force_login(u)
    html = cliente.get(f"{comuna.get_absolute_url()}?tab=lugares").content.decode()
    assert "Activos con su dirección en Comuna Ficticia" in html and "/lugares/nuevo" not in html


def test_municipalidad_inactiva_en_cabecera(cg, comuna):
    muni = _org("Municipalidad Desactivada Ficticia", "municipalidad", comuna_municipal=comuna, activo=False)
    html = cg.get(comuna.get_absolute_url()).content.decode()
    cabecera = html[: html.index('id="pestana"')]
    assert muni.get_absolute_url() in cabecera and "Inactiva" in cabecera and "tipo=municipalidad" not in cabecera


# ---------- rendimiento ----------

def _poblar(comuna, raiz, otra, crear_actividad, gestor, desde, hasta):
    """Por cada i: un sector (hijo de `raiz`), comunidad, organización y lugar (activos y desactivados), residente con perfil y comunidad,
    integrante no residente y una actividad con participación, territorio y minuta."""
    perfil = PerfilPersona.objects.get(codigo="vecino_o_vecina_de_la_comunidad")
    tipos = ("junta_de_vecinos_o_comite", "institucion_educativa", "fundacion_u_ong", "empresa_o_partner")
    for i in range(desde, hasta):
        sector = _sector(comuna, f"Sector {i:02d}", raiz)
        d = _dir(comuna, sector)
        comunidad = Comunidad.objects.create(nombre=f"Comunidad {i}", comuna=comuna, sector=sector)
        _org(f"Organización {i}", tipos[i % 4], d)
        _org(f"Organización desactivada {i}", tipos[i % 4], d, activo=False)
        sala = _lugar(f"Sala {i}", d)
        _lugar(f"Sala desactivada {i}", d, activo=False)
        residente = Persona.objects.create(nombres=f"Residente{i}", apellido_paterno=f"Apellido{i}")
        residente.perfiles.add(perfil)
        _reside(residente, d)
        ComunidadMiembro.objects.create(comunidad=comunidad, persona=residente)
        visita = Persona.objects.create(nombres=f"Visita{i}", apellido_paterno=f"Apellido{i}")
        visita.perfiles.add(perfil)
        _reside(visita, _dir(otra))
        ComunidadMiembro.objects.create(comunidad=comunidad, persona=visita)
        a = _programada(crear_actividad, gestor, sala, (i % 40) - 5, f"Actividad {i}")
        ActividadTerritorio.objects.create(actividad=a, sector=sector)
        _participa(a, residente)
        SesionActividad.objects.create(actividad=a, numero=1, fecha=HOY - timedelta(days=i), asistentes_sin_registro=2)


def _medir(cliente, url, claves):
    medidas = {}
    for clave in claves:
        with CaptureQueriesContext(connection) as ctx:
            r = cliente.get(f"{url}?tab={clave}")
        assert r.status_code == 200 and r.context["pestana"] == clave
        medidas[clave] = len(ctx)
    return medidas


def test_pestanas_bajo_tope_de_consultas(cg, comuna, crear_actividad, gestor):
    raiz = _sector(comuna, "Sector Raíz Ficticio")
    otra = _otra_comuna(comuna)
    claves_sector = ["resumen", "sectores", "nombres", "comunidades", "organizaciones", "personas", "lugares", "actividades", "alcance"]
    cg.get(comuna.get_absolute_url())  # calienta cachés de la sesión y del catálogo

    _poblar(comuna, raiz, otra, crear_actividad, gestor, 0, 1)
    uno = _medir(cg, comuna.get_absolute_url(), PESTANAS_COMUNA)
    uno_sector = _medir(cg, raiz.get_absolute_url(), claves_sector)

    _poblar(comuna, raiz, otra, crear_actividad, gestor, 1, 30)
    treinta = _medir(cg, comuna.get_absolute_url(), PESTANAS_COMUNA)
    treinta_sector = _medir(cg, raiz.get_absolute_url(), claves_sector)

    for clave in PESTANAS_COMUNA:
        assert treinta[clave] - uno[clave] <= 2, (clave, uno[clave], treinta[clave])
        assert treinta[clave] <= 60, (clave, treinta[clave])
    for clave in claves_sector:
        assert treinta_sector[clave] - uno_sector[clave] <= 2, (clave, uno_sector[clave], treinta_sector[clave])
        assert treinta_sector[clave] <= 60, (clave, treinta_sector[clave])

"""Servicio de resumen territorial (F23): residentes, indicadores, tabla por sector y presencia por comuna. Datos ficticios."""
from datetime import time, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.actividades.models import Actividad, ActividadTerritorio, SesionActividad
from apps.actividades.servicios import programar
from apps.comunidades.models import Comunidad
from apps.lugares.models import Lugar
from apps.nucleo.models import EstadoActividad, TipoLugar, TipoOrganizacion
from apps.organizaciones.models import Organizacion
from apps.personas.models import Persona, PersonaDireccion
from apps.territorio import consultas
from apps.territorio.models import Comuna, Direccion, Provincia, Region, Sector
from apps.territorio.resumen import personas_residentes, presencia_por_comuna, resumen_territorio

pytestmark = pytest.mark.django_db

HOY = timezone.localdate()


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


def _reside(persona, direccion, tipo="residencia", vigente=True):
    return PersonaDireccion.objects.create(persona=persona, direccion=direccion, tipo=tipo, vigente=vigente)


def _programada(crear_actividad, gestor, lugar, dias, nombre="Actividad ficticia", estado=None, hora=None):
    """Actividad con su programación vigente `dias` días desde hoy (negativo = pasada)."""
    a = crear_actividad(nombre)
    programar(a, gestor, HOY + timedelta(days=dias), hora, None, lugar, None)
    if estado:
        Actividad.objects.filter(pk=a.pk).update(estado=EstadoActividad.objects.get(codigo=estado))
    return a


def _fila(resumen, sector):
    return next(f for f in resumen["sectores"] if f["sector"] == sector)


# ---------- residentes ----------

def test_residentes_por_comuna_y_sector_con_hijos(comuna, crear_persona):
    otra = _otra_comuna(comuna)
    padre = _sector(comuna, "San Pedro de la Costa")
    etapa = _sector(comuna, "Etapa 1", padre, "etapa")
    villa = _sector(comuna, "Villa Aparte", tipo="villa")
    en_etapa, en_villa, antigua, procedente = (crear_persona() for _ in range(4))
    inactiva, de_otra, dos_direcciones, en_dos_comunas, sin_direccion = (crear_persona() for _ in range(5))
    _reside(en_etapa, _dir(comuna, etapa))
    _reside(en_villa, _dir(comuna, villa))
    _reside(antigua, _dir(comuna, padre), vigente=False)
    _reside(procedente, _dir(comuna, etapa), tipo="procedencia")
    _reside(inactiva, _dir(comuna, villa))
    Persona.objects.filter(pk=inactiva.pk).update(activo=False)
    _reside(de_otra, _dir(otra))
    _reside(dos_direcciones, _dir(comuna, padre))
    _reside(dos_direcciones, _dir(comuna, etapa))
    _reside(en_dos_comunas, _dir(comuna))
    _reside(en_dos_comunas, _dir(otra))

    en_comuna = personas_residentes(comuna=comuna)
    assert set(en_comuna) == {en_etapa, en_villa, dos_direcciones, en_dos_comunas}
    assert en_comuna.count() == 4  # cada persona una sola vez, aunque tenga varias direcciones
    assert set(personas_residentes(sectores=padre.descendientes_ids())) == {en_etapa, dos_direcciones}  # el sector incluye a sus hijos
    assert set(personas_residentes(sectores=[villa.pk])) == {en_villa}
    assert set(personas_residentes(comuna=otra)) == {de_otra, en_dos_comunas}  # quien reside en dos comunas es residente de cada una
    assert sin_direccion not in en_comuna


# ---------- indicadores ----------

def test_resumen_cuenta_una_vez_actividad_con_agenda_y_territorio(comuna, lugar, crear_actividad, gestor):
    otra = _otra_comuna(comuna)
    lugar_otra = _lugar("Sala de otra comuna", _dir(otra))
    # agenda vigente en la comuna Y territorio de la comuna: cuenta una sola vez
    ambas = _programada(crear_actividad, gestor, lugar, -10, "Con agenda y territorio")
    ActividadTerritorio.objects.create(actividad=ambas, comuna=comuna)
    # solo territorio (sin programar): cuenta en el total, no en los 12 meses
    solo_territorio = crear_actividad("Solo territorio")
    ActividadTerritorio.objects.create(actividad=solo_territorio, comuna=comuna)
    # agenda de hace más de un año: total sí, 12 meses no
    _programada(crear_actividad, gestor, lugar, -400, "Muy antigua")
    # territorio indicado, pero programada en otra comuna dentro de los 12 meses: del territorio y reciente
    dirigida = _programada(crear_actividad, gestor, lugar_otra, -5, "Dirigida a la comuna")
    ActividadTerritorio.objects.create(actividad=dirigida, comuna=comuna)
    # el territorio ya no vigente no cuenta; la agenda anterior (no vigente) tampoco
    desvinculada = _programada(crear_actividad, gestor, lugar_otra, -3, "Desvinculada")
    ActividadTerritorio.objects.create(actividad=desvinculada, comuna=comuna, vigente=False)
    reprogramada = _programada(crear_actividad, gestor, lugar, 2, "Reprogramada a otra comuna")
    programar(reprogramada, gestor, HOY + timedelta(days=3), None, None, lugar_otra, None, "Cambio de sede")
    _programada(crear_actividad, gestor, lugar_otra, -2, "De otra comuna")

    r = resumen_territorio(comuna=comuna)
    assert r["actividades_total"] == 4 == consultas.actividades_de(comuna=comuna).count()
    assert r["actividades_12m"] == 2  # «Con agenda y territorio» y «Dirigida a la comuna»
    assert r["sectores"][-1]["actividades"] == 4  # sin sectores: todas caen en «Sin sector»


def test_resumen_comuna_vacia_en_cero(comuna):
    r = resumen_territorio(comuna=comuna)
    for clave in ("comunidades", "organizaciones", "personas", "lugares", "actividades_12m", "actividades_total"):
        assert r[clave] == 0, clave
    assert r["organizaciones_por_tipo"] == [] and r["proximas"] == [] and r["minutas"] == []
    assert len(r["sectores"]) == 1  # solo la fila «Sin sector», en cero
    assert r["sectores"][0] == {"sector": None, "comunidades": 0, "organizaciones": 0, "lugares": 0, "personas": 0, "actividades": 0}


def test_organizaciones_agrupadas_por_tipo_maximo_5_nombres(comuna):
    otra = _otra_comuna(comuna)
    d = _dir(comuna)
    for i in range(7):
        _org(f"Junta {i} Ficticia", "junta_de_vecinos_o_comite", d)
    _org("Colegio Ficticio", "institucion_educativa", d)
    _org("Instituto Ficticio", "institucion_educativa", d)
    _org("Junta desactivada", "junta_de_vecinos_o_comite", d, activo=False)  # no cuenta
    _org("Junta de otra comuna", "junta_de_vecinos_o_comite", _dir(otra))  # no cuenta
    sede_ajena = _dir(otra, _sector(otra, "Villa de la otra comuna"))
    muni = _org("Municipalidad Ficticia", "municipalidad", sede_ajena, comuna_municipal=comuna)  # cuenta por ser la municipalidad, aunque su sede esté fuera

    r = resumen_territorio(comuna=comuna)
    assert r["organizaciones"] == 10
    assert [f["organizaciones"] for f in r["sectores"]] == [10]  # sin sectores en la comuna: todo va a «Sin sector», también la municipalidad de sede ajena
    por_tipo = {t.codigo: (total, nombres) for t, total, nombres in r["organizaciones_por_tipo"]}
    assert set(por_tipo) == {"junta_de_vecinos_o_comite", "institucion_educativa", "municipalidad"}
    total, nombres = por_tipo["junta_de_vecinos_o_comite"]
    assert total == 7
    assert [o.nombre for o in nombres] == [f"Junta {i} Ficticia" for i in range(5)]  # 5 nombres, en orden alfabético
    assert all(isinstance(o, Organizacion) for o in nombres)
    assert por_tipo["institucion_educativa"][0] == 2 and len(por_tipo["institucion_educativa"][1]) == 2
    assert por_tipo["municipalidad"] == (1, [muni])
    assert sum(total for _, total, _ in r["organizaciones_por_tipo"]) == r["organizaciones"]
    orden = [(t.orden, t.nombre) for t, _, _ in r["organizaciones_por_tipo"]]
    assert orden == sorted(orden)  # en el orden del catálogo


def test_tabla_de_sectores_con_fila_sin_sector(comuna, lugar, crear_persona, crear_actividad, gestor):
    padre = _sector(comuna, "San Pedro de la Costa")
    etapa = _sector(comuna, "Etapa 1", padre, "etapa")
    villa = _sector(comuna, "Villa Aparte", tipo="villa")
    d_etapa, d_padre, d_sin = _dir(comuna, etapa), _dir(comuna, padre), _dir(comuna)

    Comunidad.objects.create(nombre="Comunidad de la etapa", comuna=comuna, sector=etapa)
    Comunidad.objects.create(nombre="Comunidad sin sector", comuna=comuna)
    _org("Junta del sector", "junta_de_vecinos_o_comite", d_padre)
    _org("Fundación sin sector", "fundacion_u_ong", d_sin)
    Comunidad.objects.create(nombre="Comunidad desactivada", comuna=comuna, sector=etapa, activo=False)  # no cuenta
    sala_etapa = _lugar("Sala de la etapa", d_etapa)  # «lugar» (fixture) queda sin sector
    _lugar("Sala desactivada", d_etapa, activo=False)  # no cuenta
    _reside(crear_persona(), d_etapa)
    _reside(crear_persona(), d_sin)
    _programada(crear_actividad, gestor, sala_etapa, 5, "En la etapa")
    _programada(crear_actividad, gestor, lugar, 5, "Sin sector")
    en_villa = crear_actividad("Dirigida a la villa")
    ActividadTerritorio.objects.create(actividad=en_villa, sector=villa)
    en_comuna = crear_actividad("Dirigida a toda la comuna")
    ActividadTerritorio.objects.create(actividad=en_comuna, comuna=comuna)

    r = resumen_territorio(comuna=comuna)
    filas = r["sectores"]
    assert [f["sector"] for f in filas] == [padre, etapa, villa, None]  # cada sector seguido de sus hijos; «Sin sector» al final
    claves = ("comunidades", "organizaciones", "lugares", "personas", "actividades")
    cuenta = lambda f: tuple(f[c] for c in claves)  # noqa: E731
    assert cuenta(_fila(r, padre)) == (0, 1, 0, 0, 0)  # conteo directo: no suma lo de la etapa
    assert cuenta(_fila(r, etapa)) == (1, 0, 1, 1, 1)
    assert cuenta(_fila(r, villa)) == (0, 0, 0, 0, 1)
    assert cuenta(_fila(r, None)) == (1, 1, 1, 1, 2)
    assert (r["comunidades"], r["organizaciones"], r["lugares"], r["personas"], r["actividades_total"]) == (2, 2, 2, 2, 4)

    en_sector = resumen_territorio(sectores=padre.descendientes_ids())
    assert [f["sector"] for f in en_sector["sectores"]] == [padre, etapa]  # sin fila «Sin sector»
    assert (en_sector["comunidades"], en_sector["organizaciones"], en_sector["lugares"], en_sector["personas"], en_sector["actividades_total"]) == (1, 1, 1, 1, 1)
    assert cuenta(_fila(en_sector, etapa)) == (1, 0, 1, 1, 1)


def test_resumen_proximas_y_minutas(comuna, lugar, crear_actividad, gestor):
    otra = _otra_comuna(comuna)
    lugar_otra = _lugar("Sala de otra comuna", _dir(otra))
    tarde = _programada(crear_actividad, gestor, lugar, 3, "Tarde", hora=time(10))
    temprano = _programada(crear_actividad, gestor, lugar, 3, "Temprano", hora=time(9))
    hoy = _programada(crear_actividad, gestor, lugar, 0, "Hoy")
    limite = _programada(crear_actividad, gestor, lugar, 30, "Último día")
    _programada(crear_actividad, gestor, lugar, 31, "Muy lejana")
    _programada(crear_actividad, gestor, lugar, -1, "Ayer")
    _programada(crear_actividad, gestor, lugar, 5, "Cancelada", estado="cancelada")
    _programada(crear_actividad, gestor, lugar, 7, "Suspendida", estado="suspendida")
    _programada(crear_actividad, gestor, lugar_otra, 4, "De otra comuna")
    dirigida = _programada(crear_actividad, gestor, lugar_otra, 4, "Dirigida a la comuna")
    ActividadTerritorio.objects.create(actividad=dirigida, comuna=comuna)

    r = resumen_territorio(comuna=comuna)
    assert [a.actividad for a in r["proximas"]] == [hoy, temprano, tarde, dirigida, limite]
    assert all(a.vigente for a in r["proximas"])

    serie = crear_actividad("Con sesiones")
    programar(serie, gestor, HOY + timedelta(days=60), None, None, lugar, None)
    for n in range(1, 8):
        SesionActividad.objects.create(actividad=serie, numero=n, fecha=HOY - timedelta(days=n))
    SesionActividad.objects.create(actividad=serie, numero=8)  # sin fecha: no es minuta
    SesionActividad.objects.create(actividad=serie, numero=9, fecha=HOY, vigente=False)  # anulada
    ajena = _programada(crear_actividad, gestor, lugar_otra, 60, "Ajena")
    SesionActividad.objects.create(actividad=ajena, numero=1, fecha=HOY)
    minutas = resumen_territorio(comuna=comuna)["minutas"]
    assert [m.numero for m in minutas] == [1, 2, 3, 4, 5]  # las 5 más recientes, la más nueva primero
    assert all(m.actividad == serie for m in minutas)


# ---------- presencia ----------

def test_presencia_ordenada_y_sin_comunas_vacias(comuna, crear_actividad, crear_persona, gestor):
    region = comuna.provincia.region
    a = _otra_comuna(comuna, "99010", "Aldea Ficticia")
    b = _otra_comuna(comuna, "99011", "Barrio Ficticio")
    c = _otra_comuna(comuna, "99012", "Caleta Ficticia")
    d = _otra_comuna(comuna, "99013", "Dehesa Ficticia")  # solo un lugar: con presencia, sin nada reciente
    vacia = comuna  # «Comuna Ficticia» no tiene nada
    otra_region = Region.objects.create(codigo="98", nombre="Otra Región de Prueba")
    ajena = Comuna.objects.create(provincia=Provincia.objects.create(region=otra_region, codigo="980", nombre="Otra Provincia"), codigo="98001", nombre="Ajena Ficticia")

    # Aldea: 1 comunidad, 3 organizaciones (una por dirección, su municipalidad sin dirección y la de Dehesa con sede aquí), 1 persona; ninguna actividad reciente
    Comunidad.objects.create(nombre="Comunidad Aldea", comuna=a)
    Comunidad.objects.create(nombre="Comunidad Aldea inactiva", comuna=a, activo=False)  # no cuenta
    _org("Junta Aldea", "junta_de_vecinos_o_comite", _dir(a))
    _org("Municipalidad de Aldea", "municipalidad", comuna_municipal=a)
    _reside(crear_persona(), _dir(a))
    # Barrio: 1 actividad reciente (programada allí) y nada más
    _programada(crear_actividad, gestor, _lugar("Sala Barrio", _dir(b)), -20, "Reciente en Barrio")
    # Caleta: 1 actividad reciente por territorio y otra antigua, más una municipalidad con dirección en su misma comuna
    reciente = _programada(crear_actividad, gestor, _lugar("Sala Barrio 2", _dir(b)), -15, "Reciente dirigida a Caleta")
    ActividadTerritorio.objects.create(actividad=reciente, comuna=c)
    antigua = crear_actividad("Antigua en Caleta")
    ActividadTerritorio.objects.create(actividad=antigua, comuna=c)
    _org("Municipalidad de Caleta", "municipalidad", _dir(c), comuna_municipal=c)  # cuenta una sola vez
    # Dehesa: un lugar, su municipalidad (con sede en Aldea: cuenta en ambas) y una actividad dirigida a uno de sus sectores
    _lugar("Sala Dehesa", _dir(d))
    _lugar("Sala desactivada de Dehesa", _dir(d), activo=False)  # no cuenta
    _org("Municipalidad de Dehesa", "municipalidad", _dir(a), comuna_municipal=d)
    ActividadTerritorio.objects.create(actividad=crear_actividad("Dirigida a un sector de Dehesa"), sector=_sector(d, "Villa Dehesa"))
    # una comuna de otra región con presencia
    Comunidad.objects.create(nombre="Comunidad ajena", comuna=ajena)

    filas = presencia_por_comuna()
    nombres = [f["comuna"].nombre for f in filas]
    assert vacia.nombre not in nombres  # sin nada no aparece
    por_nombre = {f["comuna"].nombre: f for f in filas}
    assert set(por_nombre["Aldea Ficticia"]) >= {"comuna", "comunidades", "organizaciones", "personas", "actividades_12m", "total"}
    assert {k: por_nombre["Aldea Ficticia"][k] for k in ("comunidades", "organizaciones", "personas", "actividades_12m", "total")} == {
        "comunidades": 1, "organizaciones": 3, "personas": 1, "actividades_12m": 0, "total": 5,
    }
    assert por_nombre["Barrio Ficticio"]["actividades_12m"] == 2 and por_nombre["Barrio Ficticio"]["total"] == 4  # 2 actividades + 2 lugares
    assert por_nombre["Caleta Ficticia"]["organizaciones"] == 1  # la municipalidad con dirección en su comuna cuenta una sola vez
    assert por_nombre["Caleta Ficticia"]["actividades_12m"] == 1 and por_nombre["Caleta Ficticia"]["total"] == 3  # 1 organización + 2 actividades
    assert por_nombre["Dehesa Ficticia"]["organizaciones"] == 1 and por_nombre["Dehesa Ficticia"]["total"] == 3  # lugar + municipalidad + actividad
    # orden: actividades de los últimos 12 meses (desc), luego total (desc), luego nombre
    assert nombres == ["Barrio Ficticio", "Caleta Ficticia", "Aldea Ficticia", "Dehesa Ficticia", "Ajena Ficticia"]
    assert [f["comuna"].nombre for f in presencia_por_comuna(region=region)] == ["Barrio Ficticio", "Caleta Ficticia", "Aldea Ficticia", "Dehesa Ficticia"]
    assert [f["comuna"].nombre for f in presencia_por_comuna(region=otra_region)] == ["Ajena Ficticia"]


# ---------- rendimiento ----------

def _poblar(comuna, crear_actividad, gestor, desde, hasta):
    for i in range(desde, hasta):
        sector = _sector(comuna, f"Sector {i:02d}")
        d = _dir(comuna, sector)
        Comunidad.objects.create(nombre=f"Comunidad {i}", comuna=comuna, sector=sector)
        _org(f"Organización {i}", ("junta_de_vecinos_o_comite", "institucion_educativa", "fundacion_u_ong", "empresa_o_partner")[i % 4], d)
        sala = _lugar(f"Sala {i}", d)
        persona = Persona.objects.create(nombres=f"Persona{i}", apellido_paterno=f"Apellido{i}")
        _reside(persona, d)
        a = _programada(crear_actividad, gestor, sala, (i % 40) - 5, f"Actividad {i}")
        ActividadTerritorio.objects.create(actividad=a, sector=sector)
        SesionActividad.objects.create(actividad=a, numero=1, fecha=HOY - timedelta(days=i))


def test_resumen_consultas_acotadas(comuna, crear_actividad, gestor, django_assert_max_num_queries):
    _poblar(comuna, crear_actividad, gestor, 0, 1)
    with django_assert_max_num_queries(20):
        uno = resumen_territorio(comuna=comuna)
    assert uno["comunidades"] == 1 and uno["actividades_total"] == 1

    _poblar(comuna, crear_actividad, gestor, 1, 30)
    with django_assert_max_num_queries(20):
        treinta = resumen_territorio(comuna=comuna)
    assert treinta["comunidades"] == 30 and treinta["organizaciones"] == 30 and treinta["lugares"] == 30
    assert treinta["personas"] == 30 and treinta["actividades_total"] == 30 and len(treinta["sectores"]) == 31
    assert len(treinta["minutas"]) == 5 and all(len(nombres) <= 5 for _, _, nombres in treinta["organizaciones_por_tipo"])
    diez = list(Sector.objects.filter(comuna=comuna).values_list("pk", flat=True)[:10])
    with django_assert_max_num_queries(20):  # el ámbito de un sector también
        resumen_territorio(sectores=diez)


def test_presencia_consultas_independientes_del_numero_de_comunas(comuna, crear_actividad, gestor):
    def medir():
        with CaptureQueriesContext(connection) as ctx:
            filas = presencia_por_comuna()
        return len(ctx), len(filas)

    _poblar(comuna, crear_actividad, gestor, 0, 1)
    consultas_1, filas_1 = medir()
    for i in range(30):
        otra = _otra_comuna(comuna, f"98{i:03d}", f"Comuna {i:02d} Ficticia")
        Comunidad.objects.create(nombre=f"Comunidad {i}", comuna=otra)
        _org(f"Municipalidad {i}", "municipalidad", comuna_municipal=otra)
        sala = _lugar(f"Sala {i}", _dir(otra))
        a = _programada(crear_actividad, gestor, sala, -i)
        ActividadTerritorio.objects.create(actividad=a, comuna=otra)
        _reside(Persona.objects.create(nombres=f"Persona{i}", apellido_paterno="Ficticia"), _dir(otra))
    consultas_31, filas_31 = medir()
    assert (filas_1, filas_31) == (1, 31)
    assert consultas_31 == consultas_1 <= 12

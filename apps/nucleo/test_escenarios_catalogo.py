"""Escenarios del catálogo «FCHE — Escenarios hipotéticos». Cada prueba lleva el ID del escenario. Datos ficticios."""
import pytest
from django.contrib.auth.models import User
from django.test import Client

pytestmark = pytest.mark.django_db
CLAVE = "clave-ficticia-123"


# --- AC: acceso ---------------------------------------------------------------------------------------
def _fallar(ident, veces):
    for _ in range(veces):
        Client().post("/login", {"username": ident, "password": "mala"})


def test_AC_E1_bloqueo_tras_5_intentos_y_desbloqueo(gestor, ca):
    _fallar("gestor_prueba", 5)
    r = Client().post("/login", {"username": "gestor_prueba", "password": CLAVE})
    assert r.status_code == 200 and "Demasiados intentos fallidos" in r.content.decode()
    # también con el correo (la misma cuenta)
    assert "Demasiados intentos" in Client().post("/login", {"username": "gestor_prueba@ejemplo.invalid", "password": CLAVE}).content.decode()
    html = ca.get("/administracion/usuarios").content.decode()
    assert "Bloqueado por intentos fallidos" in html
    assert "Desbloquear acceso" in ca.get(f"/administracion/usuarios/{gestor.pk}/editar").content.decode()
    ca.post(f"/administracion/usuarios/{gestor.pk}/desbloquear")
    assert Client().post("/login", {"username": "gestor_prueba", "password": CLAVE}).status_code == 302


def test_AC_E1_el_bloqueo_no_revela_si_la_cuenta_existe():
    _fallar("no-existe@ejemplo.invalid", 5)
    html = Client().post("/login", {"username": "no-existe@ejemplo.invalid", "password": "x"}).content.decode()
    assert "Demasiados intentos fallidos" in html  # el mismo trato que una cuenta real


def test_AC_E1_ingreso_correcto_reinicia_el_conteo(gestor):
    _fallar("gestor_prueba", 4)
    assert Client().post("/login", {"username": "gestor_prueba", "password": CLAVE}).status_code == 302
    _fallar("gestor_prueba", 4)
    assert Client().post("/login", {"username": "gestor_prueba", "password": CLAVE}).status_code == 302


def test_AC_E1_bloqueo_vence_solo(gestor, settings):
    from datetime import timedelta

    from django.utils import timezone

    from apps.nucleo.models import Auditoria

    _fallar("gestor_prueba", 5)
    Auditoria.objects.filter(accion="ingreso_fallido").update(fecha=timezone.now() - timedelta(minutes=settings.BLOQUEO_MINUTOS + 1))
    assert Client().post("/login", {"username": "gestor_prueba", "password": CLAVE}).status_code == 302


def test_AC_E4_tras_ingresar_vuelve_al_enlace_guardado(gestor, persona):
    c = Client()
    r = c.get(persona.get_absolute_url())
    assert r.status_code == 302 and "next=" in r["Location"]
    r = c.post("/login?next=" + persona.get_absolute_url(), {"username": "gestor_prueba", "password": CLAVE, "next": persona.get_absolute_url()})
    assert r["Location"] == persona.get_absolute_url()


def test_AC_E5_desactivar_cuenta_cierra_su_sesion(cg, gestor):
    gestor.is_active = False
    gestor.save()
    assert cg.get("/dashboard").status_code == 302


def test_AC_E8_contrasena_1234_rechazada(cg):
    r = cg.post("/mi-cuenta/clave", {"old_password": CLAVE, "new_password1": "1234", "new_password2": "1234"})
    assert r.status_code == 200 and User.objects.get(username="gestor_prueba").check_password(CLAVE)


def test_AC_E7_usuario_activo_y_cerrar_sesion_visibles(cg):
    html = cg.get("/dashboard").content.decode()
    assert "gestor_prueba" in html and "Cerrar sesión" in html and "data-cerrar-sesion" in html


# --- UI: formularios -----------------------------------------------------------------------------------
def test_UI_E5_edicion_simultanea_no_pisa_cambios(cg, persona):
    html = cg.get(f"/personas/{persona.pk}/editar").content.decode()
    import re

    version = re.search(r'name="_version" value="(\d+)"', html).group(1)
    base = {"nombres": "Ana María", "apellido_paterno": "Pérez", "apellido_materno": "Soto"}
    # otra pestaña guarda primero
    assert cg.post(f"/personas/{persona.pk}/editar", {**base, "profesion": "Docente", "_version": version}).status_code == 302
    # la primera pestaña intenta guardar con la versión vieja
    r = cg.post(f"/personas/{persona.pk}/editar", {**base, "profesion": "Enfermera", "_version": version})
    persona.refresh_from_db()
    assert r.status_code == 200 and "cambió mientras lo editabas" in r.content.decode() and persona.profesion == "Docente"


def test_UI_E5_tambien_en_organizacion_y_lugar(cg, universidad, lugar):
    import re

    for url, datos in ((f"/organizaciones/{universidad.pk}/editar", {"nombre": "U2", "tipo": universidad.tipo_id}),
                       (f"/lugares/{lugar.pk}/editar", {"nombre": "Sala 2", "tipo": lugar.tipo_id, "dir-comuna": lugar.direccion.comuna_id, "dir-calle": "X"})):
        v = re.search(r'name="_version" value="(\d+)"', cg.get(url).content.decode()).group(1)
        cg.post(url, {**datos, "_version": v})
        r = cg.post(url, {**datos, "nombre": "Otro", "_version": v})
        assert "cambió mientras lo editabas" in r.content.decode(), url


def test_UI_E1_formularios_preparados_contra_doble_envio(cg):
    assert "/static/js/fche.js" in cg.get("/personas/nueva").content.decode()
    from pathlib import Path

    js = Path("static/js/fche.js").read_text()
    assert "dataset.enviando" in js and "sessionStorage" in js


def test_UI_E2_E3_tras_guardar_se_redirige(cg):
    r = cg.post("/personas/nueva", {"modo": "rapida", "nombres": "Una Vez"})
    assert r.status_code == 302  # post-redirección: F5 o «Atrás» no reenvían


def test_UI_E10_volver_conserva_filtros(cg, persona):
    cg.get("/personas?q=ana&activo=*&page=1")
    html = cg.get(persona.get_absolute_url()).content.decode()
    assert 'href="/personas?q=ana&amp;activo=*&amp;page=1"' in html


def test_UI_E13_listado_vacio_con_boton_para_crear(cg):
    html = cg.get("/lugares").content.decode()
    assert "Aún no hay registros" in html and "+ Nuevo lugar" in html


# --- PE y BU: personas y búsqueda ------------------------------------------------------------------------
from apps.personas.models import Persona  # noqa: E402


def test_PE_E8_BU_E1_busqueda_sin_tildes(cg, crear_persona):
    crear_persona("María", apellido_paterno="Guzmán")
    for q in ("guzman", "GUZMAN", "maria", "Maria Guzman"):
        assert "Guzmán" in cg.get(f"/personas?q={q}").content.decode(), q
        assert "Guzmán" in cg.get(f"/buscar?q={q}&tipo=persona").content.decode(), q
    crear_persona("Íñigo", apellido_paterno="Ñuñez")
    assert "Ñuñez" in cg.get("/personas?q=nunez").content.decode()


def test_BU_E1_tambien_en_organizaciones_y_lugares(cg, universidad):
    universidad.nombre = "Universidad de Concepción"
    universidad.save()
    assert "Concepción" in cg.get("/organizaciones?q=concepcion").content.decode()
    assert "Concepción" in cg.get("/buscar?q=concepcion").content.decode()


def test_BU_E2_buscar_telefono_en_cualquier_formato(cg, persona):
    from apps.nucleo.models import TipoContacto
    from apps.personas.models import Contacto

    Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="telefono_movil"), valor="+56 9 8765 4321")
    for q in ("987654321", "9 8765 4321", "+56987654321", "(9) 8765-4321"):
        assert "Ana María" in cg.get("/personas", {"q": q}).content.decode(), q


def test_BU_E3_apellidos_compuestos(cg, crear_persona):
    crear_persona("Pedro", apellido_paterno="De la Fuente")
    assert "De la Fuente" in cg.get("/personas", {"q": "de la fuente"}).content.decode()
    assert "De la Fuente" in cg.get("/personas", {"q": "fuente"}).content.decode()


def test_BU_E5_desactivados_aparecen_marcados(cg, crear_persona):
    p = crear_persona("Desactivada", apellido_paterno="Buscable")
    p.activo = False
    p.save()
    html = cg.get("/buscar?q=buscable").content.decode()
    assert "Desactivada Buscable" in html and "Desactivado" in html


def test_PE_E4_persona_extranjera_con_pasaporte(cg):
    r = cg.post("/personas/nueva", {"modo": "completa", "nombres": "Jean", "apellido_paterno": "Dupont", "tipo_documento": "pasaporte", "numero_documento": "ab123456"})
    p = Persona.objects.get()
    assert r.status_code == 302 and p.numero_documento == "AB123456" and p.rut_numero is None
    assert "AB123456" in cg.get("/personas?q=AB123456").content.decode()
    r = cg.post("/personas/nueva", {"modo": "completa", "nombres": "Otro", "tipo_documento": "pasaporte", "numero_documento": "AB123456", "confirmar_duplicado": "1", "nota_distincion": "x"})
    assert r.status_code == 200 and Persona.objects.count() == 1  # documento repetido
    assert cg.post("/personas/nueva", {"modo": "completa", "nombres": "Sin tipo", "numero_documento": "ZZ1"}).status_code == 200


def test_PE_E1_comparacion_lado_a_lado(cg, persona):
    from apps.nucleo.models import TipoContacto
    from apps.personas.models import Contacto

    Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="correo"), valor="ana@ejemplo.invalid")
    html = cg.post("/personas/nueva", {"modo": "rapida", "nombres": "Ana María", "apellido_paterno": "Pérez"}).content.decode()
    assert "Persona existente" in html and "ana@ejemplo.invalid" in html and "Por qué coincide" in html


def test_PE_E10_fallecida_no_es_candidata(cg, actividad, crear_persona):
    from apps.actividades import matching
    from apps.nucleo.models import EstadoRegistro

    p = crear_persona("Fallecida")
    p.estado_registro = EstadoRegistro.objects.get(codigo="fallecida")
    p.save()
    assert p not in [c.objeto for c in matching.buscar_personas(actividad)]
    assert Persona.objects.filter(pk=p.pk).exists()


def test_VA_E4_desactivada_nunca_es_candidata(actividad, crear_persona):
    from apps.actividades import matching

    p = crear_persona("Inactiva")
    p.activo = False
    p.save()
    assert p not in [c.objeto for c in matching.buscar_personas(actividad)]


# --- Fusión controlada --------------------------------------------------------------------------------------
def test_PE_E14_fusion_solo_administrador(cg, ca, persona, crear_persona):
    dup = crear_persona("Ana María", apellido_paterno="Pérez S.")
    assert cg.get(f"/personas/{dup.pk}/fusionar").status_code == 403
    assert "Fusionar con otra ficha" not in cg.get(dup.get_absolute_url()).content.decode()
    assert ca.get(f"/personas/{dup.pk}/fusionar").status_code == 200


def test_PE_E14_fusion_une_historiales(ca, persona, crear_persona, crear_actividad, rol, estado_part):
    from apps.actividades.models import Participacion
    from apps.documentos.origen import origenes_de, registrar_origen
    from apps.nucleo.models import Auditoria, TipoContacto
    from apps.personas.models import Contacto

    dup = crear_persona("Ana Maria", apellido_paterno="Perez", rut_numero=11111111, rut_dv="1")
    a1, a2 = crear_actividad("A1"), crear_actividad("A2")
    Participacion.objects.create(actividad=a1, persona=dup, rol=rol("voluntario"), estado=estado_part("confirmado"))
    Participacion.objects.create(actividad=a2, persona=dup, rol=rol("voluntario"), estado=estado_part("confirmado"))
    Participacion.objects.create(actividad=a2, persona=persona, rol=rol("voluntario"), estado=estado_part("confirmado"))  # choque
    Contacto.objects.create(persona=dup, tipo=TipoContacto.objects.get(codigo="correo"), valor="dup@ejemplo.invalid")
    a1.responsable = dup
    a1.save()
    registrar_origen(dup, None, fuente="llamado")
    r = ca.post(f"/personas/{dup.pk}/fusionar", {"destino": persona.pk, "motivo": "Misma persona, digitada dos veces", "confirmo": "on"})
    assert r.status_code == 302 and r["Location"] == persona.get_absolute_url()
    persona.refresh_from_db()
    dup.refresh_from_db()
    assert persona.participaciones.count() == 2 and dup.participaciones.count() == 1  # el choque queda en el origen
    assert persona.contactos.filter(valor="dup@ejemplo.invalid").exists()
    a1.refresh_from_db()
    assert a1.responsable == persona
    assert persona.rut_numero == 11111111 and dup.rut_numero is None  # el RUT pasa a la ficha que queda
    assert not dup.activo and dup.estado_registro.codigo == "fusionada" and "Fusionada en la ficha" in dup.observaciones
    assert origenes_de(persona).count() == 1
    assert Auditoria.objects.filter(accion="fusion").exists()


def test_PE_E14_fusion_pide_motivo_y_confirmacion(ca, persona, crear_persona):
    dup = crear_persona("Dup")
    assert ca.post(f"/personas/{dup.pk}/fusionar", {"destino": persona.pk, "motivo": "", "confirmo": "on"}).status_code == 400
    assert ca.post(f"/personas/{dup.pk}/fusionar", {"destino": persona.pk, "motivo": "x"}).status_code == 400
    assert ca.post(f"/personas/{dup.pk}/fusionar", {"destino": dup.pk, "motivo": "x", "confirmo": "on"}).status_code == 400
    dup.refresh_from_db()
    assert dup.activo


def test_OR_E1_fusion_de_organizaciones(ca, universidad, crear_actividad):
    from apps.actividades.models import ActividadOrganizacion
    from apps.organizaciones.models import Carrera, Organizacion

    dup = Organizacion.objects.create(nombre="U. Ficticia", tipo=universidad.tipo)
    Carrera.objects.create(organizacion=dup, nombre="Química")
    ActividadOrganizacion.objects.create(actividad=crear_actividad(), organizacion=dup)
    ca.post(f"/organizaciones/{dup.pk}/fusionar", {"destino": universidad.pk, "motivo": "Mismo nombre abreviado", "confirmo": "on"})
    assert universidad.carreras.filter(nombre="Química").exists() and universidad.actividades.count() == 1
    dup.refresh_from_db()
    assert not dup.activo


def test_CO_E4_unir_valores_del_catalogo(ca, cg, persona):
    from apps.nucleo.models import OrigenPersona

    mal = OrigenPersona.objects.create(nombre="Difucion")
    persona.origen = mal
    persona.save()
    bien = OrigenPersona.objects.get(codigo="difusion")
    assert cg.get(f"/administracion/catalogos/origen-persona/{mal.pk}/unir").status_code == 403
    r = ca.post(f"/administracion/catalogos/origen-persona/{mal.pk}/unir", {"destino": bien.pk, "motivo": "Mal escrito", "confirmo": "on"})
    persona.refresh_from_db()
    mal.refresh_from_db()
    assert r.status_code == 302 and persona.origen == bien and not mal.activo


# --- Iteración 3: desactivar con aviso, reasignar, capacidad ----------------------------------------------
from datetime import date, time, timedelta  # noqa: E402

from apps.actividades import servicios  # noqa: E402
from apps.actividades.models import Participacion  # noqa: E402

FUT = date.today() + timedelta(days=10)


def test_NR06_AT_E11_desactivar_persona_con_actividades_futuras(cg, persona, crear_actividad, rol, estado_part):
    a = crear_actividad("Taller futuro", estado="planificada")
    Participacion.objects.create(actividad=a, persona=persona, rol=rol("voluntario"), estado=estado_part("confirmado"))
    r = cg.post(f"/personas/{persona.pk}/alternar")
    persona.refresh_from_db()
    assert r.status_code == 200 and "Taller futuro" in r.content.decode() and persona.activo  # todavía no
    cg.post(f"/personas/{persona.pk}/alternar", {"confirmar": "1"})
    persona.refresh_from_db()
    assert not persona.activo


def test_NR06_sin_actividades_futuras_desactiva_directo(cg, persona, crear_actividad, rol, estado_part):
    a = crear_actividad("Ya realizada", estado="realizada")
    Participacion.objects.create(actividad=a, persona=persona, rol=rol("voluntario"), estado=estado_part("asistio"))
    assert cg.post(f"/personas/{persona.pk}/alternar").status_code == 302


def test_LU_E1_desactivar_lugar_con_actividades_futuras(cg, lugar, crear_actividad, gestor):
    a = crear_actividad("En la sala")
    servicios.programar(a, gestor, FUT, time(10), time(11), lugar, None)
    html = cg.post(f"/lugares/{lugar.pk}/alternar").content.decode()
    assert "En la sala" in html and "Desactivar de todos modos" in html
    cg.post(f"/lugares/{lugar.pk}/alternar", {"confirmar": "1"})
    lugar.refresh_from_db()
    assert not lugar.activo
    from apps.actividades.reglas import revisar

    assert "lugar_inactivo" in {p.codigo for p in revisar(a)}  # la actividad avisa


def test_NR06_desactivar_organizacion(cg, universidad, crear_actividad):
    from apps.actividades.models import ActividadOrganizacion

    ActividadOrganizacion.objects.create(actividad=crear_actividad("Con la U", estado="confirmada"), organizacion=universidad)
    assert "Con la U" in cg.post(f"/organizaciones/{universidad.pk}/alternar").content.decode()


def test_AT_E6_reasignar_responsable_en_bloque(cg, crear_persona, crear_actividad):
    sale, entra = crear_persona("Sale"), crear_persona("Entra")
    a1 = crear_actividad("A1", responsable=sale, estado="planificada")
    a2 = crear_actividad("A2", responsable=sale)
    pasada = crear_actividad("Pasada", responsable=sale, estado="realizada")
    assert "Reasignar sus actividades" in cg.get(sale.get_absolute_url()).content.decode()
    r = cg.post(f"/personas/{sale.pk}/reasignar", {"actividades": [a1.pk, a2.pk], "nuevo": entra.pk, "motivo": "Deja la Fundación"})
    for a in (a1, a2, pasada):
        a.refresh_from_db()
    assert r.status_code == 302 and a1.responsable == entra and a2.responsable == entra and pasada.responsable == sale
    from apps.nucleo.models import Auditoria

    assert Auditoria.objects.filter(accion="responsable_reasignado").exists()


def test_AT_E9_misma_persona_con_dos_roles_cuenta_una_vez(actividad, lugar, gestor, crear_persona, rol, estado_part):
    from apps.actividades.reglas import revisar

    lugar.capacidad = 2
    lugar.save()
    actividad.responsable = crear_persona()
    actividad.save()
    servicios.programar(actividad, gestor, FUT, time(10), time(11), lugar, None)
    ana, beto = crear_persona("Ana"), crear_persona("Beto")
    Participacion.objects.create(actividad=actividad, persona=ana, rol=rol("participante"), estado=estado_part("confirmado"))
    Participacion.objects.create(actividad=actividad, persona=ana, rol=rol("tutor"), estado=estado_part("confirmado"))
    Participacion.objects.create(actividad=actividad, persona=beto, rol=rol("participante"), estado=estado_part("confirmado"))
    assert "capacidad" not in {p.codigo for p in revisar(actividad)}  # 2 personas, no 3


def test_AT_E10_roles_fuera_de_capacidad_por_ajuste(actividad, lugar, gestor, crear_persona, rol, estado_part, settings):
    from apps.actividades.reglas import revisar

    lugar.capacidad = 1
    lugar.save()
    actividad.responsable = crear_persona()
    actividad.save()
    servicios.programar(actividad, gestor, FUT, time(10), time(11), lugar, None)
    Participacion.objects.create(actividad=actividad, persona=crear_persona(), rol=rol("participante"), estado=estado_part("confirmado"))
    Participacion.objects.create(actividad=actividad, persona=crear_persona(), rol=rol("tutor"), estado=estado_part("confirmado"))
    assert "capacidad" in {p.codigo for p in revisar(actividad)}
    settings.ROLES_FUERA_DE_CAPACIDAD = ["tutor"]
    assert "capacidad" not in {p.codigo for p in revisar(actividad)}


def test_VA_E6_capacidad_exacta_es_compatible(actividad, lugar, gestor, crear_persona, rol, estado_part):
    from apps.actividades.reglas import revisar

    actividad.responsable = crear_persona()
    actividad.save()
    servicios.programar(actividad, gestor, FUT, time(10), time(11), lugar, None)
    for _ in range(20):
        Participacion.objects.create(actividad=actividad, persona=crear_persona(), rol=rol("participante"), estado=estado_part("confirmado"))
    assert "capacidad_ok" in {p.codigo for p in revisar(actividad)}


def test_LU_E2_bajar_capacidad_avisa_actividades_excedidas(cg, lugar, crear_actividad, gestor, crear_persona, rol, estado_part):
    a = crear_actividad("Con 5 personas")
    servicios.programar(a, gestor, FUT, time(10), time(11), lugar, None)
    for _ in range(5):
        Participacion.objects.create(actividad=a, persona=crear_persona(), rol=rol("participante"), estado=estado_part("confirmado"))
    r = cg.post(f"/lugares/{lugar.pk}/editar", {"nombre": lugar.nombre, "tipo": lugar.tipo_id, "capacidad": 3, "dir-comuna": lugar.direccion.comuna_id, "dir-calle": "X"}, follow=True)
    assert "quedan excedidas" in r.content.decode() and "Con 5 personas" in r.content.decode()


def test_LU_E11_lugares_con_mismo_nombre_muestran_la_comuna(cg, actividad, lugar):
    from apps.lugares.models import Lugar
    from apps.territorio.models import Comuna, Direccion

    otra = Comuna.objects.create(provincia=lugar.direccion.comuna.provincia, codigo="99002", nombre="Otra Comuna")
    Lugar.objects.create(nombre="Sala Ficticia", tipo=lugar.tipo, direccion=Direccion.objects.create(comuna=otra))
    html = cg.get(f"/actividades/{actividad.pk}/programar").content.decode()
    assert "Sala Ficticia — Comuna Ficticia (capacidad 20)" in html and "Sala Ficticia — Otra Comuna (capacidad sin registrar)" in html


def test_OR_E6_cambio_de_administracion_cierra_autoridades(cg, crear_persona):
    from apps.nucleo.models import TipoOrganizacion
    from apps.organizaciones.models import Organizacion
    from apps.personas.models import PersonaOrganizacion

    muni = Organizacion.objects.create(nombre="Muni Ficticia", tipo=TipoOrganizacion.objects.get(codigo="municipalidad"))
    alcalde = PersonaOrganizacion.objects.create(persona=crear_persona("Alcalde"), organizacion=muni, cargo="Alcalde", tipo_cargo="autoridad", fecha_inicio=date(2024, 12, 6))
    oficina = PersonaOrganizacion.objects.create(persona=crear_persona("Secretaria"), organizacion=muni, cargo="Secretaria", tipo_cargo="funcional")
    assert "Cerrar cargos de autoridad" in cg.get(f"{muni.get_absolute_url()}?tab=personas").content.decode()
    cg.post(f"/organizaciones/{muni.pk}/cerrar-autoridades", {"hasta": "2028-12-05"})
    alcalde.refresh_from_db()
    oficina.refresh_from_db()
    assert alcalde.fecha_termino == date(2028, 12, 5) and oficina.fecha_termino is None


def test_CD_E3_autoridades_por_verificar_en_el_panel(cg, crear_persona, universidad):
    from apps.personas.models import PersonaOrganizacion

    PersonaOrganizacion.objects.create(persona=crear_persona("Concejal"), organizacion=universidad, cargo="Concejal", tipo_cargo="autoridad", fecha_inicio=date.today() - timedelta(days=500))
    PersonaOrganizacion.objects.create(persona=crear_persona("Reciente"), organizacion=universidad, cargo="Decano", tipo_cargo="autoridad", fecha_inicio=date.today() - timedelta(days=30))
    html = cg.get("/dashboard").content.decode()
    assert "Verificar si sigue vigente: Concejal" in html and "Reciente" not in html


# --- Iteración 4: actividades, agenda y botones según el estado -------------------------------------------------
from apps.actividades.reglas import ReglaNegocio, revisar  # noqa: E402
from apps.nucleo.models import Auditoria  # noqa: E402

HOY = date.today()


def test_AT_E1_duplicar_actividad(cg, crear_actividad, crear_persona, universidad, comuna, lugar, gestor, rol, estado_part):
    from apps.actividades.models import ActividadOrganizacion, ActividadTerritorio

    resp = crear_persona("Resp")
    a = crear_actividad("Taller 2025", responsable=resp, objetivo="Alfabetizar")
    ActividadTerritorio.objects.create(actividad=a, comuna=comuna)
    ActividadOrganizacion.objects.create(actividad=a, organizacion=universidad)
    servicios.programar(a, gestor, FUT, time(10), time(11), lugar, None)
    Participacion.objects.create(actividad=a, persona=crear_persona(), rol=rol("voluntario"), estado=estado_part("confirmado"))
    assert "Duplicar" in cg.get(a.get_absolute_url()).content.decode()
    assert a.__class__.objects.count() == 1 and cg.get(f"/actividades/{a.pk}/duplicar").status_code == 200  # GET no crea nada
    r = cg.post(f"/actividades/{a.pk}/duplicar")
    copia = a.__class__.objects.exclude(pk=a.pk).get()
    assert r.status_code == 302 and copia.nombre == "Copia de Taller 2025" and copia.responsable == resp and copia.objetivo == "Alfabetizar"
    assert copia.territorios.count() == 1 and copia.organizaciones.count() == 1
    assert copia.participaciones.count() == 0 and copia.agendas.count() == 0 and copia.estado.codigo == "pendiente"


def test_AT_E7_panel_avisa_actividad_proxima_sin_participantes(cg, crear_actividad, gestor, lugar):
    a = crear_actividad("Mañana vacía")
    servicios.programar(a, gestor, HOY + timedelta(days=1), time(10), time(11), lugar, None)
    html = cg.get("/dashboard").content.decode()
    assert "Próximas sin participantes" in html and "Mañana vacía" in html


def test_AT_E8_aviso_al_agregar_quien_excede(cg, crear_actividad, gestor, lugar, crear_persona, rol, estado_part):
    lugar.capacidad = 1
    lugar.save()
    a = crear_actividad("Chica", estado="planificada")
    servicios.programar(a, gestor, FUT, time(10), time(11), lugar, None)
    Participacion.objects.create(actividad=a, persona=crear_persona(), rol=rol("participante"), estado=estado_part("confirmado"))
    r = cg.post(f"/actividades/{a.pk}/participantes/nuevo", {"persona": crear_persona().pk, "rol": rol("participante").pk, "estado": estado_part("invitado").pk}, follow=True)
    assert "Ahora hay 2 personas para una capacidad de 1" in r.content.decode()


def test_AG_E10_reprogramar_el_mismo_dia_es_ultimo_minuto(cg, crear_actividad, gestor, lugar):
    a = crear_actividad("Hoy")
    servicios.programar(a, gestor, HOY, time(18), time(19), lugar, None)
    nueva = servicios.programar(a, gestor, HOY, time(19), time(20), lugar, None, "Se atrasó la sala")
    assert nueva.ultimo_minuto and Auditoria.objects.filter(accion="reprogramada_ultimo_minuto").exists()
    assert "Último minuto" in cg.get(f"/actividades/{a.pk}?tab=agenda").content.decode()
    otra = crear_actividad("Lejana")
    servicios.programar(otra, gestor, FUT, time(18), time(19), lugar, None)
    assert not servicios.programar(otra, gestor, FUT + timedelta(days=1), time(18), time(19), lugar, None, "x").ultimo_minuto


def test_AG_E11_reprogramar_una_suspendida_la_reanuda(crear_actividad, gestor, lugar):
    a = crear_actividad("Suspendida")
    servicios.programar(a, gestor, FUT, time(10), time(11), lugar, None)
    servicios.cambiar_estado(a, "suspendida", gestor, "lluvia")
    with pytest.raises(ReglaNegocio, match="motivo"):
        servicios.programar(a, gestor, FUT + timedelta(days=7), time(10), time(11), lugar, None)
    servicios.programar(a, gestor, FUT + timedelta(days=7), time(10), time(11), lugar, None, "Pasó la lluvia")
    a.refresh_from_db()
    assert a.estado.codigo == "planificada" and "Reanudada" in a.motivo_estado and a.agendas.count() == 2


def test_AG_E8_fin_de_semana_y_feriado_informativos(crear_actividad, gestor, lugar, settings):
    sabado = HOY + timedelta(days=(5 - HOY.weekday()) % 7 or 7)
    a = crear_actividad("Sábado")
    servicios.programar(a, gestor, sabado, time(10), time(11), lugar, None)
    p = {x.codigo: x for x in revisar(a)}
    assert p["fin_de_semana"].nivel == "info"
    settings.FERIADOS = [sabado.isoformat()]
    assert {x.codigo for x in revisar(a)} >= {"feriado"}


def test_VA_E7_lugar_de_otra_organizacion_pide_confirmar(crear_actividad, gestor, lugar, universidad):
    from apps.actividades.models import ActividadOrganizacion

    lugar.organizacion_propietaria = universidad
    lugar.save()
    a = crear_actividad("En sala ajena")
    servicios.programar(a, gestor, FUT, time(10), time(11), lugar, None)
    assert "lugar_sin_confirmar" in {x.codigo for x in revisar(a)}
    ActividadOrganizacion.objects.create(actividad=a, organizacion=universidad)
    assert "lugar_sin_confirmar" not in {x.codigo for x in revisar(a)}


def test_VA_E9_advertencias_ignoradas_quedan_registradas(cg, crear_actividad, crear_persona, gestor, lugar):
    a = crear_actividad("Sin gente", responsable=crear_persona())
    servicios.programar(a, gestor, FUT, time(10), time(11), lugar, None)
    cg.post(f"/actividades/{a.pk}/confirmar", {"acepto": "1", "motivo_advertencias": "Los inscribimos esta semana"})
    reg = Auditoria.objects.get(accion="confirmada_con_advertencias")
    assert "No hay participantes" in reg.detalle and "Los inscribimos esta semana" in reg.detalle


def test_VA_E3_sin_candidatos_sugiere_aflojar_filtros(cg, actividad):
    html = cg.get(f"/actividades/{actividad.pk}/candidatos?tipo=personas&buscar=1&q=zzzz").content.decode()
    assert "Sin candidatos" in html and "quitar" in html.lower()


def test_LU_E8_actividad_virtual_con_enlace(cg, crear_actividad):
    from apps.nucleo.models import Modalidad

    a = crear_actividad("Live", modalidad=Modalidad.objects.get(codigo="virtual"))
    cg.post(f"/actividades/{a.pk}/programar", {"fecha": FUT, "hora_inicio": "19:00", "modalidad": Modalidad.objects.get(codigo="virtual").pk, "enlace": "https://reunion.ejemplo.invalid/abc"})
    assert a.agenda_vigente.enlace == "https://reunion.ejemplo.invalid/abc"
    assert "enlace virtual" in cg.get(a.get_absolute_url()).content.decode()
    assert "virtual_ok" in {x.codigo for x in revisar(a)}


def test_seccion3_asistencia_y_finalizar_desde_la_fecha(cg, crear_actividad, gestor, lugar, crear_persona, rol, estado_part):
    a = crear_actividad("Futura", responsable=crear_persona(), resultado="x", asistencia_sin_registro=True)
    servicios.programar(a, gestor, FUT, time(10), time(11), lugar, None)
    p = Participacion.objects.create(actividad=a, persona=crear_persona(), rol=rol("participante"), estado=estado_part("confirmado"))
    cg.post(f"/actividades/{a.pk}/asistencia", {f"asistencia_{p.pk}": "si"})
    p.refresh_from_db()
    assert p.asistencia is None
    with pytest.raises(ReglaNegocio, match="desde ese día"):
        servicios.finalizar(a, gestor)
    html = cg.get(f"{a.get_absolute_url()}?tab=asistencia").content.decode()
    assert "desde el día de la actividad" in html


def test_RE_E3_asistencia_tardia_despues_de_finalizar(cg, crear_actividad, gestor, lugar, crear_persona, rol, estado_part):
    a = crear_actividad("Hoy", responsable=crear_persona(), resultado="ok", asistencia_sin_registro=True)
    servicios.programar(a, gestor, HOY, time(10), time(11), lugar, None)
    p = Participacion.objects.create(actividad=a, persona=crear_persona(), rol=rol("participante"), estado=estado_part("confirmado"))
    servicios.finalizar(a, gestor)
    cg.post(f"/actividades/{a.pk}/asistencia", {f"asistencia_{p.pk}": "si"})
    p.refresh_from_db()
    assert p.asistencia is True and Auditoria.objects.filter(accion="asistencia_tardia").exists()
    # en una realizada solo entra la «persona que llegó»
    nueva = crear_persona("Tarde")
    cg.post(f"/actividades/{a.pk}/participantes/nuevo", {"persona": nueva.pk, "rol": rol("participante").pk, "estado": estado_part("invitado").pk})
    assert not a.participaciones.filter(persona=nueva).exists()
    cg.post(f"/actividades/{a.pk}/participantes/nuevo", {"persona": nueva.pk, "rol": rol("participante").pk, "estado": estado_part("invitado").pk, "llego": "1"})
    assert a.participaciones.get(persona=nueva).asistencia is True and Auditoria.objects.filter(accion="registro_tardio").exists()


def test_RE_E5_finalizar_avisa_quienes_quedaron_sin_asistencia(cg, crear_actividad, gestor, lugar, crear_persona, rol, estado_part):
    a = crear_actividad("Hoy", responsable=crear_persona(), resultado="ok")
    servicios.programar(a, gestor, HOY, time(10), time(11), lugar, None)
    ps = [Participacion.objects.create(actividad=a, persona=crear_persona(), rol=rol("participante"), estado=estado_part("confirmado")) for _ in range(3)]
    ps[0].asistencia = True
    ps[0].save()
    r = cg.post(f"/actividades/{a.pk}/finalizar", follow=True)
    assert "2 participante(s) quedaron sin registro de asistencia" in r.content.decode()


def test_RE_E8_se_ve_la_fecha_real_y_la_de_registro(cg, crear_actividad, gestor, lugar, crear_persona):
    a = crear_actividad("Pasada", responsable=crear_persona(), resultado="ok", asistencia_sin_registro=True)
    servicios.programar(a, gestor, HOY - timedelta(days=60), time(10), time(11), lugar, None)
    servicios.finalizar(a, gestor)
    html = cg.get(f"{a.get_absolute_url()}?tab=resultados").content.decode()
    assert f"realizada</strong> el {(HOY - timedelta(days=60)):%d-%m-%Y}" in html and "finalizada en el sistema el" in html


def test_RE_E9_quien_rechazo_pero_asistio(cg, crear_actividad, crear_persona, rol, estado_part):
    a = crear_actividad("Confirmada", estado="confirmada")
    p = Participacion.objects.create(actividad=a, persona=crear_persona("Rechazó"), rol=rol("participante"), estado=estado_part("rechazo"))
    assert "Rechazó" in cg.get(f"{a.get_absolute_url()}?tab=asistencia").content.decode()
    cg.post(f"/actividades/{a.pk}/asistencia", {f"asistencia_{p.pk}": "si"})
    p.refresh_from_db()
    assert p.asistencia is True and p.estado.codigo == "asistio" and p.history.filter(estado__codigo="rechazo").exists()


def test_HI_E2_quitar_participante_por_error(cg, actividad, persona, rol, estado_part):
    p = Participacion.objects.create(actividad=actividad, persona=persona, rol=rol("voluntario"), estado=estado_part("confirmado"))
    assert cg.post(f"/actividades/{actividad.pk}/participantes/{p.pk}/quitar", {"motivo": ""}).status_code == 302
    p.refresh_from_db()
    assert p.estado.codigo == "confirmado"
    cg.post(f"/actividades/{actividad.pk}/participantes/{p.pk}/quitar", {"motivo": "Era otra persona"})
    p.refresh_from_db()
    assert p.estado.codigo == "registro_erroneo" and not p.activa and "Era otra persona" in p.observaciones
    assert Participacion.objects.filter(pk=p.pk).exists() and Auditoria.objects.filter(accion="participacion_quitada").exists()


def test_AT_E13_cancelar_jornada_no_toca_hijas_realizadas(crear_actividad, gestor):
    jornada = crear_actividad("Jornada", estado="planificada")
    hija = crear_actividad("Charla", estado="realizada", actividad_padre=jornada)
    servicios.cambiar_estado(jornada, "cancelada", gestor, "se cayó el auspicio")
    hija.refresh_from_db()
    assert hija.estado.codigo == "realizada"


def test_AT_E14_cancelar_una_sesion_de_la_serie(cg, actividad, lugar, gestor):
    servicios.crear_serie(actividad, gestor, FUT, 7, 8, time(18), time(19), lugar)
    cuarta = list(actividad.hijas.order_by("agendas__fecha"))[3]
    servicios.cambiar_estado(cuarta, "cancelada", gestor, "feriado")
    estados = [h.estado.codigo for h in actividad.hijas.all()]
    assert estados.count("cancelada") == 1 and estados.count("planificada") == 7

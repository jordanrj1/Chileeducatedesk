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

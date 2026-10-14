"""Pruebas automáticas de documentos: subir, tipos y tamaños no permitidos, descarga con permiso y auditoría,
restringidos, archivar sin borrar, asociar sin duplicar el archivo, vencimiento, origen y transcripción."""
import pytest
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.documentos.models import Documento, OrigenDato
from apps.documentos.origen import origenes_de, registrar_origen
from apps.nucleo.models import TipoDocumento

pytestmark = pytest.mark.django_db


_contador = {"n": 0}


def archivo(nombre="minuta.pdf", contenido=None):
    """Cada llamada genera contenido distinto (salvo que se indique), para no activar el aviso de archivo repetido."""
    if contenido is None:
        _contador["n"] += 1
        contenido = b"%PDF-1.4 contenido ficticio " + str(_contador["n"]).encode()
    return SimpleUploadedFile(nombre, contenido, content_type="application/pdf")


def subir(c, actividad=None, **extra):
    datos = {"nombre": "Minuta de reunión", "archivo": archivo(), "tipo": TipoDocumento.objects.get(codigo="minuta").pk, "fecha": "2026-10-01"}
    if actividad is not None:
        datos["actividad"] = actividad.pk
    datos.update(extra)
    return c.post("/documentos/nuevo", datos)


def test_subir_documento_a_una_actividad(cg, actividad):
    r = subir(cg, actividad)
    d = Documento.objects.get()
    assert r.status_code == 302 and "tab=documentos" in r["Location"] and d.actividad == actividad and d.subido_por
    assert "Minuta de reunión" in cg.get(f"/actividades/{actividad.pk}?tab=documentos").content.decode()
    assert d.archivo.read().startswith(b"%PDF")


def test_documento_exige_una_asociacion(cg):
    r = subir(cg)
    assert r.status_code == 200 and not Documento.objects.exists()


def test_archivo_invalido(cg, actividad):
    for malo in (archivo("virus.exe", b"MZ"), archivo("vacio.pdf", b""), archivo("sin_extension", b"x")):
        assert subir(cg, actividad, archivo=malo).status_code == 200
    assert not Documento.objects.exists()


def test_archivo_muy_grande(cg, actividad, monkeypatch):
    import apps.documentos.models as m

    monkeypatch.setattr(m, "TAMANO_MAXIMO_MB", 0)
    # con límite 0 MB cualquier archivo con contenido excede
    assert subir(cg, actividad).status_code == 200 and not Documento.objects.exists()


def test_documento_de_persona_y_organizacion(cg, persona, universidad):
    assert subir(cg, persona=persona.pk).status_code == 302
    assert subir(cg, organizacion=universidad.pk, nombre="Certificado de directorio", tipo=TipoDocumento.objects.get(codigo="certificado").pk).status_code == 302
    assert "Minuta" in cg.get(f"/personas/{persona.pk}?tab=documentos").content.decode()
    assert "Certificado de directorio" in cg.get(f"/organizaciones/{universidad.pk}?tab=documentos").content.decode()


def test_descarga_pasa_por_la_vista_y_queda_en_auditoria(cg, actividad):
    subir(cg, actividad)
    d = Documento.objects.get()
    r = cg.get(f"/documentos/{d.pk}/archivo")
    assert r.status_code == 200 and b"".join(r.streaming_content).startswith(b"%PDF") and r["X-Content-Type-Options"] == "nosniff"
    assert "attachment" in r["Content-Disposition"]
    assert not d.archivo.url.startswith("/static")
    from apps.nucleo.models import Auditoria

    assert Auditoria.objects.filter(accion="documento_descargado").exists()
    assert Client().get(f"/documentos/{d.pk}/archivo").status_code == 302  # sin sesión


def test_documento_restringido_exige_permiso(cg, ca, cs, actividad, gestor, administrador):
    subir(cg, actividad, restringido="on", nombre="Antecedentes")
    d = Documento.objects.get()
    assert d.restringido
    # el Gestor lo ve y descarga
    assert cg.get(f"/documentos/{d.pk}/archivo").status_code == 200
    # un usuario con acceso a documentos pero sin el permiso especial recibe 403 y no lo ve en listados
    administrador.groups.first().permissions.remove(Permission.objects.get(codename="ver_restringido"))
    c = Client()
    c.force_login(type(administrador).objects.get(pk=administrador.pk))
    assert c.get(f"/documentos/{d.pk}/archivo").status_code == 403
    assert c.get(f"/documentos/{d.pk}").status_code == 403
    assert "Antecedentes" not in c.get("/documentos").content.decode()
    assert "Antecedentes" not in c.get(f"/actividades/{actividad.pk}?tab=documentos").content.decode()
    assert c.post(f"/documentos/{d.pk}/alternar").status_code == 403


def test_archivar_no_borra_el_archivo(cg, actividad):
    subir(cg, actividad)
    d = Documento.objects.get()
    cg.post(f"/documentos/{d.pk}/alternar")
    d.refresh_from_db()
    assert d.activo  # sin motivo no se archiva (DO-E9)
    cg.post(f"/documentos/{d.pk}/alternar", {"motivo": "subido por error"})
    d.refresh_from_db()
    assert not d.activo and d.archivo.storage.exists(d.archivo.name)
    assert b"Eliminar" not in cg.get(f"/documentos/{d.pk}").content


def test_listado_con_filtros(cg, actividad):
    subir(cg, actividad, nombre="Carta a la municipalidad", tipo=TipoDocumento.objects.get(codigo="carta").pk)
    subir(cg, actividad, nombre="Ficha de voluntario", tipo=TipoDocumento.objects.get(codigo="ficha").pk)
    assert "Carta a la" in cg.get("/documentos?q=carta").content.decode()
    assert "Ficha de voluntario" not in cg.get("/documentos?q=carta").content.decode()
    carta = TipoDocumento.objects.get(codigo="carta")
    assert "Ficha de voluntario" not in cg.get(f"/documentos?tipo={carta.pk}").content.decode()


# --- origen del dato (F14) ---------------------------------------------------------------------------
def test_origen_al_crear_registros(cg):
    cg.post("/personas/nueva", {"nombres": "Luis"})
    cg.post("/proyectos/nuevo", {"nombre": "P", "estado": "preparacion"})
    cg.post("/actividades/nueva", {"nombre": "A"})
    cg.post("/solicitudes/nueva", {"origen": "solicitud_externa", "fecha": "2026-10-01"})
    assert OrigenDato.objects.filter(fuente="formulario").count() == 4
    assert all(o.registrado_por and o.estado_verificacion == "sin_verificar" for o in OrigenDato.objects.all())


def test_registrar_origen_desde_un_documento_y_verificar(cg, persona, actividad):
    subir(cg, actividad, nombre="Postulación 2025", tipo=TipoDocumento.objects.get(codigo="postulacion").pk)
    d = Documento.objects.get()
    r = cg.post(f"/origen/personas/persona/{persona.pk}/nuevo", {"fuente": "documento", "documento": d.pk, "detalle": "Página 3", "fecha": "2026-10-01", "estado_verificacion": "por_revisar"})
    assert r.status_code == 302
    o = origenes_de(persona).get()
    assert o.documento == d and o.estado_verificacion == "por_revisar"
    assert "Postulación 2025" in cg.get(f"/personas/{persona.pk}?tab=origen").content.decode()
    cg.post(f"/origen/{o.pk}/verificar", {"estado": "verificado"})
    o.refresh_from_db()
    assert o.estado_verificacion == "verificado"
    cg.post(f"/origen/{o.pk}/verificar", {"estado": "inventado"})
    o.refresh_from_db()
    assert o.estado_verificacion == "verificado"
    assert "Postulación 2025" in cg.get(f"/documentos/{d.pk}").content.decode()  # trazabilidad inversa


def test_origen_solo_para_modelos_permitidos(cg, gestor):
    assert cg.get(f"/origen/auth/user/{gestor.pk}/nuevo").status_code == 404
    assert cg.get("/origen/personas/persona/999999/nuevo").status_code == 404


def test_origen_requiere_permiso(ca, cs, persona):
    assert cs.get(f"/origen/personas/persona/{persona.pk}/nuevo").status_code == 403
    assert ca.get(f"/origen/personas/persona/{persona.pk}/nuevo").status_code == 403  # el Administrador solo lee


def test_registrar_origen_helper(persona, gestor):
    registrar_origen(persona, gestor, fuente="llamado", detalle="Llamó el 10-10")
    assert origenes_de(persona).get().get_fuente_display() == "Llamado"


# --- Requerimientos por módulo (DO, IG-05) -----------------------------------------------------------
def test_vencimiento_y_filtros(cg, actividad, persona):
    from datetime import date, timedelta

    hoy = date.today()
    subir(cg, actividad, nombre="Certificado vencido", fecha_vencimiento=str(hoy - timedelta(days=1)))
    subir(cg, actividad, nombre="Certificado por vencer", fecha_vencimiento=str(hoy + timedelta(days=10)))
    subir(cg, persona=persona.pk, nombre="De la persona")
    assert Documento.objects.get(nombre="Certificado vencido").vencido
    html = cg.get("/documentos?vencimiento=vencidos").content.decode()
    assert "Certificado vencido" in html and "por vencer" not in html and "Vencido" in html
    assert "Certificado por vencer" in cg.get("/documentos?vencimiento=por_vencer").content.decode()
    html = cg.get(f"/documentos?persona={persona.pk}").content.decode()
    assert "De la persona" in html and "Certificado vencido" not in html
    assert "De la persona" not in cg.get(f"/documentos?actividad={actividad.pk}").content.decode()


def test_asociar_existente_sin_duplicar_el_archivo(cg, actividad, persona):
    subir(cg, actividad, nombre="Ficha de voluntario")
    original = Documento.objects.get()
    assert "Asociar existente" in cg.get(f"/personas/{persona.pk}?tab=documentos").content.decode()
    r = cg.post("/documentos/asociar", {"persona": persona.pk, "documento": original.pk})
    assert r.status_code == 302
    copia = Documento.objects.exclude(pk=original.pk).get()
    assert copia.persona == persona and copia.archivo.name == original.archivo.name
    archivos = list((original.archivo.storage.path(original.archivo.name).rsplit("/", 1)[0],))
    import os

    assert len(os.listdir(archivos[0])) == 1  # un solo archivo en disco
    cg.post("/documentos/asociar", {"persona": persona.pk, "documento": original.pk})
    assert Documento.objects.count() == 2  # no se asocia dos veces
    assert cg.get("/documentos/asociar").status_code == 404


def test_asociar_no_ofrece_restringidos_sin_permiso(cg, actividad, persona, administrador):
    from django.contrib.auth.models import Permission

    subir(cg, actividad, nombre="Secreto", restringido="on")
    administrador.groups.first().permissions.remove(Permission.objects.get(codename="ver_restringido"))
    administrador.groups.first().permissions.add(Permission.objects.get(codename="add_documento"))
    c = Client()
    c.force_login(type(administrador).objects.get(pk=administrador.pk))
    assert "Secreto" not in c.get(f"/documentos/asociar?persona={persona.pk}").content.decode()


def test_ver_documento_dentro_del_sistema(cg, actividad):
    subir(cg, actividad)
    d = Documento.objects.get()
    r = cg.get(f"/documentos/{d.pk}/ver")
    assert r.status_code == 200 and r["Content-Disposition"] == "inline" and r["X-Frame-Options"] == "SAMEORIGIN"
    subir(cg, actividad, nombre="Planilla", archivo=archivo("lista.xlsx", b"PK ficticio"))
    xl = Documento.objects.get(nombre="Planilla")
    assert cg.get(f"/documentos/{xl.pk}/ver").status_code == 404


def test_transcribir_persona_desde_un_documento(cg, actividad):
    from apps.documentos.origen import origenes_de
    from apps.personas.models import Persona

    subir(cg, actividad, nombre="Minuta con asistentes")
    d = Documento.objects.get()
    html = cg.get(f"/documentos/{d.pk}/transcribir").content.decode()
    assert f"/documentos/{d.pk}/ver" in html and 'name="nombres"' in html
    r = cg.post(f"/documentos/{d.pk}/transcribir", {"registro": "persona", "nombres": "Teresa", "apellido_paterno": "Transcrita", "correo": "t@ejemplo.invalid"})
    p = Persona.objects.get()
    o = origenes_de(p).get()
    assert r.status_code == 302 and o.fuente == "documento" and o.documento == d and o.estado_verificacion == "por_revisar"
    assert p.estado_registro.codigo == "por_verificar" and p.contactos.count() == 1
    r = cg.post(f"/documentos/{d.pk}/transcribir", {"registro": "persona", "nombres": "Teresa", "apellido_paterno": "Transcrita"})
    assert r.status_code == 200 and "Podría ya existir" in r.content.decode() and Persona.objects.count() == 1


def test_transcribir_organizacion(cg, actividad):
    from apps.documentos.origen import origenes_de
    from apps.nucleo.models import TipoOrganizacion
    from apps.organizaciones.models import Organizacion

    subir(cg, actividad, nombre="Carta")
    d = Documento.objects.get()
    assert 'name="naturaleza_juridica"' in cg.get(f"/documentos/{d.pk}/transcribir?registro=organizacion").content.decode()
    junta = TipoOrganizacion.objects.get(codigo="junta_de_vecinos_o_comite")
    r = cg.post(f"/documentos/{d.pk}/transcribir", {"registro": "organizacion", "nombre": "Junta Transcrita", "tipo": junta.pk})
    o = Organizacion.objects.get()
    assert r.status_code == 302 and "registro=organizacion" in r["Location"] and o.tipo == junta
    assert origenes_de(o).get().documento == d
    assert cg.post(f"/documentos/{d.pk}/transcribir", {"registro": "organizacion", "nombre": "Sin tipo"}).status_code == 400


def test_transcribir_requiere_permisos(cs, ca, actividad, cg):
    subir(cg, actividad)
    d = Documento.objects.get()
    assert cs.get(f"/documentos/{d.pk}/transcribir").status_code == 403
    assert ca.get(f"/documentos/{d.pk}/transcribir").status_code == 403  # el Administrador no digita

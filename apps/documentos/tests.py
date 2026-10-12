import pytest
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.documentos.models import Documento, OrigenDato
from apps.documentos.origen import origenes_de, registrar_origen
from apps.nucleo.models import TipoDocumento

pytestmark = pytest.mark.django_db


def archivo(nombre="minuta.pdf", contenido=b"%PDF-1.4 contenido ficticio"):
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

"""F27 A2: consentimiento en un solo documento, contactos compartidos y foto protegida. Datos ficticios."""
import datetime

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documentos.models import Documento
from apps.nucleo.models import Auditoria, TipoContacto, TipoDocumento
from apps.personas.models import Consentimiento, Contacto, Persona

pytestmark = pytest.mark.django_db

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 64


def pdf(nombre="consentimiento.pdf"):
    return SimpleUploadedFile(nombre, b"%PDF-1.4 consentimiento ficticio", content_type="application/pdf")


def tipo(codigo):
    return TipoContacto.objects.get(codigo=codigo)


# --- 4. Consentimiento en un solo documento ---------------------------------------------------------------
def firmar(cg, persona, **extra):
    datos = {"archivo": pdf(), "aut_datos": "on", "aut_imagen": "on", "aut_contacto": "on", "fecha": "2026-11-10", "medio": "papel",
             "otorga": "persona"}
    datos.update(extra)
    return cg.post(f"/personas/{persona.pk}/consentimientos/firmado", datos)


def test_consentimiento_firmado_crea_cuatro_con_el_mismo_documento_y_la_pestana_lo_muestra(cg, persona):
    r = firmar(cg, persona)
    assert r.status_code == 302 and r["Location"].endswith("?tab=consentimientos")
    cs = list(persona.consentimientos.all())
    assert sorted(c.tipo for c in cs) == ["contacto", "datos", "imagen", "sensibles"]
    assert len({c.documento_id for c in cs}) == 1
    doc = cs[0].documento
    assert doc.persona == persona and doc.restringido and doc.tipo.codigo == "consentimiento"
    otorgados = {c.tipo: c.otorgado for c in cs}
    assert otorgados == {"datos": True, "imagen": True, "contacto": True, "sensibles": False}  # la no marcada queda «no otorgado»
    assert persona.consentimiento_vigente("imagen") and not persona.consentimiento_vigente("sensibles")
    html = cg.get(f"/personas/{persona.pk}?tab=consentimientos").content.decode()
    assert "Documento firmado:" in html and f"/documentos/{doc.pk}/archivo" in html  # enlace protegido, no /media
    assert "No otorgado" in html and "+ Registrar consentimiento firmado" in html
    assert "/media/" not in html


def test_consentimiento_firmado_con_documento_existente_y_apoderado(cg, persona, crear_persona):
    madre = crear_persona("Madre Ficticia")
    doc = Documento.objects.create(nombre="Ficha firmada", archivo=pdf(), tipo=TipoDocumento.objects.get(codigo="ficha"), persona=persona)
    r = cg.post(f"/personas/{persona.pk}/consentimientos/firmado", {"documento": doc.pk, "aut_datos": "on", "fecha": "2026-11-10",
                                                                    "medio": "papel", "otorga": "apoderado", "otorgado_por": madre.pk})
    assert r.status_code == 302
    assert set(persona.consentimientos.values_list("documento_id", flat=True)) == {doc.pk}
    assert set(persona.consentimientos.values_list("otorgado_por_id", flat=True)) == {madre.pk}
    assert Documento.objects.filter(persona=persona).count() == 1  # no se copió el archivo


def test_consentimiento_firmado_exige_documento_y_respeta_datos_sensibles(cg, persona, settings):
    r = cg.post(f"/personas/{persona.pk}/consentimientos/firmado", {"aut_datos": "on", "fecha": "2026-11-10", "medio": "papel", "otorga": "persona"})
    assert r.status_code == 200 and "Sube el documento firmado" in r.content.decode()
    assert not persona.consentimientos.exists()
    settings.DATOS_SENSIBLES = False
    assert 'name="aut_sensibles"' not in cg.get(f"/personas/{persona.pk}/consentimientos/firmado").content.decode()
    firmar(cg, persona)
    assert sorted(persona.consentimientos.values_list("tipo", flat=True)) == ["contacto", "datos", "imagen"]


def test_consentimiento_firmado_sin_permiso_403(cs, persona):
    assert cs.get(f"/personas/{persona.pk}/consentimientos/firmado").status_code == 403


def test_revocar_una_autorizacion_no_afecta_a_las_otras(cg, persona):
    firmar(cg, persona)
    imagen = persona.consentimientos.get(tipo="imagen")
    r = cg.post(f"/personas/{persona.pk}/consentimientos/{imagen.pk}/editar", {
        "tipo": "imagen", "otorgado": "on", "fecha": "2026-11-10", "medio": "papel", "documento": imagen.documento_id, "revocado_en": "2026-11-12"})
    assert r.status_code == 302
    assert not persona.consentimiento_vigente("imagen")
    assert persona.consentimiento_vigente("datos") and persona.consentimiento_vigente("contacto")
    assert Consentimiento.objects.filter(persona=persona).count() == 4  # se revoca, no se borra


# --- 6. Contactos repetidos ---------------------------------------------------------------------------------
@pytest.fixture
def otra(crear_persona):
    p = crear_persona("Otra Ficticia")
    Contacto.objects.create(persona=p, tipo=tipo("telefono_movil"), valor="+56 9 1111 2222")
    return p


def test_contacto_repetido_avisa_y_no_guarda(cg, persona, otra):
    r = cg.post(f"/personas/{persona.pk}/contactos/nuevo", {"tipo": tipo("telefono_movil").pk, "valor": "9 1111 2222"})
    html = r.content.decode()
    assert r.status_code == 200 and not persona.contactos.exists()
    assert "Este contacto ya lo tiene" in html and otra.get_absolute_url() in html
    assert "Es la misma persona" in html and "Es otra persona que comparte este contacto" in html and "Cancelar" in html
    assert 'name="compartir-motivo"' in html


def test_contacto_compartido_guarda_con_motivo_y_queda_en_auditoria(cg, persona, otra, gestor):
    datos = {"tipo": tipo("telefono_movil").pk, "valor": "+56911112222", "compartir": "1"}
    r = cg.post(f"/personas/{persona.pk}/contactos/nuevo", datos)  # sin motivo: no guarda
    assert r.status_code == 200 and not persona.contactos.exists() and "Elige por qué lo comparten" in r.content.decode()
    r = cg.post(f"/personas/{persona.pk}/contactos/nuevo", {**datos, "compartir-motivo": "familiar", "compartir-nota": "teléfono de la casa"})
    assert r.status_code == 302
    c = persona.contactos.get()
    assert c.compartido and c.motivo_compartido == "familiar" and c.nota_compartido == "teléfono de la casa"
    a = Auditoria.objects.get(accion="contacto_compartido")
    assert a.usuario == gestor and a.fecha and "Familiar" in a.detalle and "Otra Ficticia" in a.detalle
    html = cg.get(f"/personas/{persona.pk}?tab=contacto").content.decode()
    assert "Compartido con:" in html and otra.get_absolute_url() in html and "Motivo: Familiar (teléfono de la casa)" in html
    # editar sin cambiar el valor no vuelve a preguntar
    r = cg.post(f"/personas/{persona.pk}/contactos/{c.pk}/editar", {"tipo": tipo("telefono_movil").pk, "valor": "+56911112222", "proposito": "casa", "vigente": "on"})
    assert r.status_code == 302


def test_contacto_misma_persona_sin_permiso_de_fusion(cg, persona, otra):
    # el Gestor (sin permiso de fusión) ve la ficha de la otra persona y que se le pida al Administrador
    html = cg.post(f"/personas/{persona.pk}/contactos/nuevo", {"tipo": tipo("telefono_movil").pk, "valor": "+56911112222"}).content.decode()
    assert otra.get_absolute_url() in html and "pídeselo al Administrador" in html


def test_contacto_misma_persona_con_permiso_de_fusion(persona, otra, gestor, client):
    from django.contrib.auth.models import Permission

    gestor.user_permissions.add(Permission.objects.get(codename="fusionar_persona"))
    client.force_login(gestor)
    html = client.post(f"/personas/{persona.pk}/contactos/nuevo", {"tipo": tipo("telefono_movil").pk, "valor": "+56911112222"}).content.decode()
    assert f'href="/personas/{persona.pk}/fusionar"' in html and "Unir fichas" in html


def test_contacto_de_organizacion_no_se_compara_con_personas(cg, universidad, otra):
    r = cg.post(f"/organizaciones/{universidad.pk}/contactos/nuevo", {"tipo": tipo("telefono_movil").pk, "valor": "+56911112222"})
    assert r.status_code == 302


def test_crear_persona_igual_deja_el_contacto_compartido(cg, otra):
    datos = {"modo": "rapida", "nombres": "Nueva Ficticia", "apellido_paterno": "Prueba", "telefono": "+56 9 1111 2222"}
    r = cg.post("/personas/nueva", datos)
    assert r.status_code == 200 and not Persona.objects.filter(nombres="Nueva Ficticia").exists()  # aviso de posible duplicado
    r = cg.post("/personas/nueva", {**datos, "confirmar_duplicado": "1", "nota_distincion": "es la hija; comparten el teléfono"})
    assert r.status_code == 302
    c = Persona.objects.get(nombres="Nueva Ficticia").contactos.get()
    assert c.compartido and c.motivo_compartido == "otro" and c.nota_compartido == "es la hija; comparten el teléfono"
    assert Auditoria.objects.filter(accion="contacto_compartido").exists()


# --- 5. Foto (datos y servidor) -----------------------------------------------------------------------------
def subir_foto(c, persona, contenido=PNG, nombre="foto.png"):
    return c.post(f"/personas/{persona.pk}/foto/editar", {"foto": SimpleUploadedFile(nombre, contenido)})


@pytest.mark.parametrize("contenido,nombre", [(PNG, "a.png"), (JPG, "a.jpg"), (WEBP, "a.webp")])
def test_foto_valida_se_guarda_fuera_del_codigo_con_nombre_aleatorio(cg, persona, settings, contenido, nombre):
    assert subir_foto(cg, persona, contenido, nombre).status_code == 302
    persona.refresh_from_db()
    base = persona.foto.name.split("/")[-1]
    assert persona.foto.name.startswith("personas/fotos/") and len(base.split(".")[0]) == 32  # sin el nombre original
    assert str(settings.MEDIA_ROOT) in persona.foto.path
    assert Auditoria.objects.filter(accion="foto_subida").exists()


@pytest.mark.parametrize("contenido,nombre,mensaje", [
    (b"<html>no soy imagen</html>" * 3, "falsa.png", "no es una imagen"),
    (PNG, "foto.gif", "JPG, PNG o WEBP"),
    (JPG, "foto.png", "no es una imagen"),  # la extensión no coincide con el contenido
    (PNG + b"\x00" * (3 * 1024 * 1024), "grande.png", "3 MB"),
])
def test_foto_invalida_se_rechaza(cg, persona, contenido, nombre, mensaje):
    r = subir_foto(cg, persona, contenido, nombre)
    assert r.status_code == 200 and mensaje in r.content.decode()
    persona.refresh_from_db()
    assert not persona.foto


def test_foto_de_menor_exige_consentimiento_de_imagen(cg, persona):
    persona.fecha_nacimiento = datetime.date.today().replace(year=datetime.date.today().year - 12)
    persona.save()
    r = subir_foto(cg, persona)
    assert r.status_code == 200 and "Es menor de edad" in r.content.decode()
    persona.refresh_from_db()
    assert not persona.foto
    Consentimiento.objects.create(persona=persona, tipo="imagen", otorgado=True, fecha=datetime.date.today())
    assert subir_foto(cg, persona).status_code == 302


def test_foto_vista_protegida_y_sin_acceso_por_media(cg, cs, persona, client):
    subir_foto(cg, persona)
    persona.refresh_from_db()
    r = cg.get(f"/personas/{persona.pk}/foto")
    assert r.status_code == 200 and r["Content-Type"] == "image/png" and r["X-Content-Type-Options"] == "nosniff"
    assert b"".join(r.streaming_content).startswith(b"\x89PNG")
    assert cs.get(f"/personas/{persona.pk}/foto").status_code == 403
    assert client.get(f"/personas/{persona.pk}/foto").status_code in (302, 403)  # sin sesión: al ingreso
    assert cg.get(f"/media/{persona.foto.name}").status_code == 404
    html = cg.get(f"/personas/{persona.pk}").content.decode()
    assert "Cambiar o quitar la foto" in html


def test_quitar_foto_borra_el_archivo_si_nadie_lo_usa(cg, persona, crear_persona):
    subir_foto(cg, persona)
    persona.refresh_from_db()
    nombre, ruta = persona.foto.name, persona.foto.path
    otra = crear_persona("Fusionada Ficticia")
    Persona.objects.filter(pk=otra.pk).update(foto=nombre)  # como tras una fusión: dos fichas con el mismo archivo
    assert cg.post(f"/personas/{persona.pk}/foto/editar", {"quitar": "1"}).status_code == 302
    persona.refresh_from_db()
    import os

    assert not persona.foto and os.path.exists(ruta)  # lo sigue usando la otra ficha
    assert cg.post(f"/personas/{otra.pk}/foto/editar", {"quitar": "1"}).status_code == 302
    assert not os.path.exists(ruta)
    assert cg.get(f"/personas/{persona.pk}/foto").status_code == 404

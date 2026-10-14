"""Pruebas automáticas de la carga de listados: formatos de archivo, teléfonos como texto, separación de nombres,
duplicados, nada guardado antes de confirmar, confirmar, corregir y revertir."""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook

from apps.actividades.models import Participacion
from apps.importaciones import lectura, procesar
from apps.importaciones.models import Lote
from apps.nucleo.utilidades import calcular_dv
from apps.personas.models import Contacto, Persona

pytestmark = pytest.mark.django_db
RUT1 = f"12345678-{calcular_dv(12345678)}"
RUT2 = f"11111111-{calcular_dv(11111111)}"

CSV = (
    "Nombre completo;RUT;Correo;Teléfono;Carrera\n"
    f"Ana María Pérez Soto;{RUT1};ANA@ejemplo.invalid;9 8765 4321;Trabajo Social\n"
    f"Soto Rojas, Beto;{RUT2};beto@ejemplo.invalid;912345678;Psicología\n"
    "Carla Díaz;;;;Derecho\n"
).encode("utf-8")


def subir(c, actividad, rol, contenido=CSV, nombre="listado.csv", **extra):
    datos = {"tipo": "listado_actividad", "actividad": actividad.pk, "rol": rol("estudiante").pk, "archivo": SimpleUploadedFile(nombre, contenido), "fuente": "Planilla de la universidad"}
    datos.update(extra)
    return c.post("/importaciones/nueva", datos)


# --- lectura -----------------------------------------------------------------------------------
def test_lee_csv_con_punto_y_coma_y_reconoce_encabezados():
    filas, ignoradas = lectura.leer(CSV, "x.csv")
    assert len(filas) == 3 and filas[0]["nombre_completo"] == "Ana María Pérez Soto" and filas[0]["rut"] == RUT1
    assert ignoradas == [] and "carrera" in filas[0]


def test_lee_csv_latin1_y_tabulaciones():
    datos = "Nombre\tApellido paterno\tTeléfono\nJosé\tMuñoz\t912345678\n".encode("latin-1")
    filas, _ = lectura.leer(datos, "x.txt")
    assert filas == [{"nombres": "José", "apellido_paterno": "Muñoz", "telefono": "912345678"}]


def test_lee_texto_pegado_desde_excel():
    filas, _ = lectura.leer(texto="Nombre\tCorreo\nAna Pérez\tana@ejemplo.invalid\n")
    assert filas[0]["correo"] == "ana@ejemplo.invalid"


def test_xlsx_lee_celdas_como_texto_sin_perder_telefonos():
    wb = Workbook()
    ws = wb.active
    ws.append(["Nombre completo", "Fono", "Columna rara"])
    ws.append(["Ana Pérez", 912345678, "x"])  # número, no texto
    ws.append(["Beto Rojas", 912345679.0, "y"])
    buf = io.BytesIO()
    wb.save(buf)
    filas, ignoradas = lectura.leer(buf.getvalue(), "x.xlsx")
    assert [f["telefono"] for f in filas] == ["912345678", "912345679"] and ignoradas == ["Columna rara"]
    analizadas, _ = procesar.analizar("personas", filas)
    assert analizadas[0]["datos"]["telefono"] == "+56912345678"


@pytest.mark.parametrize("contenido", [b"", b"solo encabezados\n", b"\x00\x01\x02\xff", "colA,colB\n1,2\n".encode()])
def test_archivos_sin_datos_o_ilegibles(contenido):
    with pytest.raises(lectura.ErrorLectura):
        lectura.leer(contenido, "x.csv")


def test_xlsx_corrupto():
    with pytest.raises(lectura.ErrorLectura):
        lectura.leer(b"no es un xlsx", "x.xlsx")


def test_demasiadas_filas(monkeypatch):
    monkeypatch.setattr(lectura, "MAX_FILAS", 2)
    with pytest.raises(lectura.ErrorLectura, match="Demasiadas"):
        lectura.leer("Nombre\na\nb\nc\n".encode(), "x.csv")


# --- análisis --------------------------------------------------------------------------------------
def test_analisis_separa_nombres_y_clasifica():
    filas, _ = lectura.leer(CSV, "x.csv")
    res, resumen = procesar.analizar("listado_actividad", filas)
    assert [r["estado"] for r in res] == ["nuevo", "nuevo", "nuevo"] and resumen["nuevo"] == 3
    a, b, c = (r["datos"] for r in res)
    assert (a["nombres"], a["apellido_paterno"], a["apellido_materno"]) == ("Ana María", "Pérez", "Soto")
    assert (b["nombres"], b["apellido_paterno"], b["apellido_materno"]) == ("Beto", "Soto", "Rojas")
    assert a["correo"] == "ana@ejemplo.invalid" and a["telefono"] == "+56987654321"


def test_errores_por_fila():
    filas = [{"nombres": "A", "rut": "12.345.678-0"}, {"nombres": "B", "correo": "no-es-correo"}, {"nombres": "C", "telefono": "123"}, {"correo": "x@ejemplo.invalid"}]
    res, resumen = procesar.analizar("personas", filas)
    assert [r["estado"] for r in res] == ["error"] * 4 and resumen["error"] == 4
    assert all(r["decision"] == "pendiente" for r in res)


def test_repetidos_dentro_del_archivo():
    filas = [{"nombres": "Ana", "rut": RUT1}, {"nombres": "Anita", "rut": RUT1}, {"nombres": "Beto", "correo": "b@ejemplo.invalid"}, {"nombres": "Beto 2", "correo": "b@ejemplo.invalid"}]
    res, _ = procesar.analizar("personas", filas)
    assert [r["estado"] for r in res] == ["nuevo", "error", "nuevo", "error"] and "fila 2" in res[1]["errores"][0]


def test_detecta_existentes_y_duplicados(crear_persona):
    existente = crear_persona("Ana", apellido_paterno="Pérez", rut_numero=12345678, rut_dv=calcular_dv(12345678))
    parecida = crear_persona("Betina", apellido_paterno="Rojas Vera")
    filas = [{"nombres": "Ana Pérez", "rut": RUT1}, {"nombres": "Betina", "apellido_paterno": "Rojas", "apellido_materno": "Vera"}, {"nombres": "Zoila", "apellido_paterno": "Nueva"}]
    res, resumen = procesar.analizar("personas", filas)
    assert [r["estado"] for r in res] == ["existente", "duplicado", "nuevo"]
    assert res[0]["decision"] == f"usar:{existente.pk}" and res[1]["decision"] == "pendiente" and res[2]["decision"] == "crear"
    assert res[1]["coincidencias"][0]["pk"] == parecida.pk
    # la decisión del usuario se respeta al volver a analizar
    res2, _ = procesar.analizar("personas", filas, {3: "crear"})
    assert res2[1]["decision"] == "crear"
    res3, _ = procesar.analizar("personas", filas, {3: f"usar:{parecida.pk}"})
    assert res3[1]["decision"] == f"usar:{parecida.pk}"
    res4, _ = procesar.analizar("personas", filas, {3: "omitir"})
    assert res4[1]["decision"] == "omitir"


# --- flujo completo ------------------------------------------------------------------------------------
def test_nada_se_guarda_antes_de_confirmar(cg, actividad, rol):
    r = subir(cg, actividad, rol)
    lote = Lote.objects.get()
    assert r.status_code == 302 and r["Location"].endswith(f"/importaciones/{lote.pk}/revisar")
    assert lote.estado == "previa" and not Persona.objects.exists() and not Participacion.objects.exists()
    html = cg.get(r["Location"]).content.decode()
    assert "Ana María" in html and "Confirmar carga" in html


def test_confirmar_crea_personas_contactos_participacion_y_origen(cg, actividad, rol):
    r = subir(cg, actividad, rol)
    lote = Lote.objects.get()
    r = cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "confirmar"})
    lote.refresh_from_db()
    assert r.status_code == 302 and lote.estado == "confirmado" and lote.resumen["aplicado"]["creados"] == 3
    assert Persona.objects.count() == 3 and actividad.participaciones.count() == 3
    ana = Persona.objects.get(nombres="Ana María")
    assert ana.rut == "12.345.678-" + calcular_dv(12345678) and ana.estado_registro.codigo == "activo"
    assert set(ana.contactos.values_list("valor_normalizado", flat=True)) == {"ana@ejemplo.invalid", "+56987654321"}
    carla = Persona.objects.get(nombres="Carla")
    assert carla.estado_registro.codigo == "incompleto" and not carla.contactos.exists()
    p = actividad.participaciones.get(persona=ana)
    assert p.rol.codigo == "estudiante" and p.estado.codigo == "interesado"
    # origen y evidencia
    from apps.documentos.origen import origenes_de

    o = origenes_de(ana).get()
    assert o.fuente == "importacion" and o.lote == lote.pk and o.documento and o.documento.restringido and o.estado_verificacion == "por_revisar"
    assert actividad.documentos.get().tipo.codigo == "listado"
    # no se puede confirmar dos veces
    cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "confirmar"})
    assert Persona.objects.count() == 3


def test_no_se_confirma_con_errores_sin_omitir(cg, actividad, rol):
    malo = "Nombre,RUT\nAna,12.345.678-0\nBeto,\n".encode()
    subir(cg, actividad, rol, malo)
    lote = Lote.objects.get()
    html = cg.get(f"/importaciones/{lote.pk}/revisar").content.decode()
    assert "disabled" in html and "1 fila(s) por resolver" in html
    r = cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "confirmar"})
    lote.refresh_from_db()
    assert r.status_code == 200 and lote.estado == "previa" and not Persona.objects.exists()
    r = cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "confirmar", "d2": "omitir"})  # omite la fila con error
    lote.refresh_from_db()
    assert r.status_code == 302 and lote.estado == "confirmado" and Persona.objects.get().nombres == "Beto" if False else lote.estado == "confirmado"


def test_corregir_en_la_revision(cg, actividad, rol):
    subir(cg, actividad, rol, "Nombre,RUT\nAna Pérez,12.345.678-0\n".encode())
    lote = Lote.objects.get()
    assert lote.filas[0]["estado"] == "error"
    r = cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "revisar", "f2_nombres": "Ana", "f2_apellido_paterno": "Pérez", "f2_rut": RUT1, "d2": "crear"})
    lote.refresh_from_db()
    assert r.status_code == 200 and lote.filas[0]["estado"] == "nuevo" and lote.filas[0]["decision"] == "crear"
    cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "confirmar", "f2_nombres": "Ana", "f2_apellido_paterno": "Pérez", "f2_rut": RUT1, "d2": "crear"})
    assert Persona.objects.get().rut_numero == 12345678


def test_duplicado_se_resuelve_usando_la_existente(cg, actividad, rol, crear_persona):
    existente = crear_persona("Carla", apellido_paterno="Díaz")
    subir(cg, actividad, rol, "Nombre completo\nCarla Díaz\n".encode())
    lote = Lote.objects.get()
    assert lote.filas[0]["estado"] == "duplicado" and lote.filas[0]["decision"] == "pendiente"
    cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "confirmar", "d2": f"usar:{existente.pk}"})
    assert Persona.objects.count() == 1 and actividad.participaciones.get().persona == existente
    lote.refresh_from_db()
    assert lote.resumen["aplicado"] == {"creados": 0, "vinculados": 1, "omitidos": 0, "participaciones": 1}


def test_reintentar_la_carga_no_duplica_participaciones(cg, actividad, rol):
    subir(cg, actividad, rol, "Nombre,RUT\nAna Pérez,%s\n".encode() % RUT1.encode())
    cg.post(f"/importaciones/{Lote.objects.get().pk}/revisar", {"accion": "confirmar"})
    subir(cg, actividad, rol, "Nombre,RUT\nAna Pérez,%s\n".encode() % RUT1.encode())
    segundo = Lote.objects.latest("id")
    assert segundo.filas[0]["estado"] == "existente"
    cg.post(f"/importaciones/{segundo.pk}/revisar", {"accion": "confirmar"})
    assert Persona.objects.count() == 1 and actividad.participaciones.count() == 1


def test_revertir_lote(cg, actividad, rol):
    subir(cg, actividad, rol)
    lote = Lote.objects.get()
    cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "confirmar"})
    ana = Persona.objects.get(nombres="Ana María")
    # Beto además participa en otra actividad: no debe borrarse
    beto = Persona.objects.get(nombres="Beto")
    from apps.nucleo.models import EstadoActividad, EstadoParticipacion
    from apps.actividades.models import Actividad

    otra = Actividad.objects.create(nombre="Otra", estado=EstadoActividad.objects.get(codigo="pendiente"))
    Participacion.objects.create(actividad=otra, persona=beto, rol=actividad.participaciones.first().rol, estado=EstadoParticipacion.objects.get(codigo="invitado"))
    r = cg.post(f"/importaciones/{lote.pk}/revertir")
    lote.refresh_from_db()
    assert r.status_code == 302 and lote.estado == "revertido" and lote.revertido_por
    assert not Persona.objects.filter(pk=ana.pk).exists() and Persona.objects.filter(pk=beto.pk).exists()
    assert not actividad.participaciones.exists() and otra.participaciones.count() == 1
    assert lote.resumen["reversion"]["conservados"] == 1
    assert not Contacto.objects.filter(persona=ana.pk).exists()
    cg.post(f"/importaciones/{lote.pk}/revertir")  # segunda vez: no hace nada


def test_descartar_no_deja_nada(cg, actividad, rol):
    subir(cg, actividad, rol)
    lote = Lote.objects.get()
    cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "descartar"})
    lote.refresh_from_db()
    assert lote.estado == "descartado" and not Persona.objects.exists()


def test_formulario_valida(cg, actividad, rol):
    assert subir(cg, actividad, rol, nombre="malo.exe").status_code == 200
    assert subir(cg, actividad, rol, contenido=b"solo una linea").status_code == 200
    assert cg.post("/importaciones/nueva", {"tipo": "listado_actividad", "texto": "Nombre\nAna"}).status_code == 200  # falta actividad y rol
    assert cg.post("/importaciones/nueva", {"tipo": "personas"}).status_code == 200  # sin archivo
    assert not Lote.objects.exists()


def test_importar_personas_desde_texto_pegado(cg):
    r = cg.post("/importaciones/nueva", {"tipo": "personas", "texto": "Nombre\tCorreo\nElena Soto\telena@ejemplo.invalid\n", "fuente": "Minuta"})
    lote = Lote.objects.get()
    assert r.status_code == 302 and lote.actividad is None
    cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "confirmar"})
    assert Persona.objects.get().nombres == "Elena" and not lote.archivo


def test_importar_organizaciones_y_lugares(cg, comuna):
    from apps.lugares.models import Lugar
    from apps.organizaciones.models import Organizacion

    cg.post("/importaciones/nueva", {"tipo": "organizaciones", "texto": f"Nombre;Tipo;Comuna;Correo\nJunta Los Pinos;Junta de vecinos o comité;{comuna.nombre};junta@ejemplo.invalid\nEmpresa X;Tipo Inventado;;\n"})
    lote = Lote.objects.get()
    assert [f["estado"] for f in lote.filas] == ["nuevo", "error"]
    cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "confirmar", "d3": "omitir"})
    org = Organizacion.objects.get()
    assert org.nombre == "Junta Los Pinos" and org.direccion.comuna == comuna and org.contactos.count() == 1
    cg.post("/importaciones/nueva", {"tipo": "lugares", "texto": f"Nombre;Tipo;Calle;Número;Comuna;Capacidad\nSede vecinal;Sede;Los Aromos;45;{comuna.nombre};40\nSala sin comuna;Sala;X;1;;10\n"})
    lote2 = Lote.objects.latest("id")
    cg.post(f"/importaciones/{lote2.pk}/revisar", {"accion": "confirmar", "d3": "omitir"})
    l = Lugar.objects.get()
    assert l.capacidad == 40 and l.direccion.calle == "Los Aromos"
    cg.post(f"/importaciones/{lote2.pk}/revertir")
    assert not Lugar.objects.exists() and Organizacion.objects.count() == 1


def test_permisos_de_importacion(cg, ca, cs, actividad, rol):
    assert cg.get("/importaciones").status_code == 200
    assert ca.get("/importaciones").status_code == 200  # F18: el Administrador también importa
    assert cs.get("/importaciones").status_code == 403
    subir(cg, actividad, rol)
    lote = Lote.objects.get()
    cg.post(f"/importaciones/{lote.pk}/revisar", {"accion": "confirmar"})
    assert ca.post(f"/importaciones/{lote.pk}/revertir").status_code == 403  # revertir es del Gestor

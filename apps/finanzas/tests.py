"""Pruebas automáticas de finanzas (2.ª fase): permisos, montos positivos, anular sin borrar y presupuesto por proyecto."""
import pytest
from django.db import IntegrityError, transaction

from apps.finanzas.models import ItemPresupuesto, Movimiento
from apps.finanzas.resumen import resumen_proyecto
from apps.proyectos.models import Proyecto

pytestmark = pytest.mark.django_db


@pytest.fixture
def proyecto(db):
    return Proyecto.objects.create(nombre="Proyecto con plata")


def mov(c, proyecto, **extra):
    datos = {"proyecto": proyecto.pk, "tipo": "gasto", "monto": 50000, "fecha": "2026-10-01", "concepto": "Materiales"}
    datos.update(extra)
    return c.post("/finanzas/nuevo", datos)


def test_solo_usuarios_autorizados(cg, ca, cs, proyecto):
    assert cg.get("/finanzas").status_code == 200
    assert ca.get("/finanzas").status_code == 403  # el Administrador no tiene finanzas por defecto
    assert cs.get("/finanzas").status_code == 403
    assert ca.get(f"/proyectos/{proyecto.pk}?tab=presupuesto").status_code == 403 or b"Presupuesto" not in ca.get(f"/proyectos/{proyecto.pk}").content


def test_el_administrador_puede_recibir_el_permiso(ca, administrador, proyecto):
    from django.contrib.auth.models import Permission

    administrador.groups.first().permissions.add(Permission.objects.get(codename="view_movimiento"))
    c = type(ca)()
    c.force_login(type(administrador).objects.get(pk=administrador.pk))
    assert c.get("/finanzas").status_code == 200
    assert c.get("/finanzas/nuevo").status_code == 403  # solo lectura


def test_registrar_gasto_y_resumen(cg, proyecto):
    assert mov(cg, proyecto).status_code == 302
    ItemPresupuesto.objects.create(proyecto=proyecto, concepto="Honorarios", monto_estimado=300000, categoria="recursos_humanos")
    ItemPresupuesto.objects.create(proyecto=proyecto, concepto="Folletos", monto_estimado=80000)
    r = resumen_proyecto(proyecto)
    assert (r["presupuestado"], r["gastado"], r["saldo"]) == (380000, 50000, -50000)


def test_aporte_y_donacion_exigen_quien_aporta(cg, proyecto, crear_persona, universidad):
    assert mov(cg, proyecto, tipo="aporte").status_code == 200
    assert mov(cg, proyecto, tipo="donacion", persona=crear_persona("Donante").pk, monto=100000, concepto="Donación").status_code == 302
    assert mov(cg, proyecto, tipo="aporte", organizacion=universidad.pk, monto=200000, concepto="Aporte institucional").status_code == 302
    r = resumen_proyecto(proyecto)
    assert (r["aportes"], r["donaciones"], r["saldo"]) == (200000, 100000, 300000)


def test_monto_positivo(cg, proyecto):
    assert mov(cg, proyecto, monto=0).status_code == 200 and mov(cg, proyecto, monto=-5).status_code == 200
    with pytest.raises(IntegrityError), transaction.atomic():
        Movimiento.objects.create(proyecto=proyecto, tipo="gasto", monto=0, concepto="x")


def test_anular_no_borra_y_no_cuenta(cg, proyecto):
    mov(cg, proyecto)
    m = Movimiento.objects.get()
    assert cg.post(f"/finanzas/{m.pk}/anular", {"motivo": ""}).status_code == 302
    m.refresh_from_db()
    assert not m.anulado
    cg.post(f"/finanzas/{m.pk}/anular", {"motivo": "Factura duplicada"})
    m.refresh_from_db()
    assert m.anulado and resumen_proyecto(proyecto)["gastado"] == 0 and Movimiento.objects.count() == 1
    r = cg.post(f"/finanzas/{m.pk}/editar", {"proyecto": proyecto.pk, "tipo": "gasto", "monto": 1, "fecha": "2026-10-01", "concepto": "cambio"})
    m.refresh_from_db()
    assert m.monto == 50000  # anulado: no se edita
    assert "Factura duplicada" in cg.get(f"/finanzas/{m.pk}").content.decode()


def test_respaldo_documental_y_historial(cg, proyecto):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.documentos.models import Documento
    from apps.nucleo.models import TipoDocumento

    d = Documento.objects.create(nombre="Boleta", archivo=SimpleUploadedFile("boleta.pdf", b"%PDF-1"), tipo=TipoDocumento.objects.get(codigo="otro"), proyecto=proyecto, restringido=True)
    mov(cg, proyecto, documento=d.pk)
    m = Movimiento.objects.get()
    assert m.documento == d and "Boleta" in cg.get(f"/finanzas/{m.pk}").content.decode()
    cg.post(f"/finanzas/{m.pk}/editar", {"proyecto": proyecto.pk, "tipo": "gasto", "monto": 60000, "fecha": "2026-10-01", "concepto": "Materiales", "documento": d.pk})
    assert "Modificación" in cg.get(f"/finanzas/{m.pk}?tab=historial").content.decode()


def test_presupuesto_por_proyecto_y_listado(cg, proyecto):
    r = cg.post(f"/finanzas/proyectos/{proyecto.pk}/items/nuevo", {"categoria": "materiales", "concepto": "Cuadernos", "monto_estimado": 120000, "vigente": "on"})
    assert r.status_code == 302 and "tab=presupuesto" in r["Location"]
    mov(cg, proyecto)
    html = cg.get(f"/proyectos/{proyecto.pk}?tab=presupuesto").content.decode()
    assert "Cuadernos" in html and "120000" in html.replace(".", "").replace(",", "")
    lista = cg.get(f"/finanzas?proyecto={proyecto.pk}").content.decode()
    assert "Saldo" in lista and "Materiales" in lista
    assert cg.get("/finanzas/exportar").status_code == 200

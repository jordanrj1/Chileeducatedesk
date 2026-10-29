"""F26 P1b: solicitud → actividad en un paso (con «Programar ahora»), tarea desde una solicitud convertida en proyecto,
pestañas por estado en Solicitudes, la primera interacción pasa a «en seguimiento», «Para hoy y vencidas» en el Inicio
(con número fijo de consultas), finalizar exige fecha, menú (Lista | Calendario, historial de cargas, «+ Nuevo») y un
solo botón de filtros. Datos ficticios."""
import re
from datetime import date, time, timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.actividades.models import Actividad, ActividadOrganizacion, AgendaActividad
from apps.nucleo.models import Canal, EstadoActividad, EstadoSolicitud
from apps.solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db
HOY = date.today()


def _solicitud(motivo="Taller de huertos inventado", estado="pendiente", **kw):
    return Solicitud.objects.create(motivo=motivo, estado=EstadoSolicitud.objects.get(codigo=estado), **kw)


# --- 1. Solicitud → actividad en un paso -----------------------------------------------------------------------------
def test_crear_actividad_abre_formulario_relleno_y_programa_en_un_paso(cg, universidad, crear_persona, lugar):
    contacto = crear_persona("Contacto")
    s = _solicitud(persona=contacto, organizacion=universidad)
    r = cg.get(f"/solicitudes/{s.pk}/crear-actividad")
    assert r.status_code == 302 and r["Location"] == f"/actividades/nueva?solicitud={s.pk}"
    html = cg.get(r["Location"]).content.decode()
    assert 'value="Taller de huertos inventado"' in html and "Programar ahora" in html and "Universidad Ficticia" in html
    r = cg.post(r["Location"], {"nombre": "Taller de huertos", "fecha": str(HOY + timedelta(days=3)), "hora_inicio": "10:00",
                                "hora_fin": "12:00", "lugar": lugar.pk, "responsable": contacto.pk})
    a = Actividad.objects.get()
    s.refresh_from_db()
    assert r.status_code == 302 and s.actividad == a and s.estado.codigo == "convertida"
    assert a.estado.codigo == "planificada" and a.agenda_vigente.lugar == lugar and a.agenda_vigente.hora_inicio == time(10)
    assert ActividadOrganizacion.objects.get(actividad=a).contacto == contacto
    # una solicitud no tiene dos actividades: el formulario ya no se ofrece y la ruta vieja tampoco crea otra
    assert cg.get(f"/actividades/nueva?solicitud={s.pk}")["Location"] == f"/solicitudes/{s.pk}"
    cg.post(f"/actividades/nueva?solicitud={s.pk}", {"nombre": "Otra"})
    cg.post(f"/solicitudes/{s.pk}/crear-actividad")
    assert Actividad.objects.count() == 1


def test_sin_fecha_queda_pendiente_y_horas_malas_no_guardan_nada(cg):
    s = _solicitud()
    url = f"/actividades/nueva?solicitud={s.pk}"
    r = cg.post(url, {"nombre": "Charla", "fecha": str(HOY), "hora_inicio": "12:00", "hora_fin": "10:00"})
    assert r.status_code == 200 and not Actividad.objects.exists()
    s.refresh_from_db()
    assert s.estado.codigo == "pendiente" and s.actividad is None
    cg.post(url, {"nombre": "Charla"})
    s.refresh_from_db()
    assert s.estado.codigo == "convertida" and s.actividad.estado.codigo == "pendiente" and not s.actividad.agendas.exists()


def test_solicitud_convertida_en_proyecto_ofrece_crear_tarea_ligada(cg):
    s = _solicitud(motivo="Campaña inventada")
    cg.post(f"/solicitudes/{s.pk}/crear-proyecto")
    s.refresh_from_db()
    html = cg.get(s.get_absolute_url()).content.decode()
    url = f"/proyectos/{s.proyecto_id}/tareas/nueva?solicitud={s.pk}"
    assert "Crear tarea en el proyecto" in html and url in html
    assert 'value="Campaña inventada"' in cg.get(url).content.decode()
    cg.post(url, {"nombre": "Primera visita", "fecha": str(HOY + timedelta(days=1)), "hora_inicio": "09:00"})
    s.refresh_from_db()
    assert s.actividad.proyecto_id == s.proyecto_id and s.actividad.agendas.filter(vigente=True).exists()
    assert "Crear tarea en el proyecto" not in cg.get(s.get_absolute_url()).content.decode()


# --- 2. Solicitudes: un solo «+ Nueva», pestañas por estado y primera interacción -------------------------------------
def test_solicitudes_un_boton_y_pestanas_con_contador(cg):
    _solicitud("Una"), _solicitud("Dos"), _solicitud("Tres", estado="descartada")
    html = cg.get("/solicitudes?estado=pendiente&q=o").content.decode()
    acciones = html.split('class="fche-pagina__acciones">')[1].split("</div>")[0]
    assert acciones.count("/solicitudes/nueva") == 1 and ">+ Nueva</a>" in acciones and "oportunidad" not in acciones
    pestanas = re.search(r'aria-label="Solicitudes por estado">(.*?)</nav>', html, re.S).group(1)
    textos = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip() for t in re.findall(r"<a [^>]*>(.*?)</a>", pestanas, re.S)]
    assert textos == ["Pendientes 2", "En seguimiento 0", "Convertidas 0", "Descartadas 1", "Todas 3"]
    assert 'class="nav-link active" href="?estado=pendiente&amp;q=o" aria-current="page"' in pestanas  # conserva la búsqueda


def test_primera_interaccion_pasa_la_solicitud_a_seguimiento(cg, persona):
    s = _solicitud()
    llamado = Canal.objects.get(codigo="llamado").pk
    cg.post("/interacciones/nueva", {"fecha": "2026-10-02T10:00", "canal": llamado, "persona": persona.pk, "solicitud": s.pk, "resultado": "Contesta"})
    s.refresh_from_db()
    assert s.estado.codigo == "en_seguimiento"
    descartada = _solicitud("Otra", estado="descartada")
    cg.post("/interacciones/nueva", {"fecha": "2026-10-02T10:00", "canal": llamado, "persona": persona.pk, "solicitud": descartada.pk, "resultado": "x"})
    descartada.refresh_from_db()
    assert descartada.estado.codigo == "descartada"  # solo la pendiente cambia


# --- 3. Inicio ----------------------------------------------------------------------------------------------------------
def _pendientes(n, crear_actividad, persona, universidad, gestor):
    from apps.coordinacion.models import Interaccion
    from apps.documentos.models import Documento
    from apps.nucleo.models import TipoDocumento

    canal = Canal.objects.get(codigo="llamado")
    for i in range(n):
        Interaccion.objects.create(canal=canal, persona=persona, proxima_accion=f"Llamar de nuevo {i}", proxima_fecha=HOY - timedelta(days=i))
        a = crear_actividad(f"Pasada sin finalizar {i}", estado="confirmada")
        AgendaActividad.objects.create(actividad=a, fecha=HOY - timedelta(days=2 + i), estado=a.estado)
        Documento.objects.create(nombre=f"Convenio por vencer {i}", archivo=SimpleUploadedFile("c.pdf", b"%PDF"),
                                 tipo=TipoDocumento.objects.get(codigo="otro"), organizacion=universidad, fecha_vencimiento=HOY + timedelta(days=10))


def test_inicio_para_hoy_y_vencidas_sin_repetir_ni_acciones_rapidas(cg, crear_actividad, persona, universidad, gestor):
    _pendientes(1, crear_actividad, persona, universidad, gestor)
    realizada = crear_actividad("Ya realizada", estado="realizada")
    AgendaActividad.objects.create(actividad=realizada, fecha=HOY - timedelta(days=5), estado=realizada.estado)
    html = cg.get("/dashboard").content.decode()
    tarjeta = re.search(r'id="para-hoy">(.*?)</section>', html, re.S).group(1)
    assert "Llamar de nuevo 0" in tarjeta and "Pasada sin finalizar 0" in tarjeta and "Convenio por vencer 0" in tarjeta
    assert "Ya realizada" not in tarjeta and 'href="/actividades/' in tarjeta and 'href="/documentos/' in tarjeta
    assert html.index('id="para-hoy"') < html.index('class="fche-kpis"')  # arriba
    assert "Acciones rápidas" not in html
    kpis = re.search(r'<ul class="fche-kpis".*?</ul>', html, re.S).group(0)
    titulos_tarjetas = re.findall(r"<strong>([^<]+)</strong>", html.split("Pendientes</h2>")[1])
    assert titulos_tarjetas and not any(t in kpis for t in titulos_tarjetas)  # ninguna cifra repite una tarjeta


def test_inicio_con_numero_fijo_de_consultas(cg, crear_actividad, persona, universidad, gestor, crear_persona):
    from apps.nucleo.models import EstadoRegistro

    def contar():
        with CaptureQueriesContext(connection) as c:
            assert cg.get("/dashboard").status_code == 200
        return len(c)

    _pendientes(1, crear_actividad, persona, universidad, gestor)
    crear_persona(estado_registro=EstadoRegistro.objects.get(codigo="incompleto"))
    antes = contar()
    _pendientes(4, crear_actividad, persona, universidad, gestor)
    for _ in range(3):
        crear_persona(estado_registro=EstadoRegistro.objects.get(codigo="incompleto"))
    assert contar() == antes


# --- 4. Finalizar exige fecha (por pantalla) -----------------------------------------------------------------------------
def test_finalizar_por_pantalla_sin_fecha_avisa(cg, crear_actividad):
    a = crear_actividad("Sin fecha", estado="confirmada", resultado="ok", asistencia_sin_registro=True)
    r = cg.post(f"/actividades/{a.pk}/finalizar", follow=True)
    a.refresh_from_db()
    assert a.estado.codigo == "confirmada" and "Programa la fecha antes de finalizar" in r.content.decode()


# --- 5 y 6. Menú y filtros ----------------------------------------------------------------------------------------------
def test_menu_calendario_dentro_de_actividades_y_cargas_en_configuracion(cg):
    menu = cg.get("/calendario").content.decode().split('id="menu-lateral"')[1].split("</aside>")[0]
    assert 'href="/calendario"' not in menu and "Importaciones" not in menu
    assert re.search(r'class="fche-menu-enlace active" href="/actividades" aria-current="page"', menu)
    configuracion = menu.split("Configuración")[1]
    assert 'href="/importaciones"' in configuracion and "Historial de cargas" in configuracion
    for ruta in ("/actividades", "/calendario"):
        vista = cg.get(ruta).content.decode().split('aria-label="Ver actividades como"')[1].split("</nav>")[0]
        assert 'href="/actividades"' in vista and 'href="/calendario"' in vista and 'aria-current="page"' in vista


def test_un_solo_boton_de_filtros(cg):
    barra = re.search(r'<form class="fche-filtros".*?</form>', cg.get("/personas").content.decode(), re.S).group(0)
    assert "Más filtros" not in barra and 'class="btn btn-outline-primary" type="submit"' not in barra  # sin «Filtrar» aparte
    assert re.search(r"<summary[^>]*>.*?Filtros", barra, re.S) and "Aplicar filtros" in barra
    assert 'type="submit" class="visually-hidden" tabindex="-1" aria-hidden="true"' in barra  # Enter en el buscador aplica

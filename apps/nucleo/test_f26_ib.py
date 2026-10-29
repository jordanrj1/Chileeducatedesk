"""Pruebas de F26 Ib (specs/f26/spec.md, «Paquete I · Interfaz por módulo → Ib. Fichas 360° y listas»): «De un vistazo» en
organización, comunidad y lugar (con número fijo de consultas), columnas de la lista de personas (RUT solo con permiso y
«Origen» como filtro), conteos de la lista de organizaciones y «Cargos y vínculos» sin grupos vacíos. Datos ficticios."""
import datetime
import re
from io import BytesIO

import pytest
from django.contrib.auth.models import Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.actividades.models import ActividadComunidad, ActividadOrganizacion, AgendaActividad, Participacion
from apps.comunidades.models import Comunidad, ComunidadMiembro
from apps.coordinacion.models import Interaccion
from apps.nucleo.models import Canal, OrigenPersona, TipoContacto
from apps.organizaciones.models import Organizacion
from apps.personas.models import Contacto, PersonaFormacion, PersonaOrganizacion
from apps.proyectos.models import Proyecto, ProyectoOrganizacion

pytestmark = pytest.mark.django_db
HOY = timezone.localdate()


def _html(cliente, url):
    r = cliente.get(url)
    assert r.status_code == 200, url
    return r.content.decode()


def _vistazo(html):
    return html.split('id="resumen-360"', 1)[1].split("</section>", 1)[0]


def _consultas(cliente, url):
    with CaptureQueriesContext(connection) as c:
        _html(cliente, url)
    return len(c)


def _actividad_con_agenda(crear_actividad, nombre, estado, dias, **kw):
    a = crear_actividad(nombre, estado=estado)
    AgendaActividad.objects.create(actividad=a, fecha=HOY + datetime.timedelta(days=dias), hora_inicio=datetime.time(10), estado=a.estado, **kw)
    return a


# ── Organización ──────────────────────────────────────────────────────────

def _poblar_organizacion(org, crear_persona, crear_actividad, n):
    for i in range(n):
        PersonaOrganizacion.objects.create(persona=crear_persona(f"Vinculada{i}"), organizacion=org, cargo="Coordinación")
        PersonaFormacion.objects.create(persona=crear_persona(f"Estudiante{i}"), organizacion=org)
        for nombre, estado, dias in ((f"Hecha {i}", "realizada", -10 - i), (f"Futura {i}", "confirmada", 5 + i)):
            ActividadOrganizacion.objects.create(actividad=_actividad_con_agenda(crear_actividad, nombre, estado, dias), organizacion=org)
        ProyectoOrganizacion.objects.create(proyecto=Proyecto.objects.create(nombre=f"Proyecto Ficticio {i}"), organizacion=org)
        Interaccion.objects.create(organizacion=org, canal=Canal.objects.get(codigo="llamado"), motivo=f"Llamado {i}",
                                   fecha=timezone.now() - datetime.timedelta(days=i))
    Contacto.objects.create(organizacion=org, tipo=TipoContacto.objects.get(codigo="telefono_fijo"), valor="+56 41 000 0000")
    Contacto.objects.create(organizacion=org, tipo=TipoContacto.objects.get(codigo="correo"), valor="contacto@ejemplo.invalid", principal=True)


def test_vistazo_organizacion_muestra_lo_esencial(cg, universidad, crear_persona, crear_actividad):
    PersonaOrganizacion.objects.create(persona=crear_persona("Antigua"), organizacion=universidad, fecha_termino=HOY - datetime.timedelta(days=1))
    _poblar_organizacion(universidad, crear_persona, crear_actividad, 2)
    bloque = _vistazo(_html(cg, universidad.get_absolute_url()))
    assert "4 personas vigentes" in bloque and "Antigua" not in bloque  # 2 con cargo + 2 estudiando; la del cargo terminado no
    assert "Ver las 4" in bloque
    assert "4 actividades · 2 proyectos" in bloque
    assert "Hecha 0" in bloque and "Futura 0" in bloque  # la última realizada y la próxima programada
    assert "contacto@ejemplo.invalid" in bloque and "mailto:" in bloque  # el marcado como principal
    assert "Llamado 0" in bloque and "/interacciones/" in bloque


def test_vistazo_organizacion_vacia(cg, universidad):
    bloque = _vistazo(_html(cg, universidad.get_absolute_url()))
    for texto in ("Sin personas vinculadas vigentes", "Aún no participa", "Sin contactos vigentes", "Sin interacciones registradas"):
        assert texto in bloque


def test_vistazo_organizacion_con_consultas_fijas(cg, tipo_org, crear_persona, crear_actividad):
    una = Organizacion.objects.create(nombre="Una Ficticia", tipo=tipo_org("institucion_educativa"))
    varias = Organizacion.objects.create(nombre="Varias Ficticia", tipo=tipo_org("institucion_educativa"))
    _poblar_organizacion(una, crear_persona, crear_actividad, 1)
    _poblar_organizacion(varias, crear_persona, crear_actividad, 6)
    _html(cg, una.get_absolute_url())  # calienta cachés de permisos y catálogos
    assert _consultas(cg, una.get_absolute_url()) == _consultas(cg, varias.get_absolute_url())


# ── Comunidad ─────────────────────────────────────────────────────────────

def _poblar_comunidad(com, crear_persona, crear_actividad, n):
    for i in range(n):
        ComunidadMiembro.objects.create(comunidad=com, persona=crear_persona(f"Vecina{i}"), rol="dirigente" if i == 0 else "integrante")
        ActividadComunidad.objects.create(comunidad=com, actividad=_actividad_con_agenda(crear_actividad, f"Pasada {i}", "realizada", -3 - i))
        ActividadComunidad.objects.create(comunidad=com, actividad=_actividad_con_agenda(crear_actividad, f"Siguiente {i}", "planificada", 2 + i))


def test_vistazo_comunidad(cg, comuna, crear_persona, crear_actividad):
    com = Comunidad.objects.create(nombre="Vecinos Ficticios", comuna=comuna, tipo="vecinal", poblacion_estimada=40)
    _poblar_comunidad(com, crear_persona, crear_actividad, 2)
    html = _html(cg, com.get_absolute_url())
    bloque = _vistazo(html)
    assert "2 integrantes vigentes de ~40" in bloque
    assert "Vecina0" in bloque and "según su padrón" in bloque
    assert "Pasada 0" in bloque and "Siguiente 0" in bloque
    datos = html.split('id="info-datos"', 1)[1]
    assert "Referente o dirigente" not in datos and "Población estimada" not in datos.split("Sin completar", 1)[0]  # no se repite abajo


def test_vistazo_comunidad_con_consultas_fijas(cg, comuna, crear_persona, crear_actividad):
    una = Comunidad.objects.create(nombre="Una Ficticia", comuna=comuna, tipo="vecinal")
    varias = Comunidad.objects.create(nombre="Varias Ficticia", comuna=comuna, tipo="vecinal")
    _poblar_comunidad(una, crear_persona, crear_actividad, 1)
    _poblar_comunidad(varias, crear_persona, crear_actividad, 6)
    _html(cg, una.get_absolute_url())
    assert _consultas(cg, una.get_absolute_url()) == _consultas(cg, varias.get_absolute_url())


# ── Lugar ─────────────────────────────────────────────────────────────────

def test_vistazo_lugar_y_consultas_fijas(cg, lugar, crear_actividad, comuna):
    from apps.lugares.models import Lugar

    otro = Lugar.objects.create(nombre="Otra Sala Ficticia", tipo=lugar.tipo, direccion=lugar.direccion)
    _actividad_con_agenda(crear_actividad, "Charla pasada", "realizada", -2, lugar=lugar)
    _actividad_con_agenda(crear_actividad, "Charla futura", "confirmada", 2, lugar=lugar)
    for i in range(5):
        _actividad_con_agenda(crear_actividad, f"Uso {i}", "confirmada", 3 + i, lugar=otro)
    _actividad_con_agenda(crear_actividad, "Uso realizado", "realizada", -1, lugar=otro)
    bloque = _vistazo(_html(cg, lugar.get_absolute_url()))
    assert "2 actividades programadas aquí" in bloque
    assert "Charla pasada" in bloque and "Charla futura" in bloque
    _html(cg, otro.get_absolute_url())
    assert _consultas(cg, lugar.get_absolute_url()) == _consultas(cg, otro.get_absolute_url())


# ── Lista de personas ─────────────────────────────────────────────────────

def _encabezados(html):
    thead = html.split("<thead>", 1)[1].split("</thead>", 1)[0]
    return [h.split(">", 1)[1].split("</th>", 1)[0] for h in thead.split("<th")[1:]]


def test_lista_personas_columnas_y_rut_solo_con_permiso(cg, gestor, crear_persona, comuna):
    from apps.personas.models import PersonaDireccion
    from apps.territorio.models import Direccion

    p = crear_persona("Rosa", rut_numero=11111111, rut_dv="1")
    Contacto.objects.create(persona=p, tipo=TipoContacto.objects.get(codigo="correo"), valor="rosa@ejemplo.invalid")
    PersonaDireccion.objects.create(persona=p, tipo="residencia", direccion=Direccion.objects.create(calle="Calle Inventada", numero="1", comuna=comuna))
    html = _html(cg, "/personas")
    assert _encabezados(html) == ["Nombre", "RUT 🔒", "Perfil", "Contacto", "Comuna", "Edad", "Estado de la ficha"]
    assert "rosa@ejemplo.invalid" in html and "Comuna Ficticia" in html and "11.111.111-1" in html
    for g in gestor.groups.all():
        g.permissions.remove(Permission.objects.get(codename="exportar_persona"))
    from django.test import Client

    c = Client()
    c.force_login(gestor)
    html = _html(c, "/personas")
    assert "RUT 🔒" not in _encabezados(html) and "11.111.111-1" not in html
    assert "Origen" not in _encabezados(html)


def test_lista_personas_origen_como_filtro(cg, crear_persona):
    origen = OrigenPersona.objects.get(codigo="invitacion")
    crear_persona("ConOrigen", origen=origen)
    crear_persona("SinOrigen")
    html = _html(cg, "/personas")
    assert 'name="origen"' in html.split("fche-filtros__mas", 1)[1]  # en «Más filtros»
    filtrada = _html(cg, f"/personas?origen={origen.pk}")
    assert "ConOrigen" in filtrada and "SinOrigen" not in filtrada


def test_lista_personas_sin_consultas_por_fila(cg, crear_persona, universidad):
    from apps.nucleo.models import PerfilPersona

    perfil = PerfilPersona.objects.filter(activo=True).first()

    def crear(n):
        for _ in range(n):
            p = crear_persona()
            p.perfiles.add(perfil)
            Contacto.objects.create(persona=p, tipo=TipoContacto.objects.get(codigo="telefono_movil"), valor="+56 9 0000 0000")
            PersonaFormacion.objects.create(persona=p, organizacion=universidad)

    crear(1)
    _html(cg, "/personas")
    antes = _consultas(cg, "/personas")
    crear(8)
    assert _consultas(cg, "/personas") == antes


def test_exportar_personas_conserva_rut_correo_y_origen(cg, crear_persona):
    from openpyxl import load_workbook

    crear_persona("Exportada", rut_numero=11111111, rut_dv="1", origen=OrigenPersona.objects.get(codigo="invitacion"))
    r = cg.get("/personas/exportar")
    assert r.status_code == 200
    filas = list(load_workbook(BytesIO(r.content)).worksheets[0].values)
    assert {"RUT", "Correo", "Teléfono", "Origen", "Le falta"} <= set(filas[0])


# ── Lista de organizaciones ───────────────────────────────────────────────

def test_lista_organizaciones_cuenta_personas_y_actividades(cg, universidad, crear_persona, crear_actividad):
    p = crear_persona()
    PersonaOrganizacion.objects.create(persona=p, organizacion=universidad)
    PersonaFormacion.objects.create(persona=p, organizacion=universidad)  # la misma persona cuenta una vez
    PersonaFormacion.objects.create(persona=crear_persona(), organizacion=universidad)
    PersonaFormacion.objects.create(persona=crear_persona(), organizacion=universidad, vigente=False)  # no vigente: no cuenta
    for i in range(3):
        ActividadOrganizacion.objects.create(actividad=crear_actividad(f"Act {i}"), organizacion=universidad)
    html = _html(cg, "/organizaciones?q=Universidad")
    enc = _encabezados(html)
    assert "Personas" in enc and "Actividades" in enc
    fila = html.split("<tbody>", 1)[1].split("</tr>", 1)[0]
    valores = [c.strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", fila, re.S)]  # las celdas llevan data-label para el celular
    assert valores[enc.index("Personas")] == "2" and valores[enc.index("Actividades")] == "3"
    assert _html(cg, "/organizaciones?orden=-personas").count("<tr>") >= 2  # se puede ordenar por los conteos


# ── Cargos y vínculos ─────────────────────────────────────────────────────

def test_vinculos_solo_grupos_con_datos(cg, persona, universidad):
    PersonaOrganizacion.objects.create(persona=persona, organizacion=universidad, cargo="Coordinadora")
    html = _html(cg, f"{persona.get_absolute_url()}?tab=vinculos")
    pestana = html.split('id="pestana"', 1)[1]
    assert "Organizaciones y cargos" in pestana
    for vacio in (">Estudios", ">Lugares", ">Comunidades", ">Proyectos", ">Actividades y tareas"):
        assert vacio not in pestana
    assert "Sin estudios, lugares, comunidades, proyectos ni actividades." in pestana
    assert "Sin registros." not in pestana

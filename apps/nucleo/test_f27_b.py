"""F27 B: interfaz. Tarjeta de identidad de la persona (foto o iniciales, metadatos con enlace, organización y cargo
vigentes), aviso «Le falta» arriba (sin «Sin completar» al final del Resumen), tareas del proyecto como tarjetas con sus
cifras y consultas fijas, y «Vincular persona» con las fechas de a dos. Todos los datos son ficticios."""
from datetime import date, time, timedelta

import pytest

from apps.actividades.models import ActividadComunidad, AgendaActividad, Participacion
from apps.nucleo.models import EstadoActividad, RolOrganizacion, TipoContacto
from apps.personas.models import Contacto, PersonaDireccion, PersonaOrganizacion
from apps.territorio.models import Direccion

pytestmark = pytest.mark.django_db


def _cabecera(html):
    return html[html.index('class="fche-ficha-cabecera"'):html.index('id="pestana"')]


def _cuerpo(html):
    return html.split('id="pestana"', 1)[1]


@pytest.fixture
def ficha_completa(persona, universidad, comuna):
    persona.fecha_nacimiento = date(1990, 5, 3)
    persona.save()
    Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="correo"), valor="ana.ficticia@ejemplo.invalid", principal=True)
    Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="telefono_movil"), valor="+56 9 1111 2222")
    PersonaDireccion.objects.create(persona=persona, direccion=Direccion.objects.create(comuna=comuna), tipo="residencia")
    PersonaOrganizacion.objects.create(persona=persona, organizacion=universidad, cargo="Encargada ficticia", rol=RolOrganizacion.objects.order_by("pk").first())
    PersonaOrganizacion.objects.create(persona=persona, organizacion=universidad, cargo="Cargo antiguo", fecha_termino=date.today() - timedelta(days=30))
    return persona


# --- 1. Tarjeta de identidad ---------------------------------------------------------------------
def test_tarjeta_con_iniciales_metadatos_y_vinculo_vigente(cg, ficha_completa, universidad, comuna):
    cab = _cabecera(cg.get(ficha_completa.get_absolute_url()).content.decode())
    assert "fche-retrato fche-retrato--persona" in cab and ">AM<" in cab and "<img" not in cab  # sin foto: iniciales
    assert 'href="mailto:ana.ficticia@ejemplo.invalid"' in cab and 'href="tel:+56911112222"' in cab
    assert comuna.get_absolute_url() in cab and f"{ficha_completa.edad} años" in cab
    assert universidad.get_absolute_url() in cab and "Encargada ficticia" in cab
    assert "Cargo antiguo" not in cab  # solo los vínculos vigentes
    assert 'class="fche-meta"' in cab and cab.count('class="fche-icono') >= 5  # cada dato con su icono


def test_tarjeta_con_foto_usa_la_vista_protegida(cg, persona):
    persona.foto = "personas/fotos/ficticia.png"  # solo el nombre: la plantilla no lee el archivo
    persona.save()
    cab = _cabecera(cg.get(persona.get_absolute_url()).content.decode())
    assert f'src="/personas/{persona.pk}/foto"' in cab and 'alt="Foto de ' in cab
    assert "/media/" not in cab  # nunca como archivo estático


def test_otras_fichas_usan_el_mismo_patron_con_icono_del_tipo(cg, crear_actividad, lugar):
    from apps.proyectos.models import Proyecto

    p = Proyecto.objects.create(nombre="Proyecto Ficticio")
    for url in (p.get_absolute_url(), lugar.get_absolute_url(), crear_actividad().get_absolute_url()):
        cab = _cabecera(cg.get(url).content.decode())
        assert "fche-retrato fche-retrato--icono" in cab and 'class="fche-meta"' in cab, url


# --- 2. «Le falta» arriba -------------------------------------------------------------------------
def test_le_falta_arriba_y_sin_completar_ya_no_esta_al_final(cg, persona):
    html = cg.get(persona.get_absolute_url()).content.decode()
    assert html.index('id="aviso-le-falta"') < html.index('id="resumen-360"')
    aviso = html[html.index('id="aviso-le-falta"'):html.index("</li>\n", html.index('id="aviso-le-falta"'))]
    assert "Le falta" in aviso and "un contacto" in aviso and "comuna de residencia" in aviso
    assert "Nacionalidad" in aviso and "Completar" in aviso  # los opcionales vacíos, plegados en el mismo aviso
    assert "Sin completar" not in _cuerpo(html) and "fche-sin-completar" not in _cuerpo(html)


def test_consentimiento_y_le_falta_son_el_mismo_componente_uno_debajo_del_otro(cg, persona):
    html = cg.get(persona.get_absolute_url()).content.decode()
    avisos = html[html.index('class="fche-ficha-avisos"'):html.index('class="nav nav-tabs"')]
    assert avisos.index("Consentimiento pendiente") < avisos.index('id="aviso-le-falta"')
    assert avisos.count('class="fche-aviso fche-aviso--') == 2


def test_ficha_completa_sin_faltantes_no_muestra_le_falta(cg, ficha_completa):
    html = cg.get(ficha_completa.get_absolute_url()).content.decode()
    assert ">Le falta<" not in html and "Tiene lo mínimo" in html  # solo quedan los opcionales, en un aviso neutro


# --- 3. Tareas del proyecto como tarjetas -----------------------------------------------------------
def _tareas(proyecto, n, crear_actividad, crear_persona, rol, estado_part, lugar, comunidad):
    for i in range(n):
        t = crear_actividad(f"Tarea ficticia {i}", estado="planificada", proyecto=proyecto, responsable=crear_persona())
        AgendaActividad.objects.create(actividad=t, fecha=date.today() + timedelta(days=i + 1), hora_inicio=time(10), hora_fin=time(12),
                                       lugar=lugar, estado=EstadoActividad.objects.get(codigo="planificada"))
        ActividadComunidad.objects.create(actividad=t, comunidad=comunidad)
        for k in range(2):
            Participacion.objects.create(actividad=t, persona=crear_persona(), rol=rol("voluntario"), estado=estado_part("confirmado"), asistencia=k == 0)


@pytest.fixture
def comunidad(comuna):
    from apps.comunidades.models import Comunidad

    return Comunidad.objects.create(nombre="Vecinos Ficticios", comuna=comuna)


def test_tareas_en_tarjetas_con_cifras_y_consultas_fijas(cg, crear_actividad, crear_persona, rol, estado_part, lugar, comunidad,
                                                         django_assert_max_num_queries):
    from apps.proyectos.models import Proyecto

    pocos, muchos = Proyecto.objects.create(nombre="Pocos"), Proyecto.objects.create(nombre="Muchos")
    _tareas(pocos, 1, crear_actividad, crear_persona, rol, estado_part, lugar, comunidad)
    _tareas(muchos, 6, crear_actividad, crear_persona, rol, estado_part, lugar, comunidad)
    cg.get(f"/proyectos/{pocos.pk}?tab=tareas")  # calienta sesión y permisos
    with django_assert_max_num_queries(60) as q:
        cg.get(f"/proyectos/{pocos.pk}?tab=tareas")
    with django_assert_max_num_queries(len(q.captured_queries)):
        html = cg.get(f"/proyectos/{muchos.pk}?tab=tareas").content.decode()
    cuerpo = _cuerpo(html)
    assert cuerpo.count('class="fche-tarjeta-item"') == 6 and "<table" not in cuerpo
    tarjeta = cuerpo[cuerpo.index('class="fche-tarjeta-item"'):cuerpo.index("</article>")]
    assert "Planificada" in tarjeta and lugar.nombre in tarjeta and "Vecinos Ficticios" in tarjeta and "A cargo:" in tarjeta
    assert ">2</a>" in tarjeta and ">1</a>" in tarjeta  # participantes y asistieron
    assert ">Ver</a>" in tarjeta and "Editar" in tarjeta


def test_proyecto_sin_tareas_ofrece_nueva_tarea(cg):
    from apps.proyectos.models import Proyecto

    p = Proyecto.objects.create(nombre="Sin tareas")
    cuerpo = _cuerpo(cg.get(f"/proyectos/{p.pk}?tab=tareas").content.decode())
    assert "aún no tiene tareas" in cuerpo and cuerpo.count("+ Nueva tarea") == 1


# --- 4. Formularios cortos de vínculo ----------------------------------------------------------------
def test_vincular_persona_desde_la_organizacion_con_fechas_de_a_dos(cg, universidad, persona):
    html = cg.get(f"/organizaciones/{universidad.pk}/personas/nuevo").content.decode()
    assert "<h1" in html and "Vincular persona" in html and "Agregar persona con cargo" not in html
    lista = html[html.index('class="fche-form__lista"'):]
    assert lista.count("fche-campo--fecha") == 2  # Desde y Hasta, de a dos en escritorio
    assert "+ Vincular persona" in cg.get(f"{universidad.get_absolute_url()}?tab=personas").content.decode()


def test_vinculo_con_lugar_tambien_pone_las_fechas_de_a_dos(cg, persona):
    html = cg.get(f"/personas/{persona.pk}/lugares/nuevo").content.decode()
    assert html.count("fche-campo--fecha") == 2

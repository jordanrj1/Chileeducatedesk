"""Pruebas de F25 E (E1, E2, E3 y E6): ficha rápida única, cinco estados de participación, aviso de persona repetida
con otro rol y ayuda de «Horas» con la duración programada. Todos los datos son ficticios."""
from datetime import date, time, timedelta

import pytest

from apps.actividades import servicios
from apps.actividades.forms import ESTADOS_PARA_ELEGIR, ParticipacionEditarForm, ParticipanteNuevoForm, PersonaRapidaForm
from apps.actividades.models import Participacion
from apps.personas.forms import CAMPOS_FICHA_RAPIDA, PersonaCrearRapidaForm
from apps.personas.forms import PersonaRapidaForm as PersonaModoRapidoForm
from apps.personas.models import Persona

pytestmark = pytest.mark.django_db
FUTURO = date.today() + timedelta(days=7)


# --- E1: una ficha rápida igual en todas partes ---------------------------------------------
def test_los_tres_lugares_usan_los_mismos_campos_y_etiquetas():
    formularios = [PersonaCrearRapidaForm(), PersonaRapidaForm(), PersonaModoRapidoForm()]
    for f in formularios:
        assert set(CAMPOS_FICHA_RAPIDA) <= set(f.fields), type(f)
    etiquetas = [{c: f.fields[c].label for c in CAMPOS_FICHA_RAPIDA} for f in formularios]
    assert etiquetas[0] == etiquetas[1] == etiquetas[2]


def test_las_tres_pantallas_muestran_la_ficha_rapida(cg, actividad):
    # F26 P1a: /participantes/rapido lleva al único «+ Agregar persona», cuyo buscador crea la persona con la ventana
    # «+ Crear persona» (/personas/crear-rapida, la segunda pantalla de esta lista)
    r = cg.get(f"/actividades/{actividad.pk}/participantes/rapido")
    assert r.status_code == 302 and r["Location"] == f"/actividades/{actividad.pk}/participantes/nuevo"
    unico = cg.get(r["Location"]).content.decode()
    assert 'name="persona"' in unico and "crear=1" in unico
    pantallas = [  # (prefijo de los campos, página)
        ("rapida-", cg.get("/personas/crear-rapida").content.decode()),
        ("", cg.get("/personas/nueva").content.decode()),  # modo rápido
    ]
    for prefijo, html in pantallas:
        for campo in CAMPOS_FICHA_RAPIDA:
            assert f'name="{prefijo}{campo}"' in html, (prefijo, campo)
    # el enlace «Créala aquí mismo» se quitó (la ruta sigue funcionando)
    assert "Créala aquí mismo" not in cg.get(f"/actividades/{actividad.pk}/participantes/nuevo").content.decode()


def test_crear_persona_del_buscador_guarda_comuna_y_queda_incompleta(cg, comuna):
    r = cg.post("/personas/crear-rapida", {"campo": "id_responsable", "rapida-nombres": "Fidelia", "rapida-apellido_paterno": "Inventada",
                                           "rapida-rut": "11.111.111-1", "rapida-sexo": "mujer", "rapida-comuna": comuna.pk})
    assert r.status_code == 200 and r["HX-Reswap"] == "none"
    p = Persona.objects.get(nombres="Fidelia")
    assert (p.rut_numero, p.sexo, p.estado_registro.codigo) == (11111111, "mujer", "incompleto")
    assert p.direcciones.get(tipo="residencia").direccion.comuna == comuna
    # el mismo RUT se avisa y no crea otra persona
    r = cg.post("/personas/crear-rapida", {"rapida-nombres": "Otra", "rapida-rut": "11.111.111-1"})
    assert "Ya existe una persona con ese RUT" in r.content.decode() and Persona.objects.filter(rut_numero=11111111).count() == 1


def test_documento_extranjero_repetido_se_avisa_en_la_ficha_de_terreno(cg, actividad, crear_persona, rol):
    crear_persona("Jean", tipo_documento="pasaporte", numero_documento="AB123456")
    r = cg.post(f"/actividades/{actividad.pk}/participantes/rapido", {"nombres": "Otro", "sin_rut": "on", "tipo_documento": "pasaporte",
                                                                     "numero_documento": "ab123456", "rol": rol("voluntario").pk})
    assert r.status_code == 400 and "Ya existe una persona con ese documento" in r.content.decode()


def test_modo_rapido_de_personas_queda_incompleto_con_comuna(cg, comuna):
    r = cg.post("/personas/nueva", {"modo": "rapida", "nombres": "Rápida", "apellido_paterno": "Completa", "correo": "rapida@ejemplo.invalid",
                                    "comuna": comuna.pk})
    p = Persona.objects.get(nombres="Rápida")
    # F26 P2: el estado se calcula (completitud): con apellido, un contacto y la comuna, la ficha rápida ya queda «activo»;
    # sin contacto queda «incompleto»
    assert r.status_code == 302 and p.estado_registro.codigo == "activo"
    assert p.direcciones.get(tipo="residencia").direccion.comuna == comuna
    cg.post("/personas/nueva", {"modo": "rapida", "nombres": "Rápida Dos", "apellido_paterno": "Sin Contacto", "comuna": comuna.pk})
    assert Persona.objects.get(nombres="Rápida Dos").estado_registro.codigo == "incompleto"


# --- E2: cinco estados; toda alta queda «Inscrito» -------------------------------------------
def test_alta_queda_inscrito(cg, actividad, crear_persona, rol):
    r = cg.post(f"/actividades/{actividad.pk}/participantes/rapido", {"nombres": "Nueva", "apellido_paterno": "Ficticia", "rol": rol("voluntario").pk})
    assert r.status_code == 302
    nueva = actividad.participaciones.get(persona__nombres="Nueva")
    assert nueva.estado.codigo == "confirmado" and nueva.estado.nombre == "Inscrito"
    existente = crear_persona()
    cg.post(f"/actividades/{actividad.pk}/participantes/usar/{existente.pk}", {"rol": rol("participante").pk})
    assert actividad.participaciones.get(persona=existente).estado.nombre == "Inscrito"
    assert ParticipanteNuevoForm(actividad=actividad).fields["estado"].initial.codigo == "confirmado"


def test_el_estado_ofrece_solo_los_cinco_y_conserva_el_antiguo(actividad, crear_persona, rol, estado_part):
    cinco = set(ESTADOS_PARA_ELEGIR)
    assert cinco == {"confirmado", "asistio", "no_asistio", "cancelo", "lista_espera"}
    assert set(ParticipanteNuevoForm(actividad=actividad).fields["estado"].queryset.values_list("codigo", flat=True)) == cinco
    nueva = Participacion.objects.create(actividad=actividad, persona=crear_persona(), rol=rol("voluntario"), estado=estado_part("confirmado"))
    assert set(ParticipacionEditarForm(instance=nueva).fields["estado"].queryset.values_list("codigo", flat=True)) == cinco
    antigua = Participacion.objects.create(actividad=actividad, persona=crear_persona(), rol=rol("voluntario"), estado=estado_part("invitado"))
    assert set(ParticipacionEditarForm(instance=antigua).fields["estado"].queryset.values_list("codigo", flat=True)) == cinco | {"invitado"}


# --- E3: misma persona con otro rol -------------------------------------------------------------
def test_misma_persona_con_otro_rol_pide_confirmar(cg, actividad, crear_persona, rol, estado_part):
    p = crear_persona("Marta", apellido_paterno="Repetida")
    Participacion.objects.create(actividad=actividad, persona=p, rol=rol("voluntario"), estado=estado_part("confirmado"))
    aviso = "Marta Repetida ya participa como voluntario. Marca la casilla para agregarla también como tallerista."
    datos = {"persona": p.pk, "rol": rol("tallerista").pk, "estado": estado_part("confirmado").pk}
    r = cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", datos)
    assert r.status_code == 400 and aviso in r.content.decode() and 'name="otro_rol"' in r.content.decode()
    assert cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", {**datos, "otro_rol": "on"}).status_code == 302
    assert actividad.participaciones.filter(persona=p).count() == 2
    # desde «Usar esta persona» también se pide confirmar
    r = cg.post(f"/actividades/{actividad.pk}/participantes/usar/{p.pk}", {"rol": rol("participante").pk})
    assert r.status_code == 400 and "ya participa como" in r.content.decode() and actividad.participaciones.filter(persona=p).count() == 2
    assert cg.post(f"/actividades/{actividad.pk}/participantes/usar/{p.pk}", {"rol": rol("participante").pk, "otro_rol": "1"}).status_code == 302
    assert actividad.participaciones.filter(persona=p).count() == 3


def test_registro_erroneo_no_cuenta_como_otro_rol(cg, actividad, crear_persona, rol, estado_part):
    p = crear_persona()
    Participacion.objects.create(actividad=actividad, persona=p, rol=rol("voluntario"), estado=estado_part("registro_erroneo"))
    r = cg.post(f"/actividades/{actividad.pk}/participantes/nuevo", {"persona": p.pk, "rol": rol("tallerista").pk, "estado": estado_part("confirmado").pk})
    assert r.status_code == 302


# --- E6: ayuda de «Horas» ------------------------------------------------------------------------
def test_ayuda_de_horas_dice_la_duracion_programada(actividad, gestor, lugar, crear_persona, rol, estado_part):
    part = Participacion.objects.create(actividad=actividad, persona=crear_persona(), rol=rol("voluntario"), estado=estado_part("confirmado"))
    assert ParticipacionEditarForm(instance=part).fields["horas"].help_text == "Aún no hay programación: se usará su duración cuando se programe."
    servicios.programar(actividad, gestor, FUTURO, time(10), time(11, 30), lugar, None)
    part = Participacion.objects.get(pk=part.pk)
    assert ParticipacionEditarForm(instance=part).fields["horas"].help_text == "Si lo dejas vacío se usan 1,5 h, la duración programada (10:00 a 11:30)."

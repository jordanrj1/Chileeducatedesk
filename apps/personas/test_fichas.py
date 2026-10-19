"""Pruebas del modelo de las fichas por tipo de persona: catálogos y perfiles con su ficha, la sede del estudiante
(y su enlace desde el texto anterior), las reglas del hogar y de los familiares, la copia del hogar desde los datos
sensibles, la edad aproximada y que la fusión de duplicados no la vuelva exacta. Todos los datos son ficticios."""
import importlib
from datetime import date

import pytest
from django.apps import apps as registro
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.lugares.models import Lugar
from apps.nucleo.models import CATALOGOS, EstadoVoluntario, Parentesco, PerfilPersona, TipoInvitado, TipoLugar, TramoEtario
from apps.organizaciones.models import Organizacion
from apps.personas.models import (
    FamiliarVinculado, FichaInvitado, FichaVecino, FichaVoluntario, IntegranteHogar, PerfilSensible, Persona, PersonaFormacion,
)
from apps.territorio.models import Direccion

pytestmark = pytest.mark.django_db

semillas_nucleo = importlib.import_module("apps.nucleo.migrations.0013_fichas_por_tipo")
datos_personas = importlib.import_module("apps.personas.migrations.0004_fichas_por_tipo")
enlace_sedes = importlib.import_module("apps.personas.migrations.0005_enlazar_sedes")


def _choca(crear):
    with pytest.raises(IntegrityError), transaction.atomic():
        crear()


def test_catalogos_nuevos_y_ficha_de_cada_perfil(cg):
    assert CATALOGOS["parentesco"] is Parentesco and CATALOGOS["tipo-invitado"] is TipoInvitado and CATALOGOS["estado-voluntario"] is EstadoVoluntario
    assert list(EstadoVoluntario.objects.values_list("codigo", flat=True)) == ["postulante", "activo", "en_pausa", "retirado"]
    assert Parentesco.objects.filter(codigo="nieto_o_nieta").exists() and TipoInvitado.objects.filter(codigo="autoridad").exists()
    assert TipoLugar.objects.filter(codigo="casa_matriz", nombre="Casa matriz").exists()
    fichas = dict(PerfilPersona.objects.values_list("codigo", "ficha"))
    assert fichas["estudiante"] == "estudiante" and fichas["vecino_o_vecina_de_la_comunidad"] == "vecino"
    assert fichas["voluntario_o_voluntaria"] == "voluntario" and fichas["invitado_o_invitada"] == "invitado"
    assert fichas["beneficiario_o_beneficiaria"] == "" and fichas["dirigente_social"] == ""
    # el Gestor cambia en Catálogos qué ficha abre un perfil, y la lista lo muestra
    benef = PerfilPersona.objects.get(codigo="beneficiario_o_beneficiaria")
    r = cg.post(f"/administracion/catalogos/perfil-persona/{benef.pk}/editar", {"nombre": benef.nombre, "ficha": "vecino", "orden": benef.orden, "activo": "on"})
    assert r.status_code == 302
    html = cg.get("/administracion/catalogos/perfil-persona/").content.decode()
    assert "Ficha que abre" in html and "Vecino o vecina" in html
    # repetir la carga inicial no duplica ni pisa lo editado
    semillas_nucleo.sembrar(registro, None)
    assert PerfilPersona.objects.filter(codigo="invitado_o_invitada").count() == 1
    assert TipoLugar.objects.filter(codigo="casa_matriz").count() == 1 and Parentesco.objects.count() == 8
    PerfilPersona.objects.filter(codigo="estudiante").update(ficha="")
    semillas_nucleo.sembrar(registro, None)
    assert PerfilPersona.objects.get(codigo="estudiante").ficha == "estudiante"  # solo completa la que está vacía
    benef.refresh_from_db()
    assert benef.ficha == "vecino"


def test_la_sede_debe_ser_un_lugar_de_la_institucion(universidad, crear_persona, comuna):
    otra = Organizacion.objects.create(nombre="Instituto Ficticio", tipo=universidad.tipo)
    direccion = Direccion.objects.create(calle="Avenida Inventada", numero="1", comuna=comuna)

    def lugar(nombre, dueno, tipo):
        return Lugar.objects.create(nombre=nombre, tipo=TipoLugar.objects.get(codigo=tipo), direccion=direccion, organizacion_propietaria=dueno)

    casa_matriz = lugar("Casa Matriz Ficticia", universidad, "casa_matriz")
    sede_ajena = lugar("Sede del Instituto", otra, "sede")
    sala_propia = lugar("Sala de la Universidad", universidad, "sala")
    assert set(PersonaFormacion.sedes_de(universidad)) == {casa_matriz}
    f = PersonaFormacion(persona=crear_persona(), organizacion=universidad, sede_institucion=casa_matriz)
    f.full_clean()
    f.save()
    assert list(casa_matriz.estudiantes.all()) == [f]
    for mala in (sede_ajena, sala_propia):
        f.sede_institucion = mala
        with pytest.raises(ValidationError) as e:
            f.full_clean()
        assert "sede_institucion" in e.value.message_dict


def test_enlaza_la_sede_escrita_solo_si_hay_un_lugar_con_ese_nombre(universidad, crear_persona, comuna):
    direccion = Direccion.objects.create(calle="Calle Inventada", numero="2", comuna=comuna)
    sede, matriz = TipoLugar.objects.get(codigo="sede"), TipoLugar.objects.get(codigo="casa_matriz")
    norte = Lugar.objects.create(nombre="Sede Valle Ficticio", tipo=sede, direccion=direccion, organizacion_propietaria=universidad)
    for _ in range(2):  # dos lugares con el mismo nombre: no se adivina cuál es
        Lugar.objects.create(nombre="Campus Doble", tipo=matriz, direccion=direccion, organizacion_propietaria=universidad)

    def formacion(texto):
        return PersonaFormacion.objects.create(persona=crear_persona(), organizacion=universidad, sede=texto)

    coincide, ambigua, sin_lugar = formacion("  sede VALLE ficticio "), formacion("Campus Doble"), formacion("Sede Inventada")
    enlace_sedes.enlazar_sedes(registro, None)
    enlace_sedes.enlazar_sedes(registro, None)  # repetirla no cambia nada
    for f in (coincide, ambigua, sin_lugar):
        f.refresh_from_db()
    assert coincide.sede_institucion == norte and coincide.sede == "  sede VALLE ficticio "  # el texto anterior se conserva
    assert ambigua.sede_institucion is None and sin_lugar.sede_institucion is None


def test_hogar_y_familiares_sin_repetir_ni_ser_su_propio_familiar(crear_persona):
    vecina, hijo = crear_persona(), crear_persona()
    ficha = FichaVecino.objects.create(persona=vecina, jefatura_hogar=True, integrantes_hogar=3)
    hija = Parentesco.objects.get(codigo="hijo_o_hija")
    ninez = TramoEtario.objects.get(codigo="ninez")
    IntegranteHogar.objects.create(ficha=ficha, parentesco=hija, tramo=ninez, cantidad=2)
    IntegranteHogar.objects.create(ficha=ficha, parentesco=hija, tramo=None)
    IntegranteHogar.objects.create(ficha=ficha, parentesco=hija, tramo=ninez, vive_en_hogar=False)  # otra casa: es otra fila
    _choca(lambda: IntegranteHogar.objects.create(ficha=ficha, parentesco=hija, tramo=ninez))
    _choca(lambda: IntegranteHogar.objects.create(ficha=ficha, parentesco=hija, tramo=None))  # «sin tramo» tampoco se repite
    _choca(lambda: IntegranteHogar.objects.create(ficha=ficha, parentesco=hija, tramo=TramoEtario.objects.get(codigo="jovenes"), cantidad=0))
    assert ficha.integrantes.count() == 3 and ficha.history.count() == 1
    FamiliarVinculado.objects.create(persona=vecina, familiar=hijo, parentesco=hija)
    _choca(lambda: FamiliarVinculado.objects.create(persona=vecina, familiar=hijo, parentesco=Parentesco.objects.get(codigo="otro_familiar")))
    _choca(lambda: FamiliarVinculado.objects.create(persona=vecina, familiar=vecina, parentesco=hija))
    with pytest.raises(ValidationError):
        FamiliarVinculado(persona=hijo, familiar=hijo, parentesco=hija).full_clean()
    assert list(vecina.familiares.values_list("familiar", flat=True)) == [hijo.pk]
    _choca(lambda: FichaVecino.objects.create(persona=vecina))  # una sola ficha por persona


def test_copia_el_hogar_desde_los_datos_sensibles_sin_pisar(crear_persona):
    con_hogar, sin_hogar, ya_tenia = crear_persona(), crear_persona(), crear_persona()
    PerfilSensible.objects.create(persona=con_hogar, jefatura_hogar=True, integrantes_hogar=4, tramo_rsh="40")
    PerfilSensible.objects.create(persona=sin_hogar, genero="femenino")
    PerfilSensible.objects.create(persona=ya_tenia, jefatura_hogar=False, integrantes_hogar=5)
    FichaVecino.objects.create(persona=ya_tenia, integrantes_hogar=3)
    datos_personas.copiar_hogar(registro, None)
    datos_personas.copiar_hogar(registro, None)  # repetirla no duplica
    assert FichaVecino.objects.count() == 2 and not FichaVecino.objects.filter(persona=sin_hogar).exists()
    assert (con_hogar.ficha_vecino.jefatura_hogar, con_hogar.ficha_vecino.integrantes_hogar) == (True, 4)
    ya_tenia.refresh_from_db()
    assert (ya_tenia.ficha_vecino.jefatura_hogar, ya_tenia.ficha_vecino.integrantes_hogar) == (False, 3)  # completa, no pisa
    ps = PerfilSensible.objects.get(persona=con_hogar)
    assert (ps.jefatura_hogar, ps.integrantes_hogar, ps.tramo_rsh) == (True, 4, "40")  # las columnas antiguas se conservan


def test_edad_aproximada_sexo_e_invitado_y_voluntario(crear_persona):
    p = crear_persona(sexo="mujer")
    p.fijar_edad_aproximada(67)
    p.save()
    p.refresh_from_db()
    assert p.fecha_nacimiento == date(timezone.localdate().year - 67, 1, 1) and p.fecha_nacimiento_aproximada and p.edad == 67
    assert p.get_sexo_display() == "Mujer"
    p.fecha_nacimiento = None
    p.save()
    assert not Persona.objects.get(pk=p.pk).fecha_nacimiento_aproximada  # sin fecha no queda marcada
    invitada = FichaInvitado.objects.create(persona=p, tipo=TipoInvitado.objects.get(codigo="autoridad"), cargo="Alcaldesa ficticia")
    assert invitada.history.count() == 1
    invitada.invitado_por = p
    with pytest.raises(ValidationError):
        invitada.full_clean()
    vol = FichaVoluntario(persona=crear_persona(), estado=EstadoVoluntario.objects.get(codigo="activo"), horas_semanales=200)
    with pytest.raises(ValidationError):
        vol.full_clean()
    _choca(vol.save)
    vol.horas_semanales = 6
    vol.save()
    assert vol.persona.ficha_voluntario.estado.codigo == "activo"


def test_fusionar_conserva_el_sexo_y_la_marca_de_fecha_aproximada(crear_persona):
    from apps.nucleo.fusion import fusionar

    duplicada, queda = crear_persona(sexo="hombre"), crear_persona()
    duplicada.fijar_edad_aproximada(70)
    duplicada.save()
    fusionar(duplicada, queda, None, "misma persona")
    queda.refresh_from_db()
    assert queda.sexo == "hombre" and queda.fecha_nacimiento == duplicada.fecha_nacimiento and queda.fecha_nacimiento_aproximada

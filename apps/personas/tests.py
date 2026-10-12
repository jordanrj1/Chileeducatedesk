import pytest
from django.db import IntegrityError, transaction

from apps.nucleo.models import TipoContacto
from apps.nucleo.utilidades import calcular_dv
from apps.personas.duplicados import candidatos
from apps.personas.models import Contacto, ContactoEmergencia, Persona, PersonaFormacion

pytestmark = pytest.mark.django_db

RUT = f"12345678-{calcular_dv(12345678)}"


def nueva(c, **extra):
    datos = {"nombres": "Luis", "apellido_paterno": "Rojas", "apellido_materno": "Vera"}
    datos.update(extra)
    return c.post("/personas/nueva", datos)


def test_ficha_rapida_solo_con_nombre(cg):
    r = nueva(cg, apellido_paterno="", apellido_materno="")
    p = Persona.objects.get()
    assert r.status_code == 302 and r["Location"] == p.get_absolute_url()
    assert p.estado_registro.codigo == "incompleto"
    assert p.creado_por is not None


def test_persona_completa_con_contactos_normalizados(cg):
    nueva(cg, rut="12.345.678-5", correo="Luis@Ejemplo.invalid", telefono="9 8765 4321")
    p = Persona.objects.get()
    assert (p.rut_numero, p.rut_dv, p.rut) == (12345678, "5", "12.345.678-5")
    assert p.estado_registro.codigo == "activo"
    assert set(p.contactos.values_list("valor_normalizado", flat=True)) == {"luis@ejemplo.invalid", "+56987654321"}


def test_rut_invalido_rechazado(cg):
    r = nueva(cg, rut="12.345.678-0")
    assert r.status_code == 200 and not Persona.objects.exists()


def test_rut_unico_si_existe(cg):
    nueva(cg, rut="12.345.678-5")
    r = nueva(cg, nombres="Otro", rut="12345678-5", confirmar_duplicado="1")
    assert r.status_code == 200 and Persona.objects.count() == 1


def test_varias_personas_sin_rut_permitidas(cg):
    nueva(cg, nombres="Sin Rut Uno", apellido_paterno="Aa", apellido_materno="")
    nueva(cg, nombres="Sin Rut Dos", apellido_paterno="Bb", apellido_materno="", confirmar_duplicado="1")
    assert Persona.objects.filter(rut_numero__isnull=True).count() == 2


def test_restriccion_bd_rut_unico(db):
    Persona.objects.create(nombres="A", rut_numero=11111111, rut_dv="1")
    with pytest.raises(IntegrityError), transaction.atomic():
        Persona.objects.create(nombres="B", rut_numero=11111111, rut_dv="1")


def test_aviso_de_posible_duplicado_no_guarda_sola(cg):
    nueva(cg, nombres="Carolina", apellido_paterno="Fuentes", apellido_materno="Mora", correo="caro@ejemplo.invalid")
    r = nueva(cg, nombres="Carolina", apellido_paterno="Fuentes", apellido_materno="Mora", correo="otro@ejemplo.invalid")
    assert r.status_code == 200 and b"podr\xc3\xada ya existir" in r.content
    assert Persona.objects.count() == 1
    r = nueva(cg, nombres="Carolina", apellido_paterno="Fuentes", apellido_materno="Mora", correo="otro@ejemplo.invalid", confirmar_duplicado="1")
    assert r.status_code == 302 and Persona.objects.count() == 2  # nunca se fusiona ni bloquea sola


def test_duplicado_por_correo_aunque_el_nombre_sea_distinto(cg):
    nueva(cg, correo="Mismo@Ejemplo.invalid")
    p = Persona.objects.get()
    res = candidatos(nombres="Totalmente Distinto", correo="mismo@ejemplo.invalid")
    assert [x[0] for x in res] == [p] and "mismo correo" in res[0][1]


def test_duplicado_por_rut_y_telefono(persona):
    Persona.objects.filter(pk=persona.pk).update(rut_numero=11111111, rut_dv="1")
    Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="telefono_movil"), valor="9 1111 2222")
    res = candidatos(nombres="X", rut_numero=11111111, telefono="+56 9 1111 2222")
    assert res[0][0] == persona and {"mismo RUT", "mismo teléfono"} <= set(res[0][1])


def test_contacto_tiene_un_solo_dueno(persona, universidad):
    tipo = TipoContacto.objects.get(codigo="correo")
    with pytest.raises(IntegrityError), transaction.atomic():
        Contacto.objects.create(tipo=tipo, valor="a@b.invalid", persona=persona, organizacion=universidad)
    with pytest.raises(IntegrityError), transaction.atomic():
        Contacto.objects.create(tipo=tipo, valor="a@b.invalid")


def test_agregar_contacto_y_marcar_no_vigente(cg, persona):
    tipo = TipoContacto.objects.get(codigo="telefono_movil")
    r = cg.post(f"/personas/{persona.pk}/contactos/nuevo", {"tipo": tipo.pk, "valor": "9 1234 5678", "vigente": "on", "principal": "on"})
    assert r.status_code == 302
    c = persona.contactos.get()
    assert c.valor_normalizado == "+56912345678"
    cg.post(f"/personas/{persona.pk}/contactos/{c.pk}/alternar")
    c.refresh_from_db()
    assert c.vigente is False


def test_telefono_invalido_en_contacto(cg, persona):
    tipo = TipoContacto.objects.get(codigo="telefono_movil")
    r = cg.post(f"/personas/{persona.pk}/contactos/nuevo", {"tipo": tipo.pk, "valor": "123"})
    assert r.status_code == 200 and not persona.contactos.exists()


def test_no_se_edita_contacto_de_otra_persona(cg, persona):
    otra = Persona.objects.create(nombres="Otra")
    c = Contacto.objects.create(persona=otra, tipo=TipoContacto.objects.get(codigo="correo"), valor="x@y.invalid")
    assert cg.get(f"/personas/{persona.pk}/contactos/{c.pk}/editar").status_code == 404


def test_carrera_debe_pertenecer_a_la_institucion(cg, persona, universidad):
    from apps.nucleo.models import TipoOrganizacion
    from apps.organizaciones.models import Carrera, Organizacion

    otra = Organizacion.objects.create(nombre="Instituto Ficticio", tipo=TipoOrganizacion.objects.get(codigo="institucion_educativa"))
    carrera_otra = Carrera.objects.create(organizacion=otra, nombre="Pedagogía")
    r = cg.post(f"/personas/{persona.pk}/formacion/nuevo", {"organizacion": universidad.pk, "carrera": carrera_otra.pk, "estado": "estudiante"})
    assert r.status_code == 200 and not PersonaFormacion.objects.exists()
    carrera = Carrera.objects.create(organizacion=universidad, nombre="Trabajo Social")
    r = cg.post(f"/personas/{persona.pk}/formacion/nuevo", {"organizacion": universidad.pk, "carrera": carrera.pk, "estado": "estudiante", "vigente": "on"})
    assert r.status_code == 302 and PersonaFormacion.objects.count() == 1


def test_formacion_solo_en_institucion_educativa(cg, persona):
    from apps.nucleo.models import TipoOrganizacion
    from apps.organizaciones.models import Organizacion

    muni = Organizacion.objects.create(nombre="Muni Ficticia", tipo=TipoOrganizacion.objects.get(codigo="municipalidad"))
    r = cg.post(f"/personas/{persona.pk}/formacion/nuevo", {"organizacion": muni.pk, "estado": "titulado"})
    assert r.status_code == 200 and not PersonaFormacion.objects.exists()


def test_vinculos_historicos_de_cargo(cg, persona, universidad):
    r = cg.post(f"/personas/{persona.pk}/vinculos/nuevo", {"organizacion": universidad.pk, "cargo": "Directora de carrera", "tipo_cargo": "autoridad", "fecha_inicio": "2020-03-01", "fecha_termino": "2022-12-31"})
    assert r.status_code == 302
    v = persona.vinculos.get()
    assert v.vigente is False
    r = cg.post(f"/personas/{persona.pk}/vinculos/nuevo", {"organizacion": universidad.pk, "cargo": "Directora", "tipo_cargo": "autoridad", "fecha_inicio": "2023-01-01"})
    assert persona.vinculos.count() == 2  # los cargos anteriores se conservan


def test_vinculo_fechas_incoherentes(cg, persona, universidad):
    r = cg.post(f"/personas/{persona.pk}/vinculos/nuevo", {"organizacion": universidad.pk, "tipo_cargo": "funcional", "fecha_inicio": "2024-01-01", "fecha_termino": "2023-01-01"})
    assert r.status_code == 200


def test_disponibilidad_hora_coherente(cg, persona):
    r = cg.post(f"/personas/{persona.pk}/disponibilidad/nuevo", {"dia": 1, "hora_inicio": "18:00", "hora_fin": "17:00", "vigente": "on"})
    assert r.status_code == 200
    r = cg.post(f"/personas/{persona.pk}/disponibilidad/nuevo", {"dia": 1, "hora_inicio": "17:00", "hora_fin": "19:00", "vigente": "on"})
    assert r.status_code == 302 and persona.disponibilidades.count() == 1


def test_datos_sensibles_exigen_permiso(cg, ca, persona, gestor):
    from django.contrib.auth.models import Permission

    gestor.user_permissions.clear()
    gestor.groups.first().permissions.remove(Permission.objects.get(codename="ver_sensibles"))
    gestor = type(gestor).objects.get(pk=gestor.pk)
    cg.force_login(gestor)
    assert cg.get(f"/personas/{persona.pk}/emergencia/nuevo").status_code == 403
    assert cg.post(f"/personas/{persona.pk}/emergencia/nuevo", {"nombre": "X", "telefono": "+56911112222"}).status_code == 403
    assert not ContactoEmergencia.objects.exists()
    # la pestaña tampoco aparece
    assert b"Contacto de emergencia" not in cg.get(persona.get_absolute_url()).content


def test_contacto_de_emergencia_normaliza_telefono(cg, persona):
    cg.post(f"/personas/{persona.pk}/emergencia/nuevo", {"nombre": "Marta", "parentesco": "madre", "telefono": "9 1111 2222", "vigente": "on"})
    assert persona.contactos_emergencia.get().telefono_normalizado == "+56911112222"


def test_pestanas_de_la_ficha(cg, persona):
    for tab in ["datos", "contactos", "direcciones", "formacion", "experiencia", "disponibilidad", "vinculos", "emergencia", "verificaciones", "historial"]:
        assert cg.get(f"/personas/{persona.pk}?tab={tab}").status_code == 200, tab


def test_historial_registra_cambios(cg, persona):
    cg.post(f"/personas/{persona.pk}/editar", {"nombres": "Ana María", "apellido_paterno": "Pérez", "apellido_materno": "Soto", "profesion": "Docente"})
    html = cg.get(f"/personas/{persona.pk}?tab=historial").content.decode()
    assert "Modificación" in html and "Docente" in html
    assert persona.history.count() == 2


def test_desactivar_no_borra(cg, persona):
    cg.post(f"/personas/{persona.pk}/alternar")
    persona.refresh_from_db()
    assert persona.activo is False and Persona.objects.filter(pk=persona.pk).exists()
    cg.post(f"/personas/{persona.pk}/alternar")
    persona.refresh_from_db()
    assert persona.activo is True


def test_no_existe_ruta_para_eliminar(cg, persona):
    for metodo in ("delete", "post"):
        for ruta in (f"/personas/{persona.pk}/eliminar", f"/personas/{persona.pk}/borrar"):
            assert getattr(cg, metodo)(ruta).status_code == 404
    assert b"Eliminar" not in cg.get(persona.get_absolute_url()).content


def test_listado_busqueda_filtros_y_paginacion(cg):
    for i in range(30):
        Persona.objects.create(nombres=f"Nombre{i:02d}", apellido_paterno="Lista")
    html = cg.get("/personas").content.decode()
    assert "30 registros" in html and "Siguiente" in html
    assert "Nombre05" in cg.get("/personas?q=nombre05").content.decode()
    assert "Sin resultados" in cg.get("/personas?q=zzzz").content.decode()
    Persona.objects.filter(nombres="Nombre01").update(activo=False)
    assert "Nombre01" not in cg.get("/personas").content.decode()
    assert "Nombre01" in cg.get("/personas?activo=*&q=nombre01").content.decode()


def test_busqueda_por_rut(cg):
    Persona.objects.create(nombres="Con Rut", rut_numero=12345678, rut_dv="5")
    assert "Con Rut" in cg.get("/personas?q=12.345.678").content.decode()


def test_administrador_ve_pero_no_crea(ca, persona):
    assert ca.get("/personas").status_code == 200
    assert ca.get(persona.get_absolute_url()).status_code == 200
    assert ca.get("/personas/nueva").status_code == 403
    assert ca.post(f"/personas/{persona.pk}/editar", {"nombres": "X"}).status_code == 403


def test_persona_en_varios_estados_de_registro(persona):
    assert Persona.objects.cola_incompletos is not None


# --- Requerimientos por módulo (PE) -----------------------------------------------------------------
def test_ficha_rapida_y_ficha_completa(cg):
    rapida = cg.get("/personas/nueva").content.decode()
    assert "Ficha rápida" in rapida and 'name="rut"' not in rapida and 'name="telefono"' in rapida
    completa = cg.get("/personas/nueva?modo=completa").content.decode()
    assert 'name="rut"' in completa and 'name="origen"' in completa
    r = cg.post("/personas/nueva", {"modo": "rapida", "nombres": "Rápida", "telefono": "9 1234 5678"})
    assert r.status_code == 302 and Persona.objects.get().contactos.count() == 1


def test_guardar_y_completar_despues(cg):
    r = cg.post("/personas/nueva", {"modo": "completa", "nombres": "Luego", "apellido_paterno": "Completo", "correo": "l@ejemplo.invalid", "despues": "1"})
    p = Persona.objects.get()
    assert r["Location"] == "/personas/nueva" and p.estado_registro.codigo == "incompleto"


def test_aviso_de_duplicado_ofrece_usar_existente(cg, persona):
    html = cg.post("/personas/nueva", {"modo": "rapida", "nombres": "Ana María", "apellido_paterno": "Pérez"}).content.decode()
    assert "Usar existente" in html and persona.get_absolute_url() in html and "Crear de todos modos" in html


def test_filtros_por_relacion_organizacion_y_comuna(cg, crear_actividad, rol, estado_part, universidad, comuna):
    from apps.actividades.models import Participacion
    from apps.personas.models import PersonaDireccion, PersonaOrganizacion
    from apps.territorio.models import Direccion

    vol = Persona.objects.create(nombres="Voluntaria")
    otra = Persona.objects.create(nombres="Otra")
    Participacion.objects.create(actividad=crear_actividad(), persona=vol, rol=rol("voluntario"), estado=estado_part("confirmado"))
    PersonaOrganizacion.objects.create(persona=vol, organizacion=universidad, cargo="Ayudante")
    PersonaDireccion.objects.create(persona=vol, direccion=Direccion.objects.create(comuna=comuna))
    for filtro in (f"rol={rol('voluntario').pk}", f"organizacion={universidad.pk}", f"comuna={comuna.pk}"):
        html = cg.get(f"/personas?{filtro}").content.decode()
        assert "Voluntaria" in html and ">Otra<" not in html, filtro


def test_candado_en_datos_restringidos(cg, persona):
    html = cg.get(persona.get_absolute_url()).content.decode()
    assert "Direcciones 🔒" in html and "Dato restringido" in html and "Participaciones" in html


def test_agregar_persona_con_cargo_desde_la_organizacion(cg, universidad, persona):
    r = cg.post(f"/organizaciones/{universidad.pk}/personas/nuevo", {"persona": persona.pk, "cargo": "Presidenta", "tipo_cargo": "directorio", "fecha_inicio": "2025-01-01"})
    assert r.status_code == 302 and persona.vinculos.get().cargo == "Presidenta"
    html = cg.get(f"/organizaciones/{universidad.pk}?tab=personas").content.decode()
    assert "Presidenta" in html and "Agregar persona con cargo" in html
    v = persona.vinculos.get()
    assert cg.post(f"/organizaciones/{universidad.pk}/personas/{v.pk}/alternar").status_code == 404  # no hay «vigente» real: se cierra con fecha

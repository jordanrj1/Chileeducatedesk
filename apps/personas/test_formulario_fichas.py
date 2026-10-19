"""Pruebas del formulario por tipo de persona: marcar estudiante, vecino, invitado o voluntario muestra su sección y guarda
solo esas secciones (con la sede, la carrera y la comunidad creadas en el momento), «Mostrar secciones» sin JavaScript,
el aviso de duplicados antes de guardar nada y las tarjetas de la pestaña Datos con su «Editar». Datos ficticios."""
import re

import pytest

from apps.comunidades.models import Comunidad, ComunidadMiembro
from apps.lugares.models import Lugar
from apps.nucleo.models import EstadoVoluntario, Parentesco, PerfilPersona, TipoInvitado, TipoLugar, TramoEtario
from apps.organizaciones.models import Carrera, Organizacion
from apps.personas.models import FamiliarVinculado, FichaInvitado, FichaVecino, FichaVoluntario, Persona, PersonaFormacion
from apps.territorio.models import Direccion

pytestmark = pytest.mark.django_db


def _perfil(ficha):
    return PerfilPersona.objects.filter(ficha=ficha).order_by("orden").first().pk


def _filas(prefijo, filas, iniciales=0, total=None):
    """Datos de un grupo de filas (formset) tal como los envía el navegador."""
    datos = {f"{prefijo}-TOTAL_FORMS": total or len(filas), f"{prefijo}-INITIAL_FORMS": iniciales, f"{prefijo}-MIN_NUM_FORMS": 0, f"{prefijo}-MAX_NUM_FORMS": 1000}
    for i, fila in enumerate(filas):
        datos.update({f"{prefijo}-{i}-{k}": v for k, v in fila.items()})
    return datos


def test_estudiante_elige_sede_y_carrera_de_su_institucion_y_crea_las_que_faltan(cg, universidad, comuna):
    sede = Lugar.objects.create(nombre="Sede Ficticia Norte", tipo=TipoLugar.objects.get(codigo="sede"), organizacion_propietaria=universidad,
                                direccion=Direccion.objects.create(comuna=comuna))
    otra = Organizacion.objects.create(nombre="Instituto Inventado", tipo=universidad.tipo)
    Carrera.objects.create(organizacion=otra, nombre="Carrera de Otra Institución")
    Carrera.objects.create(organizacion=universidad, nombre="Trabajo Social Ficticio")
    html = cg.get("/personas/nueva").content.decode()
    assert "Tipo de registro" in html and 'data-tipo-ficha="estudiante"' in html
    assert re.search(r'id="ficha-estudiante" data-ficha-seccion="estudiante" hidden', html)  # oculta hasta marcarla
    # al elegir la institución se ofrecen solo sus sedes y carreras
    html = cg.get(f"/personas/estudios/dependientes?_prefijo=est&est-organizacion={universidad.pk}").content.decode()
    assert "Sede Ficticia Norte" in html and "Trabajo Social Ficticio" in html and "Carrera de Otra Institución" not in html
    assert "+ Crear sede de Universidad Ficticia" in html and "+ Crear carrera de Universidad Ficticia" in html
    # sede elegida y carrera escrita: la carrera se crea al guardar
    r = cg.post("/personas/nueva", {"modo": "rapida", "nombres": "Tomás", "apellido_paterno": "Inventado", "perfiles": [_perfil("estudiante")],
                                    "est-organizacion": universidad.pk, "est-sede_institucion": sede.pk, "est-nueva_carrera": "Técnico en Huertos Urbanos",
                                    "est-estado": "estudiante", "est-jornada": "vespertina", "est-nivel_actual": 2})
    assert r.status_code == 302
    f = PersonaFormacion.objects.get(persona__nombres="Tomás")
    assert f.sede_institucion == sede and f.carrera.nombre == "Técnico en Huertos Urbanos" and f.carrera.organizacion == universidad
    # sede escrita: se crea como lugar de la institución, en la comuna indicada; repetir el nombre de una sede existente se rechaza
    base = {"modo": "rapida", "nombres": "Valentina", "apellido_paterno": "Ejemplo", "perfiles": [_perfil("estudiante")], "est-organizacion": universidad.pk,
            "est-nueva_sede_tipo": "casa_matriz", "est-nueva_sede_comuna": comuna.pk, "est-estado": "estudiante"}
    r = cg.post("/personas/nueva", {**base, "est-nueva_sede": "sede ficticia  NORTE"})
    assert r.status_code == 200 and "ya tiene la sede «Sede Ficticia Norte»" in r.content.decode() and not Persona.objects.filter(nombres="Valentina").exists()
    r = cg.post("/personas/nueva", {**base, "est-nueva_sede": "Casa Central Ficticia"})
    assert r.status_code == 302
    nueva = PersonaFormacion.objects.get(persona__nombres="Valentina").sede_institucion
    assert nueva.organizacion_propietaria == universidad and nueva.tipo.codigo == "casa_matriz" and nueva.direccion.comuna == comuna


def test_vecino_con_direccion_comunidad_hogar_y_familiar(cg, comuna, crear_persona):
    nieta = crear_persona("Nieta Ficticia")
    hijo, nieto = Parentesco.objects.get(codigo="hijo_o_hija"), Parentesco.objects.get(codigo="nieto_o_nieta")
    ninez = TramoEtario.objects.get(codigo="ninez")
    datos = {
        "modo": "rapida", "nombres": "Rosa", "apellido_paterno": "Vecina", "perfiles": [_perfil("vecino")],
        "vec-comuna": comuna.pk, "vec-calle": "Pasaje Inventado", "vec-numero": "123", "vec-rol_comunidad": "integrante",
        "vec-nueva_comunidad": "Vecinos del Pasaje Inventado", "vec-per-edad": 67, "vec-per-sexo": "mujer",
        "vec-hog-jefatura_hogar": "True", "vec-hog-integrantes_hogar": 3,
        # como el navegador: las filas sin tocar llegan con «vive en el hogar» marcado y la cantidad vacía
        **_filas("vec-int", [{"cantidad": 2, "parentesco": hijo.pk, "tramo": ninez.pk, "vive_en_hogar": "on"}] + [{"cantidad": "", "vive_en_hogar": "on"}] * 2),
        **_filas("vec-fam", [{"familiar": nieta.pk, "parentesco": nieto.pk}], total=2),
    }
    r = cg.post("/personas/nueva", datos)
    assert r.status_code == 302
    p = Persona.objects.get(nombres="Rosa")
    assert p.sexo == "mujer" and p.fecha_nacimiento_aproximada and p.edad == 67
    residencia = p.direcciones.get(tipo="residencia")
    assert residencia.direccion.numero == "123" and residencia.direccion.comuna == comuna
    comunidad = Comunidad.objects.get(nombre="Vecinos del Pasaje Inventado")
    assert comunidad.comuna == comuna and ComunidadMiembro.objects.filter(comunidad=comunidad, persona=p).exists()
    ficha = FichaVecino.objects.get(persona=p)
    assert ficha.jefatura_hogar is True and ficha.integrantes_hogar == 3
    assert [(i.cantidad, i.parentesco, i.tramo) for i in ficha.integrantes.all()] == [(2, hijo, ninez)]
    assert FamiliarVinculado.objects.get(persona=p).familiar == nieta
    # la ficha muestra la tarjeta del vecino, con el hogar 🔒 y «Editar»
    html = cg.get(p.get_absolute_url()).content.decode()
    tarjeta = html[html.index('id="tarjeta-vecino"'):]
    assert "Vecinos del Pasaje Inventado" in tarjeta and "2 · Hijo o hija · Niñez" in tarjeta and "Dato restringido" in tarjeta
    assert f"/personas/{p.pk}/fichas/vecino" in tarjeta and nieta.get_absolute_url() in tarjeta
    editar = cg.get(f"/personas/{p.pk}/fichas/vecino").content.decode()
    assert "Cambiar en Direcciones" in editar and 'name="vec-int-0-cantidad" value="2"' in editar


def test_invitado_y_voluntario_a_la_vez_y_solo_lo_marcado(cg):
    autoridad, activo = TipoInvitado.objects.get(codigo="autoridad"), EstadoVoluntario.objects.get(codigo="activo")
    r = cg.post("/personas/nueva", {
        "modo": "completa", "nombres": "Julia", "apellido_paterno": "Doble", "perfiles": [_perfil("invitado"), _perfil("voluntario")],
        "inv-tipo": autoridad.pk, "inv-cargo": "Concejala ficticia", "vol-estado": activo.pk, "vol-horas_semanales": 4,
        "est-nueva_carrera": "No se marcó estudiante",  # una sección no marcada no se guarda ni se valida
    })
    assert r.status_code == 302
    p = Persona.objects.get(nombres="Julia")
    assert FichaInvitado.objects.get(persona=p).cargo == "Concejala ficticia" and FichaVoluntario.objects.get(persona=p).horas_semanales == 4
    assert not p.formaciones.exists() and not Carrera.objects.exists()
    # «Editar» de la tarjeta guarda solo esa ficha
    r = cg.post(f"/personas/{p.pk}/fichas/voluntario", {"vol-estado": activo.pk, "vol-horas_semanales": 6})
    assert r.status_code == 302 and FichaVoluntario.objects.get(persona=p).horas_semanales == 6
    assert cg.post(f"/personas/{p.pk}/fichas/voluntario", {"vol-horas_semanales": 200}).status_code == 200  # una semana tiene 168 horas


def test_mostrar_secciones_sin_javascript_y_duplicados_antes_de_guardar(cg, persona):
    r = cg.post("/personas/nueva", {"modo": "rapida", "nombres": "Sin Guardar", "perfiles": [_perfil("voluntario")], "_mostrar": "1"})
    html = r.content.decode()
    assert r.status_code == 200 and not Persona.objects.filter(nombres="Sin Guardar").exists()
    assert 'id="ficha-voluntario" data-ficha-seccion="voluntario">' in html and 'id="ficha-estudiante" data-ficha-seccion="estudiante" hidden' in html
    assert "fche-campo__error" not in html  # se vuelve a dibujar sin marcar errores
    datos = {"modo": "rapida", "nombres": persona.nombres, "apellido_paterno": persona.apellido_paterno, "perfiles": [_perfil("voluntario")],
             "vol-horas_semanales": 3}
    r = cg.post("/personas/nueva", datos)
    assert r.status_code == 200 and "Crear de todos modos" in r.content.decode() and not FichaVoluntario.objects.exists()
    r = cg.post("/personas/nueva", {**datos, "confirmar_duplicado": "1", "nota_distincion": "Es la prima, de otra comuna"})
    assert r.status_code == 302 and FichaVoluntario.objects.get().persona.observaciones.startswith("Se distingue")

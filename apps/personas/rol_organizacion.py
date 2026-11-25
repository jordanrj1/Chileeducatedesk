"""F26 P2: valores del catálogo «Rol en la organización» y cómo deducir el rol desde el cargo escrito a mano.
Sin modelos: lo usan la migración que rellena `PersonaOrganizacion.rol` y el servicio `vincular()`.
F27: cada rol dice si admite cargo (`con_cargo`) y trae su descripción; también se explican los tipos de cargo."""
import unicodedata

# (código, nombre, orden) de los valores iniciales del catálogo
ROLES = [
    ("estudiante", "Estudiante", 1), ("docente", "Docente", 2), ("funcionario", "Funcionario o funcionaria", 3),
    ("dirigente", "Dirigente", 4), ("socio", "Socio o socia", 5), ("practicante", "Practicante", 6),
    ("autoridad", "Autoridad", 7), ("otro", "Otro", 8),
]

# F27: (código, nombre, orden, con_cargo, descripción) de los valores del catálogo ampliado. Los que ya existían conservan
# su nombre y orden; la migración solo completa su descripción si está vacía y fija `con_cargo`. Valores por validar [V].
ROLES_F27 = [
    ("estudiante", "Estudiante", 1, False, "Estudia en la institución. La carrera y la sede quedan en sus Estudios."),
    ("docente", "Docente", 2, True, "Docente o académico: enseña o investiga en la institución. Puede tener un cargo (jefa de carrera)."),
    ("funcionario", "Funcionario o funcionaria", 3, True, "Trabaja en la organización con contrato u honorarios. Puede tener un cargo (encargado de vinculación)."),
    ("dirigente", "Dirigente", 4, True, "Integra la directiva electa o designada (presidencia, secretaría, tesorería, directores)."),
    ("socio", "Socio o socia", 5, True, "Pertenece a la organización como socio o miembro inscrito. Puede tener un cargo (delegada)."),
    ("practicante", "Practicante", 6, False, "Hace su práctica profesional o pasantía en la organización."),
    ("autoridad", "Autoridad", 7, True, "Es la máxima autoridad de la institución o un cargo público (alcaldesa, director de liceo, rector, seremi)."),
    ("otro", "Otro", 8, True, "Otro vínculo con la organización. El detalle va en el cargo o en las observaciones."),
    ("representante_legal", "Representante legal", 9, True, "Representa legalmente a la organización y firma por ella (convenios, cartas)."),
    ("voluntario", "Voluntario o voluntaria", 10, True, "Colabora con la organización sin remuneración. Puede tener un cargo (coordinadora de voluntariado)."),
    ("contacto", "Contacto o enlace", 11, True, "Es la persona con quien la Fundación se comunica en la organización."),
    ("egresado", "Egresado o egresada", 12, False, "Terminó sus estudios en la institución."),
    ("vecino", "Vecino o vecina", 13, False, "Vive en el territorio de la organización (junta de vecinos, comité)."),
    ("apoderado", "Apoderado o apoderada", 14, False, "Es apoderado de un estudiante de la institución."),
    ("beneficiario", "Beneficiario o beneficiaria", 15, False, "Recibe apoyo o servicios de la organización."),
]
SIN_CARGO = {c for c, _n, _o, con_cargo, _d in ROLES_F27 if not con_cargo}

# F27: explicación de cada tipo de cargo (se muestra bajo la lista «Tipo de cargo»)
DESCRIPCIONES_TIPO_CARGO = {
    "directorio": "Integra la directiva electa o designada (presidencia, secretaría, tesorería, directores).",
    "funcional": "Trabaja, coordina o tiene una responsabilidad en un área, sin ser parte de la directiva (encargado, coordinadora, profesional).",
    "autoridad": "Es la máxima autoridad de la institución o un cargo público (alcaldesa, director de liceo, rector, seremi).",
}


def tipo_cargo_sugerido(codigo_rol):
    """Tipo de cargo que se deduce del rol cuando no se indica: dirigente → directorio, autoridad → autoridad; si no, vacío."""
    return {"dirigente": "directorio", "autoridad": "autoridad"}.get(codigo_rol or "", "")


# Primera palabra del cargo (sin tildes ni mayúsculas) → código del rol
PREFIJOS = {
    "estudiante": "estudiante", "alumno": "estudiante", "alumna": "estudiante",
    "docente": "docente", "profesor": "docente", "profesora": "docente",
    "funcionario": "funcionario", "funcionaria": "funcionario", "funcionario/a": "funcionario",
    "dirigente": "dirigente", "dirigenta": "dirigente", "dirigente/a": "dirigente",
    "socio": "socio", "socia": "socio", "socio/a": "socio",
    "practicante": "practicante", "autoridad": "autoridad", "otro": "otro", "otra": "otro",
    # F27: roles nuevos
    "egresado": "egresado", "egresada": "egresado", "egresado/a": "egresado",
    "vecino": "vecino", "vecina": "vecino", "vecino/a": "vecino",
    "apoderado": "apoderado", "apoderada": "apoderado", "apoderado/a": "apoderado",
    "beneficiario": "beneficiario", "beneficiaria": "beneficiario", "beneficiario/a": "beneficiario",
    "voluntario": "voluntario", "voluntaria": "voluntario", "voluntario/a": "voluntario",
    "representante": "representante_legal", "contacto": "contacto", "enlace": "contacto",
}


def _sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def codigo_desde_cargo(cargo):
    """«Docente de Lenguaje» → «docente»; «Socio/a» → «socio»; sin coincidencia → ""."""
    texto = _sin_tildes((cargo or "").strip().lower())
    if not texto:
        return ""
    primera = texto.replace("·", " ").replace(",", " ").replace(":", " ").split()[0]
    return PREFIJOS.get(primera, "")

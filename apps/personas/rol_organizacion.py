"""F26 P2: valores del catálogo «Rol en la organización» y cómo deducir el rol desde el cargo escrito a mano.
Sin modelos: lo usan la migración que rellena `PersonaOrganizacion.rol` y el servicio `vincular()`."""
import unicodedata

# (código, nombre, orden) de los valores iniciales del catálogo
ROLES = [
    ("estudiante", "Estudiante", 1), ("docente", "Docente", 2), ("funcionario", "Funcionario o funcionaria", 3),
    ("dirigente", "Dirigente", 4), ("socio", "Socio o socia", 5), ("practicante", "Practicante", 6),
    ("autoridad", "Autoridad", 7), ("otro", "Otro", 8),
]

# Primera palabra del cargo (sin tildes ni mayúsculas) → código del rol
PREFIJOS = {
    "estudiante": "estudiante", "alumno": "estudiante", "alumna": "estudiante",
    "docente": "docente", "profesor": "docente", "profesora": "docente",
    "funcionario": "funcionario", "funcionaria": "funcionario", "funcionario/a": "funcionario",
    "dirigente": "dirigente", "dirigenta": "dirigente", "dirigente/a": "dirigente",
    "socio": "socio", "socia": "socio", "socio/a": "socio",
    "practicante": "practicante", "autoridad": "autoridad", "otro": "otro", "otra": "otro",
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

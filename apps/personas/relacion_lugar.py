"""F27: valores iniciales del catálogo «Relación con un lugar» (qué hace una persona ahí), agrupados por ámbito, y cómo
pasar del campo antiguo `PersonaLugar.relacion` al catálogo y de vuelta. Sin modelos: lo usan la migración y el modelo.
Valores por validar con el cliente [V]."""

# (código, nombre, ámbito, orden, descripción)
RELACIONES = [
    ("estudia", "Estudia ahí", "estudio", 1, "Es estudiante del establecimiento o de la sede."),
    ("practica", "Hace su práctica ahí", "estudio", 2, "Hace su práctica profesional o pasantía en el lugar."),
    ("trabaja", "Trabaja ahí", "trabajo", 3, "Trabaja en el lugar con contrato o de planta."),
    ("presta_servicios", "Presta servicios u honorarios", "trabajo", 4, "Trabaja ahí a honorarios o presta un servicio puntual."),
    ("dirige", "Dirige o administra el lugar", "trabajo", 5, "Está a cargo del lugar: director, administradora, encargado de la sede."),
    ("socio", "Es socia o miembro", "comunidad", 6, "Pertenece a la organización o club que funciona en el lugar."),
    ("voluntariado", "Hace voluntariado ahí", "comunidad", 7, "Colabora sin remuneración en el lugar."),
    ("participa", "Participa en talleres o actividades", "comunidad", 8, "Asiste a talleres, cursos o actividades que se hacen en el lugar."),
    ("punto_reunion", "Lo usa como punto de reunión", "comunidad", 9, "Se reúne ahí con su grupo o comunidad."),
    ("vive", "Vive ahí", "residencia", 10, "Vive en el lugar (por ejemplo, una residencia o un hogar)."),
    ("vive_cerca", "Vive cerca (vecino del lugar)", "residencia", 11, "Vive al lado o en el barrio del lugar."),
    ("contacto", "Contacto o enlace del lugar", "otra", 12, "Es con quien se coordina el uso del lugar."),
    ("dueno", "Dueño o arrendatario", "otra", 13, "Es dueño del lugar o lo arrienda."),
    ("otra", "Otra relación", "otra", 14, "Otra relación: detállala en las observaciones."),
]

# Campo antiguo `relacion` → código del catálogo
DESDE_ANTIGUA = {"estudia": "estudia", "trabaja": "trabaja", "participa": "participa", "vive": "vive", "otra": "otra"}

# Ámbito del catálogo → valor del campo antiguo (que se mantiene al día sin mostrarse)
ANTIGUA_POR_AMBITO = {"estudio": "estudia", "trabajo": "trabaja", "comunidad": "participa", "residencia": "vive", "otra": "otra"}

"""F28 B: categorías de gasto iniciales (editables en Catálogos) y a qué ítem del presupuesto del proyecto se comparan.
Un valor agregado después en Catálogos se compara con «Otros» mientras no se le asigne otra cosa."""

# (código, nombre, orden, descripción)
CATEGORIAS = [
    ("alimentacion", "Alimentación", 1, "Colaciones, almuerzos, café y agua para el equipo o los asistentes."),
    ("traslado", "Traslado", 2, "Pasajes, bencina, peajes, arriendo de movilización y similares."),
    ("materiales", "Materiales", 3, "Insumos, útiles, herramientas y materiales que se usan o se entregan en la actividad."),
    ("arriendo_de_espacio", "Arriendo de espacio", 4, "Salas, sedes, equipos o instalaciones arrendadas por el día."),
    ("servicios_u_honorarios", "Servicios u honorarios", 5, "Pagos a quien presta un servicio o dicta una charla o taller."),
    ("impresion_y_difusion", "Impresión y difusión", 6, "Fotocopias, impresiones, afiches, pendones y publicidad."),
    ("otros", "Otros", 7, "Lo que no calza en las demás categorías. Explícalo en el concepto."),
]

# Categoría del gasto -> categoría del ítem de presupuesto (ItemPresupuesto.CATEGORIAS)
A_PRESUPUESTO = {
    "alimentacion": "operacional",
    "traslado": "operacional",
    "materiales": "materiales",
    "arriendo_de_espacio": "operacional",
    "servicios_u_honorarios": "recursos_humanos",
    "impresion_y_difusion": "difusion",
    "otros": "otros",
}

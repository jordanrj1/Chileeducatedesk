MENU = [
    ("dashboard", "Inicio", "/dashboard"),
    ("solicitudes", "Solicitudes", "/solicitudes"),
    ("actividades", "Actividades", "/actividades"),
    ("personas", "Personas", "/personas"),
    ("organizaciones", "Organizaciones", "/organizaciones"),
    ("lugares", "Lugares", "/lugares"),
    ("calendario", "Calendario", "/calendario"),
    ("documentos", "Documentos", "/documentos"),
]


def navegacion(request):
    return {"menu": MENU}

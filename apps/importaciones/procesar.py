"""Análisis (vista previa), aplicación y reversión de lotes. Nada se guarda sin revisión."""
import re

from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.actividades.models import Participacion
from apps.documentos.origen import registrar_origen
from apps.nucleo.auditoria import registrar
from apps.nucleo.models import EstadoParticipacion, EstadoRegistro, TipoContacto, TipoLugar, TipoOrganizacion
from apps.nucleo.utilidades import normalizar_telefono, separar_nombre, separar_rut, telefono_normalizado_valido
from apps.organizaciones.models import Carrera, Organizacion
from apps.personas.duplicados import candidatos
from apps.personas.models import Contacto, Persona, PersonaFormacion
from apps.territorio.models import Comuna, Direccion

from .models import Lote, LoteItem

CAMPOS = {
    "listado_actividad": ["nombres", "apellido_paterno", "apellido_materno", "rut", "correo", "telefono"],
    "personas": ["nombres", "apellido_paterno", "apellido_materno", "rut", "correo", "telefono"],
    "organizaciones": ["nombre", "tipo", "rut", "correo", "telefono", "comuna"],
    "lugares": ["nombre", "tipo", "calle", "numero", "comuna", "capacidad"],
}
CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
UMBRAL = 0.5


def _normalizar_persona(d):
    d = dict(d)
    if not d.get("nombres") and d.get("nombre_completo"):
        d["nombres"], d["apellido_paterno"], d["apellido_materno"] = separar_nombre(d["nombre_completo"])
    elif d.get("apellidos") and not d.get("apellido_paterno"):
        partes = d["apellidos"].split(" ", 1)
        d["apellido_paterno"], d["apellido_materno"] = partes[0], (partes[1] if len(partes) > 1 else "")
    elif d.get("nombres") and not d.get("apellido_paterno") and not d.get("apellidos") and " " in d["nombres"].strip():
        # Una sola columna «Nombre» con nombre y apellidos juntos («Nombre Apellido» o «Apellido, Nombre»)
        d["nombres"], d["apellido_paterno"], d["apellido_materno"] = separar_nombre(d["nombres"])
    d.pop("nombre_completo", None)
    d.pop("apellidos", None)
    if d.get("telefono"):
        d["telefono"] = normalizar_telefono(d["telefono"])
    if d.get("correo"):
        d["correo"] = d["correo"].strip().lower()
    return d


def _analizar_persona(d, vistos):
    errores, cands, estado, existente = [], [], "nuevo", None
    d = _normalizar_persona(d)
    rut = None
    if not d.get("nombres"):
        errores.append("Falta el nombre.")
    if d.get("rut"):
        try:
            rut = separar_rut(d["rut"])
            d["rut"] = f"{rut[0]}-{rut[1]}"
        except ValidationError as e:
            errores.append(e.messages[0])
    if d.get("correo") and not CORREO.match(d["correo"]):
        errores.append("Correo no válido.")
    if d.get("telefono") and not telefono_normalizado_valido(d["telefono"]):
        errores.append("Teléfono no interpretable (usa +56 9 …).")
    for clave in (("rut", d.get("rut")), ("correo", d.get("correo"))):
        if clave[1]:
            if clave in vistos:
                errores.append(f"Repetida en el archivo (misma {clave[0]} que la fila {vistos[clave]}).")
            else:
                vistos[clave] = vistos.get("_fila", 0)
    if errores:
        return d, "error", errores, [], None
    encontrados = candidatos(d.get("nombres", ""), d.get("apellido_paterno", ""), d.get("apellido_materno", ""), rut[0] if rut else None, d.get("correo", ""), d.get("telefono", ""))
    for p, razones in encontrados:
        cands.append({"pk": p.pk, "nombre": p.nombre_completo, "razones": razones})
    fuertes = [c for c in cands if any(r in ("mismo RUT", "mismo correo") for r in c["razones"])]
    if fuertes:
        estado, existente = "existente", fuertes[0]["pk"]
    elif cands:
        estado = "duplicado"
    return d, estado, errores, cands, existente


def _comuna(nombre):
    if not nombre:
        return None
    return Comuna.objects.filter(nombre__iexact=nombre.strip()).first()


def _analizar_org(d, vistos):
    errores, cands, estado, existente = [], [], "nuevo", None
    d = dict(d)
    if not d.get("nombre") and d.get("nombres"):
        d["nombre"] = d.pop("nombres")
    if not d.get("nombre"):
        errores.append("Falta el nombre.")
    rut = None
    if d.get("rut"):
        try:
            rut = separar_rut(d["rut"])
            d["rut"] = f"{rut[0]}-{rut[1]}"
        except ValidationError as e:
            errores.append(e.messages[0])
    if d.get("tipo") and not TipoOrganizacion.objects.filter(nombre__iexact=d["tipo"]).exists():
        errores.append(f"Tipo de organización desconocido: «{d['tipo']}».")
    if d.get("comuna") and not _comuna(d["comuna"]):
        errores.append(f"Comuna desconocida: «{d['comuna']}».")
    if d.get("telefono"):
        d["telefono"] = normalizar_telefono(d["telefono"])
        if not telefono_normalizado_valido(d["telefono"]):
            errores.append("Teléfono no interpretable.")
    if d.get("correo") and not CORREO.match(d["correo"].lower()):
        errores.append("Correo no válido.")
    clave = ("rut", d.get("rut")) if d.get("rut") else ("nombre", (d.get("nombre") or "").lower())
    if clave[1]:
        if clave in vistos:
            errores.append(f"Repetida en el archivo (fila {vistos[clave]}).")
        else:
            vistos[clave] = vistos.get("_fila", 0)
    if errores:
        return d, "error", errores, [], None
    if rut:
        o = Organizacion.objects.filter(rut_numero=rut[0]).first()
        if o:
            return d, "existente", [], [{"pk": o.pk, "nombre": o.nombre, "razones": ["mismo RUT"]}], o.pk
    for o in Organizacion.objects.annotate(sim=TrigramSimilarity("nombre", d["nombre"])).filter(sim__gte=UMBRAL).order_by("-sim")[:5]:
        cands.append({"pk": o.pk, "nombre": o.nombre, "razones": [f"nombre parecido ({int(o.sim * 100)}%)"]})
    exacto = next((c for c in cands if c["nombre"].lower() == d["nombre"].lower()), None)
    if exacto:
        return d, "existente", [], cands, exacto["pk"]
    return d, ("duplicado" if cands else "nuevo"), [], cands, None


def _analizar_lugar(d, vistos):
    errores, cands = [], []
    d = dict(d)
    if not d.get("nombre") and d.get("nombres"):
        d["nombre"] = d.pop("nombres")
    if not d.get("nombre"):
        errores.append("Falta el nombre.")
    if not d.get("comuna"):
        errores.append("Falta la comuna (la dirección es obligatoria).")
    elif not _comuna(d["comuna"]):
        errores.append(f"Comuna desconocida: «{d['comuna']}».")
    if d.get("tipo") and not TipoLugar.objects.filter(nombre__iexact=d["tipo"]).exists():
        errores.append(f"Tipo de lugar desconocido: «{d['tipo']}».")
    if d.get("capacidad"):
        if not d["capacidad"].isdigit() or int(d["capacidad"]) < 1:
            errores.append("La capacidad debe ser un número entero positivo.")
    clave = ("lugar", (d.get("nombre") or "").lower(), (d.get("comuna") or "").lower())
    if d.get("nombre") and clave in vistos:
        errores.append(f"Repetido en el archivo (fila {vistos[clave]}).")
    elif d.get("nombre"):
        vistos[clave] = vistos.get("_fila", 0)
    if errores:
        return d, "error", errores, [], None
    from apps.lugares.models import Lugar

    qs = Lugar.objects.annotate(sim=TrigramSimilarity("nombre", d["nombre"])).filter(sim__gte=UMBRAL).order_by("-sim")[:5]
    for l in qs:
        cands.append({"pk": l.pk, "nombre": f"{l.nombre} ({l.direccion.comuna})", "razones": [f"nombre parecido ({int(l.sim * 100)}%)"]})
    exacto = Lugar.objects.filter(nombre__iexact=d["nombre"], direccion__comuna__nombre__iexact=d["comuna"]).first()
    if exacto:
        return d, "existente", [], cands, exacto.pk
    return d, ("duplicado" if cands else "nuevo"), [], cands, None


ANALIZADORES = {"listado_actividad": _analizar_persona, "personas": _analizar_persona, "organizaciones": _analizar_org, "lugares": _analizar_lugar}


def analizar(tipo, filas_crudas, decisiones=None):
    """Lista de filas con estado, errores y coincidencias. `decisiones[i]` conserva lo elegido por el usuario."""
    decisiones = decisiones or {}
    vistos, salida = {}, []
    resumen = {"nuevo": 0, "existente": 0, "duplicado": 0, "error": 0}
    for i, crudo in enumerate(filas_crudas, start=2):  # 2 = primera fila de datos (la 1 son encabezados)
        vistos["_fila"] = i
        datos, estado, errores, cands, existente = ANALIZADORES[tipo](crudo, vistos)
        # Duplicados y errores quedan «pendiente»: el usuario debe decidir o corregir antes de confirmar.
        decision = {"nuevo": "crear", "existente": f"usar:{existente}", "duplicado": "pendiente", "error": "pendiente"}[estado]
        previa = decisiones.get(i)
        if previa:
            if previa == "omitir":
                decision = "omitir"
            elif estado in ("nuevo", "duplicado") and previa == "crear":
                decision = "crear"
            elif estado in ("existente", "duplicado") and previa.startswith("usar:") and any(str(c["pk"]) == previa[5:] for c in cands):
                decision = previa
        for c in cands:
            c["valor"] = f"usar:{c['pk']}"
        salida.append({"fila": i, "datos": datos, "estado": estado, "errores": errores, "coincidencias": cands, "decision": decision})
        resumen[estado] += 1
    return salida, resumen


# --- Aplicación ---------------------------------------------------------------
def _contactos_persona(lote, fila, persona, d):
    if d.get("correo"):
        c = Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="correo"), valor=d["correo"], principal=True)
        LoteItem.objects.create(lote=lote, tipo_objeto="contacto", objeto_id=c.pk, fila=fila)
    if d.get("telefono"):
        c = Contacto.objects.create(persona=persona, tipo=TipoContacto.objects.get(codigo="telefono_movil"), valor=d["telefono"], principal=not d.get("correo"))
        LoteItem.objects.create(lote=lote, tipo_objeto="contacto", objeto_id=c.pk, fila=fila)


def _persona(lote, f, usuario):
    d = f["datos"]
    if f["decision"].startswith("usar:"):
        return Persona.objects.get(pk=int(f["decision"][5:])), False
    rut = separar_rut(d["rut"]) if d.get("rut") else (None, None)
    completa = d.get("apellido_paterno") and (d.get("correo") or d.get("telefono"))
    p = Persona.objects.create(
        nombres=d["nombres"], apellido_paterno=d.get("apellido_paterno", ""), apellido_materno=d.get("apellido_materno", ""), rut_numero=rut[0], rut_dv=rut[1],
        profesion=d.get("profesion", ""), creado_por=usuario, estado_registro=EstadoRegistro.objects.filter(codigo="activo" if completa else "incompleto").first(),
    )
    LoteItem.objects.create(lote=lote, tipo_objeto="persona", objeto_id=p.pk, fila=f["fila"])
    _contactos_persona(lote, f["fila"], p, d)
    if d.get("institucion"):
        org = Organizacion.objects.filter(nombre__iexact=d["institucion"], tipo__codigo="institucion_educativa").first()
        if org:
            carrera = Carrera.objects.filter(organizacion=org, nombre__iexact=d.get("carrera", "")).first() if d.get("carrera") else None
            fm = PersonaFormacion.objects.create(persona=p, organizacion=org, carrera=carrera)
            LoteItem.objects.create(lote=lote, tipo_objeto="formacion", objeto_id=fm.pk, fila=f["fila"])
    return p, True


def _organizacion(lote, f, usuario):
    d = f["datos"]
    if f["decision"].startswith("usar:"):
        return Organizacion.objects.get(pk=int(f["decision"][5:])), False
    rut = separar_rut(d["rut"]) if d.get("rut") else (None, None)
    tipo = TipoOrganizacion.objects.filter(nombre__iexact=d.get("tipo", "")).first() or TipoOrganizacion.objects.get(codigo="otra")
    direccion = None
    if d.get("comuna"):
        direccion = Direccion.objects.create(comuna=_comuna(d["comuna"]))
        LoteItem.objects.create(lote=lote, tipo_objeto="direccion", objeto_id=direccion.pk, fila=f["fila"])
    o = Organizacion.objects.create(nombre=d["nombre"], tipo=tipo, rut_numero=rut[0], rut_dv=rut[1], direccion=direccion, creado_por=usuario, estado_registro=EstadoRegistro.objects.filter(codigo="incompleto").first())
    LoteItem.objects.create(lote=lote, tipo_objeto="organizacion", objeto_id=o.pk, fila=f["fila"])
    for valor, codigo in ((d.get("correo"), "correo"), (d.get("telefono"), "telefono_movil")):
        if valor:
            c = Contacto.objects.create(organizacion=o, tipo=TipoContacto.objects.get(codigo=codigo), valor=valor, principal=codigo == "correo")
            LoteItem.objects.create(lote=lote, tipo_objeto="contacto", objeto_id=c.pk, fila=f["fila"])
    return o, True


def _lugar(lote, f, usuario):
    from apps.lugares.models import Lugar

    d = f["datos"]
    if f["decision"].startswith("usar:"):
        return Lugar.objects.get(pk=int(f["decision"][5:])), False
    direccion = Direccion.objects.create(calle=d.get("calle", ""), numero=d.get("numero", ""), comuna=_comuna(d["comuna"]))
    LoteItem.objects.create(lote=lote, tipo_objeto="direccion", objeto_id=direccion.pk, fila=f["fila"])
    tipo = TipoLugar.objects.filter(nombre__iexact=d.get("tipo", "")).first() or TipoLugar.objects.get(codigo="otro")
    l = Lugar.objects.create(nombre=d["nombre"], tipo=tipo, direccion=direccion, capacidad=int(d["capacidad"]) if d.get("capacidad") else None, creado_por=usuario)
    LoteItem.objects.create(lote=lote, tipo_objeto="lugar", objeto_id=l.pk, fila=f["fila"])
    return l, True


@transaction.atomic
def aplicar(lote, usuario):
    """Confirma el lote. Exige que no queden errores sin omitir ni duplicados sin decidir."""
    if lote.estado != "previa":
        raise ValueError("El lote ya fue procesado.")
    if any(f["decision"] == "pendiente" for f in lote.filas):
        raise ValueError("Hay filas con errores o posibles duplicados sin resolver: corrígelas, elige qué hacer u omítelas.")
    n = {"creados": 0, "vinculados": 0, "omitidos": 0, "participaciones": 0}
    estado_part = EstadoParticipacion.objects.get(codigo="interesado")
    documento = _documento_original(lote, usuario)
    for f in lote.filas:
        if f["decision"] == "omitir":
            n["omitidos"] += 1
            continue
        if lote.tipo in ("listado_actividad", "personas"):
            obj, creado = _persona(lote, f, usuario)
        elif lote.tipo == "organizaciones":
            obj, creado = _organizacion(lote, f, usuario)
        else:
            obj, creado = _lugar(lote, f, usuario)
        n["creados" if creado else "vinculados"] += 1
        if creado:
            registrar_origen(obj, usuario, fuente="importacion", documento=documento, detalle=lote.fuente or lote.nombre_archivo, lote=lote.pk, verificacion="por_revisar")
        if lote.tipo == "listado_actividad":
            part, nueva = Participacion.objects.get_or_create(actividad=lote.actividad, persona=obj, rol=lote.rol, defaults={"estado": estado_part, "creado_por": usuario})
            if nueva:
                LoteItem.objects.create(lote=lote, tipo_objeto="participacion", objeto_id=part.pk, fila=f["fila"])
                n["participaciones"] += 1
    lote.estado = "confirmado"
    lote.confirmado_en = timezone.now()
    lote.resumen = {**lote.resumen, "aplicado": n}
    lote.filas = []  # minimización (RNF-02): el detalle de las filas ya está en los registros creados
    lote.save()
    registrar(usuario, "importacion_confirmada", lote, str(n))
    return n


def _documento_original(lote, usuario):
    """La planilla original queda como evidencia (restringida) cuando el lote pertenece a una actividad."""
    if not lote.archivo or not lote.actividad_id:
        return None
    from apps.documentos.models import Documento
    from apps.nucleo.models import TipoDocumento

    doc = Documento(nombre=f"Listado original: {lote.nombre_archivo}", tipo=TipoDocumento.objects.get(codigo="listado"), actividad=lote.actividad, restringido=True, subido_por=usuario, descripcion=lote.fuente)
    doc.archivo.name = lote.archivo.name
    doc.save()
    return doc


@transaction.atomic
def revertir(lote, usuario):
    """Deshace el lote. Lo que ya tiene otra historia asociada (p. ej. la persona participó en otra actividad) se conserva."""
    from apps.documentos.models import OrigenDato
    from apps.lugares.models import Lugar

    if lote.estado != "confirmado":
        raise ValueError("Solo se puede revertir un lote confirmado.")
    modelos = {"participacion": Participacion, "contacto": Contacto, "formacion": PersonaFormacion, "persona": Persona, "organizacion": Organizacion, "lugar": Lugar, "direccion": Direccion}
    n = {"eliminados": 0, "conservados": 0}
    OrigenDato.objects.filter(lote=lote.pk).delete()
    for item in reversed(list(lote.items.filter(creado=True))):
        modelo = modelos[item.tipo_objeto]
        obj = modelo.objects.filter(pk=item.objeto_id).first()
        if not obj:
            continue
        try:
            with transaction.atomic():
                obj.delete()
            n["eliminados"] += 1
        except ProtectedError:
            n["conservados"] += 1
    lote.estado = "revertido"
    lote.revertido_en = timezone.now()
    lote.revertido_por = usuario
    lote.resumen = {**lote.resumen, "reversion": n}
    lote.save()
    registrar(usuario, "importacion_revertida", lote, str(n))
    return n

"""Lectura y análisis de planillas: separa nombres, normaliza RUT y teléfonos, y clasifica cada fila en
nueva, existente, posible duplicado o con error. Nada se guarda hasta que Claudio confirma,
y una carga confirmada se puede revertir."""
import re

from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.actividades.models import Participacion
from apps.documentos.origen import registrar_origen
from apps.nucleo.auditoria import registrar
from apps.nucleo.models import EstadoParticipacion, EstadoRegistro, PerfilPersona, TipoContacto, TipoLugar, TipoOrganizacion
from apps.nucleo.utilidades import normalizar_telefono, separar_nombre, separar_rut, telefono_normalizado_valido
from apps.organizaciones.models import Carrera, Organizacion
from apps.personas.duplicados import candidatos
from apps.personas.models import Contacto, Persona, PersonaDireccion, PersonaFormacion
from apps.territorio.models import Comuna, Direccion

from .models import Lote, LoteItem

CAMPOS = {
    "listado_actividad": ["nombres", "apellido_paterno", "apellido_materno", "rut", "correo", "telefono", "fecha_nacimiento", "comuna"],
    "personas": ["nombres", "apellido_paterno", "apellido_materno", "rut", "correo", "telefono", "fecha_nacimiento", "comuna"],
    "organizaciones": ["nombre", "tipo", "rut", "correo", "telefono", "comuna"],
    "lugares": ["nombre", "tipo", "calle", "numero", "comuna", "capacidad"],
}
CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
UMBRAL = 0.5


def fecha_planilla(texto):
    """Fecha escrita como en Chile (dd-mm-aaaa, dd/mm/aa) o como la exporta Excel (aaaa-mm-dd [hh:mm:ss]). None si no se entiende."""
    from datetime import date

    t = (texto or "").strip().split(" ")[0].replace("/", "-").replace(".", "-")
    partes = t.split("-")
    if len(partes) != 3 or not all(x.isdigit() for x in partes):
        return None
    try:
        if len(partes[0]) == 4:
            return date(int(partes[0]), int(partes[1]), int(partes[2]))
        anio = int(partes[2])
        if len(partes[2]) == 2:
            anio += 2000 if anio <= timezone.localdate().year % 100 else 1900
        return date(anio, int(partes[1]), int(partes[0]))
    except ValueError:
        return None


JORNADAS = {"diurna": "diurna", "diurno": "diurna", "vespertina": "vespertina", "vespertino": "vespertina", "online": "en_linea", "en linea": "en_linea", "en línea": "en_linea", "virtual": "en_linea"}


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
    if d.get("tipo") and not d.get("perfil"):  # en una planilla de personas, «tipo» es el perfil (F24)
        d["perfil"] = d.pop("tipo")
    d.pop("tipo", None)
    if d.get("telefono"):
        d["telefono"] = normalizar_telefono(d["telefono"])
    if d.get("correo"):
        d["correo"] = d["correo"].strip().lower()
    return d


DOS_PERSONAS = re.compile(r"\s(y|e)\s|/|&|\+", re.IGNORECASE)


def _analizar_persona(d, vistos):
    errores, cands, estado, existente = [], [], "nuevo", None
    original = d.get("nombre_completo") or d.get("nombres") or ""
    d = _normalizar_persona(d)
    if DOS_PERSONAS.search(f" {original} "):
        errores.append("Parece traer dos personas en la misma fila: sepáralas en dos filas.")
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
    if d.get("fecha_nacimiento"):
        fecha = fecha_planilla(d["fecha_nacimiento"])
        if not fecha or fecha > timezone.localdate():
            errores.append("Fecha de nacimiento no reconocida (usa dd-mm-aaaa).")
        else:
            d["fecha_nacimiento"] = fecha.strftime("%d-%m-%Y")
    if d.get("nivel_actual") and not str(d["nivel_actual"]).strip().rstrip("°º.").isdigit():
        d["nivel_actual"] = "".join(c for c in str(d["nivel_actual"]) if c.isdigit())[:2]
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
        cands.append({"pk": p.pk, "nombre": p.nombre_completo, "razones": razones, "activo": p.activo})
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


def _sin_tildes(t):
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", (t or "").strip().lower()) if unicodedata.category(c) != "Mn")


def _institucion(nombre):
    from django.db.models.functions import Lower

    if not nombre:
        return None
    clave = _sin_tildes(nombre)
    for o in Organizacion.objects.filter(tipo__codigo="institucion_educativa"):
        if _sin_tildes(o.nombre) == clave:
            return o
    return None


def _carrera(org, nombre):
    clave = _sin_tildes(nombre)
    return next((c for c in org.carreras.all() if _sin_tildes(c.nombre) == clave), None)


def _perfiles_activos():
    """{texto sin tildes: perfil} con el nombre y el código de cada perfil activo. Se arma una vez por carga."""
    claves = {}
    for p in PerfilPersona.objects.filter(activo=True):
        claves.setdefault(_sin_tildes(p.nombre), p)
        claves.setdefault(_sin_tildes(p.codigo), p)
        claves.setdefault(_sin_tildes(p.codigo.replace("_", " ")), p)
    return claves


def _perfil(texto, perfiles):
    return perfiles.get(_sin_tildes(texto)) if texto else None


def _avisos_formacion(d, crear_carreras):
    """IG-E9: institución o carrera que no existen (no bloquea)."""
    avisos = []
    if d.get("institucion"):
        org = _institucion(d["institucion"])
        if not org:
            avisos.append(f"La institución «{d['institucion']}» no está registrada: no se guardará su formación.")
        elif d.get("carrera") and not _carrera(org, d["carrera"]):
            avisos.append(f"La carrera «{d['carrera']}» no existe en {org}: " + ("se creará." if crear_carreras else "se registrará sin carrera (o marca «crear carreras»)."))
    return avisos


def _diferencias(persona, d):
    """IG-E8: qué trae la planilla distinto de lo que ya hay."""
    dif = []
    for campo, etiqueta in (("apellido_paterno", "Apellido paterno"), ("apellido_materno", "Apellido materno"), ("profesion", "Profesión")):
        nuevo, actual = d.get(campo, ""), getattr(persona, campo)
        if nuevo and _sin_tildes(nuevo) != _sin_tildes(actual):
            dif.append(f"{etiqueta}: actual «{actual or '—'}» · planilla «{nuevo}»")
    actuales = set(persona.contactos.values_list("valor_normalizado", flat=True))
    for campo in ("correo", "telefono"):
        if d.get(campo) and d[campo] not in actuales:
            dif.append(f"Contacto nuevo: {d[campo]}")
    return dif


def _opciones(fila):
    """[(valor, etiqueta)] para «Qué hacer» en la revisión."""
    estado, ops = fila["estado"], []
    if fila["decision"] == "pendiente":
        ops.append(("pendiente", "— Corrige los datos o elige omitir —" if estado == "error" else "— Decide qué hacer —"))
    if estado == "error":
        return ops + [("omitir", "Omitir esta fila")]
    if estado != "existente":
        ops.append(("crear", "Crear nuevo"))
    for c in fila["coincidencias"]:
        ops.append((f"usar:{c['pk']}", f"Usar existente: {c['nombre']} ({', '.join(c['razones'])})" + ("" if c.get("activo", True) else " — DESACTIVADA")))
        if estado == "existente" and c["pk"] == fila.get("existente"):
            if fila.get("diferencias"):
                ops.append((f"contacto:{c['pk']}", "Conservar la ficha y agregar solo los contactos nuevos"))
                ops.append((f"actualizar:{c['pk']}", "Actualizar la ficha con los datos de la planilla"))
            if not c.get("activo", True):
                ops.append((f"reactivar:{c['pk']}", "Usar y reactivar la ficha"))
    return ops + [("omitir", "Omitir")]


def analizar(tipo, filas_crudas, decisiones=None, crear_carreras=False):
    """Lista de filas con estado, errores y coincidencias. `decisiones[i]` conserva lo elegido por el usuario."""
    decisiones = decisiones or {}
    vistos, salida = {}, []
    resumen = {"nuevo": 0, "existente": 0, "duplicado": 0, "error": 0}
    perfiles = _perfiles_activos() if tipo in ("personas", "listado_actividad") else {}
    for i, crudo in enumerate(filas_crudas, start=2):  # 2 = primera fila de datos (la 1 son encabezados)
        vistos["_fila"] = i
        datos, estado, errores, cands, existente = ANALIZADORES[tipo](crudo, vistos)
        # Duplicados y errores quedan «pendiente»: el usuario debe decidir o corregir antes de confirmar.
        fila = {"fila": i, "datos": datos, "estado": estado, "errores": errores, "coincidencias": cands, "existente": existente, "avisos": [], "diferencias": []}
        if tipo in ("personas", "listado_actividad") and estado != "error":
            fila["avisos"] = _avisos_formacion(datos, crear_carreras)
            if datos.get("comuna") and not _comuna(datos["comuna"]):
                fila["avisos"].append(f"La comuna «{datos['comuna']}» no está registrada: no se guardará su dirección.")
            if datos.get("perfil") and not _perfil(datos["perfil"], perfiles):
                fila["avisos"].append(f"El perfil «{datos['perfil']}» no existe en Catálogos: la persona se guardará sin ese perfil.")
            if existente:
                fila["diferencias"] = _diferencias(Persona.objects.get(pk=existente), datos)
                if not Persona.objects.filter(pk=existente, activo=True).exists():
                    fila["avisos"].append("La persona existe pero está desactivada: puedes reactivarla.")  # IG-E14
        decision = {"nuevo": "crear", "existente": f"usar:{existente}", "duplicado": "pendiente", "error": "pendiente"}[estado]
        fila["decision"] = decision
        validas = {v for v, _ in _opciones(fila)}
        previa = decisiones.get(i)
        if previa and previa in validas and previa != "pendiente":
            fila["decision"] = previa
        fila["opciones"] = _opciones(fila)
        salida.append(fila)
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


def _formacion(lote, f, persona, d):
    org = _institucion(d.get("institucion"))
    if not org:
        return
    carrera = _carrera(org, d["carrera"]) if d.get("carrera") else None
    if d.get("carrera") and not carrera and lote.crear_carreras:
        carrera = Carrera.objects.create(organizacion=org, nombre=d["carrera"].strip())
        LoteItem.objects.create(lote=lote, tipo_objeto="carrera", objeto_id=carrera.pk, fila=f["fila"])
    if PersonaFormacion.objects.filter(persona=persona, organizacion=org, carrera=carrera).exists():
        return
    nivel = "".join(c for c in str(d.get("nivel_actual") or "") if c.isdigit())[:2]
    fm = PersonaFormacion.objects.create(
        persona=persona, organizacion=org, carrera=carrera, sede=(d.get("sede") or "").strip()[:120],
        jornada=JORNADAS.get((d.get("jornada") or "").strip().lower(), ""), nivel_actual=int(nivel) if nivel else None,
        asignatura=(d.get("asignatura") or "").strip()[:200],
    )
    LoteItem.objects.create(lote=lote, tipo_objeto="formacion", objeto_id=fm.pk, fila=f["fila"])


def _existente(lote, f, usuario):
    """usar / contacto / actualizar / reactivar sobre una persona que ya existe (IG-E8, IG-E14)."""
    accion, pk = f["decision"].split(":", 1)
    p = Persona.objects.get(pk=int(pk))
    d = f["datos"]
    if accion in ("contacto", "actualizar"):
        actuales = set(p.contactos.values_list("valor_normalizado", flat=True))
        for valor, codigo in ((d.get("correo"), "correo"), (d.get("telefono"), "telefono_movil")):
            if valor and valor not in actuales:
                c = Contacto.objects.create(persona=p, tipo=TipoContacto.objects.get(codigo=codigo), valor=valor)
                LoteItem.objects.create(lote=lote, tipo_objeto="contacto", objeto_id=c.pk, fila=f["fila"])
    if accion == "actualizar":
        antes = {}
        for campo in ("apellido_paterno", "apellido_materno", "profesion"):
            if d.get(campo) and d[campo] != getattr(p, campo):
                antes[campo] = getattr(p, campo)
                setattr(p, campo, d[campo])
        if d.get("rut") and not p.rut_numero:
            antes["rut_numero"], antes["rut_dv"] = None, None
            p.rut_numero, p.rut_dv = separar_rut(d["rut"])
        if antes:
            p.save()
            LoteItem.objects.create(lote=lote, tipo_objeto="actualizacion", objeto_id=p.pk, creado=False, fila=f["fila"], antes=antes)
        _formacion(lote, f, p, d)
    if accion == "reactivar" and not p.activo:
        p.activo = True
        p.save()
        LoteItem.objects.create(lote=lote, tipo_objeto="actualizacion", objeto_id=p.pk, creado=False, fila=f["fila"], antes={"activo": False})
    return p


def _persona(lote, f, usuario):
    d = f["datos"]
    if ":" in f["decision"]:
        return _existente(lote, f, usuario), False
    rut = separar_rut(d["rut"]) if d.get("rut") else (None, None)
    completa = d.get("apellido_paterno") and (d.get("correo") or d.get("telefono"))
    niveles = {n.lower(): c for c, n in Persona.NIVELES_EDUCACIONALES}
    p = Persona.objects.create(
        nombres=d["nombres"], apellido_paterno=d.get("apellido_paterno", ""), apellido_materno=d.get("apellido_materno", ""), rut_numero=rut[0], rut_dv=rut[1],
        profesion=d.get("profesion", ""), creado_por=usuario, estado_registro=EstadoRegistro.objects.filter(codigo="activo" if completa else "incompleto").first(),
        fecha_nacimiento=fecha_planilla(d.get("fecha_nacimiento")), nacionalidad=(d.get("nacionalidad") or "").strip()[:60],
        nivel_educacional=niveles.get((d.get("nivel_educacional") or "").strip().lower(), ""),
    )
    LoteItem.objects.create(lote=lote, tipo_objeto="persona", objeto_id=p.pk, fila=f["fila"])
    _contactos_persona(lote, f["fila"], p, d)
    _formacion(lote, f, p, d)
    _residencia(lote, f, p, d)
    return p, True


def _residencia(lote, f, persona, d):
    """Comuna y calle de la planilla: dirección de residencia (F22)."""
    comuna = _comuna(d.get("comuna"))
    if not comuna:
        return
    direccion = Direccion.objects.create(calle=(d.get("calle") or "").strip()[:160], numero=(d.get("numero") or "").strip()[:20], comuna=comuna)
    LoteItem.objects.create(lote=lote, tipo_objeto="direccion", objeto_id=direccion.pk, fila=f["fila"])
    pd = PersonaDireccion.objects.create(persona=persona, direccion=direccion, tipo="residencia")
    LoteItem.objects.create(lote=lote, tipo_objeto="persona_direccion", objeto_id=pd.pk, fila=f["fila"])


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
    perfiles = _perfiles_activos() if lote.tipo in ("listado_actividad", "personas") else {}
    for f in lote.filas:
        if f["decision"] == "omitir":
            n["omitidos"] += 1
            continue
        if lote.tipo in ("listado_actividad", "personas"):
            obj, creado = _persona(lote, f, usuario)
            perfil = _perfil(f["datos"].get("perfil"), perfiles)
            if perfil:  # se suma a los que ya tenga; la reversión no lo quita
                obj.perfiles.add(perfil)
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
    lote.filas, lote.crudas = [], []  # minimización (RNF-02): el detalle de las filas ya está en los registros creados
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
    modelos = {"participacion": Participacion, "contacto": Contacto, "formacion": PersonaFormacion, "persona_direccion": PersonaDireccion, "persona": Persona,
               "organizacion": Organizacion, "lugar": Lugar, "direccion": Direccion, "carrera": Carrera}
    n = {"eliminados": 0, "conservados": 0, "editados": 0, "restaurados": 0}

    def editado_despues(obj):
        """IG-E11: alguien lo modificó después de la carga: no se toca."""
        h = getattr(obj, "history", None)
        return bool(h is not None and lote.confirmado_en and h.filter(history_date__gt=lote.confirmado_en).exists())

    for item in reversed(list(lote.items.filter(creado=False, tipo_objeto="actualizacion"))):
        p = Persona.objects.filter(pk=item.objeto_id).first()
        if not p:
            continue
        if editado_despues(p):
            n["editados"] += 1
            continue
        for campo, valor in (item.antes or {}).items():
            setattr(p, campo, valor)
        p.save()
        n["restaurados"] += 1
    OrigenDato.objects.filter(lote=lote.pk).delete()
    for item in reversed(list(lote.items.filter(creado=True))):
        modelo = modelos[item.tipo_objeto]
        obj = modelo.objects.filter(pk=item.objeto_id).first()
        if not obj:
            continue
        if editado_despues(obj):
            n["editados"] += 1
            n["conservados"] += 1
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

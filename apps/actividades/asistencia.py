"""F28 · Asistencia por jornada (specs/f28/spec.md, puntos 1 a 4).

Tres conceptos separados:
- **Inscripción** (`Participacion`): la persona está en la tarea con un rol. Pasar lista nunca la cambia.
- **Jornada** (`SesionActividad`): cada día o bloque en que se realiza la tarea. La fecha programada vigente tiene su
  jornada aunque aún no se guarde: aparece sola como «jornada programada» y queda guardada al usarla (pasar lista,
  suspenderla o registrar su conteo) [P]. «+ Nueva jornada» agrega otras.
- **Asistencia del día** (`SesionAsistencia`): una marca por persona y jornada (Presente, Atrasado, Se retiró antes,
  Justificado o Ausente), con observación, quién y cuándo, y su historial.

Quién aparece en la lista de una jornada: las inscripciones activas en su fecha (`Participacion.en_lista_de`). Nadie
desaparece por faltar, y quien ya tiene marca en esa jornada sigue apareciendo en ella. Si una persona tiene dos roles
en la tarea, aparece una vez y tiene una sola marca: la de su participación principal (la vigente, con el rol de menor
orden; se elige siempre igual) [P].

Las lecturas (matriz, lista, resumen) hacen un número fijo de consultas. Las escrituras bloquean la actividad para que
dos envíos a la vez no se pisen, y la lista lleva una versión: si otra pestaña la cambió, se avisa y no se guarda.
"""
from dataclasses import dataclass, field
from datetime import date, time

from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone

from apps.nucleo.auditoria import registrar
from apps.nucleo.utilidades import plural

from .models import Actividad, CambioLista, Participacion, SesionActividad, SesionAsistencia
from .reglas import ReglaNegocio

M = SesionAsistencia
MARCAS = M.MARCAS
NOMBRE_MARCA = dict(MARCAS)
CORTA = {M.PRESENTE: "P", M.ATRASADO: "T", M.RETIRO_ANTICIPADO: "R", M.JUSTIFICADO: "J", M.AUSENTE: "A"}
CUENTAN = M.CUENTAN
GRUPOS = [("ejecutor", "Equipo ejecutor"), ("contacto", "Invitados y contactos"), ("asistente", "Beneficiarios")]
ORDEN_GRUPO = {clave: i for i, (clave, _) in enumerate(GRUPOS)}
MENSAJE_VERSION = ("La lista cambió mientras la tenías abierta (en otra pestaña o por otra persona). "
                   "Revisa las marcas que se ven ahora y vuelve a guardar.")
ESTADOS_SIN_LISTA = ("cancelada", "pendiente", "suspendida")


# --- Lecturas ----------------------------------------------------------------------------------------------------
def participaciones(actividad):
    """Todas las participaciones menos los registros erróneos, con persona, rol y estado. Una consulta."""
    return list(Participacion.objects.filter(actividad=actividad).exclude(estado__codigo="registro_erroneo")
                .select_related("persona", "rol", "estado"))


def _clave_principal(p):
    return (0 if (p.activa or p.retirada) else 1, p.rol.orden, p.rol_id, p.pk)


def por_persona(partes):
    """{persona_id: [participaciones]}, la principal primero (determinista)."""
    res = {}
    for p in partes:
        res.setdefault(p.persona_id, []).append(p)
    for lista in res.values():
        lista.sort(key=_clave_principal)
    return res


def jornada_programada(actividad, agenda, todas):
    """La jornada de la fecha programada vigente, aún sin guardar (pk vacío)."""
    numero = max((j.numero for j in todas), default=0) + 1
    return SesionActividad(actividad=actividad, numero=numero, fecha=agenda.fecha, hora_inicio=agenda.hora_inicio,
                           hora_fin=agenda.hora_fin, lugar=agenda.lugar if agenda.lugar_id else None, lugar_id=agenda.lugar_id)


def _orden_jornada(j):
    return (j.fecha or date.max, j.hora_inicio or time.min, j.numero)


def armar_jornadas(actividad, todas, agenda):
    """Sin consultas: las jornadas vigentes de `todas` (sus sesiones) en orden y la programada, si falta."""
    res = [j for j in todas if j.vigente]
    if agenda and agenda.fecha and not any(j.fecha == agenda.fecha for j in res):
        res.append(jornada_programada(actividad, agenda, todas))
    return sorted(res, key=_orden_jornada)


def jornadas(actividad, con_programada=True):
    """Jornadas vigentes en orden (fecha, hora, número) y, si la fecha programada vigente no tiene la suya, la
    «jornada programada» sin guardar. Una consulta (y la de la agenda, si la ficha no la fijó antes)."""
    todas = list(SesionActividad.objects.filter(actividad=actividad).select_related("lugar", "cerrada_por"))
    return armar_jornadas(actividad, todas, actividad.agenda_vigente if con_programada else None)


def _marcas_qs(**filtro):
    return (SesionAsistencia.objects.filter(**filtro).exclude(marca="").select_related("marcado_por")
            .annotate(persona_ref=F("participacion__persona_id")).order_by("marcado_en", "pk"))


def marcas(actividad):
    """{(jornada_id, persona_id): SesionAsistencia} de las marcas puestas. Si una persona tiene marcas con dos de sus
    participaciones en la misma jornada (registros antiguos), vale la más reciente. Una consulta."""
    return {(m.sesion_id, m.persona_ref): m for m in _marcas_qs(sesion__actividad=actividad)}


@dataclass
class Fila:
    """Una persona en la lista de una jornada."""

    persona: object
    participacion: Participacion  # la principal: aquí se guarda su marca
    otras: list = field(default_factory=list)
    marca: SesionAsistencia = None
    inscrita: bool = True  # False: no está inscrita ese día, pero tiene marca y no desaparece

    @property
    def grupo(self):
        return self.participacion.rol.grupo

    @property
    def roles(self):
        return " · ".join([self.participacion.rol_y_cargo] + [p.rol_y_cargo for p in self.otras])

    @property
    def codigo(self):
        return self.marca.marca if self.marca else ""

    @property
    def nombre_marca(self):
        return NOMBRE_MARCA.get(self.codigo, "Sin marcar")


def _orden_persona(persona):
    return ((persona.apellido_paterno or "").lower(), (persona.nombres or "").lower(), persona.pk)


def filas(jornada, grupos_persona, marcas_jornada):
    """Lista de la jornada: una fila por persona, por grupo y apellido. Sin consultas."""
    res = []
    for persona_id, partes in grupos_persona.items():
        visibles = [p for p in partes if p.en_lista_de(jornada.fecha)]
        marca = marcas_jornada.get((jornada.pk, persona_id)) if jornada.pk else None
        if not visibles and marca is None:
            continue
        principal = visibles[0] if visibles else next((p for p in partes if p.pk == marca.participacion_id), partes[0])
        otras = [p for p in (visibles or partes) if p.pk != principal.pk]
        res.append(Fila(principal.persona, principal, otras, marca, bool(visibles)))
    res.sort(key=lambda f: (ORDEN_GRUPO.get(f.grupo, 9), _orden_persona(f.persona)))
    return res


def resumen_persona(celdas):
    """Días presentes, porcentaje y última marca. «Justificado» y las jornadas suspendidas no cuentan para el porcentaje [P]."""
    presentes = sum(1 for j, m in celdas if m and not j.suspendida and m.marca in CUENTAN)
    ausentes = sum(1 for j, m in celdas if m and not j.suspendida and m.marca == M.AUSENTE)
    justificados = sum(1 for j, m in celdas if m and not j.suspendida and m.marca == M.JUSTIFICADO)
    total = presentes + ausentes
    ultima = next((m for j, m in reversed(celdas) if m), None)
    return {"presentes": presentes, "ausentes": ausentes, "justificados": justificados, "con_marca": total,
            "porcentaje": round(100 * presentes / total) if total else None, "ultima": ultima}


def matriz(actividad, grupo=None, partes=None, js=None):
    """Personas por jornadas, con la marca de cada día, el total y el porcentaje por persona, y presentes sobre
    inscritos y el estado de la lista por jornada. `grupo`: ejecutor, contacto o asistente (vacío: todos).
    Consultas fijas: participaciones, jornadas y marcas."""
    partes = participaciones(actividad) if partes is None else partes
    js = jornadas(actividad) if js is None else js
    return armar_matriz(partes, js, marcas(actividad), grupo)


def armar_matriz(partes, js, todas_marcas, grupo=None):
    """Sin consultas: la matriz con lo ya leído (ver `matriz`)."""
    grupos_persona = por_persona(partes)
    columnas = []
    for j in js:
        lista = filas(j, grupos_persona, todas_marcas)
        columnas.append({
            "jornada": j, "lista": lista, "inscritos": sum(1 for f in lista if f.inscrita),
            "presentes": sum(1 for f in lista if f.codigo in CUENTAN), "marcadas": sum(1 for f in lista if f.marca),
            "personas": {f.persona.pk for f in lista},
        })
    filas_matriz = []
    for persona_id, lista in grupos_persona.items():
        principal = lista[0]
        if grupo and principal.rol.grupo != grupo:
            continue
        celdas = []
        for c in columnas:
            j = c["jornada"]
            m = todas_marcas.get((j.pk, persona_id)) if j.pk else None
            celdas.append({"jornada": j, "marca": m, "en_lista": persona_id in c["personas"],
                           "corta": CORTA.get(m.marca, "") if m else "", "nombre": NOMBRE_MARCA.get(m.marca, "") if m else ""})
        if not (principal.activa or principal.retirada) and not any(c["en_lista"] for c in celdas):
            continue  # canceló, rechazó o en lista de espera, sin ninguna marca: no está en la tarea
        filas_matriz.append({"persona": principal.persona, "participacion": principal, "otras": lista[1:],
                             "roles": " · ".join(p.rol_y_cargo for p in lista), "celdas": celdas,
                             "resumen": resumen_persona([(c["jornada"], c["marca"]) for c in celdas])})
    filas_matriz.sort(key=lambda f: (ORDEN_GRUPO.get(f["participacion"].rol.grupo, 9), _orden_persona(f["persona"])))
    return {"columnas": columnas, "filas": filas_matriz, "grupo": grupo or ""}


def jornada_de_hoy(js, hoy=None):
    """La jornada para «Pasar lista» por defecto: la de hoy (la primera aún abierta, si hay dos) o, si no hay, la
    última que ya pasó. None si todas son futuras."""
    hoy = hoy or timezone.localdate()
    de_hoy = [j for j in js if j.fecha == hoy]
    if de_hoy:
        return next((j for j in de_hoy if j.lista_abierta), de_hoy[0])
    pasadas = [j for j in js if j.fecha and j.fecha < hoy]
    return pasadas[-1] if pasadas else None


def jornada_para_marcar(actividad, js=None):
    """La de hoy; si la actividad no tiene fecha ni jornadas, una jornada de hoy sin guardar (se guarda al marcar)."""
    js = jornadas(actividad) if js is None else js
    j = jornada_de_hoy(js)
    if j is None and not js and actividad.agenda_vigente is None:
        j = SesionActividad(actividad=actividad, numero=1, fecha=timezone.localdate())
    return j


def elegir_jornada(js, valor):
    """La jornada pedida en la dirección (?jornada=<id> o «programada»), o la de hoy."""
    if valor == "programada":
        return next((j for j in js if not j.pk), None) or jornada_de_hoy(js)
    if str(valor or "").isdigit():
        elegida = next((j for j in js if j.pk == int(valor)), None)
        if elegida:
            return elegida
    return jornada_de_hoy(js) or (js[0] if js else None)


def puede_pasar_lista(actividad, jornada, hoy=None):
    """(sí o no, por qué no). Desde el día de la jornada, y no en actividades canceladas, pendientes o suspendidas."""
    hoy = hoy or timezone.localdate()
    if actividad.estado.codigo in ESTADOS_SIN_LISTA:
        return False, f"No se pasa lista en una actividad {actividad.estado.nombre.lower()}."
    if jornada is None:
        return False, "Aún no hay jornadas: programa la fecha o agrega una jornada."
    if jornada.fecha and jornada.fecha > hoy:
        return False, f"La lista se pasa desde el día de la jornada ({jornada.fecha:%d-%m-%Y})."
    return True, ""


def tiene_lista(jornada):
    """¿Ya se usó? Con marcas, cerrada o suspendida, o con conteo sin nombres. Una consulta."""
    if not jornada.pk:
        return False
    return (not jornada.lista_abierta) or jornada.tiene_conteo or jornada.asistencias.exclude(marca="").exists()


def jornadas_pendientes(actividad, js=None, partes=None, hoy=None):
    """Para Finalizar: (pendientes, por_cerrar). Pendientes: textos de las jornadas hasta hoy sin resolver (lista
    abierta con personas sin marcar, o sin lista). Por cerrar: jornadas abiertas con todas las personas marcadas, que
    Finalizar cierra [P]. Las suspendidas, las cerradas y las que tienen conteo sin nombres están resueltas."""
    hoy = hoy or timezone.localdate()
    js = jornadas(actividad) if js is None else js
    grupos_persona = por_persona(participaciones(actividad) if partes is None else partes)
    todas_marcas = marcas(actividad)
    pendientes, por_cerrar = [], []
    for j in js:
        if not j.fecha or j.fecha > hoy or j.suspendida or j.lista_cerrada or j.tiene_conteo:
            continue
        lista = filas(j, grupos_persona, todas_marcas)
        sin_marca = [f for f in lista if not f.marca]
        nombre = f"{j.nombre_jornada} ({j.fecha:%d-%m-%Y})"
        if j.pk and lista and not sin_marca:
            por_cerrar.append(j)
        elif lista and len(sin_marca) < len(lista):
            pendientes.append(f"{nombre}: falta marcar a {plural(len(sin_marca), 'persona', 'personas')}. Márcalas o usa «Marcar el resto como ausente».")
        else:
            pendientes.append(f"{nombre}: falta pasar lista. Pásala y ciérrala, suspende la jornada o registra un conteo sin nombres.")
    return pendientes, por_cerrar


def resumen_proyecto(proyecto):
    """Pestaña «Asistencia» del proyecto: por tarea (jornadas, inscritos, presentes y porcentaje promedio) y por
    persona (tareas, días presentes y porcentaje), con lo mismo que la matriz de cada tarea. Cinco consultas, sin
    importar cuántas tareas, jornadas o personas haya."""
    from .models import AgendaActividad

    tareas = list(proyecto.actividades.select_related("estado").order_by("creado_en", "pk"))
    ids = [t.pk for t in tareas]
    partes_de, sesiones_de, marcas_de = {}, {}, {}
    for p in (Participacion.objects.filter(actividad_id__in=ids).exclude(estado__codigo="registro_erroneo")
              .select_related("persona", "rol", "estado")):
        partes_de.setdefault(p.actividad_id, []).append(p)
    for j in SesionActividad.objects.filter(actividad_id__in=ids).select_related("lugar", "cerrada_por"):
        sesiones_de.setdefault(j.actividad_id, []).append(j)
    agendas = {a.actividad_id: a for a in AgendaActividad.objects.filter(actividad_id__in=ids, vigente=True).select_related("lugar")}
    sesion_actividad = {j.pk: aid for aid, lista in sesiones_de.items() for j in lista}
    for m in _marcas_qs(sesion__actividad_id__in=ids):
        marcas_de.setdefault(sesion_actividad.get(m.sesion_id), {})[(m.sesion_id, m.persona_ref)] = m
    filas_tareas, personas = [], {}
    for t in tareas:
        js = armar_jornadas(t, sesiones_de.get(t.pk, []), agendas.get(t.pk))
        mat = armar_matriz(partes_de.get(t.pk, []), js, marcas_de.get(t.pk, {}))
        porcentajes = [f["resumen"]["porcentaje"] for f in mat["filas"] if f["resumen"]["porcentaje"] is not None]
        filas_tareas.append({
            "tarea": t, "jornadas": len(js), "con_lista": sum(1 for c in mat["columnas"] if c["marcadas"] or c["jornada"].lista_cerrada),
            "suspendidas": sum(1 for j in js if j.suspendida), "inscritos": len(mat["filas"]),
            "presentes": sum(c["presentes"] for c in mat["columnas"]),
            "promedio": round(sum(porcentajes) / len(porcentajes)) if porcentajes else None,
        })
        for f in mat["filas"]:
            r = f["resumen"]
            acum = personas.setdefault(f["persona"].pk, {"persona": f["persona"], "tareas": [], "presentes": 0, "con_marca": 0, "justificados": 0})
            acum["tareas"].append(t)
            acum["presentes"] += r["presentes"]
            acum["con_marca"] += r["con_marca"]
            acum["justificados"] += r["justificados"]
    filas_personas = sorted(personas.values(), key=lambda x: _orden_persona(x["persona"]))
    for x in filas_personas:
        x["porcentaje"] = round(100 * x["presentes"] / x["con_marca"]) if x["con_marca"] else None
    return {"tareas": filas_tareas, "personas": filas_personas}


# --- Escrituras ----------------------------------------------------------------------------------------------------
def _bloquear(actividad):
    return Actividad.objects.select_for_update().select_related("estado").get(pk=actividad.pk)


def _guardar_jornada(actividad, jornada):
    """La jornada guardada y bloqueada. Si viene sin guardar (la programada o la de hoy), se guarda; si otra petición
    ya la guardó, se usa esa. Se llama con la actividad bloqueada."""
    if jornada.pk:
        return SesionActividad.objects.select_for_update().get(pk=jornada.pk, actividad=actividad)
    ya = SesionActividad.objects.filter(actividad=actividad, vigente=True, fecha=jornada.fecha).order_by("hora_inicio", "numero").first()
    if ya:
        return SesionActividad.objects.select_for_update().get(pk=ya.pk)
    numero = (SesionActividad.objects.filter(actividad=actividad).aggregate(n=Max("numero"))["n"] or 0) + 1
    return SesionActividad.objects.create(actividad=actividad, numero=numero, fecha=jornada.fecha, hora_inicio=jornada.hora_inicio,
                                          hora_fin=jornada.hora_fin, lugar_id=jornada.lugar_id)


def _exigir_version(jornada, version):
    if version not in (None, "") and str(version) != str(jornada.version_lista):
        raise ReglaNegocio(MENSAJE_VERSION)


def _exigir_abierta(jornada):
    if jornada.lista_cerrada:
        raise ReglaNegocio(f"La lista de la {jornada.nombre_jornada.lower()} está cerrada: es de solo lectura. Reábrela con un motivo para corregirla.")
    if jornada.suspendida:
        raise ReglaNegocio(f"La {jornada.nombre_jornada.lower()} está suspendida: no tiene lista. Reábrela con un motivo si sí se realizó.")


def _exigir_dia(actividad, jornada):
    ok, motivo = puede_pasar_lista(actividad, jornada)
    if not ok:
        raise ReglaNegocio(motivo)


def _subir_version(jornada):
    jornada.version_lista = (jornada.version_lista or 0) + 1
    jornada.save()


def _poner_marca(jornada, fila, marca, observacion, usuario, existentes):
    """Guarda la marca de una persona en la jornada (sobre su participación principal, o la fila que ya tenía) y
    devuelve True si cambió. Otras marcas de la misma persona en la jornada (registros antiguos) se vacían."""
    suyas = [e for e in existentes if e.participacion_id in {fila.participacion.pk, *(p.pk for p in fila.otras)}]
    destino = next((e for e in suyas if e.participacion_id == fila.participacion.pk), suyas[0] if suyas else None)
    cambio = False
    for otra in suyas:
        if otra is not destino and otra.marca:
            otra.marca, otra.marcado_por, otra.marcado_en = "", usuario, timezone.now()
            otra.save()
            cambio = True
    observacion = (observacion or "").strip()[:250]
    if destino is None:
        if not marca and not observacion:
            return cambio
        destino = SesionAsistencia(sesion=jornada, participacion=fila.participacion)
        existentes.append(destino)
    elif destino.marca == marca and destino.observacion == observacion:
        return cambio
    destino.marca, destino.observacion = marca, observacion
    destino.marcado_por, destino.marcado_en = usuario, timezone.now()
    destino.save()
    return True


@dataclass
class Resultado:
    jornada: SesionActividad
    cambios: int = 0
    cerrada: bool = False
    sin_marcar: list = field(default_factory=list)  # nombres de quienes quedaron sin marca


def _lista_actual(actividad, jornada):
    partes = participaciones(actividad)
    grupos_persona = por_persona(partes)
    existentes = list(SesionAsistencia.objects.filter(sesion=jornada).select_related("participacion"))
    marcadas = {}
    for e in sorted(existentes, key=lambda e: (e.marcado_en or timezone.now(), e.pk or 0)):
        if e.marca:
            marcadas[(jornada.pk, e.participacion.persona_id)] = e
    return filas(jornada, grupos_persona, marcadas), existentes, grupos_persona


@transaction.atomic
def guardar_lista(actividad, jornada, usuario, valores, version=None, resto_ausente=False, cerrar=False):
    """Guarda la lista de una jornada abierta. `valores`: {persona_id: (marca, observación)}; marca vacía = sin marcar.
    Solo se marca a quien está en la lista de ese día (quien llegó sin estar inscrito se agrega con «+ Agregar persona
    que llegó»). `resto_ausente`: quien quede sin marca queda Ausente. `cerrar`: además cierra la lista, si nadie quedó
    sin marca (si quedan, guarda igual y los nombra en el resultado, sin cerrar)."""
    actividad = _bloquear(actividad)
    jornada = _guardar_jornada(actividad, jornada)
    _exigir_abierta(jornada)
    _exigir_version(jornada, version)
    _exigir_dia(actividad, jornada)
    lista, existentes, grupos_persona = _lista_actual(actividad, jornada)
    res = Resultado(jornada)
    tocadas = set()
    for fila in lista:
        if fila.persona.pk in valores:
            marca, observacion = valores[fila.persona.pk]
            marca = marca if marca in NOMBRE_MARCA else ""
            if observacion is None:  # las rutas de antes no traen observación: se conserva la que había
                observacion = fila.marca.observacion if fila.marca else ""
        else:
            marca, observacion = fila.codigo, fila.marca.observacion if fila.marca else ""
        if resto_ausente and not marca:
            marca = M.AUSENTE
        if _poner_marca(jornada, fila, marca, observacion, usuario, existentes):
            res.cambios += 1
            tocadas.add(fila.persona.pk)
        if not marca:
            res.sin_marcar.append(str(fila.persona))
    if cerrar and not res.sin_marcar:
        _cerrar(jornada, usuario)
        res.cerrada = True
    elif res.cambios:
        _subir_version(jornada)
    if tocadas:
        actualizar_resumen(actividad, tocadas)
    if actividad.estado.codigo == "realizada" and res.cambios:
        registrar(usuario, "asistencia_tardia", actividad, f"{res.cambios} cambios en la {jornada.nombre_jornada.lower()} después de finalizar")
    return res


def _cerrar(jornada, usuario, motivo=""):
    jornada.estado_lista = SesionActividad.LISTA_CERRADA
    jornada.cerrada_por, jornada.cerrada_en = usuario, timezone.now()
    _subir_version(jornada)
    CambioLista.objects.create(sesion=jornada, accion="cerrada", usuario=usuario, motivo=motivo[:250])


@transaction.atomic
def cerrar_lista(actividad, jornada, usuario, version=None):
    """Cierra la lista: queda de solo lectura, con quién la cerró y cuándo. Exige que todas las personas tengan marca."""
    actividad = _bloquear(actividad)
    jornada = _guardar_jornada(actividad, jornada)
    _exigir_abierta(jornada)
    _exigir_version(jornada, version)
    _exigir_dia(actividad, jornada)
    lista, _, _ = _lista_actual(actividad, jornada)
    sin = [str(f.persona) for f in lista if not f.marca]
    if sin:
        raise ReglaNegocio(texto_sin_marcar(sin))
    _cerrar(jornada, usuario)
    registrar(usuario, "lista_cerrada", actividad, jornada.nombre_jornada)
    return jornada


def texto_sin_marcar(nombres):
    muestra = ", ".join(nombres[:3]) + (f" y {len(nombres) - 3} más" if len(nombres) > 3 else "")
    return (f"No se puede cerrar: falta marcar a {plural(len(nombres), 'persona', 'personas')} ({muestra}). "
            "Márcalas o usa «Marcar el resto como ausente».")


@transaction.atomic
def reabrir_lista(actividad, jornada, usuario, motivo):
    """Reabre una lista cerrada o una jornada suspendida. Pide motivo y queda en el historial de la lista."""
    motivo = (motivo or "").strip()
    if not motivo:
        raise ReglaNegocio("Indica el motivo para reabrir la lista.")
    actividad = _bloquear(actividad)
    jornada = _guardar_jornada(actividad, jornada)
    if jornada.lista_abierta:
        raise ReglaNegocio("La lista ya está abierta.")
    era_suspendida = jornada.suspendida
    jornada.estado_lista = SesionActividad.LISTA_ABIERTA
    jornada.cerrada_por, jornada.cerrada_en = None, None
    if era_suspendida:
        jornada.motivo_suspension = ""
    _subir_version(jornada)
    CambioLista.objects.create(sesion=jornada, accion="reabierta", usuario=usuario, motivo=motivo[:250])
    registrar(usuario, "lista_reabierta", actividad, f"{jornada.nombre_jornada}: {motivo}")
    return jornada


@transaction.atomic
def suspender_jornada(actividad, jornada, usuario, motivo):
    """Jornada suspendida (lluvia, paro…): sin lista y con motivo; no cuenta para el porcentaje. Si ya tiene marcas, no
    se suspende: se corrigen o se dejan [P]."""
    motivo = (motivo or "").strip()
    if not motivo:
        raise ReglaNegocio("Indica el motivo de la suspensión (por ejemplo, lluvia).")
    actividad = _bloquear(actividad)
    if actividad.estado.codigo in ESTADOS_SIN_LISTA and actividad.estado.codigo != "suspendida":
        raise ReglaNegocio(f"No se suspenden jornadas de una actividad {actividad.estado.nombre.lower()}.")
    jornada = _guardar_jornada(actividad, jornada)
    _exigir_abierta(jornada)
    if jornada.asistencias.exclude(marca="").exists():
        raise ReglaNegocio("La lista ya tiene marcas: una jornada suspendida no tiene lista. Si sí se realizó, ciérrala.")
    jornada.estado_lista = SesionActividad.SUSPENDIDA
    jornada.motivo_suspension = motivo[:250]
    _subir_version(jornada)
    CambioLista.objects.create(sesion=jornada, accion="suspendida", usuario=usuario, motivo=motivo[:250])
    registrar(usuario, "jornada_suspendida", actividad, f"{jornada.nombre_jornada}: {motivo}")
    return jornada


@transaction.atomic
def nueva_jornada(actividad, usuario, fecha, hora_inicio=None, hora_fin=None, lugar=None, nombre=""):
    """«+ Nueva jornada». Si la fecha programada aún no tenía su jornada guardada, se guarda primero (así queda con el
    número 1 y las demás siguen en orden)."""
    if hora_inicio and hora_fin and hora_fin <= hora_inicio:
        raise ReglaNegocio("La hora de término debe ser posterior a la de inicio.")
    actividad = _bloquear(actividad)
    if actividad.estado.codigo in ("cancelada", "realizada"):
        raise ReglaNegocio(f"No se agregan jornadas a una actividad {actividad.estado.nombre.lower()}.")
    programada = next((j for j in jornadas(actividad) if not j.pk), None)
    if programada is not None and (programada.fecha, programada.hora_inicio) != (fecha, hora_inicio):
        _guardar_jornada(actividad, programada)  # p. ej. la de la mañana, antes de agregar la de la tarde
    numero = (SesionActividad.objects.filter(actividad=actividad).aggregate(n=Max("numero"))["n"] or 0) + 1
    j = SesionActividad.objects.create(actividad=actividad, numero=numero, fecha=fecha, hora_inicio=hora_inicio, hora_fin=hora_fin,
                                       lugar=lugar, nombre=(nombre or "").strip()[:150], redactada_por=usuario)
    registrar(usuario, "jornada_creada", actividad, f"{j.nombre_jornada} {fecha:%d-%m-%Y}")
    return j


@transaction.atomic
def guardar_jornada_programada(actividad, jornada):
    """Guarda la jornada (la programada o la de hoy, si aún no lo está) y la devuelve: para registrar su conteo."""
    actividad = _bloquear(actividad)
    return _guardar_jornada(actividad, jornada)


def al_reprogramar(actividad, anterior, nueva):
    """Reprogramar no borra jornadas con lista: avisa. La jornada de la fecha anterior que aún no se usa sigue a la
    nueva fecha (o toma las horas y el lugar nuevos, si la fecha es la misma). Devuelve los avisos."""
    if anterior is None:
        return []
    vieja = (SesionActividad.objects.filter(actividad=actividad, vigente=True, fecha=anterior.fecha)
             .order_by("hora_inicio", "numero").first())
    if vieja is None:
        return []
    if tiene_lista(vieja):
        if anterior.fecha != nueva.fecha:
            return [f"La {vieja.nombre_jornada.lower()} del {vieja.fecha:%d-%m-%Y} ya tiene lista: se conserva. "
                    "Si no se realizó, suspéndela desde «Equipo y asistencia»."]
        return []
    if anterior.fecha != nueva.fecha and SesionActividad.objects.filter(actividad=actividad, vigente=True, fecha=nueva.fecha).exists():
        return []
    vieja.fecha, vieja.hora_inicio, vieja.hora_fin, vieja.lugar_id = nueva.fecha, nueva.hora_inicio, nueva.hora_fin, nueva.lugar_id
    vieja.save()
    return []


# --- Inscripción: llegó, retiro y reincorporación ---------------------------------------------------------------------
@transaction.atomic
def marcar_llegada(actividad, usuario, persona, jornada=None, rol=None):
    """«+ Agregar persona que llegó»: la deja Presente en la jornada (la de hoy si no se indica). Si su inscripción no
    estaba activa ese día (inscrita después, retirada, canceló, rechazó o en lista de espera), queda «Inscrita» desde
    esa fecha. Devuelve (jornada, marcada, aviso): si la lista está cerrada o suspendida, no marca y lo avisa."""
    from apps.nucleo.models import EstadoParticipacion

    actividad = _bloquear(actividad)
    if jornada is None:
        jornada = jornada_para_marcar(actividad)
    if jornada is None:
        return None, False, "Aún no es el día de la actividad: queda inscrita y se marca desde ese día."
    ok, motivo = puede_pasar_lista(actividad, jornada)
    if not ok:
        return None, False, motivo + " Queda inscrita."
    jornada = _guardar_jornada(actividad, jornada)
    partes = sorted([p for p in participaciones(actividad) if p.persona_id == persona.pk], key=_clave_principal)
    if rol is not None:
        partes.sort(key=lambda p: p.rol_id != rol.pk)
    if not partes:
        return jornada, False, ""
    principal = partes[0]
    if not principal.en_lista_de(jornada.fecha):
        if principal.estado.codigo in Participacion.INACTIVOS:
            principal.estado = EstadoParticipacion.objects.get(codigo="confirmado")
            principal.retirado_en, principal.motivo_retiro = None, ""
        if principal.inscrito_en and jornada.fecha and principal.inscrito_en > jornada.fecha:
            principal.inscrito_en = jornada.fecha
        principal.save()
    if not jornada.lista_abierta:
        return jornada, False, (f"La lista de la {jornada.nombre_jornada.lower()} está {jornada.get_estado_lista_display().lower()}: "
                                "queda inscrita, sin marca. Reabre la lista para marcarla.")
    lista, existentes, _ = _lista_actual(actividad, jornada)
    fila = next((f for f in lista if f.persona.pk == persona.pk), None)
    if fila and _poner_marca(jornada, fila, M.PRESENTE, fila.marca.observacion if fila.marca else "", usuario, existentes):
        _subir_version(jornada)
        actualizar_resumen(actividad, {persona.pk})
    return jornada, True, ""


@transaction.atomic
def incluir_desde(actividad, jornada, usuario, participacion_ids):
    """Quienes se inscribieron después de esta jornada (por ejemplo, porque se digitaron tarde) pasan a estar inscritas
    desde su fecha y aparecen en su lista. Devuelve (cuántas, la jornada guardada)."""
    actividad = _bloquear(actividad)
    jornada = _guardar_jornada(actividad, jornada)
    _exigir_abierta(jornada)
    n = 0
    for p in Participacion.objects.filter(actividad=actividad, pk__in=participacion_ids, inscrito_en__gt=jornada.fecha):
        p.inscrito_en = jornada.fecha
        p.save()
        n += 1
    if n:
        _subir_version(jornada)
        registrar(usuario, "inscripcion_adelantada", actividad, f"{n} desde la {jornada.nombre_jornada.lower()} ({jornada.fecha:%d-%m-%Y})")
    return n, jornada


@transaction.atomic
def retirar(participacion, usuario, motivo, fecha=None):
    """«Quitar de la tarea»: la inscripción queda «Retirado», con fecha y motivo. Conserva sus asistencias y no aparece
    en las jornadas siguientes."""
    from apps.nucleo.models import EstadoParticipacion

    motivo = (motivo or "").strip()
    if not motivo:
        raise ReglaNegocio("Indica el motivo del retiro.")
    p = Participacion.objects.select_for_update().select_related("estado", "persona", "actividad").get(pk=participacion.pk)
    if p.estado.codigo in ("retirado", "registro_erroneo"):
        raise ReglaNegocio("Esa inscripción ya no está en la tarea.")
    fecha = fecha or timezone.localdate()
    if p.inscrito_en and fecha < p.inscrito_en:
        raise ReglaNegocio(f"La fecha del retiro no puede ser anterior a su inscripción ({p.inscrito_en:%d-%m-%Y}).")
    p.estado = EstadoParticipacion.objects.get(codigo="retirado")
    p.retirado_en, p.motivo_retiro = fecha, motivo[:250]
    p.save()
    registrar(usuario, "participacion_retirada", p, f"{fecha:%d-%m-%Y}: {motivo}")
    return p


@transaction.atomic
def reincorporar(participacion, usuario):
    """Deshace un retiro hecho por error: vuelve al estado que tenía antes (o «Inscrito») y a las listas siguientes."""
    from apps.nucleo.models import EstadoParticipacion

    p = Participacion.objects.select_for_update().select_related("estado", "persona", "actividad").get(pk=participacion.pk)
    if p.estado.codigo != "retirado":
        raise ReglaNegocio("Esa inscripción no está retirada.")
    anterior = (p.history.exclude(estado__codigo__in=Participacion.INACTIVOS).exclude(estado__codigo__in=("asistio", "no_asistio"))
                .order_by("-history_date", "-history_id").values_list("estado_id", flat=True).first())
    p.estado = EstadoParticipacion.objects.get(pk=anterior) if anterior else EstadoParticipacion.objects.get(codigo="confirmado")
    p.retirado_en, p.motivo_retiro = None, ""
    p.save()
    registrar(usuario, "participacion_reincorporada", p)
    return p


def actualizar_resumen(actividad, persona_ids):
    """`Participacion.asistencia` como resumen de las jornadas no suspendidas: verdadero si fue a una o más, falso si
    sus marcas son ausencias, vacío si no tiene marcas (o solo justificadas) [P]. Solo de las personas indicadas."""
    persona_ids = set(persona_ids)
    if not persona_ids:
        return 0
    suyas = {}
    for persona_id, marca in (SesionAsistencia.objects.filter(sesion__actividad=actividad, sesion__vigente=True, participacion__persona_id__in=persona_ids)
                              .exclude(marca="").exclude(sesion__estado_lista=SesionActividad.SUSPENDIDA)
                              .values_list("participacion__persona_id", "marca")):
        suyas.setdefault(persona_id, set()).add(marca)
    n = 0
    for p in Participacion.objects.filter(actividad=actividad, persona_id__in=persona_ids).exclude(estado__codigo="registro_erroneo"):
        m = suyas.get(p.persona_id, set())
        valor = True if m & set(CUENTAN) else (False if M.AUSENTE in m else None)
        if valor != p.asistencia:
            p.asistencia = valor
            p.save(update_fields=["asistencia"])
            n += 1
    return n

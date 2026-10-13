"""Carga un conjunto pequeño de datos FICTICIOS para probar y demostrar el sistema. No usar con datos reales."""
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.actividades import servicios
from apps.actividades.models import Actividad, Participacion
from apps.lugares.models import Lugar
from apps.nucleo.models import EstadoActividad, EstadoParticipacion, EstadoRegistro, RolParticipacion, TipoActividad, TipoContacto, TipoLugar, TipoOrganizacion
from apps.organizaciones.models import Carrera, Organizacion
from apps.personas.models import Contacto, Persona
from apps.proyectos.models import Proyecto
from apps.territorio.models import Comuna, Direccion, Provincia, Region


class Command(BaseCommand):
    help = "Carga datos ficticios de demostración (personas, organizaciones, lugar, proyecto y actividades)."

    def add_arguments(self, parser):
        parser.add_argument("--si-estoy-seguro", action="store_true", dest="seguro")
        parser.add_argument("--ampliar", action="store_true", help="Agrega a una base de demostración existente la comunidad y la bitácora (F22).")

    @transaction.atomic
    def handle(self, *args, seguro, ampliar=False, **opts):
        if not seguro:
            raise CommandError("Esto crea datos ficticios. Si estás seguro, agrega --si-estoy-seguro.")
        if ampliar:
            from apps.comunidades.models import Comunidad

            a = Actividad.objects.filter(nombre="Taller Demo 1").first()
            if not a or Comunidad.objects.exists():
                raise CommandError("Solo se amplía una base con los datos de demostración y sin comunidades.")
            self._demo_f22(a)
            self.stdout.write(self.style.SUCCESS("Comunidad y bitácora de demostración agregadas (todo ficticio)."))
            return
        if Persona.objects.exists() or Proyecto.objects.exists():
            raise CommandError("La base ya tiene datos; no se cargan los de demostración.")
        region, _ = Region.objects.get_or_create(codigo="99", defaults={"nombre": "Región Demo"})
        prov, _ = Provincia.objects.get_or_create(codigo="990", defaults={"region": region, "nombre": "Provincia Demo"})
        comuna, _ = Comuna.objects.get_or_create(codigo="99001", defaults={"provincia": prov, "nombre": "Comuna Demo"})
        activo = EstadoRegistro.objects.get(codigo="activo")
        correo, movil = TipoContacto.objects.get(codigo="correo"), TipoContacto.objects.get(codigo="telefono_movil")
        uni = Organizacion.objects.create(nombre="Universidad Demo", tipo=TipoOrganizacion.objects.get(codigo="institucion_educativa"), estado_registro=activo)
        Carrera.objects.create(organizacion=uni, nombre="Trabajo Social Demo")
        Organizacion.objects.create(nombre="Junta de Vecinos Demo", tipo=TipoOrganizacion.objects.get(codigo="junta_de_vecinos_o_comite"), estado_registro=activo)
        coord = Persona.objects.create(nombres="Coordinadora", apellido_paterno="Demo", estado_registro=activo)
        Contacto.objects.create(persona=coord, tipo=correo, valor="coordinadora@ejemplo.invalid", principal=True)
        vols = []
        for i in range(1, 6):
            p = Persona.objects.create(nombres=f"Voluntario{i}", apellido_paterno="Demo", estado_registro=activo)
            Contacto.objects.create(persona=p, tipo=movil, valor=f"9 0000 000{i}")
            vols.append(p)
        lugar = Lugar.objects.create(nombre="Sede Demo", tipo=TipoLugar.objects.get(codigo="sede"), capacidad=25, direccion=Direccion.objects.create(calle="Calle Demo", numero="123", comuna=comuna))
        proyecto = Proyecto.objects.create(nombre="Proyecto Demo de alfabetización", estado="ejecucion", responsable=coord, zona="Comuna Demo")
        a = Actividad.objects.create(nombre="Taller Demo 1", proyecto=proyecto, tipo=TipoActividad.objects.get(codigo="taller"), estado=EstadoActividad.objects.get(codigo="pendiente"), responsable=coord)
        servicios.programar(a, None, date.today() + timedelta(days=7), time(18), time(20), lugar, None)
        for p in vols[:3]:
            Participacion.objects.create(actividad=a, persona=p, rol=RolParticipacion.objects.get(codigo="voluntario"), estado=EstadoParticipacion.objects.get(codigo="confirmado"))
        Actividad.objects.create(nombre="Taller Demo 2 (sin programar)", proyecto=proyecto, estado=EstadoActividad.objects.get(codigo="pendiente"))
        self._demo_f22(a)
        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados (todos ficticios)."))

    def _demo_f22(self, actividad):
        """Comunidad con padrón, actividad dirigida, estudiante con formación y una sesión con minuta (F22). Todo ficticio."""
        from apps.actividades.models import ActividadComunidad, SesionActividad, SesionFacilitador
        from apps.comunidades.models import Comunidad, ComunidadMiembro
        from apps.nucleo.models import AreaTematica, PerfilPersona
        from apps.personas.models import PersonaFormacion

        comuna = actividad.agenda_vigente.lugar.direccion.comuna if actividad.agenda_vigente and actividad.agenda_vigente.lugar else Comuna.objects.first()
        junta = Organizacion.objects.filter(nombre="Junta de Vecinos Demo").first()
        uni = Organizacion.objects.filter(nombre="Universidad Demo").first()
        area = AreaTematica.objects.get(codigo="educacion")
        actividad.area_tematica = area
        actividad.publico_objetivo = "Vecinas y vecinos adultos del sector que quieren aprender a leer y escribir."
        actividad.beneficiarios_estimados = 20
        actividad.save()
        com = Comunidad.objects.create(nombre="Vecinos de la Villa Demo", tipo="vecinal", comuna=comuna, organizacion=junta, poblacion_estimada=120,
                                       rango_etario="Personas adultas y mayores", diagnostico="Interés en alfabetización y uso del celular (ficticio).")
        com.areas_interes.add(area)
        vecinos = []
        for i in range(1, 4):
            v = Persona.objects.create(nombres=f"Vecina{i}", apellido_paterno="Demo", fecha_nacimiento=date(1950 + i * 8, 3, i))
            v.perfiles.add(PerfilPersona.objects.get(codigo="vecino_o_vecina_de_la_comunidad"))
            ComunidadMiembro.objects.create(comunidad=com, persona=v, rol="dirigente" if i == 1 else "integrante")
            vecinos.append(v)
        ActividadComunidad.objects.create(actividad=actividad, comunidad=com, beneficiarios_estimados=20)
        estudiante = Persona.objects.filter(nombres="Voluntario1").first()
        if estudiante and uni:
            estudiante.fecha_nacimiento = date(2003, 6, 15)
            estudiante.save()
            estudiante.perfiles.add(PerfilPersona.objects.get(codigo="estudiante"))
            PersonaFormacion.objects.create(persona=estudiante, organizacion=uni, carrera=uni.carreras.first(), sede="Campus Demo", jornada="diurna", nivel_actual=3,
                                            asignatura="Aprendizaje + servicio (ficticio)", horas_comprometidas=30)
        for v in vecinos:
            Participacion.objects.get_or_create(actividad=actividad, persona=v, rol=RolParticipacion.objects.get(codigo="beneficiario"),
                                                defaults={"estado": EstadoParticipacion.objects.get(codigo="confirmado")})
        s = SesionActividad.objects.create(
            actividad=actividad, numero=1, nombre="Diagnóstico y presentación", fecha=actividad.agenda_vigente.fecha if actividad.agenda_vigente else None,
            hora_inicio=time(18), hora_fin=time(20), objetivo="Conocer a los participantes y sus intereses.",
            desarrollo="Presentación del equipo y ronda de expectativas (ficticio).", avances="Se formaron dos grupos según nivel de lectura.",
            acuerdos="Reunirse los martes a las 18:00.", proximos_pasos="Preparar material de lectura con letra grande.",
            asistentes_sin_registro=6, conteo_mayores=4, conteo_adultos=2, conteo_mujeres=5, conteo_hombres=1,
        )
        if actividad.responsable_id:
            SesionFacilitador.objects.create(sesion=s, persona=actividad.responsable)

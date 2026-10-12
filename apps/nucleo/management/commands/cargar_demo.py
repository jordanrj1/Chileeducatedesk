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

    @transaction.atomic
    def handle(self, *args, seguro, **opts):
        if not seguro:
            raise CommandError("Esto crea datos ficticios. Si estás seguro, agrega --si-estoy-seguro.")
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
        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados (todos ficticios)."))

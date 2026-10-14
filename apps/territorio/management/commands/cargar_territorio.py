"""Comando `cargar_territorio`: carga o actualiza las regiones, provincias y comunas de Chile (códigos CUT oficiales).

Sin argumentos usa la lista oficial guardada en `apps/territorio/datos/cut_chile.csv`; también acepta otro CSV con las columnas
region_codigo, region_nombre, provincia_codigo, provincia_nombre, comuna_codigo, comuna_nombre. Revisa todo el archivo antes de
escribir y, si hay errores, no carga nada. Se puede repetir: agrega lo nuevo, corrige nombres y nunca borra ni duplica.
  --si-falta  no hace nada si ya están todas las comunas del archivo (lo usan iniciar.bat e iniciar.sh al arrancar).
  --simular   muestra lo que cambiaría, sin guardar nada.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.territorio.carga import ARCHIVO_OFICIAL, ErrorCarga, cargar, comunas_que_faltan, leer

DETALLE_MAXIMO = 30  # cuántos cambios se listan uno por uno


class Command(BaseCommand):
    help = "Carga o actualiza las regiones, provincias y comunas de Chile desde la lista oficial (códigos CUT). Nunca borra."

    def add_arguments(self, parser):
        parser.add_argument("archivo", nargs="?", default=str(ARCHIVO_OFICIAL), help="CSV con códigos CUT. Si no se indica, usa la lista oficial del sistema.")
        parser.add_argument("--si-falta", action="store_true", help="No hace nada si ya están todas las comunas del archivo.")
        parser.add_argument("--simular", action="store_true", help="Muestra lo que cambiaría, sin guardar nada.")

    def handle(self, *args, archivo, si_falta, simular, **opts):
        try:
            filas = leer(archivo)
        except ErrorCarga as e:
            raise CommandError(str(e))
        if si_falta and not comunas_que_faltan(filas):
            self.stdout.write(f"Territorio: ya están las {len(filas)} comunas del archivo; no se cambió nada.")
            return
        resultados = cargar(filas, simular=simular)
        if simular:
            self.stdout.write(f"Simulación con «{archivo}»: así cambiaría la base (no se guardó nada).")
        else:
            self.stdout.write(f"Territorio cargado desde «{archivo}».")
        for r in resultados:
            self.stdout.write(f"  {r.linea()}")
            if 0 < len(r.nuevas) <= DETALLE_MAXIMO:
                self.stdout.write("    Nuevas: " + "; ".join(r.nuevas))
            for texto in r.actualizadas[:DETALLE_MAXIMO]:
                self.stdout.write(f"    Actualizada {texto}")
            if len(r.actualizadas) > DETALLE_MAXIMO:
                self.stdout.write(f"    … y {len(r.actualizadas) - DETALLE_MAXIMO} más.")
        if simular:
            self.stdout.write("Simulación terminada: no se guardó nada.")
        else:
            self.stdout.write(self.style.SUCCESS("Listo. No se borró nada; lo que no está en el archivo (como la Región Demo) sigue igual."))

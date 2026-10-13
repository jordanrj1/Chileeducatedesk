"""Respaldo (RNF-10): copia de la base (pg_dump) y de la carpeta de documentos. Funciona igual en Windows, Mac y Linux."""
import os
import shutil
import subprocess
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.nucleo.auditoria import registrar


def _buscar_pg_dump():
    if os.environ.get("PG_DUMP"):
        return os.environ["PG_DUMP"]
    ruta = shutil.which("pg_dump")
    if ruta:
        return ruta
    candidatos = list(Path.home().glob("Applications/Postgres.app/Contents/Versions/*/bin/pg_dump")) + list(Path("C:/Program Files/PostgreSQL").glob("*/bin/pg_dump.exe"))
    return str(sorted(candidatos)[-1]) if candidatos else None


class Command(BaseCommand):
    help = "Respalda la base de datos y los documentos en una carpeta con fecha."

    def add_arguments(self, parser):
        parser.add_argument("--destino", default=os.environ.get("RESPALDO_DIR") or str(settings.BASE_DIR.parent / "fche_respaldos"))
        parser.add_argument("--dias", type=int, default=30, help="Se conservan los respaldos de los últimos N días.")

    def handle(self, *args, destino, dias, **opts):
        pg_dump = _buscar_pg_dump()
        if not pg_dump:
            raise CommandError("No se encontró pg_dump. Instala las herramientas de PostgreSQL o define la variable PG_DUMP con su ruta.")
        destino = Path(destino)
        destino.mkdir(parents=True, exist_ok=True)
        sello = datetime.now().strftime("%Y%m%d_%H%M%S")
        bd = settings.DATABASES["default"]
        archivo_bd = destino / f"fche_bd_{sello}.dump"
        entorno = {**os.environ, "PGPASSWORD": bd.get("PASSWORD") or ""}
        cmd = [pg_dump, "-Fc", "-h", bd["HOST"] or "127.0.0.1", "-p", str(bd["PORT"] or 5432), "-U", bd["USER"], "-f", str(archivo_bd), bd["NAME"]]
        r = subprocess.run(cmd, env=entorno, capture_output=True, text=True)
        if r.returncode != 0:
            archivo_bd.unlink(missing_ok=True)
            raise CommandError(f"pg_dump falló: {r.stderr.strip()}")
        env = Path(settings.BASE_DIR) / ".env"
        if env.exists():  # OP-E8: sin la configuración no se puede volver a levantar el sistema
            shutil.copy2(env, destino / f"fche_config_{sello}.env")
        archivo_media = destino / f"fche_documentos_{sello}.zip"
        n = 0
        media = Path(settings.MEDIA_ROOT)
        with zipfile.ZipFile(archivo_media, "w", zipfile.ZIP_DEFLATED) as z:
            if media.exists():
                for f in media.rglob("*"):
                    if f.is_file():
                        z.write(f, f.relative_to(media))
                        n += 1
        limite = datetime.now() - timedelta(days=dias)
        borrados = 0
        for f in destino.glob("fche_*"):
            if f.stat().st_mtime < limite.timestamp() and f not in (archivo_bd, archivo_media):
                f.unlink()
                borrados += 1
        registrar(None, "respaldo", str(destino), f"bd={archivo_bd.name} documentos={n}")
        self.stdout.write(self.style.SUCCESS(f"Respaldo listo en {destino}: {archivo_bd.name} ({archivo_bd.stat().st_size // 1024} KB) y {archivo_media.name} ({n} archivos). Antiguos eliminados: {borrados}."))

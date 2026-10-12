import shutil
import zipfile
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.nucleo.management.commands.respaldar import _buscar_pg_dump

pytestmark = pytest.mark.django_db


def test_cargar_demo_exige_confirmacion_y_es_ficticio():
    with pytest.raises(CommandError):
        call_command("cargar_demo")
    call_command("cargar_demo", "--si-estoy-seguro")
    from apps.actividades.models import Actividad
    from apps.personas.models import Persona

    assert Persona.objects.count() == 6 and Actividad.objects.count() == 2
    assert all("Demo" in p.apellido_paterno for p in Persona.objects.all())
    with pytest.raises(CommandError):
        call_command("cargar_demo", "--si-estoy-seguro")  # no pisa datos existentes


@pytest.mark.skipif(not _buscar_pg_dump(), reason="pg_dump no está disponible en este equipo")
def test_respaldo_genera_dump_y_zip_y_borra_antiguos(tmp_path, settings):
    media = Path(settings.MEDIA_ROOT)
    (media / "documentos").mkdir(parents=True)
    (media / "documentos" / "ficticio.txt").write_text("contenido ficticio")
    destino = tmp_path / "respaldos"
    destino.mkdir()
    viejo = destino / "fche_bd_20200101_000000.dump"
    viejo.write_text("viejo")
    import os, time

    antiguo = time.time() - 90 * 86400
    os.utime(viejo, (antiguo, antiguo))
    call_command("respaldar", "--destino", str(destino), "--dias", "30")
    dumps = list(destino.glob("fche_bd_*.dump"))
    zips = list(destino.glob("fche_documentos_*.zip"))
    assert len(dumps) == 1 and dumps[0].stat().st_size > 1000 and not viejo.exists()
    assert zipfile.ZipFile(zips[0]).namelist() == ["documentos/ficticio.txt"]
    from apps.nucleo.models import Auditoria

    assert Auditoria.objects.filter(accion="respaldo").exists()


def test_respaldo_sin_pg_dump_da_un_error_claro(monkeypatch, tmp_path):
    monkeypatch.setattr("apps.nucleo.management.commands.respaldar._buscar_pg_dump", lambda: None)
    with pytest.raises(CommandError, match="pg_dump"):
        call_command("respaldar", "--destino", str(tmp_path))

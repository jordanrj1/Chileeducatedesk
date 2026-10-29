"""Capturas de pantalla de páginas de FCHE con Chrome sin interfaz (escritorio y celular).

Uso:  .venv/bin/python scripts/revision/capturar.py <carpeta_salida> [/ruta1 /ruta2 ...]
Requiere el servidor corriendo en http://127.0.0.1:8000 (para el CSS y JS) y Google Chrome instalado.
Renderiza cada página como Gestor con el cliente de pruebas de Django y la fotografía; no modifica datos.
Nota: Chrome sin interfaz tiene un ancho mínimo de ventana de 500 px; por eso la captura «celular» muestra la página dentro
de un iframe de 400 px (viewport real de 400) en una ventana de 520. Lo que se corte a la derecha dentro del marco es un
desborde real.
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402

settings.ALLOWED_HOSTS = ["*"]
from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402

CHROME = next((c for c in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome"), shutil.which("chrome"),
                            r"C:\Program Files\Google\Chrome\Application\chrome.exe"] if c and os.path.exists(c)), None)
SERVIDOR = "http://127.0.0.1:8000"
POR_DEFECTO = ["/dashboard", "/personas", "/actividades", "/comunidades", "/buscar?q=demo"]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    salida = os.path.abspath(sys.argv[1])
    rutas = sys.argv[2:] or POR_DEFECTO
    if not CHROME:
        sys.exit("No se encontró Google Chrome.")
    os.makedirs(salida, exist_ok=True)
    c = Client()
    c.force_login(User.objects.filter(groups__name="Gestor", is_active=True).first())
    for ruta in rutas:
        html = c.get(ruta).content.decode()
        html = html.replace('href="/static/', f'href="{SERVIDOR}/static/').replace('src="/static/', f'src="{SERVIDOR}/static/')
        nombre = ruta.strip("/").replace("/", "_").replace("?", "_").replace("=", "-").replace("&", "_") or "inicio"
        archivo = os.path.join(salida, f"{nombre}.html")
        open(archivo, "w", encoding="utf-8").write(html)
        # Celular: la página va dentro de un iframe de 400 px (viewport real de 400); la ventana mide 520 porque Chrome no baja de 500.
        marco = os.path.join(salida, f"{nombre}.marco400.html")
        open(marco, "w", encoding="utf-8").write(
            f'<!doctype html><body style="margin:0;background:#888"><iframe src="file://{archivo}" '
            'style="width:400px;height:1400px;border:0;background:#fff"></iframe></body>')
        for sufijo, ancho, alto, pagina in (("", 1440, 1800, archivo), ("_celular", 520, 1400, marco)):
            png = os.path.join(salida, f"{nombre}{sufijo}.png")
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                            f"--window-size={ancho},{alto}", f"--screenshot={png}", "file://" + pagina], capture_output=True, timeout=90)
        print("capturada:", ruta)


if __name__ == "__main__":
    main()

"""Recorre todas las páginas y pestañas de FCHE como Gestor y Administrador y reporta errores 5xx o de plantilla.

Uso (desde la raíz del repositorio):  .venv/bin/python scripts/revision/recorrer.py
Usa la base de desarrollo (config.settings.local) y solo hace GET: no modifica datos.
"""
import os
import re
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
import django  # noqa: E402

django.setup()
from django.conf import settings  # noqa: E402

settings.ALLOWED_HOSTS = ["*"]
from django.apps import apps  # noqa: E402
from django.contrib.auth.models import User  # noqa: E402
from django.test import Client  # noqa: E402

FIJAS = ["/dashboard", "/buscar", "/buscar?q=a", "/ayuda", "/mi-cuenta", "/calendario", "/administracion/", "/administracion/catalogos/",
         "/administracion/usuarios", "/administracion/roles", "/administracion/auditoria", "/territorio", "/importaciones", "/importaciones/nueva",
         "/personas/nueva", "/personas/nueva?modo=completa", "/actividades/nueva", "/organizaciones/nueva", "/lugares/nuevo", "/documentos/nuevo",
         "/solicitudes/nueva", "/proyectos/nuevo", "/comunidades/nueva"]
LISTADOS = ["/personas", "/organizaciones", "/comunidades", "/lugares", "/actividades", "/proyectos", "/solicitudes", "/documentos"]
MODELOS = ["personas.Persona", "organizaciones.Organizacion", "comunidades.Comunidad", "lugares.Lugar", "actividades.Actividad", "proyectos.Proyecto",
           "solicitudes.Solicitud", "documentos.Documento", "territorio.Comuna", "territorio.Region", "actividades.SesionActividad"]
FICHA = re.compile(r"^/(personas|organizaciones|lugares|actividades|proyectos|solicitudes|documentos|comunidades|territorio)/\d+$")


def urls():
    res = FIJAS + LISTADOS + [u + "?q=a&activo=*" for u in LISTADOS]
    for etiqueta in MODELOS:
        for obj in apps.get_model(etiqueta).objects.all()[:2]:
            res.append(obj.get_absolute_url())
    return res


def main():
    errores, vistas = [], 0
    for rol in ("Gestor", "Administrador"):
        u = User.objects.filter(groups__name=rol, is_active=True).first()
        if not u:
            print(f"Sin usuario activo con rol {rol}: se omite.")
            continue
        c = Client()
        c.force_login(u)
        pendientes, vistos = urls(), set()
        while pendientes:
            url = pendientes.pop(0)
            if url in vistos:
                continue
            vistos.add(url)
            r = c.get(url)
            vistas += 1
            html = r.content.decode(errors="ignore") if "text/html" in r.get("Content-Type", "") else ""
            if r.status_code >= 500 or r.status_code not in (200, 302, 403, 404) or "TemplateSyntaxError" in html:
                errores.append((rol, url, r.status_code))
            if r.status_code == 200 and FICHA.match(url.split("?")[0]):
                pendientes += [f"{url.split('?')[0]}?tab={t}" for t in re.findall(r'href="\?tab=([a-z_]+)"', html)]
    print(f"{vistas} páginas revisadas; errores: {len(errores)}")
    for e in errores:
        print("  ", e)
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()

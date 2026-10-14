#!/usr/bin/env python
"""Puerta de entrada a los comandos del sistema desde la consola: migrar, crear usuarios, cargar territorio, respaldar…
Ejemplo: python manage.py crear_usuario claudio --correo … --rol Gestor (con el entorno virtual activado).
Por defecto usa los ajustes de desarrollo; iniciar.bat y respaldar.bat eligen los de producción."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

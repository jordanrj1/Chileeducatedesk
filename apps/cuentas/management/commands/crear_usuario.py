"""Comando de consola para crear una cuenta con rol Gestor o Administrador.
Sirve para la primera cuenta, cuando aún no hay nadie que pueda crearla desde la pantalla.
Pide la contraseña por teclado sin mostrarla; ninguna contraseña queda escrita en el código."""
from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.cuentas.models import PerfilCuenta


class Command(BaseCommand):
    help = "Crea un usuario con rol Gestor o Administrador."

    def add_arguments(self, parser):
        parser.add_argument("usuario")
        parser.add_argument("--correo", required=True)
        parser.add_argument("--rol", required=True, choices=["Gestor", "Administrador"])
        parser.add_argument("--nombres", default="")
        parser.add_argument("--apellidos", default="")
        parser.add_argument("--password", help="Solo para automatizar; por defecto se pide por teclado.")

    def handle(self, *args, usuario, correo, rol, nombres, apellidos, password, **opts):
        User = get_user_model()
        if User.objects.filter(username__iexact=usuario).exists() or User.objects.filter(email__iexact=correo).exists():
            raise CommandError("Ya existe un usuario con ese nombre o correo.")
        if not password:
            password = getpass("Contraseña: ")
            if password != getpass("Repetir contraseña: "):
                raise CommandError("Las contraseñas no coinciden.")
        u = User(username=usuario, email=correo.lower(), first_name=nombres, last_name=apellidos)
        try:
            validate_password(password, u)
        except ValidationError as e:
            raise CommandError("Contraseña no válida: " + " ".join(e.messages))
        u.set_password(password)
        u.save()
        u.groups.add(Group.objects.get(name=rol))
        PerfilCuenta.objects.create(usuario=u)
        self.stdout.write(self.style.SUCCESS(f"Usuario «{usuario}» creado con rol {rol}."))

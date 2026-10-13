from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sembrar(sender, **kwargs):
    from django.apps import apps as registro
    from django.contrib.auth.management import create_permissions
    from django.contrib.contenttypes.management import create_contenttypes

    for config in registro.get_app_configs():
        create_contenttypes(config, verbosity=0)
        create_permissions(config, verbosity=0)
    from .roles import sembrar_roles

    sembrar_roles()


class CuentasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cuentas"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed

        from apps.nucleo.auditoria import registrar

        post_migrate.connect(_sembrar, sender=self, dispatch_uid="fche_sembrar_roles")
        user_logged_in.connect(lambda sender, request, user, **k: registrar(user, "ingreso", user.get_username().lower()), weak=False, dispatch_uid="aud_in")
        user_logged_out.connect(lambda sender, request, user, **k: registrar(user, "salida"), weak=False, dispatch_uid="aud_out")
        user_login_failed.connect(
            lambda sender, credentials, **k: registrar(None, "ingreso_fallido", (credentials.get("username") or "").strip().lower()), weak=False, dispatch_uid="aud_fail"
        )

# F28 B · Datos de los gastos. De datos (reversible como no-op):
# - los movimientos que ya estaban anulados quedan con el estado «anulado» (los demás parten «registrados»);
# - el rol Gestor recibe ver, agregar y cambiar movimiento si aún no los tiene: los gastos de las actividades son visibles siempre.
#   (En una base nueva los permisos aún no existen aquí: los asigna el sistema al terminar de migrar, ver apps/cuentas/roles.py.)
from django.db import migrations


def anulados(apps, schema_editor):
    apps.get_model("finanzas", "Movimiento").objects.filter(anulado=True).update(estado="anulado")


def permisos_del_gestor(apps, schema_editor):
    Group, Permission = apps.get_model("auth", "Group"), apps.get_model("auth", "Permission")
    gestor = Group.objects.filter(name="Gestor").first()
    if gestor is None:
        return
    permisos = Permission.objects.filter(content_type__app_label="finanzas", codename__in=["view_movimiento", "add_movimiento", "change_movimiento"])
    gestor.permissions.add(*permisos)


class Migration(migrations.Migration):

    dependencies = [
        ("finanzas", "0003_f28_gastos"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(anulados, migrations.RunPython.noop),
        migrations.RunPython(permisos_del_gestor, migrations.RunPython.noop),
    ]

"""F26 P2: el estado «activo» o «incompleto» de la ficha se recalcula solo al guardar la persona y al guardar o
desactivar sus contactos, direcciones y formación (ver servicios.recalcular_estado). Así vale para todas las pantallas,
la importación y las ventanas «+ Crear persona», sin repetir la regla en cada una."""
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import Contacto, FichaInvitado, FichaVoluntario, Persona, PersonaDireccion, PersonaFormacion


@receiver(post_save, sender=Persona, dispatch_uid="personas_recalcular_persona")
def _persona_guardada(sender, instance, raw=False, update_fields=None, **kw):
    if raw or (update_fields is not None and set(update_fields) <= {"estado_registro"}):
        return  # cargas de datos, o el propio recálculo
    from .servicios import recalcular_estado

    recalcular_estado(instance)


def _hijo_guardado(sender, instance, raw=False, **kw):
    if raw or not instance.persona_id:
        return  # p. ej., un contacto de una organización
    from .servicios import recalcular_estado

    recalcular_estado(instance.persona)


@receiver(m2m_changed, sender=Persona.perfiles.through, dispatch_uid="personas_recalcular_perfiles")
def _perfiles_cambiados(sender, instance, action, reverse=False, **kw):
    if not reverse and action in ("post_add", "post_remove", "post_clear"):
        from .servicios import recalcular_estado

        recalcular_estado(instance)


# Además de contactos, direcciones y formación: el padrón de comunidades (vecinos) y las fichas de voluntario e invitado,
# que también cuentan en faltantes()
def _modelos_hijos():
    from apps.comunidades.models import ComunidadMiembro

    return (Contacto, PersonaDireccion, PersonaFormacion, FichaVoluntario, FichaInvitado, ComunidadMiembro)


for _modelo in _modelos_hijos():
    post_save.connect(_hijo_guardado, sender=_modelo, dispatch_uid=f"personas_recalcular_{_modelo.__name__}")

"""
Filtros de plantilla unificados para verificación de roles y grupos.
Reutiliza las utilidades centralizadas en core.roles.
"""
from django import template
from core import roles as core_roles

register = template.Library()


@register.filter
def has_group(user, group_name: str):
    """Comprueba pertenencia a un grupo normalizando acentos y mayúsculas."""
    if not getattr(user, "is_authenticated", False):
        return False
    normalized_target = core_roles.normalize_group_name(str(group_name))
    if not normalized_target:
        return False
    user_groups = core_roles.get_normalized_user_groups(user)
    return normalized_target in user_groups


@register.filter
def is_slab_technician(user):
    return core_roles.is_slab_tech(user)


@register.filter
def is_mec_technician(user):
    return core_roles.is_mec_tech(user)


@register.filter
def is_dp_technician(user):
    return core_roles.is_dp_tech(user)


@register.filter
def is_sem_technician(user):
    return core_roles.is_sem_tech(user)


@register.filter
def is_sims_technician(user):
    return core_roles.is_sims_tech(user)


@register.filter
def is_optics_technician(user):
    return core_roles.is_optics_tech(user)


@register.filter
def is_imp_technician(user):
    return core_roles.is_imp_tech(user)


@register.filter
def is_vdg_technician(user):
    return core_roles.is_vdg_tech(user)


@register.filter
def is_confocal_technician(user):
    return core_roles.is_confocal_tech(user)


@register.filter
def is_olmat_technician(user):
    return core_roles.is_olmat_tech(user)


@register.filter
def is_dtf_user(user):
    return core_roles.is_dtf_user(user)


@register.filter
def is_any_technician(user):
    return core_roles.is_any_tech(user)


@register.filter
def is_reviewer(user):
    return core_roles.is_reviewer(user)


@register.filter
def is_responsable(user):
    return core_roles.is_responsable(user)


@register.filter
def is_manager(user):
    return core_roles.is_manager(user)


@register.filter
def is_icts_user(user):
    return core_roles.is_icts_user(user)


@register.filter
def add_class(field, css_class):
    """Añade clases CSS al widget manteniendo las existentes."""
    existing = field.field.widget.attrs.get("class", "")
    new_classes = (existing + " " + str(css_class)).strip()
    attrs = {**field.field.widget.attrs, "class": new_classes}
    return field.as_widget(attrs=attrs)


@register.filter
def add_attr(field, arg):
    """Añade atributos al widget a partir de cadenas "clave:valor"."""
    try:
        key, value = str(arg).split(":", 1)
    except ValueError:
        return field
    attrs = {**field.field.widget.attrs, key: value}
    return field.as_widget(attrs=attrs)

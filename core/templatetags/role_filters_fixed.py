"""
Filtros de plantilla unificados para verificación de roles y grupos.
Reemplaza las múltiples implementaciones de has_group con una versión robusta.
"""
from django import template
from core.roles import (
    get_normalized_user_groups,
    normalize_group_name,
    is_slab_tech,
    is_mec_tech, 
    is_dp_tech,
    is_sem_tech,
    is_imp_tech,
    is_vdg_tech,
    is_confocal_tech,
    is_dtf_user as core_is_dtf_user,
    is_any_tech,
    is_reviewer,
    is_responsable,
    is_manager,
    is_icts_user,
)

register = template.Library()


@register.filter
def has_group(user, group_name: str):
    """
    Filtro robusto para verificar pertenencia a grupos.
    Maneja acentos, mayúsculas y variaciones de nombres.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    
    normalized_target = normalize_group_name(str(group_name))
    if not normalized_target:
        return False
    
    user_groups = get_normalized_user_groups(user)
    return normalized_target in user_groups


@register.filter
def is_slab_technician(user):
    """Verifica si el usuario es técnico de S-LAB."""
    return is_slab_tech(user)


@register.filter
def is_mec_technician(user):
    """Verifica si el usuario es técnico de S-MEC."""
    return is_mec_tech(user)


@register.filter
def is_dp_technician(user):
    """Verifica si el usuario es técnico de S-DP."""
    return is_dp_tech(user)


@register.filter
def is_sem_technician(user):
    """Verifica si el usuario es técnico de SEM/FIB."""
    return is_sem_tech(user)

@register.filter
def is_imp_technician(user):
    """Verifica si el usuario es técnico de Implantador."""
    return is_imp_tech(user)

@register.filter
def is_vdg_technician(user):
    """Verifica si el usuario es tecnico de VDG."""
    return is_vdg_tech(user)




@register.filter
def is_confocal_technician(user):
    """Verifica si el usuario es técnico de Confocal."""
    return is_confocal_tech(user)


@register.filter
def is_dtf_user(user):
    """Verifica si el usuario es usuario DTF."""
    return core_is_dtf_user(user)


@register.filter
def is_any_technician(user):
    """Verifica si el usuario es cualquier tipo de técnico."""
    return is_any_tech(user)


@register.filter
def is_reviewer(user):
    """Verifica si el usuario es revisor."""
    return is_reviewer(user)


@register.filter
def is_responsable(user):
    """Verifica si el usuario es responsable."""
    return is_responsable(user)


@register.filter
def is_manager(user):
    """Verifica si el usuario es manager."""
    return is_manager(user)


@register.filter
def is_icts_user(user):
    """Verifica si el usuario tiene acceso a ICTS."""
    return is_icts_user(user)


# Filtros para clases CSS
@register.filter
def add_class(field, css_class):
    """
    Añade clases CSS al widget manteniendo las existentes.
    Uso: {{ form.username|add_class:"form-input otra-clase" }}
    """
    existing = field.field.widget.attrs.get("class", "")
    new_classes = (existing + " " + str(css_class)).strip()
    attrs = {**field.field.widget.attrs, "class": new_classes}
    return field.as_widget(attrs=attrs)


@register.filter
def add_attr(field, arg):
    """
    Añade atributos al widget.
    Uso: {{ form.username|add_attr:"placeholder:Usuario" }}
    Formato: "atributo:valor"
    """
    try:
        key, value = str(arg).split(":", 1)
    except ValueError:
        return field
    attrs = {**field.field.widget.attrs, key: value}
    return field.as_widget(attrs=attrs)

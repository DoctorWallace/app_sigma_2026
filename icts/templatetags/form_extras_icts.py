import json
from django import template
from ..auth_utils import get_normalized_user_groups, normalize_group_name, user_in_groups

register = template.Library()

@register.filter
def add_class(field, css):
    # Add classes without overriding existing ones
    attrs = field.field.widget.attrs.copy()
    current = attrs.get("class", "")
    attrs["class"] = (current + " " + css).strip()
    return field.as_widget(attrs=attrs)



@register.filter
def has_group(user, group_name: str):
    if not getattr(user, "is_authenticated", False):
        return False
    normalized = normalize_group_name(str(group_name))
    if not normalized:
        return False
    groups = get_normalized_user_groups(user)
    return normalized in groups


@register.filter(name="user_in_groups")
def user_in_groups_filter(user, group_name: str):
    if not getattr(user, "is_authenticated", False):
        return False
    normalized = normalize_group_name(str(group_name))
    if not normalized:
        return False
    return user_in_groups(user, {normalized})


@register.filter
def tojson(value):
    if value is None:
        value = {}
    return json.dumps(value, ensure_ascii=False)

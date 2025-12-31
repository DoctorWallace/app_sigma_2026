from django import template

register = template.Library()


@register.filter(name="has_group")
def has_group(user, group_name: str):
    try:
        return user.is_authenticated and user.groups.filter(name__iexact=group_name).exists()
    except Exception:
        return False


@register.filter(name="add_class")
def add_class(field, css: str):
    # Add classes preserving existing ones
    existing = field.field.widget.attrs.get("class", "")
    new_classes = (existing + " " + str(css)).strip()
    return field.as_widget(attrs={**field.field.widget.attrs, "class": new_classes})


@register.filter(name="add_attr")
def add_attr(field, arg: str):
    # Set/update an attribute using "name:value"
    try:
        key, value = str(arg).split(":", 1)
    except ValueError:
        return field
    
    # Check if field is already a SafeString (processed by another filter)
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={**field.field.widget.attrs, key: value})
    else:
        # If it's already a SafeString, we can't modify it further
        # Return the field as is and log a warning
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Cannot add attribute '{key}' to already processed field")
        return field


@register.filter(name="form_input")
def form_input(field, extra_attrs: str = ""):
    """
    Combined filter to add form-input class and optional attributes
    Usage: {{ field|form_input:"autocomplete:username" }}
    """
    attrs = {**field.field.widget.attrs}
    
    # Add form-input class
    existing_classes = attrs.get("class", "")
    new_classes = (existing_classes + " form-input").strip()
    attrs["class"] = new_classes
    
    # Add extra attributes if provided
    if extra_attrs:
        try:
            key, value = extra_attrs.split(":", 1)
            attrs[key] = value
        except ValueError:
            pass  # Ignore malformed attributes
    
    return field.as_widget(attrs=attrs)

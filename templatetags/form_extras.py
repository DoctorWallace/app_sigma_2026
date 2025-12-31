from django import template

register = template.Library()

@register.filter(name="add_class")
def add_class(field, css_class):
    """
    Uso: {{ form.username|add_class:"form-input otra-clase" }}
    Añade clases CSS al widget manteniendo las existentes.
    """
    existing = field.field.widget.attrs.get("class", "")
    new_classes = (existing + " " + str(css_class)).strip()
    attrs = {**field.field.widget.attrs, "class": new_classes}
    return field.as_widget(attrs=attrs)

@register.filter(name="add_attr")
def add_attr(field, arg):
    """
    Uso: {{ form.username|add_attr:"placeholder:Usuario" }}
         {{ form.password|add_attr:"autocomplete:current-password" }}
    Formato: "atributo:valor"
    """
    try:
        key, value = str(arg).split(":", 1)
    except ValueError:
        return field
    attrs = {**field.field.widget.attrs, key: value}
    return field.as_widget(attrs=attrs)

@register.filter
def has_group(user, group_name: str):
    return user.is_authenticated and user.groups.filter(name__iexact=group_name).exists()

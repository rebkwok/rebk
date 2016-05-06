from django import template

register = template.Library()


@register.filter
def format_field_name(field):
    return field.replace('_', ' ').title()


from django import template

register = template.Library()

@register.filter
def add_class(value, arg):
    """Thêm class vào một trường form"""
    return value.as_widget(attrs={"class": arg})
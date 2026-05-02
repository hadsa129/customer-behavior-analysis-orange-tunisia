from django import template

register = template.Library()

@register.filter
def dictget(value, key):
    """
    Template filter to get a dictionary value by key, handling spaces and quotes.
    Usage: {{ my_dict|dictget:"'key with spaces'" }}
    """
    if not isinstance(value, dict):
        return ""
    
    # Remove surrounding quotes if they exist
    if (key.startswith("'") and key.endswith("'")) or (key.startswith('"') and key.endswith('"')):
        key = key[1:-1]
    
    return value.get(key, "")


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')
# dans templatetags/custom_filters.py

@register.filter
def div_by(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0
@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, '')
# marketing_dashboard/templatetags/custom_filters.py
import datetime
def dictgets(d, key):
    if not d or not isinstance(d, dict):
        return 0
    return d.get(str(key), 0)

@register.filter
def to_date(value):
    import datetime
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None

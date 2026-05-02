from django import template
import json
from decimal import Decimal

register = template.Library()

@register.filter
def get_chart_color(index, offset=0):
    colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD', 
        '#D4A5A5', '#9B97B2', '#E8A87C', '#C38D9E', '#85DCB',
        '#E8A87C', '#C38D9E', '#41B3A3', '#E27D60', '#85DCB'
    ]
    return colors[(index + offset) % len(colors)]

@register.filter(name='to_json')
def to_json(value):
    """Convertit une valeur Python en JSON en gérant les types spécifiques comme Decimal"""
    def default_encoder(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
    
    return json.dumps(value, default=default_encoder)

@register.filter(name='to_js_array')
def to_js_array(value):
    """Convertit une liste Python en tableau JavaScript en gérant les types numériques"""
    if not value:
        return '[]'
    
    def convert_value(item):
        if isinstance(item, (Decimal, float, int)):
            return float(item)
        return str(item)
    
    # Si c'est un dictionnaire, on convertit les valeurs
    if isinstance(value, dict):
        return json.dumps({k: convert_value(v) for k, v in value.items()}, default=str)
    
    # Si c'est une liste ou un itérable, on convertit chaque élément
    try:
        return json.dumps([convert_value(item) for item in value], default=str)
    except (TypeError, ValueError):
        return json.dumps(list(value), default=str)
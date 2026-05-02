# marketing_dashboard/templatetags/custom_filters.py
import datetime
import locale
import statistics
from decimal import Decimal, InvalidOperation
from typing import List, Union, Any, Dict

from django import template
from django.utils.safestring import mark_safe

# Configurer locale pour le formatage
try:
    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
except locale.Error:
    pass  # éviter crash si locale indisponible

register = template.Library()

# ------------------ Filtres ------------------ #

@register.filter(name='divisible_by')
def divisible_by(value, arg):
    try:
        return int(value) % int(arg) == 0
    except (ValueError, ZeroDivisionError, TypeError):
        return False


@register.filter(name='dictget')
def dictget(value, key):
    """Accéder à une valeur d’un dict avec clé dynamique."""
    if not isinstance(value, dict):
        return 0
    return value.get(str(key), 0)


@register.filter(name='trim')
def trim(value):
    return str(value).strip()


@register.filter(name='percentage')
def percentage(value, total):
    try:
        value, total = float(value), float(total)
        return (value / total) * 100 if total else 0
    except (ValueError, TypeError):
        return 0


@register.filter(name='is_list')
def is_list(value):
    return isinstance(value, (list, tuple, set))


@register.filter(name='div')
def div(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


@register.filter(name='div_by')
def div_by(value, arg):
    return div(value, arg)


@register.filter(name='mul')
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter(name='intcomma')
def intcomma(value):
    try:
        return locale.format_string("%d", int(float(value)), grouping=True)
    except (ValueError, TypeError):
        return value


@register.filter(name='abs')
def abs_value(value):
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value


@register.filter(name='sub')
def sub(value, arg):
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (ValueError, TypeError, InvalidOperation):
        return 0


@register.filter(name='get_color')
def get_color(index):
    colors = [
        '#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f',
        '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac'
    ]
    return colors[int(index) % len(colors)]


@register.filter(name='get_item')
def get_item(dictionary, key):
    if not isinstance(dictionary, dict):
        return ""
    return dictionary.get(key, "")


@register.filter(name='median')
def median(value):
    try:
        numbers = [float(x) for x in value if x not in [None, ""]]
        return statistics.median(numbers) if numbers else 0
    except Exception:
        return 0


@register.filter(name='get_dominant_key')
def get_dominant_key(d: Dict[Any, Any]) -> Any:
    if not d or not isinstance(d, dict):
        return None
    try:
        return max(d.items(), key=lambda x: float(x[1] or "-inf"))[0]
    except Exception:
        return max(d.items(), key=lambda x: str(x[1]))[0] if d else None


@register.filter(name='max')
def max_value(value: Union[List[Any], Any]) -> Any:
    if not isinstance(value, (list, tuple, set)) or not value:
        return value
    try:
        return max(v for v in value if v is not None)
    except Exception:
        return value


@register.filter(name='format_segment_id')
def format_segment_id(value, format_as_badges=False):
    if not value:
        return ""

    term_mapping = {
        'type': 'Type', 'segment': 'Segment',
        'acquisition': 'Acquisition', 'fidelisation': 'Fidélisation',
        'retention': 'Rétention', 'prospection': 'Prospection',
        'rentabilite': 'Rentabilité', 'rentable': 'Rentable',
        'non_rentable': 'Non Rentable', 'haut_rentable': 'Haut Rentable',
        'moyen_rentable': 'Moyennement Rentable', 'bas_rentable': 'Peu Rentable',
        'engagement': 'Engagement', 'tres_engage': 'Très Engagé',
        'moyen_engage': 'Moyennement Engagé', 'peu_engage': 'Peu Engagé',
        'non_engage': 'Non Engagé'
    }

    parts = []
    for part in str(value).split('_'):
        parts.append(term_mapping.get(part, part.capitalize()))

    if format_as_badges:
        badge_classes = [
            'bg-blue-100 text-blue-800',
            'bg-green-100 text-green-800',
            'bg-purple-100 text-purple-800',
            'bg-yellow-100 text-yellow-800',
            'bg-indigo-100 text-indigo-800',
            'bg-pink-100 text-pink-800',
            'bg-gray-100 text-gray-800'
        ]
        badges = [
            f'<span class="px-2 py-1 text-xs font-medium rounded-full {badge_classes[i % len(badge_classes)]}">{p}</span>'
            for i, p in enumerate(parts)
        ]
        return mark_safe(" ".join(badges))

    return " ".join(parts)


@register.filter(name='to_date')
def to_date(value):
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None

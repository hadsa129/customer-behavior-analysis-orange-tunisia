from django import template

register = template.Library()

@register.filter
def action_type_color(action_type):
    """Retourne une couleur en fonction du type d'action"""
    colors = {
        'login': '#28a745',
        'logout': '#dc3545',
        'register': '#007bff',
        'analyse': '#17a2b8',
        'segmentation': '#6f42c1',
        'rapport': '#fd7e14',
        'upload': '#6c757d',
        'update': '#ffc107',
        'delete': '#dc3545',
        'create': '#28a745',
    }
    return colors.get(action_type.lower(), '#6c757d')

@register.filter
def action_type_icon(action_type):
    """Retourne une icône Font Awesome en fonction du type d'action"""
    icons = {
        'login': 'fas fa-sign-in-alt',
        'logout': 'fas fa-sign-out-alt',
        'register': 'fas fa-user-plus',
        'analyse': 'fas fa-chart-bar',
        'segmentation': 'fas fa-object-group',
        'rapport': 'fas fa-file-alt',
        'upload': 'fas fa-upload',
        'update': 'fas fa-edit',
        'delete': 'fas fa-trash-alt',
        'create': 'fas fa-plus-circle',
    }
    return icons.get(action_type.lower(), 'fas fa-circle')

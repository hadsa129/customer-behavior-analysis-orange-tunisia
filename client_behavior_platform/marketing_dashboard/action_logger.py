from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ActionLog

def log_action(request, action_type, description, target_type=None, target_id=None, user=None):
    """
    Enregistre une action dans le journal
    """
    if not user and hasattr(request, 'user') and request.user.is_authenticated:
        user = request.user
    
    ip_address = None
    user_agent = None
    
    if hasattr(request, 'META'):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT')
    
    ActionLog.objects.create(
        user=user,
        action_type=action_type,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        target_type=target_type,
        target_id=target_id
    )
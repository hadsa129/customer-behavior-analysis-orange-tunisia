# marketing_dashboard/signals.py
from django.contrib.auth import user_logged_in, user_logged_out
from django.dispatch import receiver
from .action_logger import log_action
from django.utils import timezone

@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    log_action(
        request=request,
        action_type='LOGIN',
        description=f"Connexion de l'utilisateur {user.username}",
        target_type='user',
        target_id=user.id,
        user=user
    )

@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    log_action(
        request=request,
        action_type='LOGOUT',
        description=f"Déconnexion de l'utilisateur {user.username if user else 'inconnu'}",
        target_type='user',
        target_id=user.id if user else None,
        user=user
    )
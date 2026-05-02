from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class ActionLog(models.Model):
    ACTION_TYPES = [
        ('LOGIN', 'Connexion'),
        ('LOGOUT', 'Déconnexion'),
        ('ANALYSE', 'Analyse client'),
        ('SEGMENTATION', 'Segmentation'),
        ('RAPPORT', 'Génération de rapport'),
        ('UPLOAD', 'Téléchargement de fichier'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    target_type = models.CharField(max_length=100, null=True, blank=True)
    target_id = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Journal des actions'
        verbose_name_plural = 'Journal des actions'
    
    def __str__(self):
        return f"{self.get_action_type_display()} - {self.user} - {self.created_at}"
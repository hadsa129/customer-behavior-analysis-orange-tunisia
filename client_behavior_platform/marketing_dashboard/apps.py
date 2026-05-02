# marketing_dashboard/apps.py
from django.apps import AppConfig

class MarketingDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketing_dashboard'

    def ready(self):
        # Importez les signaux pour qu'ils soient enregistrés
        import marketing_dashboard.signals
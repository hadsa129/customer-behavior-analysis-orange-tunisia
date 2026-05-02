from django.urls import path, include
from . import views
from users.views import user_logout  # Ajoutez cette ligne

app_name = 'marketing_dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('analyse_client/', views.formulaire_client, name='formulaire_client'),
    path('analyse_client/rapport/', views.vue_rapport_client, name='vue_rapport_client'),
    path('analyse_client/comportement/', views.vue_comportement_client, name='vue_comportement_client'),
    path('analyse_client/recommandation/', views.vue_recommandation_client, name='vue_recommandation_client'),
    path('analyse_client/messages/', views.vue_messages_marketing, name='vue_messages_marketing'),
    path('analyse_segment/', views.vue_filtres_segment, name='vue_filtres_segment'),
    path('analyse_segment/kpi_clients/', views.vue_kpi_clients_segment, name='vue_kpi_clients_segment'),
    path('analyse_segment/rapport/', views.vue_rapport_segment, name='vue_rapport_segment'),
    path('analyse_segment/recommandations/', views.vue_recommandations_segment, name='vue_recommandations_segment'),
    path('analyse_segment/messages/', views.vue_messages_segment, name='vue_messages_segment'),
    path('segmenter/', views.vue_segmenter, name='vue_segmenter'),
    path('segmenter/resultats/', views.vue_resultats_segmenter, name='vue_resultats_segmenter'),
    path('churn-analysis/resultat/', views.vue_analyser_churn, name='vue_analyser_churn'),
    path('churn-analysis/', views.traiter_analyse_churn, name='traiter_analyse_churn'),
    path('tables/', views.vue_tables, name='vue_tables'),
    path('catalogue-maxit/', views.vue_catalogue_maxit, name='catalogue_maxit'),
    path('historique-campagnes/', views.historique_campagnes, name='historique_campagnes'),
    path('signout/', user_logout, name='signout'),
    path('profile/', views.profile_view, name='profile'),
]

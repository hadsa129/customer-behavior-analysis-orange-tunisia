import os
import json
import pandas as pd
from datetime import datetime, date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from .action_logger import log_action
# Add this at the top with other imports
import glob
import logging
from datetime import datetime
import os
class CustomJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, 'isoformat'):  # Handles pandas Timestamp
            return obj.isoformat()
        return super().default(obj)
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
from typing import Tuple

# Dossier pour stocker les fichiers CSV des segments
SEGMENT_CSV_DIR = os.path.join(settings.MEDIA_ROOT, 'segment_csvs')
os.makedirs(SEGMENT_CSV_DIR, exist_ok=True)

@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = CustomUserCreationForm(instance=user)

    context = {
        'form': form,
    }
    return render(request, 'marketing_dashboard/profile.html', context)

def convert_date_format(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        return None



import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.conf import settings
from django.shortcuts import render
import json

# Constants
DATA_DIR = os.path.join(settings.BASE_DIR, '..', 'data')
import os
import glob
import pandas as pd
from datetime import datetime, timedelta
from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)

# Chemin vers le dossier des données
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def load_historical_data(months=3):
    """Charge toutes les données historiques disponibles"""
    import glob
    
    logger = logging.getLogger(__name__)
    historical_data = {}
    loaded_months = 0
    
    # Chercher tous les fichiers de données clients
    client_files = glob.glob(os.path.join(DATA_DIR, "df_client_info_*.csv"))
    
    for client_file in client_files:
        try:
            # Extraire le mois et l'année du nom de fichier
            filename = os.path.basename(client_file)
            month_part = filename.replace("df_client_info_", "").replace(".csv", "")
            month_num, year = month_part.split('_')
            
            # Créer la clé de mois (YYYY-MM)
            month_key = f"{year}-{month_num.zfill(2)}"
            
            # Vérifier si le fichier de segmentation correspondant existe
            seg_file = os.path.join(DATA_DIR, f"df_segmentation_mois_{month_num}_{year}.csv")
            if not os.path.exists(seg_file):
                logger.warning(f"Fichier de segmentation manquant pour le mois {month_key}")
                continue
            
            # Charger les données
            client_df = pd.read_csv(client_file)
            seg_df = pd.read_csv(seg_file)
            churn_file = os.path.join(DATA_DIR, 'churn_par_client_par_mois.csv')
            churn_data = pd.read_csv(churn_file)
            
            # Vérifier les données de base
            if client_df.empty or seg_df.empty:
                logger.warning(f"Données vides pour le mois {month_key}")
                continue
                
            # Stocker les données
            historical_data[month_key] = {
                'client': client_df,
                'segmentation': seg_df,
                'churn': churn_data
            }
            loaded_months += 1
            logger.info(f"Données chargées pour {month_key}")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données pour {client_file}: {str(e)}")
            continue
    
    if not historical_data:
        logger.error("Aucune donnée historique n'a pu être chargée.")
    else:
        logger.info(f"Chargement terminé. {loaded_months} mois de données chargés avec succès.")
    
    return historical_data

def calculate_kpis(client_df,churn, month):
    """Calcule les KPIs pour un mois donné"""
    total_clients = len(client_df)
    active_clients = client_df['est_utilisateur_actif'].sum()
    active_rate = (active_clients / total_clients) * 100 if total_clients > 0 else 0
    
    # Clients rentables
    profitable_clients = client_df[client_df['rentabilite'] == 'actif'].shape[0]
    profitable_pct = (profitable_clients / total_clients) * 100 if total_clients > 0 else 0
    
    # Données de consommation moyennes
    avg_data = client_df['consommation_totale_Mo'].mean()
    avg_voice = client_df.get('voice_usage', 0).mean() if 'voice_usage' in client_df.columns else 0
    avg_sms = client_df.get('sms_usage', 0).mean() if 'sms_usage' in client_df.columns else 0
    
    # Taux de churn
    
    churn['month'] = churn['month'].astype(str).str[:7]  # Garde uniquement YYYY-MM
    monthly_churn = churn[churn['month'] == month]
        
    if not monthly_churn.empty:
            churned_count = (monthly_churn['churn'] == 1).sum()
            churn_rate = round((churned_count / len(monthly_churn)) * 100,2)
            logger.info(f"Churn pour {month}: {churned_count}/{len(monthly_churn)} = {churn_rate:.2f}%")
    else:
            churn_rate = 0
            logger.warning(f"Aucune donnée de churn trouvée pour {month}")



    
    # Nombre de campagnes (à remplacer par les données réelles)
    campaign_count = 0  # À implémenter avec les données de campagne
    
    return {
        'month': month,
        'total_clients': total_clients,
        'active_clients': active_clients,
        'active_rate': active_rate,
        'profitable_clients': profitable_clients,
        'profitable_pct': profitable_pct,
        'churn_rate': churn_rate,
        'avg_data': avg_data,
        'avg_voice': avg_voice,
        'avg_sms': avg_sms,
        'campaign_count': campaign_count,
        'total_purchase': (client_df['montant_total_achat'].sum())/1000,
        'total_recharge': (client_df['montant_total_recharge'].sum())/1000,
        'purchase_count': client_df['nb_achat'].sum(),
        'recharge_count': client_df['nb_recharge'].sum(),
        'avg_revenue': client_df['montant_total_achat'].mean()
    }

def get_segmentation_data(seg_df):
    """Prépare les données de segmentation pour les graphiques"""
    return {
        'engagement': seg_df['segment_engagement'].value_counts(normalize=True).mul(100).round(1).to_dict(),
        'client_type': seg_df['segment_type_client'].value_counts(normalize=True).mul(100).round(1).to_dict(),
        'profitability': seg_df['segment_rentabilité'].value_counts(normalize=True).mul(100).round(1).to_dict(),
        'interest': seg_df['segment_type_interet'].value_counts(normalize=True).mul(100).round(1).to_dict()
    }

def get_trends(historical_kpis):
    """Calcule les tendances sur les KPIs"""
    if len(historical_kpis) < 2:
        return {}
    
    # Trier par mois
    sorted_kpis = sorted(historical_kpis.values(), key=lambda x: x['month'])
    current = sorted_kpis[-1]
    previous = sorted_kpis[-2]
    
    def calculate_change(current_val, previous_val):
        if previous_val == 0:
            return 0
        return ((current_val - previous_val) / previous_val) * 100
    
    return {
        'clients_actifs': calculate_change(current['active_clients'], previous['active_clients']),
        'taux_rentabilite': current['profitable_pct'] - previous['profitable_pct'],
        'taux_churn': current['churn_rate'] - previous['churn_rate'],
        'consommation_data': calculate_change(current['avg_data'], previous['avg_data']),
        'voix_moyenne': calculate_change(current['avg_voice'], previous['avg_voice']),
        'sms_moyens': calculate_change(current['avg_sms'], previous['avg_sms']),
        'total_achats': calculate_change(current['total_purchase'], previous['total_purchase']),
        'total_recharges': calculate_change(current['total_recharge'], previous['total_recharge']),
        'revenue_moyen': calculate_change(current['avg_revenue'], previous['avg_revenue'])
    }

def dashboard_home(request):
    try:
        # Charger les données historiques des 3 derniers mois
        historical_data = load_historical_data(months=3)
        if not historical_data:
            raise ValueError("Aucune donnée historique trouvée")
        
        # Récupérer le mois le plus récent
        latest_month = max(historical_data.keys())
        current_data = historical_data[latest_month]
        
        # Calculer les KPIs pour chaque mois
        historical_kpis = {}
        for month, data in historical_data.items():
            historical_kpis[month] = calculate_kpis(data['client'],data['churn'], month)
        
        # Calculer les tendances
        trends = get_trends(historical_kpis)
        
        # Préparer les données pour les graphiques
        segmentation_data = get_segmentation_data(current_data['segmentation'])
        
        # Préparer les données pour le graphique d'évolution temporelle
        timeline_data = {
            'months': [],
            'active_clients': [],
            'profitable_pct': [],
            'churn_rate': [],
            'total_purchase': [],
            'total_recharge': []
        }
        
        # Dans la vue, modifier la boucle for qui prépare timeline_data :
        for month in sorted(historical_kpis.keys()):
            kpi = historical_kpis[month]
            timeline_data['months'].append(month)
            timeline_data['active_clients'].append(float(kpi['active_clients']))
            timeline_data['profitable_pct'].append(float(kpi['profitable_pct']))
            timeline_data['churn_rate'].append(float(kpi['churn_rate']))
            timeline_data['total_purchase'].append(float(kpi['total_purchase']))  # Conversion en float
            timeline_data['total_recharge'].append(float(kpi['total_recharge']))  # Conversion en float
                
        # Préparer le contexte
        current_kpi = historical_kpis[latest_month]
        
        # Ajout de logs de débogage
        logger.info("=== DÉBOGAGE DONNÉES TRANSACTIONS ===")
        logger.info(f"Mois disponibles: {sorted(historical_kpis.keys())}")
        
        for month_key, kpi_data in historical_kpis.items():
            logger.info(f"\nMois: {month_key}")
            logger.info(f"Total achat: {kpi_data['total_purchase']} (type: {type(kpi_data['total_purchase'])})")
            logger.info(f"Total recharge: {kpi_data['total_recharge']} (type: {type(kpi_data['total_recharge'])})")
            logger.info(f"Données brutes: {kpi_data}")
        
        logger.info("\nDonnées timeline:")
        logger.info(f"Mois: {timeline_data['months']}")
        logger.info(f"Achats: {timeline_data['total_purchase']}")
        logger.info(f"Recharges: {timeline_data['total_recharge']}")
        
        context = {
            # Données générales
            'month': latest_month,
            'last_update': datetime.now().strftime('%d/%m/%Y %H:%M'),
            
            # KPIs principaux
            'total_clients': current_kpi['total_clients'],
            'active_clients': current_kpi['active_clients'],
            'active_rate': current_kpi['active_rate'],
            'profitable_clients': current_kpi['profitable_clients'],
            'profitable_pct': current_kpi['profitable_pct'],
            'churn_rate': current_kpi['churn_rate'],
            'campaign_count': current_kpi['campaign_count'],
            
            # Consommations moyennes
            'avg_data': current_kpi['avg_data'],
            'avg_voice': current_kpi['avg_voice'],
            'avg_sms': current_kpi['avg_sms'],
            
            # Transactions
            'total_purchase': current_kpi['total_purchase'],
            'total_recharge': current_kpi['total_recharge'],
            'purchase_count': current_kpi['purchase_count'],
            'recharge_count': current_kpi['recharge_count'],
            'avg_basket': (current_kpi['total_purchase'] / current_kpi['purchase_count']) if current_kpi['purchase_count'] > 0 else 0,
            'avg_recharge': (current_kpi['total_recharge'] / current_kpi['recharge_count']) if current_kpi['recharge_count'] > 0 else 0,
            
            # Tendance
            'kpi_evolution': trends,
            
            # Données pour graphiques
            'engagement_data': segmentation_data['engagement'],
            'client_type_data': segmentation_data['client_type'],
            'profitability_data': segmentation_data['profitability'],
            'interest_data': segmentation_data['interest'],
            
            # Données pour graphique d'évolution
            'timeline_data': json.loads(json.dumps(timeline_data, default=str))

        }
        
        
        # Vérification finale des données avant envoi au template
        logger.info("\n=== DONNÉES ENVOYÉES AU TEMPLATE ===")
        logger.info(f"Timeline data: {json.dumps(timeline_data, default=str, indent=2)}")
        
        return render(request, 'marketing_dashboard/dashboard_home.html', context)
        
    except Exception as e:
        import traceback
        print(f"Erreur dans dashboard_produits: {str(e)}")
        traceback.print_exc()
        return render(request, 'marketing_dashboard/dashboard_home.html', {
            'error': str(e),
            'data_loaded': False
        })
from django.shortcuts import redirect
from .action_logger import log_action


from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import AnalyseClientForm
from datetime import datetime
import pandas as pd
import os


# Page 1 : Formulaire d'entrée
import os
import json
import pandas as pd
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

# Configuration
import os
CATALOGUE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalogue.csv")
FOLDER_CLIENT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Page 1 : Formulaire d'entrée
@login_required
def formulaire_client(request):
    print("\n=== FORMULAIRE CLIENT ===")
    print(f"Méthode: {request.method}")
    print(f"Session ID: {request.session.session_key}")
    
    if request.method == 'POST':
        form = AnalyseClientForm(request.POST)
        if form.is_valid():
            # Nettoyage des données
            msisdn = form.cleaned_data['msisdn']
            date_debut = form.cleaned_data['date_debut'].strftime('%Y-%m-%d')
            date_fin = form.cleaned_data['date_fin'].strftime('%Y-%m-%d')
            
            print(f"Données du formulaire - MSISDN: {msisdn}, Période: {date_debut} à {date_fin}")
            
            # Enregistrement en session
            request.session['msisdn'] = msisdn
            request.session['date_debut'] = date_debut
            request.session['date_fin'] = date_fin
            request.session.modified = True
            
            
            print("Session après enregistrement:", {
                'msisdn': request.session.get('msisdn'),
                'date_debut': request.session.get('date_debut'),
                'date_fin': request.session.get('date_fin')
            })
            log_action(
                request=request,
                action_type='ANALYSE',
                description=f"Analyse du client {msisdn} (période: {date_debut} au {date_fin})",
                target_type='client',
                target_id=msisdn
            )
            # Redirection selon le bouton cliqué
            if 'rapport' in request.POST:
                print("Redirection vers le rapport...")
                return redirect('marketing_dashboard:vue_rapport_client')
            elif 'recommandation' in request.POST:
                return redirect('marketing_dashboard:vue_recommandation_client')
            elif 'messages' in request.POST:
                return redirect('marketing_dashboard:vue_messages_marketing')
    else:
        form = AnalyseClientForm()
    
    return render(request, 'marketing_dashboard/formulaire.html', {'form': form})

from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
import json
import os
from collections import Counter



import re  # Ajout de l'import manquant
def parse_rapport(rapport_texte):
    """
    Parse le texte complet du rapport marketing en un dictionnaire structuré
    """
    rapport = {}
    lignes = rapport_texte.split('\n')
    section = None
    
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne:
            continue
            
        # Extraction de l'ID client et période
        if '**Rapport Marketing - Client' in ligne:
            rapport['titre'] = ligne.strip('*').strip()
            rapport['client_id'] = ligne.split('Client')[-1].strip()
        elif '**Période analysée** :' in ligne:
            rapport['periode_analyse'] = ligne.split(':', 1)[1].strip()
            
        # Extraction des informations de base
        elif '**Type de client** :' in ligne:
            rapport['type_client'] = ligne.split(':', 1)[1].strip()
        elif '**Profil MaxIt** :' in ligne:
            rapport['profil_maxit'] = ligne.split(':', 1)[1].strip()
        elif '**Statut Churn** :' in ligne:
            rapport['statut_churn'] = ligne.split(':', 1)[1].strip()
        elif '**Niveau d\'engagement** :' in ligne:
            parts = ligne.split(':', 1)[1].strip().split('(')
            rapport['niveau_engagement'] = parts[0].strip()
            if len(parts) > 1:
                try:
                    rapport['score_engagement'] = int(parts[1].replace('pts)', '').strip())
                except ValueError:
                    rapport['score_engagement'] = None
        elif '**Rentabilité** :' in ligne:
            rapport['rentabilite'] = ligne.split(':', 1)[1].strip()
        elif '**Action dominante** :' in ligne:
            parts = ligne.split('|')
            if len(parts) > 1:
                rapport['action_dominante'] = parts[0].split(':', 1)[1].strip()
                rapport['type_usage'] = parts[1].split(':', 1)[1].strip()
            
        # Gestion des sections
        if '**Comportements transactionnels**' in ligne:
            section = 'transactionnel'
        elif '**Utilisation de MaxIt**' in ligne:
            section = 'maxit'
        elif '**Consommation du client**' in ligne:
            section = 'consommation'
        elif '**Options achetées**' in ligne:
            section = 'options'
        elif '**Typologie des messages marketing**' in ligne:
            section = 'recommandations'
            
        # Extraction par section
        if section == 'transactionnel' and ligne.startswith('-'):
            if 'Nombre d\'achats :' in ligne:
                parts = ligne.split('|')
                if len(parts) > 1:
                    rapport['nb_achats'] = parts[0].split(':', 1)[1].strip()
                    # Extraire montant en valeur float si possible
                    montant_str = parts[1].split(':', 1)[1].strip().split()[0].replace(',', '').replace('mM', '')
                    try:
                        rapport['montant_achats'] = float(montant_str)
                    except:
                        rapport['montant_achats'] = montant_str
            elif 'Nombre de recharges :' in ligne:
                parts = ligne.split('|')
                if len(parts) > 1:
                    rapport['nb_recharges'] = parts[0].split(':', 1)[1].strip()
                    montant_str = parts[1].split(':', 1)[1].strip().split()[0].replace(',', '').replace('mM', '')
                    try:
                        rapport['montant_recharges'] = float(montant_str)
                    except:
                        rapport['montant_recharges'] = montant_str
            elif 'Nombre de participations aux jeux :' in ligne:
                rapport['participations_jeux'] = ligne.split(':', 1)[1].strip()
            elif 'Canal d\'achat dominant :' in ligne:
                rapport['canal_achat'] = ligne.split(':', 1)[1].strip()
            elif 'Canal de recharge dominant :' in ligne:
                rapport['canal_recharge'] = ligne.split(':', 1)[1].strip()
            elif 'Montant moyen par achat :' in ligne:
                montant_moyen_str = ligne.split(':', 1)[1].strip().split()[0].replace(',', '').replace('mM', '')
                try:
                    rapport['montant_moyen_achat'] = float(montant_moyen_str)
                except:
                    rapport['montant_moyen_achat'] = montant_moyen_str
                
        elif section == 'maxit' and ligne.startswith('-'):
            if 'Actions MaxIt :' in ligne:
                parts = ligne.split(':')[1].split('/')
                if len(parts) == 2:
                    rapport['actions_maxit'] = parts[0].strip()
                    total_parts = parts[1].split('(')
                    rapport['total_actions'] = total_parts[0].strip()
                    if len(total_parts) > 1:
                        pourcentage = total_parts[1].split('%')[0].strip()
                        rapport['pourcentage_maxit'] = f"{pourcentage}%"
            elif ligne.startswith('- ') and not ligne.startswith('- **'):
                statut = ligne.strip('- ').strip()
                # Supprimer les émojis et la mise en forme Markdown
                statut = re.sub(r'[^\w\s:]', '', statut)  # Garde uniquement lettres, chiffres, espaces et deux-points
                statut = statut.replace('  ', ' ').strip()
                  # Nettoyer les espaces multiples
                rapport['statut_maxit'] = statut
            elif 'Dernière action MaxIt :' in ligne:
                rapport['derniere_action_maxit'] = ligne.split(':', 1)[1].strip()
                
        elif section == 'consommation' and ligne.startswith('-'):
            if 'Données consommées :' in ligne:
                val = ligne.split(':', 1)[1].replace('Mo', '').strip()
                try:
                    rapport['donnees_consommees'] = float(val)
                except:
                    rapport['donnees_consommees'] = val
            elif 'Voix utilisée :' in ligne:
                val = ligne.split(':', 1)[1].replace('minutes', '').strip()
                try:
                    rapport['voix_utilisee'] = float(val)
                except:
                    rapport['voix_utilisee'] = val
            elif 'SMS :' in ligne:
                val = ligne.split(':', 1)[1].replace('messages', '').strip()
                try:
                    rapport['sms'] = int(val)
                except:
                    rapport['sms'] = val
                
        elif section == 'options' and ligne.startswith('- Option'):
            if 'options_achetees' not in rapport:
                rapport['options_achetees'] = []
            
            # Séparer le nom et la quantité
            parts = ligne.replace('- Option', '').split(':')
            if len(parts) == 2:
                nom_option = parts[0].strip()
                try:
                    quantite = int(parts[1].replace('fois', '').strip())
                except:
                    quantite = parts[1].strip()
                
                # Cas spécial pour "internet bil milli"
                if nom_option.lower() == 'internet bil milli':
                    quantite = quantite  # ou ce que tu veux comme valeur spéciale
                    # tu peux aussi ajouter un flag supplémentaire si nécessaire
                    # par exemple: option_flag = True

                option = {
                    'nom': nom_option,
                    'quantite': quantite
                }
                rapport['options_achetees'].append(option)

        # Ajouter cette variable au début de la fonction
        dernieres_transactions = []

        # Ajouter cette condition dans la boucle principale, avec les autres sections
        if '**Dernières transactions (3 derniers jours)**' in ligne:
            section = 'dernieres_transactions'
            continue

        # Ajouter ce bloc après les autres sections (consommation, options, etc.)
        elif section == 'dernieres_transactions' and ligne.startswith('- '):
            if 'Aucune transaction récente' not in ligne:
                # Extraire les informations de la transaction
                transaction = {}
                parts = ligne.split(':', 1)
                if len(parts) == 2:
                    # Nettoyer et extraire le type de transaction
                    type_part = parts[0].strip()
                    if '🛍️' in type_part:
                        transaction['type'] = 'Achat'
                        # Extraire la description pour les achats
                        desc_part = parts[1].strip().split('-', 1)
                        if len(desc_part) == 2:
                            transaction['description'] = desc_part[0].strip()
                            montant_date = desc_part[1].split('(')
                            if len(montant_date) == 2:
                                transaction['montant'] = montant_date[0].replace('mM', '').strip()
                                transaction['date'] = montant_date[1].replace(')', '').strip()
                    else:  # Recharge
                        transaction['type'] = 'Recharge'
                        montant_date = parts[1].split('(')
                        if len(montant_date) == 2:
                            transaction['montant'] = montant_date[0].replace('mM', '').strip()
                            transaction['date'] = montant_date[1].replace(')', '').strip()
                    
                    if transaction:  # Si on a pu extraire des données
                        dernieres_transactions.append(transaction)

        # À la fin de la fonction, avant le return
        if dernieres_transactions:
            rapport['dernieres_transactions'] = dernieres_transactions        
        elif section == 'recommandations' and ligne.startswith('- '):
            if 'recommandations' not in rapport:
                rapport['recommandations'] = []
            # Nettoyer la ligne pour enlever les émojis et le formatage
            reco = ligne.split('**')[-1].strip('*: -')
            if reco and reco not in rapport['recommandations']:
                rapport['recommandations'].append(reco)
    
    # Calculer des métriques supplémentaires
    if 'score_engagement' in rapport and rapport['score_engagement'] is not None:
        score = rapport.get('score_engagement')
        rapport['classe_engagement'] = 'high' if score > 250 else 'medium' if score > 150 else 'low'
    
    if 'rentabilite' in rapport:
        rapport['rentabilite_classe'] = 'high' if 'élevé' in rapport['rentabilite'].lower() else 'medium' if 'moyen' in rapport['rentabilite'].lower() else 'low'
    
    return rapport


def enrichir_avec_json(rapport, json_client):
    """
    Enrichit le rapport avec des données supplémentaires du JSON client
    """
    from datetime import datetime
    from collections import Counter

    # 1. Informations client détaillées
    client_info = json_client.get("client_info", {})
    
    montant_total_achat = float(client_info.get('montant_total_achat', 0) or 0)
    montant_total_recharge = float(client_info.get('montant_total_recharge', 0) or 0)
    
    score_rentabilite = montant_total_achat + montant_total_recharge
    segment=json_client.get("segmentation",{})
    rentabilite_classe=segment.get("segment_rentabilité","Inconnu")
    
    rapport.update({
        'type_client': client_info.get('type_client', 'Inconnu'),
        'est_maxit': client_info.get('est_maxit', False),
        'engagement_score': client_info.get('engagement_score', 0),
        'engagement_level': client_info.get('engagement_level', 'Inconnu'),
        'nb_recharge': client_info.get('nb_recharge', 0),
        'nb_achat': client_info.get('nb_achat', 0),
        'nombre_jeu': client_info.get('nombre_jeu', 0),
        'montant_total_achat': montant_total_achat,
        'montant_total_recharge': montant_total_recharge,
        'rentabilite_classe': rentabilite_classe,
        'segment_rentabilite': client_info.get('segment_rentabilite', 'Standard'),
        'moyenne_achats':montant_total_achat/client_info.get('nb_achat', 1)
    })
    nb_achat = client_info.get('nb_achat', 0)
    nb_recharge = client_info.get('nb_recharge', 0)
    rapport.update({
        'action_dominante':'achat' if nb_achat > nb_recharge else 'recharge'
    })

    # 2. Analyse des achats
    achats = json_client.get("achats", {})
    if achats:
        montants_achats = [float(a.get('prix', 0)) for a in achats.values() if a and a.get('prix') is not None]
        dates_achats = []
        for a in achats.values():
            try:
                if a and a.get('event_date'):
                    date_achat = datetime.strptime(a['event_date'], '%Y-%m-%d %H:%M:%S')
                    dates_achats.append(date_achat)
            except (ValueError, TypeError):
                continue
        
        descriptions = [a.get('description', 'Inconnu') for a in achats.values() if a]
        type_achat_counter = Counter(descriptions)
        achat_plus_frequent = type_achat_counter.most_common(1)[0][0] if type_achat_counter else "Aucun achat"

        rapport.update({
            'total_achats': sum(montants_achats),
            'moyenne_achat': sum(montants_achats) / len(montants_achats) if montants_achats else 0,
            'dernier_achat': max(dates_achats).strftime('%Y-%m-%d') if dates_achats else "Jamais",
            'premier_achat': min(dates_achats).strftime('%Y-%m-%d') if dates_achats else "Jamais",
            'type_achat_plus_frequent': achat_plus_frequent,
            'nb_types_achats_differents': len(type_achat_counter)
        })

    # 3. Analyse des recharges
    recharges = json_client.get("recharges", {})
    if recharges:
        montants_recharge = [float(r.get('amount', 0)) for r in recharges.values() if r and r.get('amount') is not None]
        dates_recharge = []
        for r in recharges.values():
            try:
                if r and r.get('event_date'):
                    date_recharge = datetime.strptime(r['event_date'], '%Y-%m-%d %H:%M:%S')
                    dates_recharge.append(date_recharge)
            except (ValueError, TypeError):
                continue
        
        rapport.update({
            'total_recharges': sum(montants_recharge),
            'moyenne_recharge': sum(montants_recharge) / len(montants_recharge) if montants_recharge else 0,
            'derniere_recharge': max(dates_recharge).strftime('%Y-%m-%d') if dates_recharge else "Jamais",
            'premiere_recharge': min(dates_recharge).strftime('%Y-%m-%d') if dates_recharge else "Jamais",
            'nb_recharges': len(montants_recharge)
        })

    # 4. Segmentation et profil
    segmentation = json_client.get("segmentation", {})
    for key, value in segmentation.items():
        if key == 'segments':
            continue
        key = key.replace("segment_", "")
        rapport.update({ key: value })

    options = json_client.get('options', {})

    # Somme des volumes data
    total_data_mo = 0
    for o in options.values():
        # Vérifier si l'option contient 'data_volume'
        if 'data_volume' in o:
            total_data_mo += o['data_volume']
        # Cas spécial pour "internet bil milli"
        elif str(o.get('name', '')).lower() == 'internet bil milli':
            prix = abs(o.get('prix', 0))
            total_data_mo += prix // 90 * 20  # selon ta règle

    consommations = json_client.get("consommations", {})
    if consommations:
        rapport.update({
            'data_usage':total_data_mo ,
            'voice_usage': consommations.get('voice_usage', 0),
            'sms_usage': consommations.get('sms_usage', 0)
        })

    # 6. Recommandations basées sur l'analyse
    recommandations = []
    if rapport.get('est_maxit', False):
        recommandations.append("Client MaxIt - Proposer des offres premium")
    if rapport.get('churn') in ["Oui", "Churn"]:
        recommandations.append("Client à risque de désabonnement - Proposer des offres de fidélisation")
    if rapport.get('data_usage', 0) > 200000:  # > 200 Mo
        recommandations.append("Gros consommateur de données - Proposer des forfaits data plus importants")
    if recommandations:
        rapport['recommandations'] = recommandations
    

    return rapport


def generer_rapport_marketing_client(json_client):
    from datetime import datetime
    from collections import Counter
    
    client_info = json_client.get("client_info", {})
    segmentation = json_client.get("segmentation", {})
    
    achats = json_client.get("achats", {})
    recharges = json_client.get("recharges", {})
    consommations = json_client.get("consommations", {})
    periode = json_client.get("periode", {})
    
    # Extraction sécurisée et default
    client_id = json_client.get("client_id", "Inconnu")
    churn = json_client.get("churn", "Inconnu")
    profil_maxit = json_client.get("profil_maxit", False)
    type_programme = next(iter(achats.values()), {}).get("prgname", "Inconnu")
    
    date_debut = periode.get("date_debut", "Date inconnue")
    date_fin = periode.get("date_fin", "Date inconnue")
    
    rapport = f"📄 **Rapport Marketing - Client {client_id}**\n\n"
    rapport += f"🔹 **Période analysée** : du {date_debut} au {date_fin}\n"
    rapport += f"🔸 **Type de client** : {client_info.get('type_client', 'Inconnu')}\n"
    rapport += f"🔸 **Profil MaxIt** : {'Oui' if profil_maxit else 'Non'}\n"
    rapport += f"🔸 **Statut Churn** : {churn}\n"
    rapport += f"🔸 **Type de programme** : {type_programme}\n"
    
    rapport += f"🔸 **Niveau d'engagement** : {segmentation.get('segment_engagement', 'Inconnu')} "

    rapport += f"({client_info.get('engagement_score', 0)} pts)\n"
    rapport += f"🔸 **Rentabilité** : {segmentation.get('segment_rentabilité', 'Inconnue')}\n"
    rapport += f"🔸 **Type d'usage** : {client_info.get('type_usage', 'Inconnu')}\n\n"
    
    
    total_achats = len(achats)
    total_recharges = len(recharges)
    montant_total_achats = client_info.get('montant_total_achat', 0)
    montant_total_recharges = client_info.get('montant_total_recharge', 0)
    
    rapport += "📊 **Comportements transactionnels**\n"
    rapport += f"- Nombre d'achats : {total_achats} | Montant total : {montant_total_achats} mM\n"
    rapport += f"- Nombre de recharges : {total_recharges} | Montant total : {montant_total_recharges} mM\n"
    
    canaux_achat = [a.get("login") for a in achats.values() if a and "login" in a]
    canaux_recharge = [r.get("login") for r in recharges.values() if r and "login" in r]
    
    if canaux_achat:
        top_canal_achat = Counter(canaux_achat).most_common(1)[0]
        rapport += f"- Canal d'achat principal : {top_canal_achat[0]} ({top_canal_achat[1]} fois)\n"
    if canaux_recharge:
        top_canal_recharge = Counter(canaux_recharge).most_common(1)[0]
        rapport += f"- Canal de recharge principal : {top_canal_recharge[0]} ({top_canal_recharge[1]} fois)\n"
    
    rapport += "\n📶 **Consommation**\n"
    rapport += f"- Données consommées : {consommations.get('data_usage', 0)} Mo\n"
    rapport += f"- Appels : {consommations.get('voice_usage', 0)} minutes\n"
    rapport += f"- SMS : {consommations.get('sms_usage', 0)} messages\n"
    
    if achats:
        descriptions = [a.get("description") for a in achats.values() if a and "description" in a]
        if descriptions:
            achat_plus_frequent = Counter(descriptions).most_common(1)[0]
            rapport += f"\n🛒 **Offre la plus achetée** : {achat_plus_frequent[0]} ({achat_plus_frequent[1]} fois)\n"
    # Après la section "Offre la plus achetée", avant les recommandations
    rapport += "\n💳 **Dernières transactions (7 derniers jours)**\n"

    # Récupérer les transactions des 3 derniers jours
    from datetime import datetime, timedelta

    # Trier et filtrer les achats des 3 derniers jours
    achats_recents = sorted(
        [a for a in achats.values() if a and "event_date" in a 
        and datetime.strptime(a["event_date"].split()[0], "%Y-%m-%d") >= 
            datetime.strptime(date_fin, "%Y-%m-%d") - timedelta(days=7)],
        key=lambda x: x["event_date"],
        reverse=True
    )

    # Trier et filtrer les recharges des 3 derniers jours
    recharges_recents = sorted(
        [r for r in recharges.values() if r and "event_date" in r
        and datetime.strptime(r["event_date"].split()[0], "%Y-%m-%d") >= 
            datetime.strptime(date_fin, "%Y-%m-%d") - timedelta(days=3)],
        key=lambda x: x["event_date"],
        reverse=True
    )

    # Combiner et trier toutes les transactions
    toutes_transactions = []
    for a in achats_recents:
        a["type"] = "Achat"
        a["montant"] = a.get("prix", 0)
        toutes_transactions.append(a)
        
    for r in recharges_recents:
        r["type"] = "Recharge"
        r["montant"] = r.get("amount", 0)
        toutes_transactions.append(r)

    # Trier par date (du plus récent au plus ancien)
    toutes_transactions.sort(key=lambda x: x["event_date"], reverse=True)

    # Afficher les 3 plus récentes
    for i, t in enumerate(toutes_transactions[:3], 1):
        date = datetime.strptime(t["event_date"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        description = t.get("description", "Sans description")
        if t["type"] == "Achat":
            rapport += f"- 🛍️ {t['description']} : {description} - {t['montant']} mM ({date})\n"
        else:
            rapport += f"- 💰 {t['type']} : {t['montant']} mM ({date})\n"

    if not toutes_transactions:
        rapport += "- Aucune transaction récente\n"

    rapport += "\n💡 **Recommandations**\n"
    if profil_maxit:
        if churn == "Churn":
            rapport += "- 🚨 **Client MaxIt à risque** : Proposer des offres de fidélisation\n"
        else:
            rapport += "- ✅ **Client MaxIt fidèle** : Envisager des offres premium\n"
    else:
        rapport += "- 🎯 **Client non MaxIt** : Cibler avec des offres d'adhésion MaxIt\n"
    
    data_usage = consommations.get('data_usage', 0)
    if data_usage > 10000:  # Plus de 10 Go
        rapport += "- 📡 **Gros consommateur de données** : Proposer des forfaits data plus importants\n"
    elif data_usage < 1000:  # Moins de 1 Go
        rapport += "- 📱 **Petit consommateur de données** : Mettre en avant des forfaits voix/SMS\n"
    
    return rapport

from datetime import datetime
import json  # aussi pour json.dumps

@login_required
def vue_rapport_client(request):
    """Vue pour afficher le rapport marketing complet d'un client"""
    logger.info("Accès à la vue rapport client", extra={'user': request.user.username})
    
    try:
        # 1. Récupération des paramètres de session
        msisdn, date_debut, date_fin = get_params_session(request)
        
        if not all([msisdn, date_debut, date_fin]):
            error_msg = "Paramètres de session manquants ou invalides"
            logger.warning(error_msg, extra={
                'msisdn': msisdn,
                'date_debut': date_debut,
                'date_fin': date_fin
            })
            messages.error(request, "Session expirée. Veuillez saisir à nouveau les informations.")
            return redirect('marketing_dashboard:formulaire_client')

        logger.debug("Paramètres récupérés avec succès", extra={
            'msisdn': msisdn[:6] + '...',  # Masquage partiel pour la confidentialité
            'date_debut': date_debut,
            'date_fin': date_fin
        })

        # 2. Récupération des données client
        try:
            client_json, _, _ = filtrer_clients(msisdn, date_debut, date_fin, FOLDER_CLIENT)
            if not client_json:
                raise ValueError("Aucune donnée client trouvée")
        except Exception as e:
            logger.error("Erreur lors de la récupération des données client", exc_info=True)
            messages.error(request, "Impossible de récupérer les données du client")
            return redirect('marketing_dashboard:formulaire_client')

        # 3. Génération du rapport
        try:
            logger.debug("Début de génération du rapport")
            rapport_texte = generer_rapport_marketing_client(client_json)
            logger.debug("Rapport texte généré : %s", rapport_texte)
            rapport = parse_rapport(rapport_texte)
            logger.debug("Rapport parse généré : %s", rapport)
            rapport = enrichir_avec_json(rapport, client_json)
            logger.debug("Rapport enrichi généré : %s", rapport)
            
            logger.debug("Rapport généré avec succès", extra={
                'nb_achats': rapport.get('nb_achats'),
                'nb_recharges': rapport.get('nb_recharges')
            })
        except Exception as e:
            logger.error("Erreur lors de la génération du rapport", exc_info=True)
            messages.error(request, "Erreur lors de la génération du rapport")
            return redirect('marketing_dashboard:formulaire_client')

        # 4. Gestion des actions POST
        if request.method == 'POST':
            logger.info("Requête POST reçue", extra={
                'post_data': dict(request.POST)
            })
            if 'recommandation' in request.POST:
                logger.info("Redirection vers vue_recommandation_client")
                return redirect('marketing_dashboard:vue_recommandation_client')
            elif 'messages' in request.POST:
                logger.info("Redirection vers vue_messages_client")
                return redirect('marketing_dashboard:vue_messages_client')
        


        # 5. Préparation du contexte
        contexte = {
            'rapport': rapport,
            'msisdn': msisdn,
            'json_client': json.dumps(client_json, default=str, ensure_ascii=False, indent=2),
            'date_generation': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'periode_analyse': f"du {date_debut} au {date_fin}",
            'titre_page': f"Rapport Client {msisdn[-4:]}"  # Masquage partiel
        }

        logger.info("Affichage du rapport", extra={
            'template': 'marketing_dashboard/rapport.html',
            'rapport_keys': list(rapport.keys())
        })
        log_action(
        request=request,
        action_type='RAPPORT',
        description=f"Génération du rapport pour le client {msisdn}",
        target_type='client',
        target_id=msisdn
    )
        return render(request, 'marketing_dashboard/rapport.html', contexte)
        
    except Exception as e:
        logger.critical("Erreur non gérée dans vue_rapport_client", 
                      exc_info=True,
                      extra={
                          'user': request.user.username,
                          'error': str(e)
                      })
        messages.error(request, "Une erreur critique s'est produite. L'équipe technique a été notifiée.")
        return redirect('marketing_dashboard:formulaire_client')

# Page 3 : Comportement / Détails data (future extension)
def vue_comportement_client(request):
    return render(request, 'marketing_dashboard/comportement.html')
def extract_volumes_views(row: pd.Series) -> Tuple[int, int, int]:
    """Extrait les volumes de consommation depuis les données du catalogue"""
    # Initialiser les valeurs par défaut
    data_mo = row.get('data_volume', 0)
    voice_min = row.get('voice_volume', 0)
    sms = 0
    
    # Gérer les cas spéciaux
    if 'internet bil milli' in row.get('name', '').lower():
        prix = row.get('prix', 0)
        data_mo = round(prix / 20)  *25# Conversion correcte selon ta logique
    elif row.get('type', '').lower() == 'voix/data':
        data_mo = row.get('data_volume', 0)
        voice_min = row.get('voice_volume', 0)
    else:
        # Pour les options data, extraire le volume de la description
        desc = str(row.get('name', '')).lower()
        match_go = re.search(r'(\d+(?:\.\d+)?)\s*go', desc)
        match_mo = re.search(r'(\d+(?:\.\d+)?)\s*mo', desc)
        
        match_go = re.search(r'([\d.,]+)\s*go', desc)
        if match_go:
            valeur_str = match_go.group(1).replace(',', '.')
            data_go = float(valeur_str)
            data_mo = int(data_go * 1000)  # 1 Go = 1000 Mo

        elif match_mo:
            data_mo = int(match_mo.group(1))
    
    return data_mo, voice_min, sms
# Page 4 : Options recommandées
def vue_recommandation_client(request):
    msisdn, date_debut, date_fin = get_params_session(request)
    client_json, options_client, df_consommations = filtrer_clients(msisdn, date_debut, date_fin, FOLDER_CLIENT)

    catalogue = pd.read_csv(CATALOGUE_PATH)
    options, profil = dataframe_recommandations_vers_json_client(options_client, catalogue)
    
    # Convertir options en DataFrame pour nettoyer les doublons
    df_options = pd.DataFrame(option for option in options)
    df_consommations = pd.DataFrame(options_client)
    
    # Nettoyer les doublons en gardant la meilleure recommandation (meilleur score)
    if not df_options.empty:
        df_options = df_options.sort_values('score_similarite', ascending=False)
        df_options = df_options.drop_duplicates(subset=['id'], keep='first')
    
    # Préparer les données pour le template
    formatted_options = []
    for _, option in df_options.iterrows():
        data_mo, voice_min, sms = extract_volumes_views(option)
        formatted_options.append({
            'nom': option.get('name', ''),
            'type': option.get('type', '').capitalize(),
            'volume_data': int(data_mo),
            'volume_voix': voice_min,
            'duree': option.get('duree', 0),
            'prix': option.get('prix', 0),
            'promo': option.get('promo', False),
            'promo_flag': "🔥 Promo !" if option.get('promo', False) else "",
            'international': option.get('international', False),
            'score': option.get('score_similarite', 0)
        })
    
    # Préparer les options actives
    comportement_options = []
    df_consommations=df_consommations.sort_values('date_achat')
    if not df_consommations.empty:
        
        for _, row in df_consommations.iterrows():
            data_mo, voice_min, sms = extract_volumes_views(row)
            date_activation = str(row.get('date_achat', ''))
            comportement_options.append({
                'nom': row.get('name', ''),
                'type': row.get('type', '').capitalize(),
            'date_activation': date_activation,
            'volume_data': data_mo,
            'volume_voix': voice_min,
            'duree': row.get('duree_data', 0) if (row.get('type') == 'data' or row.get('type') == 'Data') else row.get('duree_voix', 0),
            'prix': row.get('prix', 0),
            'international': "Oui" if row.get('international', False) else "Non",
            'promo': "Oui" if row.get('promo', False) else "Non"
        })

    # Préparer le catalogue pour le template
    catalogue_options = []
    if not catalogue.empty:
        for _, row in catalogue.iterrows():
            data_mo, voice_min, sms = extract_volumes_views(row)
            catalogue_options.append({
                'nom': row.get('name', ''),
                'type': row.get('type', '').capitalize(),
                'volume_data': data_mo,
                'volume_voix': voice_min,
                'duree': row.get('duree_data', 0) if row.get('type') == 'data' else row.get('duree_voix', 0),
                'prix': row.get('prix', 0),
                'international': "Oui" if row.get('international', False) else "Non",
                'promo': "Oui" if row.get('promo', False) else "Non"
            })

    if request.method == 'POST' and 'messages' in request.POST:
        return redirect('vue_messages_marketing')
    if request.method == 'POST' and 'catalog' in request.POST:
        return redirect('vue_catalogue_maxit')
    log_action(
        request=request,
        action_type='RECOMMANDATION',
        description=f"Génération des options recommandées pour le client {msisdn}",
        target_type='client',
        target_id=msisdn
    )

    return render(request, 'marketing_dashboard/recommandation.html', {
        'options': formatted_options,
        'comportement_options': comportement_options,
        'catalogue': catalogue_options,
        'profil': {
            'data_volume': profil.get('data_volume', 0),
            'voice_volume': profil.get('voice_volume', 0),
            'duree': profil.get('duree', 0),
            'international': profil.get('international', 0),
            'promo': profil.get('promo', 0),
            'depense_actuelle': profil.get('depense_actuelle', 0)
        }
    })
from typing import List, Dict
from pydantic import BaseModel, ValidationError
import json, time, logging


# Page 5 : Messages marketing générés par LLM
@login_required
def vue_messages_marketing(request):
    try:
        # Récupération des paramètres de session
        msisdn, date_debut, date_fin = get_params_session(request)

        def construire_default_messages():
            return {
                'acquisition': [
                    "Nous n'avons pas pu générer de messages personnalisés. "
                    "Découvrez MaxIt pour des offres adaptées à votre profil : https://www.orange.tn/maxit"
                ],
                'jeux_et_fidelisation': [],
                'options_recommandees': [],
                'services_marketplace': [],
                'messages_personnalises': []
            }

        # Initialisation des variables
        client_json = None
        profil = {}
        messages_final = construire_default_messages()
        
        try:
            # Récupération des données client
            client_json, options_data, consommations = filtrer_clients(msisdn, date_debut, date_fin, FOLDER_CLIENT)
            
            if options_data is None or (hasattr(options_data, 'empty') and options_data.empty):
                logger.warning(f"[{msisdn}] Aucune option disponible.")
            else:
                df_options = pd.DataFrame(options_data) if not hasattr(options_data, 'to_dict') else options_data
                
                if not df_options.empty:
                    try:
                        # Rapport enrichi
                        rapport = generer_rapport_marketing_client(client_json)
                        
                        # Chargement du catalogue et génération des options
                        catalogue = pd.read_csv(CATALOGUE_PATH)
                        options, profil = dataframe_recommandations_vers_json_client(df_options, catalogue)

                        # Génération des messages personnalisés
                        messages_options = generer_messages_options_client(options, profil, consommations)
                        messages_final = generate_marketing_messages_client(rapport, messages_options)
                        logger.info("✅ Messages marketing générés avec succès.")
                        print(messages_final)

                    except Exception as e:
                        logger.error(f"[{msisdn}] Erreur lors du traitement marketing : {e}", exc_info=True)
                        messages.error(request, f"Erreur lors du traitement des données marketing : {str(e)}")
                else:
                    logger.warning(f"[{msisdn}] DataFrame vide malgré options_data non None.")
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données client : {str(e)}", exc_info=True)
            messages.error(request, f"Une erreur est survenue lors de la récupération des données : {str(e)}")
        
        # Construction de la conversation
        conversation = []
        
        # Message de bienvenue
        conversation.append({
            'type': 'agent',
            'content': f"🔍 J'ai analysé le comportement du client {msisdn} pour la période du {date_debut} au {date_fin}. Voici mes recommandations personnalisées :",
            'timestamp': datetime.now().strftime('%H:%M')
        })
        
        # Profil client
        if profil:
            profil_text = "👤 <strong>Profil du client :</strong><br>"
            if 'data_volume' in profil:
                profil_text += f"📊 Données consommées : {profil['data_volume']} Mo<br>"
            if 'voice_volume' in profil:
                profil_text += f"📞 Appels : {profil['voice_volume']} min<br>"
            if 'duree' in profil:
                profil_text += f"⏱️ Ancienneté : {profil['duree']} jours<br>"
            if 'depense_actuelle' in profil:
                profil_text += f"💰 Dépense moyenne : {profil['depense_actuelle']} DT"
                
            conversation.append({
                'type': 'agent',
                'content': profil_text,
                'timestamp': datetime.now().strftime('%H:%M')
            })
        
        # Catégories de messages
        categories = [
            ('acquisition', '💡 Acquisition MaxIt', 'Voici comment MaxIt peut améliorer votre expérience client :'),
            ('jeux_et_fidelisation', '🎮 Jeux & Fidélisation', 'Découvrez nos offres de fidélité :'),
            ('options_recommandees', '📊 Options Recommandées', 'Voici nos recommandations personnalisées :'),
            ('services_marketplace', '🛍️ Services & Partenaires', 'Nos offres partenaires exclusives :'),
            ('messages_personnalises', '✨ Messages Sur-Mesure', 'Des offres spécialement pour vous :')
        ]
        
        for cle, titre, intro in categories:
            if messages_final.get(cle) and isinstance(messages_final[cle], list):
                # Message de la catégorie
                conversation.append({
                    'type': 'category',
                    'title': titre,
                    'content': intro,
                    'timestamp': datetime.now().strftime('%H:%M')
                })
                
                # Messages de l'agent pour cette catégorie
                for message in messages_final[cle]:
                    if isinstance(message, str):  # S'assurer que le message est bien une chaîne
                        conversation.append({
                            'type': 'agent',
                            'content': message,
                            'timestamp': datetime.now().strftime('%H:%M')
                        })
        
        # Message de conclusion
        conversation.append({
            'type': 'agent',
            'content': "💡 Ces recommandations sont basées sur l'analyse de votre consommation. N'hésitez pas à me poser des questions !",
            'timestamp': datetime.now().strftime('%H:%M')
        })
        
        # Sérialisation de la conversation en JSON en échappant correctement les caractères spéciaux
        from django.utils.safestring import mark_safe
        import json
        
        context = {
            'conversation': mark_safe(json.dumps(conversation, ensure_ascii=False)),
            'client_id': msisdn or "Inconnu",
            'periode': f"{date_debut} au {date_fin}" if date_debut and date_fin else "Période non définie",
            'has_messages': any(messages_final.values())
        }
        print(conversation)
        log_action(
        request=request,
        action_type='MESSAGES',
        description=f"Génération des messages pour le client {msisdn}",
        target_type='client',
        target_id=msisdn
    )

        return render(request, 'marketing_dashboard/chat_messages.html', context)
    
    except Exception as e:
        logger.error(f"Erreur inattendue dans vue_messages_marketing : {str(e)}", exc_info=True)
        return render(request, 'marketing_dashboard/chat_messages.html', {
            'conversation': [{
                'type': 'agent',
                'content': f"❌ Une erreur est survenue lors de la génération des messages. Veuillez réessayer plus tard. Erreur : {str(e)}",
                'timestamp': datetime.now().strftime('%H:%M')
            }],
            'client_id': msisdn if 'msisdn' in locals() else "Inconnu",
            'periode': f"{date_debut} au {date_fin}" if 'date_debut' in locals() and 'date_fin' in locals() and date_debut and date_fin else "Période non définie",
            'has_messages': False
        })

# Fonction utilitaire pour extraire les données de session
def get_params_session(request):
    msisdn = request.session.get('msisdn')
    date_debut = request.session.get('date_debut')
    date_fin = request.session.get('date_fin')
    
    try:
        if date_debut:
            date_debut = datetime.strptime(date_debut, "%Y-%m-%d")
        if date_fin:
            date_fin = datetime.strptime(date_fin, "%Y-%m-%d")
    except (ValueError, TypeError) as e:
        print(f"Erreur de conversion de date: {e}")
        date_debut = date_fin = None
        
    return msisdn, date_debut, date_fin
def get_params_session_segment(request):
    """
    Récupère et valide les paramètres de session pour un segment.
    
    Args:
        request: L'objet HttpRequest contenant la session
        
    Returns:
        tuple: (segment_id, date_debut, date_fin, segment_criteria)
    """
    try:
        # Récupération des valeurs de la session avec des valeurs par défaut
        segment_id = request.session.get('segment_id')
        segment_criteria = request.session.get('segment_criteria', {})
        
        # Gestion des dates avec validation
        date_debut = date_fin = None
        date_format = "%Y-%m-%d"
        
        date_debut_str = request.session.get('date_debut')
        date_fin_str = request.session.get('date_fin')
        
        if date_debut_str:
            try:
                date_debut = datetime.strptime(str(date_debut_str), date_format).date()
            except (ValueError, TypeError) as e:
                logger.warning(f"Format de date de début invalide: {date_debut_str} - {e}")
                
        if date_fin_str:
            try:
                date_fin = datetime.strptime(str(date_fin_str), date_format).date()
            except (ValueError, TypeError) as e:
                logger.warning(f"Format de date de fin invalide: {date_fin_str} - {e}")
        
        # Validation de la cohérence des dates
        if date_debut and date_fin and date_debut > date_fin:
            logger.warning(f"La date de début ({date_debut}) est postérieure à la date de fin ({date_fin})")
            date_fin = date_debut
        
        return segment_id, date_debut, date_fin, segment_criteria
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des paramètres de session: {e}")
        # Retourne des valeurs par défaut en cas d'erreur
        return None, None, None, {}
def signout_view(request):
    # Usually, you'd perform the signout operation here or redirect to a signout URL
    return render(request, 'users/home.html')
#maintenant analyse segment 
# views.py
import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from .forms import SegmentFiltreForm

# views.py
from .forms import SegmentFiltreForm

def vue_filtres_segment(request):
    segment_type = request.GET.get('type', 'acquisition')  # Default to acquisition
    
    if request.method == 'POST':
        form = SegmentFiltreForm(segment_type=segment_type, data=request.POST)
        if form.is_valid():
            segment_criteria = {key: form.cleaned_data[key] for key in form.fields 
                              if key not in ['date_debut', 'date_fin'] and form.cleaned_data.get(key)}
            request.session['segment_criteria'] = segment_criteria
            request.session['date_debut'] = str(form.cleaned_data['date_debut'])
            request.session['date_fin'] = str(form.cleaned_data['date_fin'])
            request.session['segment_type'] = segment_type
            return redirect('marketing_dashboard:vue_kpi_clients_segment')
    else:
        form = SegmentFiltreForm(segment_type=segment_type)
    
    return render(request, 'marketing_dashboard/segment_filtres.html', {
        'form': form,
        'segment_type': segment_type
    })


# à placer en haut du fichier views.py (valeurs disponibles pour les filtres)
SEGMENTS_POSSIBLES = {
    'rentabilite': ['non rentable', 'rentable'],
    'engagement': ['non engagé', 'peu engagé', 'très engagé'],
    'type_client': ['orienté USSD', 'orienté APLICATION', 'orienté BOUTIQUE'],
    'type_interet': ['data', 'voix'],
    'interet_international': ['non international', 'international'],
    'interet_jeu': ['non jeu', 'peu jeu', 'très jeu'],
    'interet_promo': ['non promo', 'peu promo', 'Sensibles aux promos'],
    'action': ['achat', 'recharge', 'roue chance']
}
from django.shortcuts import render
@login_required
def vue_kpi_clients_segment(request):
    """
    Affiche les KPI et la liste des clients pour un segment donné.
    Gère les erreurs et affiche des messages appropriés à l'utilisateur.
    """
    from django.contrib import messages
    from django.contrib.humanize.templatetags.humanize import intcomma
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Récupération des paramètres de session
        folder_path = os.path.join(settings.BASE_DIR, 'data')
        
        segment_criteria = request.session.get('segment_criteria', {})
        date_debut = request.session.get('date_debut')
        date_fin = request.session.get('date_fin')
        segment_type = request.session.get('segment_type', 'acquisition')
        
        # Validation des paramètres requis
        if not all([date_debut, date_fin]):
            messages.error(request, "Les dates de début et de fin sont requises.")
            return redirect('marketing_dashboard:vue_filtres_segment')
            
        # Nettoyage des critères pour les segments de fidélisation
        if segment_type == 'loyalty' and 'type_client' in segment_criteria:
            del segment_criteria['type_client']
            request.session['segment_criteria'] = segment_criteria
            request.session.modified = True
        
        print(segment_type)

        # Appel de la fonction de filtrage
        result, all_options, clients_df, segment_id = filtrer_clients_par_segments(
            segment_criteria, date_debut, date_fin,segment_type, folder_path
        )
        
        
        
        # Gestion des cas d'erreur spécifiques
        if segment_id == 'error_missing_msisdn':
            error_msg = """
            Erreur de données : Colonne 'msisdn' manquante dans les données de segmentation.
            
            Vérifiez que :
            1. Les fichiers de segmentation (df_segmentation_mois_*.csv) sont présents dans le dossier data/
            2. Ces fichiers contiennent bien une colonne 'msisdn' ou une colonne similaire (comme 'MSISDN', 'phone', etc.)
            3. Les fichiers ne sont pas vides et sont au format CSV valide
            """
            logger.error(error_msg)
            messages.error(request, error_msg)
            return redirect('marketing_dashboard:vue_filtres_segment')
            
        if segment_id.startswith('error_'):
            error_msg = "Une erreur est survenue lors du filtrage des clients."
            logger.error(f"Erreur de filtrage: {segment_id}")
            messages.error(request, f"{error_msg} Veuillez réessayer ou contacter le support.")
            return redirect('marketing_dashboard:vue_filtres_segment')
            
        if segment_id == 'no_matching_clients':
            messages.warning(
                request,
                "Aucun client ne correspond aux critères de recherche. "
                "Veuillez élargir vos critères."
            )
            return redirect('marketing_dashboard:vue_filtres_segment')
            
        if segment_id == 'invalid_dates':
            messages.error(
                request,
                "La date de début doit être antérieure à la date de fin."
            )
            return redirect('marketing_dashboard:vue_filtres_segment')
            
        if segment_id in ['no_files', 'missing_segmentation_file', 'invalid_columns']:
            messages.error(
                request,
                "Problème d'accès aux données. Veuillez vérifier que les fichiers de données sont correctement configurés."
            )
            return redirect('marketing_dashboard:vue_filtres_segment')

        # Calcul des KPI
        try:
            kpis = analyser_kpis_segment(all_options, clients_df)
        except Exception as e:
            logger.error(f"Erreur lors du calcul des KPI: {str(e)}", exc_info=True)
            messages.error(
                request,
                "Une erreur est survenue lors du calcul des indicateurs. "
                "Certaines données pourraient être manquantes."
            )
            kpis = {}

        # Stocker uniquement les données essentielles dans la session
        request.session['segment_criteria'] = segment_criteria
        request.session['date_debut'] = str(date_debut)
        request.session['date_fin'] = str(date_fin)
        request.session['segment_type'] = segment_type
        request.session['segment_id'] = segment_id
        request.session['clients_df'] = clients_df.to_dict(orient='records')
        request.session['clients_json'] = result
        # Stocker les KPIs qui sont déjà un dictionnaire
        request.session['kpis'] = kpis
        
        # Convertir les DataFrames en listes de dictionnaires pour la sérialisation
        if all_options is not None and not all_options.empty:
            request.session['all_options_data'] = all_options.to_dict(orient='records')
        else:
            request.session['all_options_data'] = []
            
        # Sauvegarder la session
        request.session.modified = True

        # Gestion de la génération de rapport
        if request.method == 'POST' and 'rapport' in request.POST:
            return redirect('marketing_dashboard:vue_rapport_segment')

        # Préparation du contexte
        context = {
            'clients': result,
            'kpis': kpis,
            'clients_df': clients_df.to_dict(orient='records') if not clients_df.empty else [],
            'intcomma': intcomma,
            'segment_criteria': segment_criteria,
            'segment_type': segment_type,
            'nb_clients': len(result),
            'periode': f"du {date_debut} au {date_fin}"
        }
        log_action(
        request=request,
        action_type='Analyse',
        description=f"Analyse du segment {segment_id}",
        target_type='segment',
        target_id=segment_id
    )
        return render(request, 'marketing_dashboard/segment_kpi_clients.html', context)
        
    except Exception as e:
        logger.critical(f"Erreur critique dans vue_kpi_clients_segment: {str(e)}", exc_info=True)
        messages.error(
            request,
            "Une erreur inattendue est survenue. "
            "L'équipe technique a été notifiée."
        )
        return redirect('marketing_dashboard:vue_filtres_segment')
from collections import defaultdict
from collections import Counter
import numpy as np
from datetime import datetime
from typing import Tuple

class NumpyEncoder(json.JSONEncoder):
    """Custom encoder for numpy data types"""
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                         np.int16, np.int32, np.int64, np.uint8,
                         np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

def parse_number(value_str, default=0.0):
    if not value_str or not isinstance(value_str, str):
        return default
    
    try:
        # Remove thousand separators and normalize decimal point
        cleaned = value_str.replace(' ', '').replace(',', '')
        return float(cleaned)
    except (ValueError, TypeError):
        return default

def parse_rapport_segment(rapport_texte):
    """
    Parse le texte complet du rapport marketing segment en un dictionnaire structuré
    """
    rapport = {}
    lignes = rapport_texte.split('\n')
    section = None
    current_reco = None
    
    for ligne in lignes:
        ligne = ligne.strip()
        if not ligne:
            continue
            
        # Extraction de l'ID segment et période
        if '📄 **Rapport Marketing Segment –' in ligne:
            segment_id = ligne.split('`')[1].strip() if '`' in ligne else ligne.split('–')[-1].strip('*').strip()
            rapport['segment_id'] = segment_id
            rapport['titre'] = ' '.join(segment_id.split('_')).title()
            
            # Extraction des critères de segmentation
            criteres = segment_id.split('_')
            rapport['criteres_segmentation'] = [f"{criteres[i]}:{criteres[i+1]}" 
                                              for i in range(0, len(criteres)-1, 2)]
            
        elif '📅 **Période d\'analyse** :' in ligne:
            rapport['periode_analyse'] = ligne.split(':', 1)[1].strip()
        elif '👥 **Nombre de clients dans le segment** :' in ligne:
            rapport['nb_clients'] = int(parse_number(ligne.split(':')[1].strip()))
        elif '🏷️ **Type de segment** :' in ligne:
            rapport['type_segment'] = ligne.split(':', 1)[1].strip()
            
        # Extraction des informations de base
        elif ligne.startswith('- **Identifiant** :'):
            rapport['identifiant_formate'] = ligne.split(':', 1)[1].strip()
        elif ligne.startswith('- **Type de Clientèle majeure** :'):
            rapport['type_clientele'] = ligne.split(':', 1)[1].strip()
            
        # Extraction des profils
        elif ligne.startswith('- **Niveaux d\'engagement** :'):
            rapport['engagement'] = []
            parts = ligne.split(':', 1)[1].strip().split(',')
            for part in parts:
                part = part.strip()
                if '(' in part:
                    niveau = part.split('(')[0].strip()
                    count = part.split('(')[1].split('clients')[0].strip()
                    rapport['engagement'].append({
                        'niveau': niveau,
                        'count': int(parse_number(count))
                    })
                    
        elif ligne.startswith('- **Niveaux de rentabilité** :'):
            rapport['rentabilite'] = []
            parts = ligne.split(':', 1)[1].strip().split(',')
            for part in parts:
                part = part.strip()
                if '(' in part:
                    niveau = part.split('(')[0].strip()
                    count = part.split('(')[1].split('clients')[0].strip()
                    rapport['rentabilite'].append({
                        'niveau': niveau,
                        'count': int(parse_number(count))
                    })
                    
        elif ligne.startswith('- **Clients MaxIt** :'):
            parts = ligne.split(':', 1)[1].strip().split('(')
            rapport['nb_maxit'] = int(parse_number(parts[0].split('clients')[0].strip()))
            if len(parts) > 1:
                rapport['taux_maxit'] = parse_number(parts[1].split('%')[0].strip())
                
        elif ligne.startswith('- **Répartition des types de clients** :'):
            rapport['types_clients'] = []
            parts = ligne.split(':', 1)[1].strip().split(',')
            for part in parts:
                part = part.strip()
                if '(' in part:
                    type_client = part.split('(')[0].strip()
                    rest = part.split('(')[1]
                    count_part = rest.split('clients')[0].strip()
                    percentage_part = rest.split('%')[0].split(',')[-1].strip() if '%' in rest else '0'
                    
                    rapport['types_clients'].append({
                        'type': type_client,
                        'count': int(parse_number(count_part)),
                        'percentage': parse_number(percentage_part)
                    })
                    
        # Gestion des sections
        elif ligne.startswith('## '):
            section = ligne[3:].strip()
            if section == '📈 MÉTRIQUES CLÉS':
                section = 'metriques'
            elif section == '🛒 COMPORTEMENT TRANSACTIONNEL':
                section = 'transactionnel'
            elif section == '📱 CONSOMMATION MOYENNE':
                section = 'consommation'
            elif section == '⭐ OPTIONS LES PLUS UTILISÉES':
                section = 'options'
            elif section == '💡 RECOMMANDATIONS STRATÉGIQUES':
                section = 'recommandations'
                
        # Extraction par section
        if section == 'metriques':
            if ligne.startswith('- **Total des achats** :'):
                rapport['total_achats'] = int(parse_number(ligne.split(':')[1].split('opérations')[0].strip()))
            elif ligne.startswith('- **Montant total** :') and 'DT' in ligne and 'ACHATS' in lignes[lignes.index(ligne)-1]:
                rapport['montant_total_achats'] = parse_number(ligne.split(':')[1].split('DT')[0].strip())
            elif ligne.startswith('- **Panier moyen** :'):
                rapport['panier_moyen'] = parse_number(ligne.split(':')[1].split('DT')[0].strip())
            elif ligne.startswith('- **Par client** :') and 'ACHATS' in lignes[lignes.index(ligne)-3]:
                rapport['achat_par_client'] = parse_number(ligne.split(':')[1].split('DT')[0].strip())
            elif ligne.startswith('- **Total des recharges** :'):
                rapport['total_recharges'] = int(parse_number(ligne.split(':')[1].split('opérations')[0].strip()))
            elif ligne.startswith('- **Montant total** :') and 'DT' in ligne and 'RECHARGES' in lignes[lignes.index(ligne)-1]:
                rapport['montant_total_recharges'] = parse_number(ligne.split(':')[1].split('DT')[0].strip())
            elif ligne.startswith('- **Recharge moyenne** :'):
                rapport['recharge_moyenne'] = parse_number(ligne.split(':')[1].split('DT')[0].strip())
            elif ligne.startswith('- **Par client** :') and 'RECHARGES' in lignes[lignes.index(ligne)-3]:
                rapport['recharge_par_client'] = parse_number(ligne.split(':')[1].split('DT')[0].strip())
                
        elif section == 'transactionnel':
            if ligne.startswith('- **Canal d\'achat principal** :'):
                rapport['canal_achat_principal'] = ligne.split(':')[1].strip()
            elif ligne.startswith('- **Canal de recharge principal** :'):
                rapport['canal_recharge_principal'] = ligne.split(':')[1].strip()
            elif ligne.startswith('- **Répartition des canaux d\'achat** :'):
                rapport['repartition_canaux'] = []
                parts = ligne.split(':', 1)[1].strip().split(',')
                for part in parts:
                    part = part.strip()
                    if '%' in part:
                        canal = part.split('(')[0].strip()
                        percentage = part.split('(')[1].split('%')[0].strip()
                        rapport['repartition_canaux'].append({
                            'canal': canal,
                            'percentage': parse_number(percentage)
                        })
            elif ligne.startswith('- **Fréquence d\'achat moyenne** :'):
                rapport['freq_achat'] = parse_number(ligne.split(':')[1].split('achats')[0].strip())
            elif ligne.startswith('- **Fréquence de recharge moyenne** :'):
                rapport['freq_recharge'] = parse_number(ligne.split(':')[1].split('recharges')[0].strip())
            if 'Fréquence d\'achat moyenne' in ligne:
                rapport['freq_achat'] = float(ligne.split(':')[1].split('achats')[0].strip())
            elif 'Fréquence de recharge moyenne' in ligne:
                rapport['freq_recharge'] = float(ligne.split(':')[1].split('recharges')[0].strip())  
        elif section == 'consommation':
            if ligne.startswith('- **Moyenne** :') and 'DONNÉES MOBILES' in lignes[lignes.index(ligne)-1]:
                rapport['conso_data_moyenne'] = parse_number(ligne.split(':', 1)[1].split('Mo')[0].strip())
            elif ligne.startswith('- **Médiane** :') and 'DONNÉES MOBILES' in lignes[lignes.index(ligne)-2]:
                rapport['conso_data_mediane'] = parse_number(ligne.split(':', 1)[1].split('Mo')[0].strip())
            elif ligne.startswith('- **Maximum** :') and 'DONNÉES MOBILES' in lignes[lignes.index(ligne)-3]:
                rapport['conso_data_max'] = parse_number(ligne.split(':', 1)[1].split('Mo')[0].strip())
                
            elif ligne.startswith('- **Moyenne** :') and 'APPELS VOCAUX' in lignes[lignes.index(ligne)-1]:
                rapport['conso_voix_moyenne'] = parse_number(ligne.split(':', 1)[1].split('minutes')[0].strip())
            elif ligne.startswith('- **Médiane** :') and 'APPELS VOCAUX' in lignes[lignes.index(ligne)-2]:
                rapport['conso_voix_mediane'] = parse_number(ligne.split(':', 1)[1].split('minutes')[0].strip())
            elif ligne.startswith('- **Maximum** :') and 'APPELS VOCAUX' in lignes[lignes.index(ligne)-3]:
                rapport['conso_voix_max'] = parse_number(ligne.split(':', 1)[1].split('minutes')[0].strip())
                
            elif ligne.startswith('- **Moyenne** :') and 'MESSAGERIE (SMS)' in lignes[lignes.index(ligne)-1]:
                rapport['conso_sms_moyenne'] = parse_number(ligne.split(':', 1)[1].split('SMS')[0].strip())
            elif ligne.startswith('- **Médiane** :') and 'MESSAGERIE (SMS)' in lignes[lignes.index(ligne)-2]:
                rapport['conso_sms_mediane'] = parse_number(ligne.split(':', 1)[1].split('SMS')[0].strip())
            elif ligne.startswith('- **Maximum** :') and 'MESSAGERIE (SMS)' in lignes[lignes.index(ligne)-3]:
                rapport['conso_sms_max'] = parse_number(ligne.split(':', 1)[1].split('SMS')[0].strip())
                
        elif section == 'options' and ligne.startswith('- **'):
            if 'options_utilisees' not in rapport:
                rapport['options_utilisees'] = []
            option_nom = ligne.split('**')[1].strip()
            parts = ligne.split(':', 1)[1].strip().split('(')
            # convertir en int et normaliser Internet bel milli
            try:
                count_val = float(parts[0].strip().split(' ')[0])
                count_val = int(count_val)
                if count_val == 0:
                    option_nom = "Internet bel milli"
            except:
                count_val = 0
            percentage = parse_number(parts[1].split('%')[0].strip()) if len(parts) > 1 else 0.0
            rapport['options_utilisees'].append({
                'nom': option_nom,
                'count': count_val,
                'percentage': percentage
            })

            
        elif section == 'recommandations':
            if ligne.startswith('### '):
                current_reco = ligne[4:].strip()
                if 'recommandations' not in rapport:
                    rapport['recommandations'] = []
                rapport['recommandations'].append({
                    'titre': current_reco,
                    'items': []
                })
            elif ligne.startswith('- ') and current_reco and rapport['recommandations']:
                rapport['recommandations'][-1]['items'].append(ligne[2:].strip())
    
    # Extraction des exemples de messages marketing
    if '### ✉️ Exemple de message marketing à envoyer :' in lignes:
        idx = lignes.index('### ✉️ Exemple de message marketing à envoyer :')
        rapport['exemples_messages'] = []
        for ligne in lignes[idx+1:]:
            if ligne.strip() and not ligne.startswith(('*', '📌')):
                rapport['exemples_messages'].append(ligne.strip())
                
    return rapport

def enrichir_rapport_segment(rapport, json_clients):
    """
    Enrichit le rapport segment avec des données supplémentaires du JSON clients
    """
    # 1. Informations générales sur les clients
    nb_clients = len(json_clients)
    rapport['nb_clients_calc'] = nb_clients
    
    # 2. Analyse des achats et recharges
    total_achats = 0
    montant_total_achats = 0
    total_recharges = 0
    montant_total_recharges = 0
    
    canaux_achats = []
    canaux_recharges = []
    
    conso_data = []
    conso_voix = []
    conso_sms = []
    
    options_counter = Counter()
    profils_maxit = 0
    engagements = Counter()
    rentabilites = Counter()
    types_clients = Counter()
    
    for client in json_clients:
        ci = client.get("client_info", {})
        seg = client.get("segmentation", {})
        achats = client.get("achats", {})
        recharges = client.get("recharges", {})
        conso = client.get("consommations", {})
        options = client.get("options", {})
        
        # Achats
        total_achats += len(achats)
        montant_total_achats += abs(sum(float(abs(achat.get("prix", 0.0))) for achat in achats.values() if achat and "prix" in achat))
        panier_moy=montant_total_achats / total_achats if total_achats>0 else 0 


        # Recharges
        total_recharges += len(recharges)
        montant_total_recharges += sum(float(recharge.get("amount", 0.0)) for recharge in recharges.values() if recharge and "amount" in recharge)
        recharge_moy=montant_total_recharges / total_recharges if total_recharges>0 else 0 
        # Canaux
        canaux_achats += [a.get("login") for a in achats.values() if a and "login" in a]
        canaux_recharges += [r.get("login") for r in recharges.values() if r and "login" in r]
        
        # Consommations
        if isinstance(conso, dict):
            conso_data.append(float(conso.get("data_usage", 0)))
            conso_voix.append(float(conso.get("voice_usage", 0)))
            conso_sms.append(float(conso.get("sms_usage", 0)))
        
        # Options
        for opt in options.values():
            if opt and "data_volume" in opt:
                # Normalisation
                data_vol = str(opt["data_volume"]).strip()
                if data_vol in ["0", "0.0", "0 Mo", "bil milli"]:
                    data_vol = "Internet bil milli"
                else:
                    # convertir en int si possible pour éviter float inutile
                    try:
                        data_vol = int(float(data_vol))
                    except:
                        pass
                options_counter[data_vol] += 1

        
        # MaxIt profil
        if ci.get("est_maxit", False) or client.get("profil_maxit", False):
            profils_maxit += 1
        
        # Engagement & rentabilité
        engagements[seg.get("segment_engagement", "Inconnu")] += 1
        rentabilites[seg.get("segment_rentabilité", "Inconnu")] += 1
        types_clients[ci.get("type_client", "Inconnu")] += 1
    
    # Ajout des données calculées au rapport
    rapport.update({
        'total_achats_calc': total_achats,
        'montant_total_achats': montant_total_achats,
        'total_recharges_calc': total_recharges,
        'montant_total_recharges': montant_total_recharges,
        'panier_moyen_calc': panier_moy,
        'recharge_moyenne_calc': recharge_moy,
        'achat_par_client_calc': montant_total_achats / nb_clients if nb_clients else 0,
        'recharge_par_client_calc': montant_total_recharges / nb_clients if nb_clients else 0,
        'taux_maxit_calc': (profils_maxit / nb_clients * 100) if nb_clients else 0,
        'nb_maxit_calc': profils_maxit,
        'conso_data_moyenne_calc': np.mean(conso_data) if conso_data else 0,
        'conso_voix_moyenne_calc': np.mean(conso_voix) if conso_voix else 0,
        'conso_sms_moyenne_calc': np.mean(conso_sms) if conso_sms else 0,
        'canal_achat_principal_calc': Counter(canaux_achats).most_common(1)[0][0] if canaux_achats else "Inconnu",
        'canal_recharge_principal_calc': Counter(canaux_recharges).most_common(1)[0][0] if canaux_recharges else "Inconnu",
        'engagement_distribution': dict(engagements),
        'rentabilite_distribution': dict(rentabilites),
        'type_client_distribution': dict(types_clients),
        'nb_achats_moyen': int(total_achats),
        'nb_recharges_moyen': np.mean(total_recharges),
        'freq_achat':np.mean(total_achats)/nb_clients,
        'freq_recharge':np.mean(total_recharges)/nb_clients,
        'nb_clients':nb_clients
    
    })
    
    return rapport
def generer_rapport_marketing_segment_complet(segment_id, clients_json, segment_type='acquisition'):
   
    
    nb_clients = len(clients_json)
    rapport = f"📄 **Rapport Marketing Segment – `{segment_id}`**\n\n"
    rapport += f"📅 **Période d'analyse** : {datetime.now().strftime('%d/%m/%Y')}\n"
    rapport += f"👥 **Nombre de clients dans le segment** : {nb_clients}\n"
    rapport += f"🏷️ **Type de segment** : {segment_type.upper()}\n\n"
    
    total_achats = 0
    montant_total_achats = 0
    total_recharges = 0
    montant_total_recharges = 0
    total_jeux = 0
    
    canaux_achats = []
    canaux_recharges = []
    
    conso_data = []
    conso_voix = []
    conso_sms = []
    
    options_counter = Counter()
    
    profils_maxit = 0
    
    engagements = Counter()
    rentabilites = Counter()
    prg=[]
    for client in clients_json:
        ci = client.get("client_info", {})
        seg = client.get("segmentation", {})
        achats = client.get("achats", {})
        recharges = client.get("recharges", {})
        jeux = client.get("jeux", {})
        conso = client.get("consommations", {})
        options = client.get("options", {})
        
        # Achats
        total_achats += len(achats)
        montant_total_achats += float(ci.get("montant_total_achat", 0))
        # Recharges
        total_recharges += len(recharges)
        montant_total_recharges += float(ci.get("montant_total_recharge", 0))
        # Jeux
        total_jeux += len(jeux)
        maxit_flags=[]
        maxit_flags.append(bool(client.get("est_maxit", False)))
        prg+=[a.get("prgname") for a in achats.values() if a and "prgname" in a]
        # Canaux
        canaux_achats += [a.get("login") for a in achats.values() if a and "login" in a]
        canaux_recharges += [r.get("login") for r in recharges.values() if r and "login" in r]
        
        # Consommations
        if isinstance(conso, dict):
            conso_data.append(float(conso.get("data_usage", 0)))
            conso_voix.append(float(conso.get("voice_usage", 0)))
            conso_sms.append(float(conso.get("sms_usage", 0)))
        
        # Options
        for opt in options.values():
            if opt and "data_volume" in opt:
                options_counter[opt["data_volume"]] += 1
        
        # MaxIt profil
        if ci.get("est_maxit",  True) or client.get("profil_maxit", True):
            profils_maxit += 1
        
        # Engagement & rentabilité
        engagements[seg.get("segment_engagement", "Inconnu")] += 1
        rentabilites[seg.get("segment_rentabilité", "Inconnu")] += 1
    
    # Moyennes
    montant_achat_moyen = montant_total_achats / nb_clients if nb_clients else 0
    montant_recharge_moyen = montant_total_recharges / nb_clients if nb_clients else 0
    conso_data_moyenne = np.mean(conso_data) if conso_data else 0
    conso_voix_moyenne = np.mean(conso_voix) if conso_voix else 0
    conso_sms_moyenne = np.mean(conso_sms) if conso_sms else 0
    
    # Canaux dominants
    canal_achat_principal = Counter(canaux_achats).most_common(1)
    canal_recharge_principal = Counter(canaux_recharges).most_common(1)
    canal_achat_principal = canal_achat_principal[0][0] if canal_achat_principal else "N/A"
    canal_recharge_principal = canal_recharge_principal[0][0] if canal_recharge_principal else "N/A"
    # Get most common profile type
    prog = Counter(prg).most_common(1)
    profil_majoritaire = prog[0][0] if prog else "Inconnu"
    
    taux_maxit = np.mean(maxit_flags) * 100  # Convert to percentage
    
    # Format segment ID for better readability
    if isinstance(segment_id, str):
        segment_id_formatted = ' '.join(segment_id.split('_')).title()
    else:
        segment_id_formatted = str(segment_id)
    
    # Construction du rapport markdown
    rapport += f"# 📊 RAPPORT D'ANALYSE DE SEGMENT\n\n"
    rapport += f"## 🏷️ IDENTIFIANT DU SEGMENT\n"
    rapport += f"- **Identifiant** : {segment_id_formatted}\n"
    rapport += f"- **Type de segment** : {segment_type.title() if segment_type else 'Non spécifié'}\n"
    rapport += f"- **Type de Clientèle majeure** : {profil_majoritaire.upper()}\n"
    rapport += f"- **Nombre de clients** : {nb_clients:,} clients\n\n"
    # PROFIL DU SEGMENT
    rapport += "## 👤 PROFIL DU SEGMENT\n"
    
    # Format engagement data
    engagement_str = ", ".join([f"{k} ({v} clients)" for k, v in engagements.items()])
    rapport += f"- **Niveaux d'engagement** : {engagement_str}\n"
    
    # Format rentability data
    rentabilite_str = ", ".join([f"{k} ({v} clients)" for k, v in rentabilites.items()])
    rapport += f"- **Niveaux de rentabilité** : {rentabilite_str}\n"
    
    # Add MaxIt clients info
    rapport += f"- **Clients MaxIt** : {int(profils_maxit)} clients ({taux_maxit:.1f}% du segment)\n"
    
    # Add client type distribution
    if prg:
        type_client_dist = Counter(prg)
        type_client_str = ", ".join([f"{k} ({v} clients, {v/len(prg)*100:.1f}%)" for k, v in type_client_dist.most_common()])
        rapport += f"- **Répartition des types de clients** : {type_client_str}\n"
    rapport += "\n"
    
    # MÉTRIQUES CLÉS
    rapport += "## 📈 MÉTRIQUES CLÉS\n"
    
    # Format large numbers with thousands separator
    def format_number(num):
        return f"{num:,.0f}".replace(",", " ")
    
    # Purchases section
    rapport += "### 🛒 ACHATS\n"
    rapport += f"- **Total des achats** : {format_number(total_achats)} opérations\n"
    rapport += f"- **Montant total** : {montant_total_achats:,.2f} DT\n"
    rapport += f"- **Panier moyen** : {montant_achat_moyen:,.2f} DT/achat\n"
    rapport += f"- **Par client** : {montant_achat_moyen:,.2f} DT\n\n"
    
    # Recharges section
    rapport += "### 💰 RECHARGES\n"
    rapport += f"- **Total des recharges** : {format_number(total_recharges)} opérations\n"
    rapport += f"- **Montant total** : {montant_total_recharges:,.2f} DT\n"
    rapport += f"- **Recharge moyenne** : {montant_recharge_moyen:,.2f} DT/recharge\n"
    rapport += f"- **Par client** : {montant_recharge_moyen:,.2f} DT\n\n"
    
    # Games section
    if total_jeux > 0:
        jeux_par_client = total_jeux / nb_clients if nb_clients else 0
        rapport += "### 🎮 JEUX CONCOURS\n"
        rapport += f"- **Participations totales** : {format_number(total_jeux)}\n"
        rapport += f"- **Participations moyennes** : {jeux_par_client:.1f} par client\n\n"
    
    # COMPORTEMENT TRANSACTIONNEL
    rapport += "## 🛒 COMPORTEMENT TRANSACTIONNEL\n"
    
    # Transaction channels
    rapport += "### 🔄 CANAUX DE TRANSACTION\n"
    rapport += f"- **Canal d'achat principal** : {canal_achat_principal}\n"
    rapport += f"- **Canal de recharge principal** : {canal_recharge_principal}\n"
    
    # Add channel distribution if available
    if canaux_achats:
        canal_dist = Counter(canaux_achats)
        total = sum(canal_dist.values())
        canal_str = ", ".join([f"{k} ({v/total*100:.1f}%)" for k, v in canal_dist.most_common(3)])
        rapport += f"- **Répartition des canaux d'achat** : {canal_str}\n"
    
    # Add purchase frequency if available
    if total_achats and nb_clients:
        freq_achat = total_achats / nb_clients
        rapport += f"- **Fréquence d'achat moyenne** : {freq_achat:.1f} achats/client\n"
    
    # Add recharge frequency if available
    if total_recharges and nb_clients:
        freq_recharge = total_recharges / nb_clients
        rapport += f"- **Fréquence de recharge moyenne** : {freq_recharge:.1f} recharges/client\n"
    
    rapport += "\n"
    
    # CONSOMMATION MOYENNE
    rapport += "## 📱 CONSOMMATION MOYENNE\n"
    
    # Data consumption
    if conso_data:
        conso_data_med = np.median(conso_data)
        conso_data_max = max(conso_data) if conso_data else 0
        rapport += "### 📶 DONNÉES MOBILES\n"
        rapport += f"- **Moyenne** : {conso_data_moyenne:,.1f} Mo\n"
        rapport += f"- **Médiane** : {conso_data_med:,.1f} Mo\n"
        rapport += f"- **Maximum** : {conso_data_max:,.1f} Mo\n"
    
    # Voice consumption
    if conso_voix:
        conso_voix_med = np.median(conso_voix)
        conso_voix_max = max(conso_voix) if conso_voix else 0
        rapport += "### 📞 APPELS VOCAUX\n"
        rapport += f"- **Moyenne** : {conso_voix_moyenne:,.1f} minutes\n"
        rapport += f"- **Médiane** : {conso_voix_med:,.1f} minutes\n"
        rapport += f"- **Maximum** : {conso_voix_max:,.1f} minutes\n"
    
    # SMS consumption if available
    if conso_sms:
        conso_sms_med = np.median(conso_sms)
        conso_sms_max = max(conso_sms) if conso_sms else 0
        conso_sms_moyenne = np.mean(conso_sms)
        rapport += "### 💬 MESSAGERIE (SMS)\n"
        rapport += f"- **Moyenne** : {conso_sms_moyenne:,.1f} SMS\n"
        rapport += f"- **Médiane** : {conso_sms_med:,.1f} SMS\n"
        rapport += f"- **Maximum** : {conso_sms_max:,.1f} SMS\n"
    # Most used options with better formatting
    # Most used options with better formatting
    if options_counter:
        rapport += "## ⭐ OPTIONS LES PLUS UTILISÉES\n"
        total_options = sum(options_counter.values())

        options_par_type = {}
        for opt, count in options_counter.items():
            # Normalisation du nom
            option_nom = str(opt).strip()
            if option_nom in ["0", "0.0", "0 Mo", "bel milli", ""]:
                option_nom = "Internet bel milli"
            else:
                # Si le nom est une valeur numérique, on ajoute l'unité Mo
                try:
                    val = int(float(option_nom))
                    option_nom = f"{val} Mo"
                except:
                    pass  # Si ce n'est pas un nombre, on garde le nom tel quel

            # Catégorisation
            if "internet" in option_nom.lower() or "data" in option_nom.lower() or option_nom == "Internet bel milli":
                categorie = "Données"
            elif "appel" in option_nom.lower() or "min" in option_nom.lower() or "sms" in option_nom.lower():
                categorie = "Communication"
            else:
                categorie = "Autres"

            if categorie not in options_par_type:
                options_par_type[categorie] = []
            options_par_type[categorie].append((option_nom, int(count)))

        # Affichage
        for categorie, options in options_par_type.items():
            rapport += f"### {categorie.upper()}\n"
            for opt_name, count in sorted(options, key=lambda x: x[1], reverse=True)[:5]:
                pourcentage = (count / total_options) * 100
                rapport += f"- **{opt_name}** : {count} utilisations ({pourcentage:.1f}%)\n"
            rapport += "\n"

    
    # Enhanced recommendations section
    rapport += "## 💡 RECOMMANDATIONS STRATÉGIQUES\n"
    
    # MaxIt adoption
    if taux_maxit < 20:
        rapport += "### 🎯 Fidélisation MaxIt\n"
        rapport += " - Offrir des points de fidélité MaxIt ou bonus data/appels pour chaque connexion régulière à l'application\n"
        rapport += " - Créer des offres groupées avec des services partenaires\n"
        rapport += " - Mettre en place un programme de parrainage avec récompenses\n\n"
    
    # Data usage recommendations
    if conso_data_moyenne > 1000:  # High data usage
        rapport += "### 📊 Optimisation des Données\n"
        rapport += "  - Proposer des forfaits data plus adaptés aux gros consommateurs\n"
        rapport += "  - Mettre en avant les options de partage de données\n"
        rapport += "  - Offrir des bonus data pour fidélisation\n\n"
    
    # Voice usage recommendations
    if conso_voix_moyenne > 100:  # High voice usage
        rapport += "### 📞 Optimisation des Appels\n"

        rapport += " - Mettre en avant dans MaxIt les **nouveaux forfaits Flexi ou Combo** pour les utilisateurs à forte consommation\n"
        rapport += "  - Proposer des offres de nuit et week-end\n"
        rapport += " - Offrir une option de cumul de données non utilisées pour les clients fidèles (affiché sur MaxIt \n"
    
 
    if taux_maxit < 20:
        rapport += "- ✅ Bonne adoption de MaxIt, envisager fidélisation premium.\n"
    
    if montant_recharge_moyen < montant_achat_moyen * 0.5:
        rapport += "- ⚠️ Opportunité : Taux de conversion achat->recharge faible, envisager offres groupées.\n"
    
    if conso_data_moyenne > 20000:
        rapport += "- 📡 Proposer des forfaits data plus importants pour les gros consommateurs.\n"
    elif conso_data_moyenne < 1000:
        rapport += "- 📱 Mettre en avant des forfaits voix/SMS pour petits consommateurs.\n"
    
    if total_jeux < nb_clients * 0.1:
        rapport += "- 🎲 Encourager la participation aux jeux pour dynamiser l'engagement.\n"
    rapport+="### ✉️ Exemple de message marketing à envoyer :\n"
    rapport+="Marhbé ! Active ton compte MaxIt aujourd’hui et reçois 500 Mo de bienvenue 🎁. Télécharge l'app maintenant !\n"
    rapport+="🎁 Participe au jeu MaxIt ce week-end et gagne jusqu’à 50 DT ! Clique ici 👉 [Lien MaxIt]\n"
    return rapport, taux_maxit

from django.utils import timezone

import re
from collections import Counter
import numpy as np
import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
import logging



@login_required
def vue_rapport_segment(request):
    """
    Affiche le rapport détaillé pour un segment de clients.
    """
    logger.info("Début de la vue rapport segment")
    
    try:
        # Récupération des paramètres de session
        segment_id = request.session.get('segment_id')
        clients_json = request.session.get('clients_json', [])
        segment_type = request.session.get('segment_type', 'acquisition')
        date_debut = request.session.get('date_debut')
        date_fin = request.session.get('date_fin')
        
        # Validation des paramètres
        if not all([segment_id, clients_json, date_debut, date_fin]):
            messages.error(request, "Informations de session incomplètes pour le rapport segment")
            return redirect('marketing_dashboard:vue_filtres_segment')

        # Convert segment_id back to a dictionary for session storage
        criteres = segment_id.split('_')
        criteres = {criteres[i]: criteres[i+1] for i in range(0, len(criteres)-1, 2)}

        # Génération du rapport
        logger.debug("Génération du rapport...")
        rapport_text, taux_maxit = generer_rapport_marketing_segment_complet(
            segment_id, clients_json, segment_type
        )
        request.session['rapport_segment'] = rapport_text
        rapport = parse_rapport_segment(rapport_text)
        rapport = enrichir_rapport_segment(rapport, clients_json)
        request.session['rapport_enrichi'] = rapport
        request.session['taux_maxit'] = taux_maxit
        # Journalisation du rapport généré
        logger.debug("Rapport généré avec succès", extra={
            'sections': list(rapport.keys()),
            'rapport_length': len(str(rapport))
        })
        logger.debug("Génération du rapport", extra={'rapport': str(rapport)[:100] + '...' if len(str(rapport)) > 500 else str(rapport)})
        log_action(
        request=request,
        action_type='Rapport',
        description=f"Rapport du segment {request.session.get('segment_id')}",
        target_type='segment',
        target_id=request.session.get('segment_id')
    )

        # Préparation du contexte
        contexte = {
            'rapport': rapport,
            'json_client': json.dumps(clients_json, cls=NumpyEncoder, ensure_ascii=False),
            'date_generation': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'periode_analyse': f"du {date_debut} au {date_fin}"
        }
        segment_id = request.session.get('segment_id')
        logger.info("Rendu du template segment_rapport.html")
        # Store the criteria as a dictionary in the session
        request.session['segment_criteria'] = criteres
        
        return render(request, 'marketing_dashboard/segment_rapport.html', contexte)
        
    except Exception as e:
        logger.critical(f"Erreur inattendue dans vue_rapport_segment: {str(e)}", exc_info=True)
        messages.error(request, "Une erreur inattendue s'est produite")
        return redirect('marketing_dashboard:vue_filtres_segment')


def handle_rapport_post_actions(request):
    """
    Gère les actions POST spécifiques à la vue rapport
    """
    logger = logging.getLogger(__name__)
    
    if 'export_pdf' in request.POST:
        logger.info("Export PDF demandé")
        try:
            return export_rapport_pdf(request)
        except Exception as e:
            logger.error("Échec de l'export PDF", exc_info=True)
            messages.error(request, "Erreur lors de l'export PDF")
            return redirect('marketing_dashboard:vue_rapport_segment')

    elif 'recommandations' in request.POST:
        logger.info("Redirection vers les recommandations")
        return redirect('marketing_dashboard:vue_recommandations_segment')

    elif 'messages' in request.POST:
        logger.info("Redirection vers les messages")
        return redirect('marketing_dashboard:vue_messages_segment')
    elif 'filtrer' in request.POST:
        logger.info("Redirection vers nouveau filtrage")
        return redirect('marketing_dashboard:vue_filtres_segment')


    return None

@login_required
def vue_catalogue_maxit(request):
    """
    Affiche le catalogue MaxIt des options disponibles
    """
    try:
        # Chemin vers le fichier catalogue.csv
        catalogue_path = os.path.join(settings.BASE_DIR, 'catalogue.csv')
        
        # Lire le fichier CSV avec pandas
        df = pd.read_csv(catalogue_path)
        
        # Convertir le DataFrame en liste de dictionnaires pour le template
        options = df.to_dict('records')
        
        # Calculer le prix en DT (diviser par 1000)
        for option in options:
            if 'prix' in option and pd.notnull(option['prix']):
                option['prix_dt'] = round(option['prix'] / 1000, 3)
            else:
                option['prix_dt'] = 0
                
        # Filtrer les options par type
        options_voix = [opt for opt in options if opt.get('type') == 'voix']
        options_data = [opt for opt in options if opt.get('type') == 'data']
        options_combo = [opt for opt in options if opt.get('type') == 'voix/data']
        
        context = {
            'options_voix': options_voix,
            'options_data': options_data,
            'options_combo': options_combo,
            'total_options': len(options)
        }

        
        return render(request, 'marketing_dashboard/catalogue_maxit.html', context)
        
    except Exception as e:
        messages.error(request, f"Erreur lors du chargement du catalogue: {str(e)}")
        return redirect('marketing_dashboard:home')

def export_rapport_pdf(request):
    """
    Génère un PDF à partir du rapport
    """
    rapport_text = request.session.get('rapport_text', '')
    segment_id = request.session.get('segment_id', 'inconnu')
    
    # Conversion du markdown en HTML puis en PDF
    html = markdown.markdown(rapport_text)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_{segment_id}.pdf"'
    
    pisa_status = pisa.CreatePDF(
        html,
        dest=response,
        encoding='utf-8'
    )
    
    if pisa_status.err:
        raise Exception("Erreur de génération PDF")
    
    return response
def vue_recommandations_segment(request):
    """
    Affiche les recommandations pour un segment de clients.
    Gère la sérialisation des DataFrames pour le stockage en session.
    """
    import logging
    from django.contrib import messages
    from django.shortcuts import render, redirect
    import pandas as pd
    import json
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    def dataframe_to_dict(df):
        """Convertit un DataFrame en une structure sérialisable."""
        if df is None or df.empty:
            return []
        return df.to_dict(orient='records')
    
    def handle_error(request, error_message, redirect_view='marketing_dashboard:vue_filtres_segment'):
        """Généralise la gestion des erreurs avec journalisation."""
        logger.error(error_message, exc_info=True)
        messages.error(request, error_message)
        return redirect(redirect_view)
    
    # Vérifier que les données nécessaires sont présentes dans la session
    required_session_keys = ['segment_criteria', 'date_debut', 'date_fin', 'segment_type', 'all_options_data']
    if not all(key in request.session for key in required_session_keys):
        return handle_error(
            request, 
            "Session expirée ou données manquantes. Veuillez re-sélectionner votre segment."
        )
    
    try:
        # Récupérer les données des options depuis la session
        
        all_options_data = request.session.get('all_options_data', [])
        
        # Vérifier que les données sont présentes
        if not all_options_data:
            return handle_error(
                request,
                "Aucune donnée de segment disponible. Veuillez d'abord sélectionner un segment."
            )
        
        # Convertir les données en DataFrame
        try:
            all_options = pd.DataFrame(all_options_data)
        except Exception as e:
            logger.error(f"Erreur lors de la conversion des données en DataFrame: {str(e)}", exc_info=True)
            return handle_error(
                request,
                "Erreur lors du traitement des données du segment. Veuillez réessayer."
            )
        
        criteres = request.session.get('segment_criteria', {})
        
        # Créer une copie sérialisable pour la session
        df_consommations = all_options.copy()
        
        # Stocker les données sérialisées dans la session
        
        # Charger le catalogue
        try:
            catalogue = pd.read_csv(CATALOGUE_PATH)
        except Exception as e:
            logger.error(f"Erreur lors du chargement du catalogue: {str(e)}", exc_info=True)
            return handle_error(
                request,
                "Erreur lors du chargement du catalogue des offres. Veuillez réessayer plus tard."
            )
        
        # Générer les recommandations
        try:
            options, profil = dataframe_recommandations_vers_json(all_options, catalogue)
            print('recommandation completes')
            # Stocker les options sérialisées dans la session
            
            # Convertir options en DataFrame pour nettoyer les doublons
            df_options = pd.DataFrame(option for option in options) if options else pd.DataFrame()
            
            # Nettoyer les doublons en gardant la meilleure recommandation (meilleur score)
            if not df_options.empty:
                df_options = df_options.sort_values('score_similarite', ascending=False)
                df_options = df_options.drop_duplicates(subset=['id'], keep='first')
            
            # Préparer les données pour le template
            formatted_options = []
            for _, option in df_options.iterrows():
                data_mo, voice_min, _ = extract_volumes_views(option)
                formatted_options.append({
                    'nom': option.get('name', ''),
                    'type': option.get('type', '').capitalize(),
                    'volume_data': data_mo,
                    'volume_voix': voice_min,
                    'duree': option.get('duree', 0),
                    'prix': option.get('prix', 0),
                    'promo': option.get('promo', False),
                                'promo_flag': "🔥 Promo !" if option.get('promo', False) else "",

                    'international': option.get('international', False),
                    'score': option.get('score_similarite', 0)
                })
            
            # Préparer les options actives
            comportement_options = []
            df_consommations=df_consommations.sort_values('date_achat')
            if not df_consommations.empty:
                
                for _, row in df_consommations.iterrows():
                    data_mo, voice_min, _ = extract_volumes_views(row)
                    msisdn=row.get('msisdn', '')
                    date_activation = str(row.get('date_achat', ''))
                    
                    duree = row.get('duree_data', 0) if (row.get('type') == 'data' or row.get('type') == 'Data') else row.get('duree_voix', 0)
                    
                    comportement_options.append({
                        'msisdn': msisdn,
                        'nom': row.get('name', ''),
                        'type': row.get('type', '').capitalize(),
                        'date_activation': date_activation,
                        'volume_data': data_mo,
                        'volume_voix': voice_min,
                        'duree': duree,
                        'prix': row.get('prix', 0),
                        'international': row.get('international', False),
                        'promo': row.get('promo', False)
                    })

            # Préparer le catalogue pour le template
            catalogue_options = []
            if not catalogue.empty:
                for _, row in catalogue.iterrows():
                    data_mo, voice_min, _ = extract_volumes_views(row)
                    duree = row.get('duree_data', 0) if row.get('type') == 'data' else row.get('duree_voix', 0)
                    
                    catalogue_options.append({
                        'nom': row.get('name', ''),
                        'type': row.get('type', '').capitalize(),
                        'volume_data': data_mo,
                        'volume_voix': voice_min,
                        'duree': duree,
                        'prix': row.get('prix', 0),
                        'international': "Oui" if row.get('international', False) else "Non",
                        'promo': "Oui" if row.get('promo', False) else "Non"
                    })

            if request.method == 'POST' and 'messages' in request.POST:
                return redirect('vue_messages_segment')
            if request.method == 'POST' and 'catalog' in request.POST:
                return redirect('vue_catalogue_maxit')
            log_action(
        request=request,
        action_type='Recommandations',
        description=f"Recommandations du segment {request.session.get('segment_id')}",
        target_type='segment',
        target_id=request.session.get('segment_id')
    )

            return render(request, 'marketing_dashboard/segment_recommandations.html', {
                'options': formatted_options,
                'comportement_options': comportement_options,
                'catalogue': catalogue_options,
                'criteres': criteres,
                'profil': {
                    'data_volume': profil.get('data_volume', 0),
                    'voice_volume': profil.get('voice_volume', 0),
                    'duree': profil.get('duree', 0),
                    'international': profil.get('international', 0),
                    'promo': profil.get('promo', 0),
                    'depense_actuelle': profil.get('depense_actuelle', 0)
                }
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des recommandations: {str(e)}", exc_info=True)
            return handle_error(
                request,
                "Une erreur est survenue lors de la génération des recommandations. Veuillez réessayer."
            )
    
    except Exception as e:
        logger.critical(f"Erreur inattendue dans vue_recommandations_segment: {str(e)}", exc_info=True)
        return handle_error(
            request,
            "Une erreur inattendue s'est produite. Veuillez réessayer ou contacter le support technique."
        )
@login_required
def vue_messages_segment(request):
    """
    Affiche les messages marketing générés pour un segment de clients.
    Structure similaire à vue_messages_marketing mais adaptée aux segments.
    """
    from django.utils.safestring import mark_safe
    import json
    import logging
    from django.conf import settings
    from datetime import datetime
    from django.core.exceptions import ValidationError
    
    logger = logging.getLogger(__name__)
    
    def handle_error(request, error_message, redirect_view='marketing_dashboard:vue_filtres_segment', log_exception=None):
        """Généralise la gestion des erreurs avec journalisation."""
        logger.error(error_message, exc_info=log_exception)
        messages.error(request, error_message)
        return redirect(redirect_view)
    
    def construire_messages_par_defaut():
        """Construit un dictionnaire de messages par défaut."""
        return {
            'acquisition': [
                "Nous n'avons pas pu générer de messages personnalisés. "
                "Découvrez comment nos solutions peuvent répondre aux besoins spécifiques de vos clients !"
            ],
            'jeux_et_fidelisation': [],
            'options_recommandees': [],
            'services_marketplace': [],
            'messages_personnalises': []
        }
    
    def format_messages(messages_dict):
        """Formate les messages pour assurer qu'ils sont des chaînes de caractères."""
        if not messages_dict:
            return {}
            
        result = {}
        for key, messages in messages_dict.items():
            if not messages:
                result[key] = []
                continue
                
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    formatted_messages.append(msg.get('message', str(msg)))
                elif isinstance(msg, str):
                    formatted_messages.append(msg)
                else:
                    formatted_messages.append(str(msg))
            result[key] = formatted_messages
            
        return result
    
    try:
        # Récupération des paramètres de session
        segment_id, date_debut, date_fin, criteres = get_params_session_segment(request)
        
        # Initialisation des variables
        messages_segment = construire_messages_par_defaut()
        rapport = None
        rapport_enrichi = None
        
        try:
            # 1. Génération des messages d'options
            catalogue = pd.read_csv(CATALOGUE_PATH)
            all_options_data = request.session.get('all_options_data', [])
            rapport = request.session.get('rapport_segment')
            
            # Conversion de all_options_data en DataFrame si nécessaire
            if all_options_data and isinstance(all_options_data, list):
                df_options = pd.DataFrame(all_options_data)
                # Vérification des colonnes nécessaires
                required_columns = {'id', 'name', 'type', 'data_volume', 'voice_volume', 
                                  'duree_data', 'duree_voix', 'prix', 'promo', 'international'}
                missing_columns = required_columns - set(df_options.columns)
                
                if missing_columns:
                    logger.warning(f"Colonnes manquantes dans all_options_data: {missing_columns}")
                    # Création des colonnes manquantes avec des valeurs par défaut
                    for col in missing_columns:
                        if col in ['data_volume', 'voice_volume', 'duree_data', 'duree_voix', 'prix']:
                            df_options[col] = 0
                        elif col in ['promo', 'international']:
                            df_options[col] = False
                        else:
                            df_options[col] = ''
            else:
                df_options = pd.DataFrame(columns=['id', 'name', 'type', 'data_volume', 'voice_volume', 
                                                'duree_data', 'duree_voix', 'prix', 'promo', 'international'])
            
            options, profil = dataframe_recommandations_vers_json(df_options, catalogue)
            taux_maxit = request.session.get('taux_maxit', 3)
            rapport_enrichi = request.session.get('rapport_enrichi', [])
            clients_df = pd.DataFrame(request.session.get('clients_df', []))
            
            # Validation des données
            if not all([rapport, not clients_df.empty]):
                raise ValueError("Données de session incomplètes pour la génération des messages")
            
            # Chargement du catalogue et génération des recommandations
            messages_options = generer_messages_options_segment(options, profil, clients_df)
            
            if not messages_options:
                logger.warning("Aucun message d'option généré pour le segment")
            else:
                logger.info(f"{len(messages_options)} messages d'options générés avec succès")
            
            # Génération des messages marketing
            from .utils import generate_segment_marketing_messages
            max_retries = int(taux_maxit)
            
            messages_segment = generate_segment_marketing_messages(
                rapport_enrichi,
                messages_options,
                taux_maxit,
                max_retries=max_retries
            )
            
            # Formatage des messages
            messages_segment = format_messages(messages_segment)
            
            # Enregistrement des messages dans la session
            request.session['segment_messages'] = messages_segment
            request.session.modified = True
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des messages: {str(e)}", exc_info=True)
            messages_segment = construire_messages_par_defaut()
            messages_segment['acquisition'].append(
                "Une erreur est survenue lors de la génération des messages. "
                "Veuillez réessayer ou contacter le support technique."
            )
        
        # Construction de la conversation pour l'affichage
        conversation = []
        
        # Message de bienvenue
        conversation.append({
            'type': 'agent',
            'content': f"🔍 J'ai analysé le segment '{segment_id}' pour la période du {date_debut} au {date_fin}. Voici mes recommandations :",
            'timestamp': datetime.now().strftime('%H:%M')
        })
        
        # Profil du segment
        if profil:
            profil_text = "👥 <strong>Profil du segment :</strong><br>"
            if 'data_volume' in profil:
                profil_text += f"📊 Données moyennes : {profil['data_volume']} Mo<br>"
            if 'voice_volume' in profil:
                profil_text += f"📞 Appels moyens : {profil['voice_volume']} min<br>"
            if 'duree' in profil:
                profil_text += f"⏱️ Ancienneté moyenne : {profil['duree']} jours<br>"
            if 'depense_actuelle' in profil:
                profil_text += f"💰 Dépense moyenne : {profil['depense_actuelle']} DT"
                
            conversation.append({
                'type': 'agent',
                'content': profil_text,
                'timestamp': datetime.now().strftime('%H:%M')
            })
        
        # Catégories de messages
        categories = [
            ('acquisition', '💡 Acquisition', 'Voici comment améliorer l\'acquisition :'),
            ('jeux_et_fidelisation', '🎮 Jeux & Fidélisation', 'Découvrez nos offres de fidélité :'),
            ('options_recommandees', '📊 Options Recommandées', 'Voici nos recommandations personnalisées :'),
            ('services_marketplace', '🛍️ Services & Partenaires', 'Nos offres partenaires exclusives :'),
            ('messages_personnalises', '✨ Messages Sur-Mesure', 'Des offres spécialement pour vous :')
        ]
        
        for cle, titre, intro in categories:
            if messages_segment.get(cle) and isinstance(messages_segment[cle], list):
                # Message de la catégorie
                conversation.append({
                    'type': 'category',
                    'title': titre,
                    'content': intro,
                    'timestamp': datetime.now().strftime('%H:%M')
                })
                
                # Messages de l'agent pour cette catégorie
                for message in messages_segment[cle]:
                    if isinstance(message, str):
                        conversation.append({
                            'type': 'agent',
                            'content': message,
                            'timestamp': datetime.now().strftime('%H:%M')
                        })
        
        # Message de conclusion
        conversation.append({
            'type': 'agent',
            'content': "💡 Ces recommandations sont basées sur l'analyse de votre segment. N'hésitez pas à me poser des questions !",
            'timestamp': datetime.now().strftime('%H:%M')
        })
        
        # Préparation du contexte pour le template
        context = {
            'conversation': mark_safe(json.dumps(conversation, ensure_ascii=False)),
            'segment_nom': segment_id,
            'periode': f"{date_debut} au {date_fin}",
            'has_messages': any(messages_segment.values())
        }
        log_action(
        request=request,
        action_type='Messages',
        description=f"Messages du segment {segment_id}",
        target_type='segment',
        target_id=segment_id
    )
        return render(request, 'marketing_dashboard/segment_chat_messages.html', context)
        
    except Exception as e:
        logger.critical(f"Erreur inattendue dans vue_messages_segment: {str(e)}", exc_info=True)
        return handle_error(
            request,
            "Une erreur inattendue s'est produite. Veuillez réessayer ou contacter le support technique.",
            log_exception=e
        )
def build_conversation(segment_info, messages_segment):
    """Construit la conversation à afficher à l'utilisateur."""
    from datetime import datetime
    from django.utils.safestring import mark_safe
    import json
    
    try:
        conversation = []
        
        # Message d'introduction
        conversation.append({
            'type': 'agent',
            'content': f" J'ai analysé le segment '{segment_info['segment_nom']}' "
                      f"({segment_info['segment_taille']} clients). Voici mes recommandations marketing :",
            'timestamp': datetime.now().strftime('%H:%M')
        })
        
        # Détails du segment
        segment_details = (
            f" <strong>Détails du segment :</strong><br>"
            f" Taille : {segment_info['segment_taille']} clients<br>"
            f" Dernière analyse : {segment_info['date_analyse']}<br>"
            f" Critères : {segment_info['criteres_segmentation']}"
        )
        
        conversation.append({
            'type': 'agent',
            'content': segment_details,
            'timestamp': datetime.now().strftime('%H:%M')
        })
        
        # Ajout des messages par catégorie
        for category, messages in messages_segment.items():
            if messages:  # Ne pas ajouter de catégories vides
                # En-tête de catégorie
                conversation.append({
                    'type': 'system',
                    'content': f"--- {category.upper().replace('_', ' ')} ---",
                    'timestamp': datetime.now().strftime('%H:%M')
                })
                
                # Messages de la catégorie
                for message in messages:
                    conversation.append({
                        'type': 'agent',
                        'content': message,
                        'timestamp': datetime.now().strftime('%H:%M')
                    })
        
        # Convertir la conversation en JSON
        conversation_json = json.dumps(conversation, ensure_ascii=False)
        
        # Préparer le contexte pour le template
        context = {
            'conversation_json': mark_safe(conversation_json),
            'segment_nom': segment_info.get('segment_nom', 'Segment inconnu'),
            'segment_taille': segment_info.get('segment_taille', 0),
            'criteres_segmentation': segment_info.get('criteres_segmentation', 'Non spécifiés'),
            'date_analyse': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'has_messages': any(messages_segment.values())
        }
        
        return render(request, 'marketing_dashboard/segment_chat_messages.html', context)
        
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur dans build_conversation: {str(e)}")
        logger.error(traceback.format_exc())
        
        # En cas d'erreur, retourner une conversation d'erreur
        error_conversation = [{
            'type': 'agent',
            'content': "Désolé, une erreur est survenue lors de la génération des recommandations pour ce segment.",
            'timestamp': datetime.now().strftime('%H:%M')
        }]
        
        return render(request, 'marketing_dashboard/segment_chat_messages.html', {
            'conversation_json': mark_safe(json.dumps(error_conversation, ensure_ascii=False)),
            'segment_nom': 'Erreur',
            'segment_taille': 0,
            'criteres_segmentation': 'Non disponibles',
            'date_analyse': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'has_messages': False
        })


def parse_markdown_rapport(rapport_text):
    """
    Parse un rapport markdown en un dictionnaire structuré.
{{ ... }}
    
    Args:
        rapport_text (str): Le texte du rapport markdown
        
    Returns:
        dict: Un dictionnaire contenant les sections du rapport
    """
    if not rapport_text:
        return {}
        
    # Découper le texte en lignes
    lines = rapport_text.split('\n')
    
    # Initialiser le dictionnaire de résultat
    result = {}
    current_section = None
    current_content = []
    
    # Expressions régulières pour détecter les titres de section
    section_pattern = re.compile(r'^#+\s*(.+?)\s*$')
    
    for line in lines:
        # Vérifier si c'est une ligne de section
        section_match = section_pattern.match(line)
        
        if section_match:
            # Si on avait une section en cours, on l'ajoute au résultat
            if current_section:
                result[current_section] = '\n'.join(current_content).strip()
                current_content = []
            
            # Nouvelle section
            current_section = section_match.group(1).strip('# ').strip()
        else:
            # Ligne de contenu
            if line.strip() or current_content:
                current_content.append(line.strip())
    
    # Ajouter la dernière section
    if current_section and current_content:
        result[current_section] = '\n'.join(current_content).strip()
    
    return result

#segmentation
import json
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.urls import reverse

# Import des modules personnalisés
from .models import *
from .utils import *
from .forms import *

# Configuration du logger

from django.shortcuts import render, redirect
from .forms import UploadSegmentationFilesForm
import pandas as pd
from .segmentation import create_client_info
from .segmentation import *
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.urls import reverse
import logging

# Configure logging
logger = logging.getLogger(__name__)
save_dir=os.path.join(settings.BASE_DIR, 'segmentation_results')
@require_http_methods(["GET", "POST"])
def vue_segmenter(request):
    if request.method == "POST":
        form = UploadSegmentationFilesForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Clear any existing session data
                if 'df_segmentation' in request.session:
                    del request.session['df_segmentation']
                if 'achats_filename' in request.session:
                    del request.session['achats_filename']
                if 'recharges_filename' in request.session:
                    del request.session['recharges_filename']
                if 'spins_filename' in request.session:
                    del request.session['spins_filename']
                
                # Read and process the files
                achats_df = pd.read_csv(form.cleaned_data['achats_file'])
                recharge_df = pd.read_csv(form.cleaned_data['recharges_file'])
                roue_df = pd.read_csv(form.cleaned_data['spins_file'])
              
                


                # Verify required columns (already validated client-side, but double-check for security)
                required_achats_columns = {'msisdn', 'event_date'}
                required_recharge_columns = {'msisdn', 'event_date'}
                required_roue_columns = {'msisdn', 'entry_date_hist'}

                if not required_achats_columns.issubset(achats_df.columns):
                    raise ValueError("Le fichier d'achats doit contenir les colonnes: " + 
                                   ", ".join(required_achats_columns))
                if not required_recharge_columns.issubset(recharge_df.columns):
                    raise ValueError("Le fichier de recharges doit contenir les colonnes: " + 
                                   ", ".join(required_recharge_columns))
                if not required_roue_columns.issubset(roue_df.columns):
                    raise ValueError("Le fichier de jeux doit contenir les colonnes: " + 
                                   ", ".join(required_roue_columns - roue_df.columns.intersection(required_roue_columns)))

                # Process and merge data
                df_achat_recharge = pd.merge(
                    achats_df, recharge_df,
                    on=["msisdn", "event_date"],
                    how="outer",
                    suffixes=('_achat', '_recharge')
                )
                
                final_df = pd.merge(
                    df_achat_recharge, roue_df,
                    left_on=["msisdn", "event_date"],
                    right_on=["msisdn", "entry_date_hist"],
                    how="outer"
                )
                print('joiture complete')
                # Create client info and store in session
                final_df = create_client_info(final_df)
                final_df.to_csv(os.path.join(save_dir, "client_info.csv"), index=False)
                print('creation de cleint_df')
                print("colonnes",final_df.columns)
                # Store data in session
                request.session["df_segmentation"] = final_df.to_json(orient="split")
                request.session["achats_filename"] = form.cleaned_data['achats_file'].name
                request.session["recharges_filename"] = form.cleaned_data['recharges_file'].name
                request.session["spins_filename"] = form.cleaned_data['spins_file'].name
                request.session.modified = True
                
                # Handle AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Fichiers traités avec succès',
                        'redirect_url': reverse('marketing_dashboard:vue_resultats_segmenter')
                    })
                log_action(
            request=request,
            action_type='SEGMENTATION',
            description=f"Segmentation des clients",
            target_type='segment',
            target_id=None
        )
                return redirect("marketing_dashboard:vue_resultats_segmenter")
                
            except Exception as e:
                error_msg = f"Erreur lors du traitement des fichiers: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': error_msg
                    }, status=400)
                    
                messages.error(request, error_msg)
            
        else:
            # Form is not valid
            error_msg = "Veuillez corriger les erreurs ci-dessous."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': error_msg,
                    'errors': form.errors
                }, status=400)
                
            messages.error(request, error_msg)
    else:
        form = UploadSegmentationFilesForm()
    
    # Handle GET request or invalid form
    context = {
        'form': form,
        'page_title': 'Téléversement des fichiers de segmentation',
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'error',
            'message': 'Requête invalide',
            'html': render_to_string('marketing_dashboard/segment_upload_form.html', context, request=request)
        }, status=400)
        
    return render(request, "marketing_dashboard/segment_upload_form.html", context)

from .segmentation import segmenter_clients
import json
import re


def vue_resultats_segmenter(request):
    json_data = request.session.get("df_segmentation", None)
    if not json_data:
        return redirect("marketing_dashboard:vue_segmenter")
    
    # Get uploaded filenames from session
    achats_filename = request.session.get("achats_filename", "Achats.csv")
    recharges_filename = request.session.get("recharges_filename", "Recharges.csv")
    spins_filename = request.session.get("spins_filename", "Spins.csv")
    
    # Define the segmentation guide with display names and actual column names
    segmentation_guide={
    "rentabilité":["rentabilite","nb_achat","nb_recharge","frequence_utilisation_mensuelle","moy_recharge",'duree_moyenne_option'],
    "engagement":['est_utilisateur_actif','frequence_utilisation_mensuelle','engagement_score','engagement_level'],
    "type_client":['type_client','frequence_utilisation_mensuelle','type_usage'],
    "type_interet":['interet','duree_moyenne_option'],
    "interet_international":['type_usage','interet_international','source_achat','interet'],
    "interet_jeu":['nombre_jeu','win_count'],
    "interet_promo":['interet_promo','reponse_promo',],
    "action":['nombre_jeu','nb_recharge', 'nb_achat','action_majoritaire']
}

    df = pd.read_json(json_data, orient="split")
    df_copy=df.copy()
    df_copy=df_copy.drop_duplicates(subset=["msisdn"], keep="first").reset_index(drop=True)
    total_clients = len(df_copy)
    
    # Create statistics for each criterion
    criterion_stats = {}
    for critere in segmentation_guide.keys():
        print(f"→ Segmentation selon {critere}")
        df = segmenter_clients(df, critere_segmentation=critere, acquisition=True)
        df.drop(columns=['segments'], inplace=True)
        print(f'segmentation selon crietere {critere} terminée')
        critere=f"segment_{critere}"
        print(f'critere {critere}')

      
        
        # Use the correct column name (without accents) for accessing the data
        value_counts = df[critere].value_counts().to_dict()
        percentages = {k: (v / total_clients) * 100 for k, v in value_counts.items()}
        df.to_csv("segmentation.csv", index=False)
        # Store results using the display name
        criterion_stats[critere] = {            'counts': value_counts,
            'pourcentages': percentages
        }
    
    # Prepare client sample for the table (first 10 records)
    clients_sample = df.head(10).to_dict('records')
    if request.method == 'POST' and 'client' in request.POST:
        return redirect('vue_formulaire_client')
    if request.method == 'POST' and 'segment' in request.POST:
        return redirect('vue_filtres_segment')
    context = {
        'total_clients': total_clients,
        'criterion_stats': criterion_stats,
        'clients_sample': clients_sample,
        'achats_filename': achats_filename,
        'recharges_filename': recharges_filename,
        'spins_filename': spins_filename,
    }
    
    return render(request, "marketing_dashboard/segment_upload_result.html", context)

import os
from datetime import timedelta
import pandas as pd
import re
import pandas as pd
from django.shortcuts import render, redirect
from .forms import UploadChurnFilesForm


#pour tables:
import os
import pandas as pd
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render

# Dossier contenant les fichiers de données
# Utilisation de data_client qui est à la racine du projet
folder_path = os.path.join(settings.BASE_DIR,  'data')

print(f"Chemin du dossier de données: {folder_path}")
print(f"Le dossier existe: {os.path.exists(folder_path)}")

if os.path.exists(folder_path):
    print(f"Contenu du dossier: {os.listdir(folder_path)}")

def get_csv_files():
    """Récupère tous les fichiers CSV du dossier de données"""
    try:
        if not os.path.exists(folder_path):
            print(f"ERREUR: Le dossier {folder_path} n'existe pas!")
            return []
            
        all_files = os.listdir(folder_path)
        print(f"Fichiers trouvés: {all_files}")
        
        csv_files = [f for f in all_files if f.endswith(".csv")]
        print(f"Fichiers CSV trouvés: {csv_files}")
        
        return sorted(csv_files)
    except Exception as e:
        print(f"ERREUR lors de la lecture du dossier {folder_path}: {str(e)}")
        return []


def get_file_type(filename):
    """Détermine le type de fichier (achat, recharge, consommation, etc.)"""
    filename = filename.lower()
    if 'achat' in filename:
        return 'achat'
    elif 'recharge' in filename:
        return 'recharge'
    elif 'consommation' in filename:
        return 'consommation'
    elif 'client_info' in filename:
        return 'client_info'
    elif 'segmentation' in filename:
        return 'segmentation'
    elif 'churn' in filename:
        return 'churn'
    return 'autre'

def extract_month_year(filename):
    """Extrait le mois et l'année du nom de fichier"""
    import re
    # Cherche les motifs YYYY-MM ou MM-YYYY ou YYYY_MM ou MM_YYYY
    match = re.search(r'(\d{4})[-_](\d{2})|(\d{2})[-_](\d{4})', filename)
    if match:
        groups = match.groups()
        if groups[0] and groups[1]:  # format YYYY-MM ou YYYY_MM
            year = int(groups[0])
            month = int(groups[1])
        else:  # format MM-YYYY ou MM_YYYY
            year = int(groups[3])
            month = int(groups[2])
        return f"{year}-{month:02d}"
    return None

from .forms import TableFilterForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib import messages
from django.conf import settings
import pandas as pd
import os
@login_required
def vue_tables(request):
    """
    Vue pour afficher les données tabulaires avec filtrage et recherche.
    Gère à la fois les requêtes normales et AJAX pour le filtrage dynamique.
    """
    try:
        # Récupérer tous les fichiers disponibles
        available_files = get_csv_files()
        
        # Vérifier si c'est une requête AJAX pour le filtrage
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Initialiser le formulaire avec les fichiers disponibles
        form = TableFilterForm(
            data=request.GET or None,
            fichiers_disponibles=available_files
        )
        
        # Variables pour le contexte
        donnees = []
        colonnes = []
        fichier_selectionne = None
        total_lignes = 0
        fichiers_filtres = available_files
    
        # Traiter le formulaire s'il est valide
        if form.is_valid():
            # Récupérer les données du formulaire
            print(form.cleaned_data)
            type_fichier = form.cleaned_data.get('type_fichier')
            mois = form.cleaned_data.get('mois')
            fichier = form.cleaned_data.get('fichier')
            terme_recherche = form.cleaned_data.get('recherche', '').strip()
            
            # Filtrer les fichiers disponibles selon les critères
            fichier = form.cleaned_data.get('fichier')
            fichiers_filtres = form.filtrer_fichiers(available_files)
            if fichiers_filtres:
                fichier = fichiers_filtres[0]
                print(fichier)
            else:
                fichier = None
                print("Aucun fichier sélectionné")
            
            # Si c'est une requête AJAX, renvoyer uniquement la liste des fichiers filtrés
            if is_ajax:
                fichiers_data = [{'nom': fichier, 'type': get_file_type(fichier)}]
                return JsonResponse({'fichiers': fichiers_data})
                
            # Si un fichier est sélectionné, charger ses données
            if fichier :
                try:
                    # Construire le chemin complet du fichier
                    filepath = os.path.join(folder_path, fichier)
                    print(f"Chemin du fichier: {filepath}")
                    print(f"Le fichier existe: {os.path.exists(filepath)}")
                    # Vérifier si le fichier existe
                    if not os.path.exists(filepath):
                        messages.error(request, f"Le fichier {fichier} n'existe pas à l'emplacement: {filepath}")
                    else:
                        # Lire le fichier CSV avec pandas (limité à 1000 lignes pour des raisons de performance)
                        try:
                            df = pd.read_csv(filepath, nrows=1000, encoding='utf-8')
                            print(f"Fichier chargé avec succès. Nombre de lignes: {len(df)}")
                            print(f"Colonnes: {df.columns.tolist()}")
                        except Exception as e:
                            print(f"Erreur lors de la lecture du fichier: {str(e)}")
                            raise

                        total_lignes = len(df)
                        print(total_lignes)
                        fichier_selectionne = fichier
                        
                        # Récupérer les noms des colonnes
                        colonnes = [str(col).strip() for col in df.columns.tolist()]
                        print(colonnes)
                        
                        
                        # Convertir en format de données pour le template
                        donnees = df.to_dict(orient='records')
        
                except Exception as e:
                    messages.error(request, f"Erreur lors de la lecture du fichier {fichier} : {str(e)}")
        
        # Pagination
        paginate_by = 20  # Nombre d'éléments par page
        paginator = Paginator(donnees, paginate_by)
        
        # Récupérer le numéro de page depuis la requête
        page_number = request.GET.get('page', 1)
        
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Préparer le contexte avec les noms de variables attendus par le template
        context = {
            'form': form,
            'columns': colonnes,  # Changé de 'colonnes' à 'columns' pour correspondre au template
            'data': donnees,     # Changé de 'donnees' à 'data' pour correspondre au template
            'page_obj': page_obj,
            'selected_file': fichier,
            'total_lignes': total_lignes,
            'fichiers_disponibles': fichiers_filtres,  # Utiliser la liste complète des fichiers filtrés
        }
        
        return render(request, 'marketing_dashboard/tables.html', context)
    
    except Exception as e:
        messages.error(request, f"Une erreur inattendue s'est produite : {str(e)}")
        context = {
            'form': TableFilterForm(),
            'colonnes': [],
            'donnees': [],
            'fichier_selectionne': None,
            'total_lignes': 0,
            'fichiers_disponibles': [],
        }
        
        return render(request, 'marketing_dashboard/tables.html', context)

from django.shortcuts import render, redirect
from .forms import UploadChurnFilesForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
import pandas as pd
from .churn_analysis import analyze_churn



@login_required
def vue_analyser_churn(request):
    """
    Affiche uniquement les résultats de l'analyse de churn
    """
    # Récupérer les résultats de la session
    results = request.session.get('churn_analysis_results')
    
    if not results:
        # Si pas de résultats, rediriger vers la page de traitement
        return redirect('marketing_dashboard:traiter_analyse_churn')
    
    # Préparer le contexte avec les résultats
    context = {
        'form': UploadChurnFilesForm(),
        'analysis_results': results,
        'churn_summary': results.get('churn_summary', {}),
        'total_clients': results.get('total_clients', 0),
        'churn_rate': results.get('churn_rate', 0),
        'start_date': results.get('start_date'),
        'end_date': results.get('end_date'),
        'analysis_date': results.get('analysis_date')
    }
    
    return render(request, 'marketing_dashboard/churn_analysis.html', context)

@login_required
def traiter_analyse_churn(request):
    """
    Affiche le formulaire d'upload et traite la soumission
    """
    if request.method == 'POST':
        form = UploadChurnFilesForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Effacer les résultats précédents
                if 'churn_analysis_results' in request.session:
                    del request.session['churn_analysis_results']
                
                # Lire les fichiers CSV
                achat_df = pd.read_csv(form.cleaned_data['achats_file'])
                recharge_df = pd.read_csv(form.cleaned_data['recharges_file'])
                spin_df = pd.read_csv(form.cleaned_data['spins_file'])
                
                # Effectuer l'analyse de churn
                results = analyze_churn(achat_df, recharge_df, spin_df)
                print("Analyse de churn terminée")
                
                # Les résultats sont déjà sérialisés par analyze_churn
                serializable_results = results
                
                # Stocker les résultats dans la session
                request.session['churn_analysis_results'] = serializable_results
                log_action(
                request=request,
                action_type='UPLOAD',
                description=f"Téléchargement des fichiers pour analyse de churn",
                target_type='fichier',
                target_id=None
            )
                # Rediriger vers la page des résultats
                return redirect('marketing_dashboard:vue_analyser_churn')
                
            except Exception as e:
                error_msg = f"Erreur lors de l'analyse : {str(e)}"
                print(error_msg)
                messages.error(request, error_msg)
                return redirect('marketing_dashboard:traiter_analyse_churn')
    else:
        form = UploadChurnFilesForm()
    
    # Afficher le formulaire d'upload
    return render(request, 'marketing_dashboard/churn_upload_form.html', {'form': form})

@login_required
def vue_analyser_churn(request):
    """
    Affiche uniquement les résultats de l'analyse de churn
    """
    # Récupérer les résultats de la session
    results = request.session.get('churn_analysis_results')
    
    if not results:
        # Si pas de résultats, rediriger vers la page de traitement
        return redirect('marketing_dashboard:traiter_analyse_churn')
    
    # Préparer la liste des mois et taux de churn ordonnés
    churn_summary = results.get('churn_summary', {})
    churn_list = sorted([(month, rate) for month, rate in churn_summary.items()])
    # Calculer le nombre de clients actifs par mois
    churn_data_df = pd.DataFrame(results.get('churn_data', []))
    churn_data_df['month'] = pd.to_datetime(churn_data_df['month'])
    client_counts = churn_data_df.groupby(churn_data_df['month'].dt.to_period('M'))['msisdn'].nunique()
    # Convertir l'index en chaîne pour le template
    client_counts = {str(k): v for k, v in client_counts.items()}
    churn_summary = churn_data_df.groupby('month')['churn'].mean().mul(100).round(2)
    # ne pas faire .strftime ici
    churn_list = sorted([(month, rate) for month, rate in churn_summary.items()])
    active_clients = (
        churn_data_df[churn_data_df['churn'] == False]
        .groupby(churn_data_df['month'].dt.to_period('M'))['msisdn']
        .nunique()
    )
    active_clients = {str(k): v for k, v in active_clients.items()}



    # Préparer le contexte avec les résultats
    context = {
    'form': UploadChurnFilesForm(),
    'analysis_results': results,
    'churn_summary': churn_summary,
    'churn_list': churn_list,
    'total_clients': results.get('total_clients', 0),
    'churn_rate': results.get('churn_rate', 0),
    'start_date': results.get('start_date'),
    'end_date': results.get('end_date'),
    'analysis_date': results.get('analysis_date'),
    'client_counts': client_counts,  # <-- ajouté ici
    'active_clients': active_clients
}

    
    return render(request, 'marketing_dashboard/churn_analysis.html', context)
# Dans views.py
from django.core.paginator import Paginator
from .models import ActionLog
from .templatetags import action_filters

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import ActionLog

@login_required
def historique_campagnes(request):
    # Récupération des paramètres de filtrage
    query = request.GET.get('q', '')
    action_type = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Filtrage de base
    actions = ActionLog.objects.all().select_related('user').order_by('-created_at')
    
    # Application des filtres
    if query:
        actions = actions.filter(
            Q(description__icontains=query) |
            Q(user__username__icontains=query)
        )
    
    if action_type:
        actions = actions.filter(action_type=action_type)
    
    if date_from:
        actions = actions.filter(created_at__date__gte=date_from)
    
    if date_to:
        actions = actions.filter(created_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(actions, 25)  # 25 actions par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'action_types': dict(ActionLog.ACTION_TYPES),
        'search_query': query,
        'selected_type': action_type,
        'date_from': date_from,
        'date_to': date_to,
        # Les filtres sont chargés via le tag {% load action_filters %}
    }
    
    return render(request, 'marketing_dashboard/historique_campagnes.html', context)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json


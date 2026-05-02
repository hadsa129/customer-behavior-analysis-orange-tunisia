import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import glob

class MarketingDataLoader:
    """
    Classe pour charger et traiter les données marketing à partir des fichiers CSV.
    """
    
    def __init__(self, data_dir: str = 'data'):
        """
        Initialise le chargeur de données avec le répertoire des données.
        
        Args:
            data_dir: Chemin vers le dossier contenant les fichiers CSV
        """
        self.data_dir = data_dir
        self.data_cache = {}
    
    def load_client_info(self, month: Optional[str] = None) -> pd.DataFrame:
        """
        Charge les informations sur les clients.
        
        Args:
            month: Format 'MM_YYYY' (ex: '02_2025'). Si None, charge le mois le plus récent.
            
        Returns:
            DataFrame avec les informations des clients
        """
        cache_key = f'client_info_{month}'
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
            
        if month is None:
            # Trouver le fichier le plus récent
            files = glob.glob(os.path.join(self.data_dir, 'df_client_info_*.csv'))
            if not files:
                raise FileNotFoundError("Aucun fichier d'information client trouvé")
            latest_file = max(files, key=os.path.getmtime)
        else:
            latest_file = os.path.join(self.data_dir, f'df_client_info_{month}.csv')
        
        df = pd.read_csv(latest_file)
        self.data_cache[cache_key] = df
        return df
    
    def load_segmentation(self, month: Optional[str] = None) -> pd.DataFrame:
        """
        Charge les données de segmentation des clients.
        """
        cache_key = f'segmentation_{month}'
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
            
        if month is None:
            files = glob.glob(os.path.join(self.data_dir, 'df_segmentation_mois_*.csv'))
            if not files:
                raise FileNotFoundError("Aucun fichier de segmentation trouvé")
            latest_file = max(files, key=os.path.getmtime)
        else:
            latest_file = os.path.join(self.data_dir, f'df_segmentation_mois_{month}.csv')
        
        df = pd.read_csv(latest_file)
        self.data_cache[cache_key] = df
        return df
    
    def load_achats(self, month: Optional[str] = None) -> pd.DataFrame:
        """
        Charge les données d'achats.
        """
        cache_key = f'achats_{month}'
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
            
        if month is None:
            files = glob.glob(os.path.join(self.data_dir, 'achat_*.csv'))
            if not files:
                raise FileNotFoundError("Aucun fichier d'achats trouvé")
            latest_file = max(files, key=os.path.getmtime)
        else:
            latest_file = os.path.join(self.data_dir, f'achat_{month}.csv')
        
        df = pd.read_csv(latest_file, parse_dates=['event_date', 'insert_month_date'])
        self.data_cache[cache_key] = df
        return df
    
    def load_recharges(self, month: Optional[str] = None) -> pd.DataFrame:
        """
        Charge les données de recharges.
        """
        cache_key = f'recharges_{month}'
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
            
        if month is None:
            files = glob.glob(os.path.join(self.data_dir, 'recharge_*.csv'))
            if not files:
                raise FileNotFoundError("Aucun fichier de recharges trouvé")
            latest_file = max(files, key=os.path.getmtime)
        else:
            latest_file = os.path.join(self.data_dir, f'recharge_{month}.csv')
        
        df = pd.read_csv(latest_file, parse_dates=['event_date', 'insert_month_date'])
        self.data_cache[cache_key] = df
        return df
    
    def load_consommation(self, month: Optional[str] = None) -> pd.DataFrame:
        """
        Charge les données de consommation.
        """
        cache_key = f'consommation_{month}'
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
            
        if month is None:
            files = glob.glob(os.path.join(self.data_dir, 'consommation_mois_*.csv'))
            if not files:
                raise FileNotFoundError("Aucun fichier de consommation trouvé")
            latest_file = max(files, key=os.path.getmtime)
        else:
            latest_file = os.path.join(self.data_dir, f'consommation_mois_{month}.csv')
        
        df = pd.read_csv(latest_file, parse_dates=['mois_annee'])
        self.data_cache[cache_key] = df
        return df
    
    def get_available_months(self) -> List[str]:
        """
        Retourne la liste des mois disponibles pour chaque type de données.
        """
        data_types = {
            'client_info': 'df_client_info_',
            'segmentation': 'df_segmentation_mois_',
            'achats': 'achat_',
            'recharges': 'recharge_',
            'consommation': 'consommation_mois_'
        }
        
        available_months = {}
        for key, prefix in data_types.items():
            files = glob.glob(os.path.join(self.data_dir, f'{prefix}*.csv'))
            months = [f.split('_')[-1].replace('.csv', '') for f in files]
            available_months[key] = sorted(months, key=lambda x: datetime.strptime(x, '%Y-%m') if '-' in x else datetime.strptime(x, '%m_%Y'))
        
        return available_months
    
    def get_marketing_kpis(self, month: Optional[str] = None) -> Dict:
        """
        Calcule les KPIs principaux pour le tableau de bord marketing.
        
        Returns:
            Dictionnaire contenant tous les KPIs calculés
        """
        # Charger les données nécessaires
        client_info = self.load_client_info(month)
        segmentation = self.load_segmentation(month)
        achats = self.load_achats(month)
        recharges = self.load_recharges(month)
        consommation = self.load_consommation(month)
        
        # 1. KPIs Achats & Recharges
        kpis = {}
        
        # Top 10 offres achetées
        top_offres = achats['offer_name'].value_counts().head(10).to_dict()
        
        # Répartition achat/recharge
        total_achats = len(achats)
        total_recharges = len(recharges)
        total_transactions = total_achats + total_recharges
        
        repartition = {
            'achats': (total_achats / total_transactions * 100) if total_transactions > 0 else 0,
            'recharges': (total_recharges / total_transactions * 100) if total_transactions > 0 else 0
        }
        
        # Source d'achat préférée
        source_achat = achats['login'].value_counts().to_dict()
        
        # Montants moyens
        montant_moyen_achat = achats['prix'].mean()
        montant_moyen_recharge = recharges['amount'].mean()
        
        # 2. Comportement de consommation
        conso_moyenne = consommation[['data_usage', 'voice_usage', 'sms_usage']].mean().to_dict()
        repartition_conso = {
            'data': consommation['data_usage'].sum(),
            'voix': consommation['voice_usage'].sum(),
            'sms': consommation['sms_usage'].sum()
        }
        
        # 3. Données Jeux
        total_participations = client_info['nombre_jeu'].sum()
        total_gains = client_info['win_count'].sum()
        
        # % clients joueurs par segment
        clients_par_segment = segmentation.groupby('segment_engagement')['msisdn'].nunique()
        clients_joueurs_par_segment = segmentation[segmentation['nombre_jeu'] > 0].groupby('segment_engagement')['msisdn'].nunique()
        pourcentage_joueurs_par_segment = (clients_joueurs_par_segment / clients_par_segment * 100).fillna(0).to_dict()
        
        # Compilation des KPIs
        kpis = {
            'top_offres': top_offres,
            'repartition_achat_recharge': repartition,
            'source_achat': source_achat,
            'montants_moyens': {
                'achat': montant_moyen_achat,
                'recharge': montant_moyen_recharge
            },
            'consommation_moyenne': conso_moyenne,
            'repartition_conso': repartition_conso,
            'jeux': {
                'total_participations': int(total_participations),
                'total_gains': int(total_gains),
                'pourcentage_joueurs_par_segment': pourcentage_joueurs_par_segment
            },
            'segments': segmentation['segment_engagement'].value_counts().to_dict()
        }
        
        return kpis

# Instance globale pour une utilisation facile
data_loader = MarketingDataLoader()

import re

# Fonction pour extraire la durée en jours de la description
def extract_duree(description):
    description = str(description)
    match = re.search(r'(\d+)\s*(j|jr|jrs)', description, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0  # 
def extract_absolute_price(description):
    match = re.search(r'(-?\d+(\.\d+)?)', str(description))  # Extrait les nombres, avec ou sans décimales
    if match:
        return abs(float(match.group(1)))  # Retourne la valeur absolue du prix
    return None
def detect_type_client(row):
    # Si roue (spin_number) + login_achat → on choisit login_achat
    if pd.notnull(row['spin_number']) and pd.notnull(row['login_achat']):
        return row['login_achat']
    
    # Si roue (spin_number) + login_recharge → on choisit login_recharge
    if pd.notnull(row['spin_number']) and pd.notnull(row['login_recharge']):
        return row['login_recharge']
    
    # Si login_recharge et login_achat sont non-nuls et identiques
    if pd.notnull(row['login_recharge']) and pd.notnull(row['login_achat']):
        if row['login_recharge'] == row['login_achat']:
            return row['login_recharge']

    
    # Si login_recharge seul est non-nul
    if pd.notnull(row['login_recharge']):
        return row['login_recharge']
    
    # Si login_achat seul est non-nul
    if pd.notnull(row['login_achat']):
        return row['login_achat']
    
    # Si seulement roue (spin_number) est présente
    if pd.notnull(row['spin_number']):
        return 'maxit'
    
    # Si aucune condition remplie
    return 'inconnu'
def compute_date_entry(row):
    dates = [row['recharge_event_date'], row['achat_event_date'], row['roue_entry_date_hist']]
    dates_present = [d for d in dates if pd.notna(d)]

    if len(dates_present) == 1:
        return dates_present[0]
    elif len(dates_present) == 2:
        return dates_present[0] if dates_present[0] == dates_present[1] else None
    elif len(dates_present) == 3:
        return dates_present[0] if dates_present[0] == dates_present[1] == dates_present[2] else None
    else:
        return None
def get_nombre_jeu(spin_number):
    if pd.isna(spin_number):
        return 0
    try:
        spin_number = int(spin_number)
        if spin_number >= 0:
            return spin_number
        else:
            return 0
    except (ValueError, TypeError):
        return 0
def get_interet_type(serv):
    if isinstance(serv, str):
        s = serv.lower()
        if 'data' in s:
            return 'data'
        elif 'voix' in s:
            return 'voix'
        else:
            return 'autre'
    else:
        return 'autre'
def get_mode(series):
    mode = series.mode()
    if not mode.empty:
        return mode.iloc[0]  # Plus sûr que [0]
    else:
        return 'sans achat'
def get_source_achat(serv):
    """
    Determine the source of purchase based on service string.
    
    Args:
        serv (str): Service string to analyze
        
    Returns:
        str: Source of purchase
    """
    if pd.isna(serv):  # Check for NaN values
        return 'sans achat'
    
    serv = str(serv).lower()  # Convert to string and lowercase for case-insensitive matching
    
    if 'option' in serv:
        return 'option'
    elif 'promo' in serv:
        return 'promo'
    elif 'achat' in serv:
        return 'achat'
    else:
        return 'autre'
def calculate_final_result(group):
    results = group['sprin_result'].unique()
    
    if any(result not in ['Perdu', np.nan] for result in results):
        return 1
    # If all results are 'Perdu'
    elif all(result == 'Perdu' for result in results):
        return 0
    # If all results are NaN
    elif all(pd.isna(result) for result in results):
        return -1
    # If there's a mix of 'Perdu' and NaN
    else:
        return -1
def get_type_usage(row):
    achat = row['nb_achat'] > 0
    recharge = row['nb_recharge'] > 0
    jeu = row['nombre_jeu'] > 0

    if achat and recharge and jeu:
        return 'complet'
    elif achat and recharge:
        return 'achat_recharge'
    elif achat and jeu:
        return 'achat_jeu'
    elif recharge and jeu:
        return 'recharge_jeu'
    elif achat:
        return 'achat'
    elif recharge:
        return 'recharge'
    elif jeu:
        return 'jeu'
    else:
        return 'aucun'
def get_action(row):
    achat = row['nb_achat']
    recharge = row['nb_recharge']
    jeu = row['nombre_jeu']
    
    # Trouver la valeur maximale et son type
    max_value = max(achat, recharge, jeu)
    
    if max_value == 0:
        return 'aucun'
    elif max_value == achat:
        return 'achat'
    elif max_value == recharge:
        return 'recharge'
    elif max_value == jeu:
        return 'jeu'
    else:
        return 'complet'
def extraire_quantite(description):
    if isinstance(description, str):
        # Recherche des occurrences de Mo ou Go
        match_go = re.search(r'(\d+)\s*Go', description)
        match_mo = re.search(r'(\d+)\s*Mo', description)
        
        if match_go:
            # Si Go est trouvé, convertir en Mo
            return int(match_go.group(1)) * 1000  # 1 Go = 1000 Mo
        elif match_mo:
            # Si Mo est trouvé, retourner directement
            return int(match_mo.group(1))
    return 0  # Retourner 0 si aucune quantité n'est trouvée

# Fonction pour gérer les prix "internet bil milli" (calculer la consommation en Mo)
def calculer_prix(description, prix):
    if isinstance(description, str) and 'internet bil milli' in description.lower():
        # Si "internet bil milli" est dans la description, appliquer le calcul
        return prix * 1000 / 90  # 20 Mo = 90 millimes donc 1 Mo = 90 / 20 millimes
    return 0  # Si aucune correspondance, retour à 0
def get_major_achat(x):
    mode = x.mode()
    if not mode.empty:
        return mode.iloc[0]
    else:
        return 'aucun achat'
def get_moy_recharge(total,nb_recharge):
    if nb_recharge>0:
        return total/nb_recharge
    else:
        return 0
import pandas as pd

def create_client_info(final_df):
    final_df['recharge_event_date'] = pd.to_datetime(final_df['event_date'])
    final_df['achat_event_date'] = pd.to_datetime(final_df['event_date'])
    final_df['roue_entry_date_hist'] = pd.to_datetime(final_df['event_date'])

    # Extraire le mois et l'année de chaque colonne
    final_df['recharge_month'] = final_df['recharge_event_date'].dt.to_period('M')  # Année-Mois
    final_df['achat_month'] = final_df['achat_event_date'].dt.to_period('M')  # Année-Mois
    final_df['roue_month'] = final_df['roue_entry_date_hist'].dt.to_period('M')  # Année-Mois
    # Appliquer la fonction à chaque ligne de la colonne "achat_description"
    final_df['achat_option_duree'] = final_df['description'].apply(extract_duree)

    # S'assurer que la colonne est bien en entier
    final_df['achat_option_duree'] = final_df['achat_option_duree'].astype(int)
    final_df['mois_annee'] = final_df['recharge_event_date'].dt.strftime('%m_%Y')
    # Appliquer la fonction à la colonne 'prix'
    final_df['prix'] = final_df['prix'].apply(extract_absolute_price)
    final_df['amount'] = final_df['amount'].apply(extract_absolute_price)
    final_df['recharge_event_date'] = pd.to_datetime(final_df['recharge_event_date'])

    # Créer une colonne mois_annee (ex : 01_2025)
    final_df['mois_annee'] = final_df['recharge_event_date'].dt.strftime('%m_%Y')
    # Appliquer la fonction sur la DataFrame

    final_df.loc[:, 'type_client'] = final_df.apply(detect_type_client, axis=1)
    for col in ['recharge_event_date', 'achat_event_date', 'roue_entry_date_hist']:
        final_df[col] = pd.to_datetime(final_df[col]).dt.date
    final_df['nombre_jeu'] = final_df['spin_number'].apply(get_nombre_jeu)
    final_df['nombre_jeu'] = final_df['spin_number'].apply(get_nombre_jeu)
    final_df['interet'] = final_df['serv_orig'].apply(get_interet_type)
    final_df['interet_international'] = final_df['serv_orig'].apply(
        lambda x: 1 if isinstance(x, str) and any(term in x.lower() for term in ['roaming', 'inter']) else 0
    )
    final_df['source_achat'] = final_df['serv_orig'].apply(get_source_achat)
    final_df['interet_promo'] = final_df['serv_orig'].apply(
        lambda x: 1 if isinstance(x, str) and 'promo' in x.lower() else 0
    )
    final_df['recharge_event_date'] = pd.to_datetime(final_df['recharge_event_date'])

    # 2. Trier les données
    final_df = final_df.sort_values(by=['msisdn', 'recharge_event_date'])

    # 3. Calculer le délai entre les recharges successives
    final_df['delai_recharge'] = final_df.groupby('msisdn')['recharge_event_date'].diff()

    # 4. Convertir le délai en jours
    final_df['delai_recharge'] = final_df['delai_recharge'].dt.total_seconds() / (24 * 60 * 60)
    final_df['event_date'] = pd.to_datetime(final_df['event_date'])
    # 4. Extraire uniquement les jours (sans l'heure)
    final_df['event_day'] = final_df['event_date'].dt.date

    final_df['quantite_consommée'] = final_df['description'].apply(extraire_quantite)
    final_df['prix_internet_bel_milli'] = final_df.apply(lambda row: calculer_prix(row['description'], row['prix']), axis=1)

    # Calculer la consommation totale (somme des quantités consommées et des prix)
    final_df['consommation_totale_Mo'] = final_df['quantite_consommée'] + final_df['prix_internet_bel_milli']
    final_df['achat_event_date'] = pd.to_datetime(final_df['event_date'])
    final_df['source_achat'] = final_df['serv_orig'].apply(get_source_achat)
    # Trier par client et par date d'achat (du plus ancien au plus récent)
    final_df = final_df.sort_values(by=['msisdn', 'achat_event_date'])
    def detect_maxit_usage(df):
        """
        Détecte si une transaction est MAXIT ou non
        
        Parameters:
        df (pd.DataFrame): Dataframe contenant les données
            
        Returns:
        pd.DataFrame: Dataframe avec une colonne est_maxit
        """
        # Créer une fonction pour vérifier si une ligne est MAXIT
        def is_maxit(row):
            # Vérifier les conditions de MAXIT
            if (pd.notna(row['login_recharge']) and str(row['login_recharge']).lower() == 'maxit') or \
            (pd.notna(row['login_achat']) and str(row['login_achat']).lower() == 'maxit') or \
            (pd.notna(row['spin_number']) and row['spin_number'] > 0):
                return True
            return False
        
        # Appliquer la fonction à chaque ligne
        df['est_maxit'] = df.apply(is_maxit, axis=1)
        
        return df

    # Utilisation
    final_df = detect_maxit_usage(final_df)
    df_global_seg = final_df.groupby("msisdn").agg({
    "type_client": lambda x: x.mode()[0] if not x.mode().empty else 'inconnu',
    'amount': lambda x: (x > 0).sum(),
    'prix': lambda x: (x > 0).sum()}).reset_index()
    nombre_jeu_par_client = final_df.groupby('msisdn')['nombre_jeu'].sum()
    df_global_seg = df_global_seg.join(nombre_jeu_par_client.rename('nombre_jeu'), on='msisdn')
    interet_par_client = final_df.groupby('msisdn')['interet'].apply(get_mode)

    # 4. Ajouter au df_global_seg en alignant les index (join)
    df_global_seg = df_global_seg.join(interet_par_client.rename('interet'), on='msisdn')
    interet_international_par_client = final_df.groupby('msisdn')['interet_international'].max()

    # 3. Joindre à df_global_seg en gardant l'alignement sur msisdn
    df_global_seg = df_global_seg.join(interet_international_par_client.rename('interet_international'), on='msisdn')
    df_global_seg['interet_international'] = df_global_seg['interet_international'].fillna(0).astype(int)
    df_global_seg.rename(columns={'amount': 'nb_recharge'}, inplace=True)
    source_achat_par_client = final_df.groupby('msisdn')['source_achat'].max()

    # Rename the column to avoid conflict before joining
    source_achat_par_client = source_achat_par_client.rename('source_achat_max')

    # Join with the new column name
    df_global_seg = df_global_seg.join(source_achat_par_client, on='msisdn')
    result = final_df.groupby('msisdn').apply(calculate_final_result).reset_index(name='win_count')

    # Display the result
    df_global_seg = pd.merge(df_global_seg, result, on='msisdn', how='left')

    # Fill NaN values with 0 (meaning no win/loss recorded)
    df_global_seg['win_count'] = df_global_seg['win_count'].fillna(-1)
    df_global_seg.rename(columns={'prix': 'nb_achat'}, inplace=True)
    # 1. Calculer la somme des achats par msisdn
    montant_total_achat = final_df.groupby('msisdn')['prix'].sum()

    # 2. Ajouter la colonne à df_global_seg en alignant sur msisdn
    df_global_seg = df_global_seg.join(montant_total_achat.rename('montant_total_achat'), on='msisdn')

    # 3. Remplacer les NaN par 0 pour les clients sans achat
    df_global_seg['montant_total_achat'] = df_global_seg['montant_total_achat'].fillna(0)
    # 1. Calculer la somme des achats par msisdn
    montant_total_recharge = final_df.groupby('msisdn')['amount'].sum()

    # 2. Ajouter la colonne à df_global_seg en alignant sur msisdn
    df_global_seg = df_global_seg.join(montant_total_recharge.rename('montant_total_recharge'), on='msisdn')

    # 3. Remplacer les NaN par 0 pour les clients sans achat
    df_global_seg['montant_total_recharge'] = df_global_seg['montant_total_recharge'].fillna(0)
    df_global_seg['nb_achat'] = df_global_seg['nb_achat'].fillna(0)
    df_global_seg['nb_recharge'] = df_global_seg['nb_recharge'].fillna(0)

    interet_promo_par_client = final_df.groupby('msisdn')['interet_promo'].max()
    df_global_seg = df_global_seg.join(interet_promo_par_client.rename('interet_promo'), on='msisdn')
    df_global_seg['interet_promo'] = df_global_seg['interet_promo'].fillna(0).astype(int)
    df_global_seg['type_usage'] = df_global_seg.apply(get_type_usage, axis=1)
    df_global_seg['action_majoritaire'] = df_global_seg.apply(get_action, axis=1)
    df_global_seg['montant_total_recharge'] = df_global_seg['montant_total_recharge'].fillna(0)
    df_global_seg['montant_total_achat'] = df_global_seg['montant_total_achat'].fillna(0)
    # 1. Définir ton score d'engagement
    df_global_seg['engagement_score'] = (
        2 * df_global_seg['nb_recharge'] +
        1 * df_global_seg['nb_achat'] +
        3 * df_global_seg['nombre_jeu']
    )

    # 2. Catégoriser en Low, Medium, High
    # Par exemple, baser sur les quantiles (qcut fait des coupures équilibrées)
    df_global_seg['engagement_level'] = pd.qcut(
        df_global_seg['engagement_score'],
        q=3,
        labels=['Low', 'Medium', 'High']
    )

    # 1. Calculer la durée moyenne des options pour chaque client
    # Filtrer uniquement les lignes où achat_option_duree est > 0
    duree_moyenne_options = final_df[final_df['achat_option_duree'] > 0].groupby('msisdn')['achat_option_duree'].mean()

    # 2. Ajouter au df_global_seg
    df_global_seg = df_global_seg.join(duree_moyenne_options.rename('duree_moyenne_option'), on='msisdn')

    # 3. Remplacer les NaN par 0 pour les clients sans option
    df_global_seg['duree_moyenne_option'] = df_global_seg['duree_moyenne_option'].fillna(0)

    # 4. Convertir en entier pour éviter les valeurs décimales
    df_global_seg['duree_moyenne_option'] = df_global_seg['duree_moyenne_option'].astype(int)
    # 1. Fonction pour trouver l'achat majoritaire
    achat_majoritaire = final_df.groupby('msisdn')['description'].apply(get_major_achat)

    # 4. Ajouter au df_global_seg en utilisant join pour maintenir l'alignement
    df_global_seg = df_global_seg.join(achat_majoritaire.rename('achat_majoritaire'), on='msisdn')

    # 5. Remplacer les NaN par 'aucun achat'
    df_global_seg['achat_majoritaire'] = df_global_seg['achat_majoritaire'].fillna('aucun achat')
    # 1. Calculer dépenses de recharge par client
    depenses_recharge = df_global_seg['montant_total_recharge']
    source_achat_par_client = final_df.groupby('msisdn')['source_achat'].max()
    df_global_seg = df_global_seg.join(source_achat_par_client.rename('source_achat'), on='msisdn')


    # 2. Calculer dépenses d'achat par client
    depenses_achat = df_global_seg['montant_total_achat']

    # 3. Somme totale des dépenses par client
    depenses_totales = depenses_recharge.add(depenses_achat, fill_value=0)

    # 4. Trouver le seuil de rentabilité (par exemple médiane)
    seuil_rentabilite = depenses_totales.median()

    # 5. Créer la colonne rentabilité
    df_global_seg['rentabilite'] = depenses_totales.apply(lambda x: 'actif' if x >= seuil_rentabilite else 'passif')
    # 1. Nombre total d'achats pour chaque client
    total_achats = final_df.groupby('msisdn')['serv_orig'].count()

    # 2. Nombre d'achats en promo (en prenant en compte toutes les variations)
    achats_promo = final_df[final_df['serv_orig'].str.contains(
        r'promo|_promo|Promo|PROMO', case=False, na=False
    )].groupby('msisdn')['serv_orig'].count()

    # 3. Calculer le % de réactivité aux promotions et arrondir à 2 décimales
    taux_reponse_promo = (achats_promo / total_achats).fillna(0).round(2)

    # 4. Ajouter dans ton df global en utilisant join pour maintenir l'alignement
    df_global_seg = df_global_seg.join(taux_reponse_promo.rename('reponse_promo'), on='msisdn')

    # 5. Remplacer les NaN par 0 pour les clients sans achat
    df_global_seg['reponse_promo'] = df_global_seg['reponse_promo'].fillna(0)
    delai_moyen = final_df.groupby('msisdn')['delai_recharge'].mean().round(1)

    # 6. Ajouter la colonne du délai moyen dans le dataframe global
    df_global_seg = df_global_seg.join(delai_moyen.rename('delai_moyen_recharge'), on='msisdn')

    # 7. Remplacer les NaN par -1 pour les clients sans recharge
    df_global_seg['delai_moyen_recharge'] = df_global_seg['delai_moyen_recharge'].fillna(-1)

    # 1. Convertir les dates en datetime
    final_df['event_date'] = pd.to_datetime(final_df['event_date'])





    # 4. Extraire uniquement les jours (sans l'heure)
    final_df['event_day'] = final_df['event_date'].dt.date

    # 5. Compter le nombre de jours distincts d'activité par client
    frequence_jours_actifs = final_df.groupby('msisdn')['event_day'].nunique().reset_index()

    frequence_jours_actifs = frequence_jours_actifs.rename(columns={'event_day': 'frequence_utilisation_mensuelle'})

    # 6. Fusionner avec le DataFrame global
    df_global_seg = df_global_seg.merge(frequence_jours_actifs, on='msisdn', how='left')
    df_global_seg['frequence_utilisation_mensuelle'] = df_global_seg['frequence_utilisation_mensuelle'].fillna(0).astype(int)
    consommation_totale_client = final_df.groupby('msisdn')['consommation_totale_Mo'].sum().reset_index()

    # Ajouter cette consommation à df_global_seg
    df_global_seg = df_global_seg.merge(consommation_totale_client, on='msisdn', how='left')

    # Remplacer les NaN par 0 si nécessaire
    df_global_seg['consommation_totale_Mo'] = df_global_seg['consommation_totale_Mo'].fillna(0)

    # Récupérer pour chaque client la dernière offre achetée (description)
    derniere_offre = final_df.groupby('msisdn').last()['description'].reset_index()

    # Renommer la colonne pour plus de clarté
    derniere_offre.rename(columns={'description': 'derniere_offre_achetee'}, inplace=True)
    def check_client_maxit(client_df):
        return pd.Series({'est_maxit': client_df['est_maxit'].any()})
    result = final_df.groupby('msisdn').apply(check_client_maxit).reset_index()
    df_global_seg = pd.merge(df_global_seg, result, on='msisdn', how='left')

    # Fusionner dans df_global_seg
    df_global_seg = df_global_seg.merge(derniere_offre, on='msisdn', how='left')
    df_global_seg['moy_recharge'] = df_global_seg.apply(lambda row: get_moy_recharge(row['montant_total_recharge'], row['nb_recharge']), axis=1)
    
    df_global_seg['est_utilisateur_actif'] = (df_global_seg['frequence_utilisation_mensuelle'] > 0)
    
    # Return the processed dataframe
    return df_global_seg
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import numpy as np
import pandas as pd

from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import numpy as np
import pandas as pd

segmentation_guide={
    "rentabilité":["rentabilite","nb_achat","nb_recharge","frequence_utilisation_mensuelle","moy_recharge",'duree_moyenne_option'],
    "engagement":['est_utilisateur_actif','frequence_utilisation_mensuelle','engagement_score','engagement_level'],
    "type_client":['type_client','frequence_utilisation_mensuelle','type_usage'],
    "type_interet":['interet','duree_moyenne_option'],
    "interet_international":['type_usage','interet_international','source_achat'],
    "interet_jeu":['type_client','nombre_essai_jeu','win_count'],
    "interet_promo":['source_achat', 'interet_promo', 'type_usage','reponse_promo',],
    "action":['nombre_jeu','nb_recharge', 'nb_achat','action_majoritaire']
}
segments_labels = {
    'rentabilité': {
        'rentabilité_score': ['non rentable', 'rentable']
    },
    'engagement': {
        'engagement_score': ['non engagé','peu engagé', 'très engagé']
    },
    "type_client":{
        'type_client': ['orienté USSD', 'orienté APLICATION', 'orienté BOUTIQUE']
    },
    "type_interet":{  
        'interet':['data','voix']},
    "interet_international":{
        'interet_international':['non international', 'international']
    },
    "interet_jeu":{
        'nombre_essai_jeu':['non jeu','peu jeu','très jeu']
    },
    "interet_promo":{
        'interet_promo':['non promo','peu promo','Sensibles aux promos']
    },
    "action":{
        'action_majoritaire':['achat','recharge','roue chance']
    }
}


import numpy as np
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

def find_best_k_using_elbow(data, k_range=range(1, 11), plot=True):
    inertias = []

    # Step 1: Calculate inertias for each k
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42)
        kmeans.fit(data)
        inertias.append(kmeans.inertia_)

    # Step 2: Find the "elbow" using the largest distance method
    k_vals = list(k_range)
    p1 = np.array([k_vals[0], inertias[0]])
    p2 = np.array([k_vals[-1], inertias[-1]])

    distances = []
    for i in range(len(k_vals)):
        p = np.array([k_vals[i], inertias[i]])
        # Use np.cross with 3D vectors to avoid deprecation warning
        cross_product = np.cross(np.array([p2[0] - p1[0], p2[1] - p1[1], 0]),
                               np.array([p1[0] - p[0], p1[1] - p[1], 0]))
        distance = np.linalg.norm(cross_product) / np.linalg.norm(np.array([p2[0] - p1[0], p2[1] - p1[1], 0]))
        distances.append(distance)

    best_k = k_vals[np.argmax(distances)]

    return best_k

def assign_labels_by_feature(centroids, feature_index, ordered_labels):
    """
    Attribue des labels aux clusters selon la valeur d'une seule feature choisie.

    Args:
    centroids (np.ndarray): Matrice (n_clusters x n_features)
    feature_index (int): Index de la feature à utiliser pour le tri (ex: 0 pour 1re colonne)
    ordered_labels (list of str): Labels à assigner dans l’ordre croissant de la feature

    Returns:
    dict: Mapping des index de cluster vers labels
    """

    # Extraire la colonne (feature) choisie
    feature_values = centroids[:, feature_index]

    # Trier les indices de clusters selon cette feature
    sorted_indices = np.argsort(feature_values)

    # Assigner les labels dans l’ordre souhaité
    label_mapping = {idx: ordered_labels[i] for i, idx in enumerate(sorted_indices)}

    return label_mapping

from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import numpy as np
import pandas as pd

from sklearn.preprocessing import LabelEncoder, MinMaxScaler
import numpy as np
import pandas as pd

def preprocess_dataframe(df, threshold=0.1):
    # Create a copy of the DataFrame to avoid SettingWithCopyWarning
    df = df.copy()
    
    # Label encode categorical columns
    for col in df.columns:
        if df[col].dtype in ['category', 'object']:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col])
    
    # Select numerical columns (excluding 'msisdn')
    numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
    numerical_cols = [col for col in numerical_cols if col != 'msisdn']

    # Initialize Min-Max scaler
    scaler = MinMaxScaler()

    # List to store features that need normalization
    features_to_normalize = []

    # Check differences between min and max values for each feature
    for col in numerical_cols:
        min_val = df[col].min()
        max_val = df[col].max()

        # Calculate relative difference
        diff = (max_val - min_val) / min_val if min_val != 0 else max_val

        # If difference is greater than threshold, add feature to list
        if diff > threshold:
            features_to_normalize.append(col)

    # Apply Min-Max normalization if necessary
    if features_to_normalize:
        print(f"Normalisation des features suivantes: {features_to_normalize}")
        df[features_to_normalize] = scaler.fit_transform(df[features_to_normalize])
    else:
        print("Aucune normalisation nécessaire, les échelles des features sont déjà similaires.")

    return df

from sklearn.cluster import KMeans
def segmenter_clients(df, critere_segmentation, acquisition=True):
    # Filtrage initial
    
    
    # Dictionnaires
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
    segments_labels = {
    'rentabilité': {
        'rentabilite': ['non rentable', 'rentable']
    },
    'engagement': {
        'engagement_score': ['non engagé','peu engagé', 'très engagé']
    },
    "type_client":{
        'type_client': ['orienté USSD', 'orienté APLICATION', 'orienté BOUTIQUE']
    },
    "type_interet":{  
        'interet':['data','voix']},
    "interet_international":{
        'interet_international':['non international', 'international']
    },
    "interet_jeu":{
        'nombre_jeu':['non jeu','peu jeu','très jeu']
    },
    "interet_promo":{
        'interet_promo':['non promo','peu promo','Sensibles aux promos']
    },
    "action":{
        'action_majoritaire':['achat','recharge','roue chance']
    }
}

    # Sélection des features
    df=df.copy()
    if acquisition:
        df=df[df['type_client'] != 'maxit']
    else:
        df=df[df['type_client'] == 'maxit']
    features = segmentation_guide[critere_segmentation] + ['msisdn']
    df_seg = df[features].copy()
    df_seg = preprocess_dataframe(df_seg.copy())

    # Supprimer msisdn avant clustering
    if 'msisdn' in df_seg.columns:
        df_seg.drop(columns=['msisdn'], inplace=True)

    # Trouver l'attribut principal de segmentation
    feature_name = list(segments_labels[critere_segmentation].keys())[0]
    ordered_labels = segments_labels[critere_segmentation][feature_name]
    feature_index = df_seg.columns.get_loc(feature_name)

    # Réduction dimensionnelle optionnelle
    # df_seg, _ = select_features_pca(df_seg)  # Décommenter si défini

    # Détermination du meilleur k
    best_k = find_best_k_using_elbow(df_seg)
    max_k = len(ordered_labels)
    best_k = min(best_k, max_k)

    # Clustering
    model = KMeans(init='k-means++', n_clusters=best_k, max_iter=500, random_state=22)
    segments = model.fit_predict(df_seg)

    # Affectation des résultats
    df['segments'] = segments
    centroids = model.cluster_centers_
    mapping = assign_labels_by_feature(centroids, feature_index, ordered_labels)
    df[f'segment_{critere_segmentation}'] = df['segments'].map(mapping)
    

    return df
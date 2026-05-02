
import pandas as pd
import re
from typing import Tuple, Optional

def extract_volumes(row: pd.Series) -> Tuple[int, int, int]:
    """Extrait les volumes de consommation depuis la description"""
    # Initialize default values
    data_mo = 0
    voice_min = 0
    sms = 0
    
    desc = str(row['description']).lower()
    prix = abs(row['prix'])
    
    # Handle 'internet bil milli' case
    if desc == 'internet bil milli':
        data_mo = int(prix) // 90 * 20
    else:
        # Handle other cases
        match_go = re.search(r'(\d+)\s*go', desc)
        match_mo = re.search(r'(\d+)\s*mo', desc)
        
        if match_go:
            data_mo = int(match_go.group(1)) * 1000
        elif match_mo:
            data_mo = int(match_mo.group(1))
    
    # Extract voice minutes
    match_min = re.search(r'(\d+)\s*(?:min|m|minutes?)', desc, re.IGNORECASE)
    if match_min:
        voice_min = int(match_min.group(1))
    
    # Handle SMS case
    if voice_min == 0 and any(term in desc for term in ['voix', 'appel']) and prix < 5000:
        sms = 100
    
    return data_mo, voice_min, sms

def generate_consommations(
    achat_df: pd.DataFrame
) -> pd.DataFrame:
    """Génère un DataFrame des consommations par jour par client, filtré par date et/ou msisdn"""
    if achat_df.empty:
        return pd.DataFrame(columns=['msisdn', 'event_date', 'data_usage', 'voice_usage', 'sms_usage'])
    
    # Make a copy to avoid SettingWithCopyWarning
    df = achat_df.copy()
   
    
    # Apply extract_volumes and create new columns
    volumes = df.apply(extract_volumes, axis=1, result_type='expand')
    volumes.columns = ['data_usage', 'voice_usage', 'sms_usage']
    
    # Concatenate with the original dataframe
    df = pd.concat([df, volumes], axis=1)
    
    # Group by msisdn and event_date to get daily sums
    consommations = df.groupby(['msisdn'], as_index=False).agg({
        'data_usage': 'sum',
        'voice_usage': 'sum',
        'sms_usage': 'sum'
    })
    
    return consommations

df_catalogue_options=pd.read_csv('catalogue.csv')
def extract_month(df, date_col):
    df = df.copy()
    df['month'] = pd.to_datetime(df[date_col]).dt.to_period("M").dt.to_timestamp()
    return df[["msisdn", "month"]].drop_duplicates()
def extract_duree(row):
    """
    Extrait la durée en jours à partir de la description et des données de consommation.
    """
    description = str(row['description']).lower()
    consommation = float(row.get('prix', 0)) // 90 * 20

    if "double validité" in description:
        return 60
    if "triple validité" in description:
        return 90

    if description != 'internet bil milli':
        # Durée explicite (j/jr/jrs)
        m = re.search(r'(\d+)\s*(?:j|jr|jrs)\b', description)
        if m:
            return int(m.group(1))

        # Offres en Go
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*go', description)
        if m:
            v = float(m.group(1).replace(',', '.'))
            if 1 <= v <= 42:  return 30
            if v == 60:       return 60
            if v == 100:      return 90
            if v == 200:      return 129
            if v == 500:      return 365

        # Offres en Mo
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*mo', description)
        if m:
            v = float(m.group(1).replace(',', '.'))
            if v <= 100:      return 1
            if 200 <= v <= 300: return 4
            if v > 300:       return 7

    else:
        # Internet bil milli basé sur consommation
        if consommation <= 100:           return 1
        if 120 <= consommation <= 200:    return 2
        if 220 <= consommation <= 300:    return 4
        if 330 <= consommation <= 950:    return 7
        if 950 <= consommation <= 55000:  return 30
        else: return 60

    return 0

def capter_churn(date_reference, msisdn=None):
    # Créer des copies pour éviter les modifications des dataframes originaux
    achats_df = achats.copy()
    
    # Conversion des dates
    achats_df["event_date"] = pd.to_datetime(achats_df["event_date"], errors='coerce')
    date_reference = pd.to_datetime(date_reference)
    mois_reference = date_reference.replace(day=1).to_period('M').to_timestamp()
    
    # Filtrer pour le client spécifique si msisdn est fourni
    if msisdn is not None:
        achats_df = achats_df[achats_df['msisdn'] == msisdn]
    
    # Si pas d'achat pour ce client, c'est un churn
    if achats_df.empty:
        return 1
    
    # Calculer la durée de validité des achats
    achats_df["duree_jours"] = achats_df.apply(extract_duree, axis=1)
    achats_df["valid_until"] = achats_df.apply(
        lambda x: x["event_date"] + pd.Timedelta(days=x["duree_jours"]),
        axis=1
    )
    
    # Filtrer les achats du mois de référence
    achats_mois = achats_df[
        achats_df["event_date"].dt.to_period('M').dt.to_timestamp() == mois_reference
    ]
    
    # Si pas d'achat dans le mois, vérifier la validité des achats précédents
    if achats_mois.empty:
        # Récupérer le dernier achat avant le mois de référence
        dernier_achat = achats_df[achats_df["event_date"] < mois_reference].sort_values("event_date").iloc[-1]
        # Vérifier si la validité couvre le mois de référence
        fin_mois = (mois_reference + pd.offsets.MonthEnd(0)).normalize()
        if pd.isna(dernier_achat["valid_until"]) or dernier_achat["valid_until"] < fin_mois:
            return 1  # Churn si pas d'achat valide
        return 0  # Pas de churn si un achat précédent est encore valide
    
    # Vérifier si au moins un achat couvre la fin du mois
    fin_mois = (mois_reference + pd.offsets.MonthEnd(0)).normalize()
    if (achats_mois["valid_until"] >= fin_mois).any():
        return 0  # Pas de churn si au moins un achat couvre la fin du mois
    
    # Vérifier s'il y a eu d'autres activités (recharges, spins) dans le mois
    recharges_mois = recharges[
        (recharges["msisdn"] == msisdn) if msisdn is not None else True
    ].copy()
    recharges_mois["event_date"] = pd.to_datetime(recharges_mois["event_date"], errors='coerce')
    recharges_mois = recharges_mois[
        (recharges_mois["event_date"].dt.to_period('M').dt.to_timestamp() == mois_reference)
    ]
    
    spins_mois = spins.copy()
    spins_mois["entry_date_hist"] = pd.to_datetime(spins_mois["entry_date_hist"], errors='coerce')
    spins_mois = spins_mois[
        (spins_mois["entry_date_hist"].dt.to_period('M').dt.to_timestamp() == mois_reference)
    ]
    if msisdn is not None:
        spins_mois = spins_mois[spins_mois["msisdn"] == msisdn]
    
    # Churn si pas d'activité du tout
    if recharges_mois.empty and spins_mois.empty:
        return 1
    
    return 0



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
           (pd.notna(row['spin_number']) and row['spin_number'] >
           
            0):
            return True
        return False
    
    # Appliquer la fonction à chaque ligne
    df['est_maxit'] = df.apply(is_maxit, axis=1)
    
    return df

def extract_duree(description):
    """Extrait la durée en jours depuis la description"""
    if pd.isna(description):
        return 0
    description = str(description).lower()
    match = re.search(r'(\d+)\s*(j|jr|jrs|jour|jours)', description)
    return int(match.group(1)) if match else 0

import matplotlib.pyplot as plt

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


# Appliquer la fonction sur la DataFrame

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
def get_nombre_jeu(serv):
    if int(serv) >= 0:
        return int(serv)
    elif pd.isna(serv):
        return -1

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
def process_group(group):
    return pd.Series({
        'win_count': calculate_final_result(group)
    })

def calculate_final_result(group):
    results = group['sprin_result']
    
    if any(result not in ['Perdu', np.nan] for result in results):
        return 1
    # Si tous les résultats sont 'Perdu'
    elif all(result == 'Perdu' for result in results):
        return 0
    # Si tous les résultats sont NaN
    elif all(pd.isna(result) for result in results):
        return -1
    # S'il y a un mélange de 'Perdu' et NaN
    else:
        return -1
def check_client_maxit(client_df):
    return pd.Series({'est_maxit': client_df['est_maxit'].any()})
def get_source_achat(serv):
    """
    Determine the source of purchase based on service string.
    
    Args:
        serv (str): Service string to analyze
        
    Returns:
        str: Source of purchase
    """
    
    serv = str(serv).lower()  # Convert to string and lowercase for case-insensitive matching
    if pd.isna(serv):  # Check for NaN values
        return 'sans achat'
    
    if 'option' in serv:
        return 'option'
    elif 'promo' in serv:
        return 'promo'
    else:
        return 'autre'
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
def get_major_achat(x):
    mode = x.mode()
    if not mode.empty:
        return mode.iloc[0]
    else:
        return 'aucun achat'
import pandas as pd
from datetime import timedelta

def preparation_profil(client_id,date_debut=None,date_fin=None):
    if date_debut is not None and isinstance(date_debut, str):
        date_debut = pd.to_datetime(date_debut, errors='coerce')
    
    if date_fin is not None and isinstance(date_fin, str):
        date_fin = pd.to_datetime(date_fin, errors='coerce')
    
    recharges_copy = recharges.copy()
    achats_copy = achats.copy()
    spins_copy = spins.copy()
        
    # Convert date columns to datetime with error handling
    for df in [recharges_copy, achats_copy]:
        df['event_date'] = pd.to_datetime(df['event_date'], errors='coerce')
        
    spins_copy['entry_date_hist'] = pd.to_datetime(spins_copy['entry_date_hist'], errors='coerce')
        
    # Set date range based on inputs
    if date_debut is None or date_fin is None:
            min_dates = [
                recharges_copy['event_date'].min(),
                achats_copy['event_date'].min(),
                spins_copy['entry_date_hist'].min()
            ]
            max_dates = [
                recharges_copy['event_date'].max(),
                achats_copy['event_date'].max(),
                spins_copy['entry_date_hist'].max()
            ]
            date_debut = min(d for d in min_dates if pd.notnull(d))
            date_fin = max(d for d in max_dates if pd.notnull(d))
        
    # Filter the data
    achat_filtered = achats_copy[
        (achats_copy['msisdn'] == client_id) &
        (achats_copy['event_date'].between(date_debut, date_fin, inclusive='both'))
    ].copy()

    rech_filtered = recharges_copy[
        (recharges_copy['msisdn'] == client_id) &
        (recharges_copy['event_date'].between(date_debut, date_fin, inclusive='both'))
    ].copy()

    spin_filtered = spins_copy[
        (spins_copy['msisdn'] == client_id) &
        (spins_copy['entry_date_hist'].between(date_debut, date_fin, inclusive='both'))
    ].copy()
        
    # Ensure we have data to merge
    if achat_filtered.empty and rech_filtered.empty and spin_filtered.empty:
        return pd.DataFrame()  # Return empty dataframe if no data
            
    # Perform the merges
    df_achat_recharge = pd.merge(
        achat_filtered, 
        rech_filtered,
        on=['msisdn', 'event_date'],
        how='outer',
        suffixes=('_achat', '_recharge')
    )
        
    # For the second merge, we need to handle the case where spin_filtered might be empty
    if not spin_filtered.empty:
        df_final = pd.merge(
            df_achat_recharge, 
            spin_filtered,
            left_on=['msisdn', 'event_date'],
            right_on=['msisdn', 'entry_date_hist'],
            how='outer'
        )
    else:
        df_final = df_achat_recharge.copy()
        # Add missing columns that would come from spin_filtered
        for col in spins_copy.columns:
            if col not in df_final.columns:
                df_final[col] = None
        
    #df_final=df_final[
    #    (df_final['msisdn'] == client_id) &
    #    (df_final['entry_date_hist'].between(date_debut, date_fin))
    #].copy()
    df_final['prix'] = abs(df_final['prix'])
    df_final['prix']=df_final['prix'].fillna(0)
    df_final['amount']=df_final['amount'].fillna(0)
    df_final["serv_orig"] = df_final["serv_orig"].str.replace(r"^_+", "", regex=True)
    df_final['spin_number'] = df_final['spin_number'].fillna(-1)
    df_final['achat_option_duree'] = df_final['description'].apply(extract_duree)


    # S'assurer que la colonne est bien en entier
    df_final['achat_option_duree'] = df_final['achat_option_duree'].astype(int)
    df_final['type_client'] = df_final.apply(detect_type_client, axis=1)
    df_final = detect_maxit_usage(df_final)
    df_client = df_final.groupby("msisdn").agg({
    "type_client": lambda x: x.mode()[0] if not x.mode().empty else 'inconnu'
 
}).reset_index()
    df_client['nb_recharge'] = df_final['amount'][df_final['amount']>0].count()
    df_client['nb_achat'] = df_final['prix'][df_final['prix']>0].count()
    df_final['nombre_jeu'] = df_final['spin_number'].apply(get_nombre_jeu)
    nombre_jeu_par_client = df_final.groupby('msisdn')['nombre_jeu'].count()
    df_client = df_client.join(nombre_jeu_par_client.rename('nombre_jeu'), on='msisdn')
    df_client['nombre_jeu'] = df_client['nombre_jeu'].fillna(0).astype(int)
    df_final['interet'] = df_final['serv_orig'].apply(get_interet_type)
    interet_par_client = df_final.groupby('msisdn')['interet'].apply(get_mode)
    df_client = df_client.join(interet_par_client.rename('interet'), on='msisdn')
    # 1. Créer la colonne d'intérêt international (1 si "roaming" ou "inter" dans serv_orig, sinon 0)
    df_final['interet_international'] = df_final['serv_orig'].apply(
        lambda x: 1 if isinstance(x, str) and any(term in x.lower() for term in ['roaming', 'inter']) else 0
    )

    # 2. Prendre le maximum par client (au moins une occurrence => 1)
    interet_international_par_client = df_final.groupby('msisdn')['interet_international'].max()

    # 3. Joindre à df_global_seg en gardant l'alignement sur msisdn
    df_client = df_client.join(interet_international_par_client.rename('interet_international'), on='msisdn')
    df_client['interet_international'] = df_client['interet_international'].fillna(0).astype(int)

    
    # 1. Calculer la somme des achats par msisdn
    montant_total_achat = df_final.groupby('msisdn')['prix'].sum()

    # 2. Ajouter la colonne à df_global_seg en alignant sur msisdn
    df_client = df_client.join(montant_total_achat.rename('montant_total_achat'), on='msisdn')

    # 3. Remplacer les NaN par 0 pour les clients sans achat
    df_client['montant_total_achat'] = df_client['montant_total_achat'].fillna(0)
    
    result = df_final.groupby('msisdn').apply(check_client_maxit).reset_index()
    df_client = pd.merge(df_client, result, on='msisdn', how='left')
    # 1. Calculer la somme des achats par msisdn
    montant_total_recharge = df_final.groupby('msisdn')['amount'].sum()

    # 2. Ajouter la colonne à df_global_seg en alignant sur msisdn
    df_client = df_client.join(montant_total_recharge.rename('montant_total_recharge'), on='msisdn')

    # 3. Remplacer les NaN par 0 pour les clients sans achat
    df_client['montant_total_recharge'] = df_client['montant_total_recharge'].fillna(0)
    df_client['nb_achat'] = df_client['nb_achat'].fillna(0)
    df_client['nb_recharge'] = df_client['nb_recharge'].fillna(0)
    df_final['source_achat'] = df_final['serv_orig'].apply(get_source_achat)

    # 2. Take the maximum per client (at least one occurrence => 1)
    source_achat_par_client = df_final.groupby('msisdn')['source_achat'].max()
    df_client = df_client.join(source_achat_par_client.rename('source_achat'), on='msisdn')
    df_client['source_achat'] = df_client['source_achat'].fillna('sans achat')
    df_final['interet_promo'] = df_final['serv_orig'].apply(
    lambda x: 1 if isinstance(x, str) and 'promo' in x.lower() else 0
)

    interet_promo_par_client = df_final.groupby('msisdn')['interet_promo'].max()
    df_client = df_client.join(interet_promo_par_client.rename('interet_promo'), on='msisdn')
    df_client['interet_promo'] = df_client['interet_promo'].fillna(0).astype(int)
    df_client['type_usage'] = df_client.apply(get_type_usage, axis=1)
    df_client['action_majoritaire'] = df_client.apply(get_action, axis=1)
    df_client['montant_total_recharge'] = df_client['montant_total_recharge'].fillna(0)
    df_client['montant_total_achat'] = df_client['montant_total_achat'].fillna(0)
    # 1. Définir ton score d'engagement
    df_client['engagement_score'] = (
        df_client['nb_recharge'] +
        df_client['nb_achat'] +
        df_client['nombre_jeu']
    )

    # 2. Catégoriser en Low, Medium, High
    # Par exemple, baser sur les quantiles (qcut fait des coupures équilibrées)
    if df_client['engagement_score'].nunique() >= 3:
        df_client['engagement_level'] = pd.qcut(
            df_client['engagement_score'],
            q=3,
            labels=['Low', 'Medium', 'High'],
            duplicates='drop'
        )
    else:
        # If not enough unique values, assign all to 'Medium'
        df_client['engagement_level'] = 'Medium'
    # 1. Calculer la durée moyenne des options pour chaque client
    # Filtrer uniquement les lignes où achat_option_duree est > 0
    duree_moyenne_options=df_final [df_final['achat_option_duree'] > 0].groupby('msisdn')['achat_option_duree'].mean()

    # 2. Ajouter au df_global_seg
    df_client = df_client.join(duree_moyenne_options.rename('duree_moyenne_option'), on='msisdn')

    # 3. Remplacer les NaN par 0 pour les clients sans option
    df_client['duree_moyenne_option'] = df_client['duree_moyenne_option'].fillna(0)

    # 4. Convertir en entier pour éviter les valeurs décimales
    df_client['duree_moyenne_option'] = df_client['duree_moyenne_option'].astype(int)
    achat_majoritaire = df_final.groupby('msisdn')['description'].apply(get_major_achat)

    # 4. Ajouter au df_global_seg en utilisant join pour maintenir l'alignement
    df_client = df_client.join(achat_majoritaire.rename('achat_majoritaire'), on='msisdn')

    # 5. Remplacer les NaN par 'aucun achat'
    df_client['achat_majoritaire'] = df_client['achat_majoritaire'].fillna('aucun achat')
    total_achats = df_final.groupby('msisdn')['serv_orig'].count()

    # 2. Nombre d'achats en promo (en prenant en compte toutes les variations)
    achats_promo = df_final[df_final['serv_orig'].str.contains(
        r'promo|_promo|Promo|PROMO', case=False, na=False
    )].groupby('msisdn')['serv_orig'].count()

        # 3. Calculer le % de réactivité aux promotions et arrondir à 2 décimales
    taux_reponse_promo = (achats_promo / total_achats).fillna(0).round(2)

    # 4. Ajouter dans ton df global en utilisant join pour maintenir l'alignement
    df_client = df_client.join(taux_reponse_promo.rename('reponse_promo'), on='msisdn')

    # 5. Remplacer les NaN par 0 pour les clients sans achat
    df_client['reponse_promo'] = df_client['reponse_promo'].fillna(0)

    return df_client



def parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

import re
import pandas as pd
import pandas as pd
import numpy as np
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def calculer_depense_totale(df):
    return int(df['prix'].sum())



def construire_profil_client(df_client):
    df = df_client.copy()
    

    # Déterminer le type de chaque option (Voix ou Data)
    

    
    df['date_achat'] = pd.to_datetime(df['date_achat'], format='%Y-%m-%d')

    # Trier par option et date
    df = df.sort_values(by=['date_achat'])

    # Calculer la date du prochain achat par type d'option
    df['next_achat'] = df['date_achat'].shift(-1)

    # Calcul brut entre les achats
    df['duree_reelle'] = (df['next_achat'] - df['date_achat']).dt.days

    # Remplir les valeurs manquantes ou incohérentes avec la durée contractuelle
    df['duree_reelle'] = df.apply(
        lambda row: row['duree_data'] if pd.isna(row['duree_reelle']) and row['type'] == 'data'
        else row['duree_voix'] if pd.isna(row['duree_reelle']) and row['type'] == 'voix'
        else row['duree_reelle'],
        axis=1
    )

    # Juste au cas où il resterait des NaN
    df['duree_reelle'] = df['duree_reelle'].fillna(0)
    depense_actuelle = calculer_depense_totale(df)

    # Calcul du profil client
    profil_client = {
        'data_volume': df[df['type'] == 'data']['data_volume'].sum(),
        'voice_volume': df[df['type'] == 'voix']['voice_volume'].sum(),
        'duree': df[df['type'] == 'data']['duree_reelle'].sum(),
        'international': 1 if df['name'].str.contains('international', case=False).any() else 0,
        'promo': 1 if df['prix'].min() == 0 else 0,
        'depense_actuelle': depense_actuelle
    }

    return profil_client, df

def calculer_depense_totale(df):
    return df['prix'].sum()
def extraire_quantite(description: str) -> int:
    """Extrait le volume de data en Mo depuis la description"""
    if pd.isna(description):
        return 0

    description = str(description).lower()
    
    # Capture les nombres avec virgule ou point (ex : 1.5 ou 1,125)
    match_go = re.search(r'([\d.,]+)\s*go', description)
    match_mo = re.search(r'([\d.,]+)\s*mo', description)
    
    def convertir_float(valeur_str):
        # Remplace la virgule par un point pour float()
        return float(valeur_str.replace(',', '.'))

    if match_go:
        valeur = convertir_float(match_go.group(1))
        return int(valeur * 1000)  # 1 Go = 1000 Mo
    elif match_mo:
        valeur = convertir_float(match_mo.group(1))
        return int(valeur)  # Déjà en Mo, donc pas de multiplication

    return 0


def extraire_quantite_voix(description: str) -> int:
    """Extrait la durée en minutes depuis la description"""
    if pd.isna(description):
        return 0
        
    description = str(description).lower()
    match = re.search(r'(\d+)\s*(min|m|minutes?)\b', description)
    return int(match.group(1)) if match else 0
def extraire_duree(description: str) -> int:
    """Extrait la durée en jours depuis la description"""
    if pd.isna(description):
        return 0
        
    description = str(description).lower()
    match_j = re.search(r'(\d+)\s*(j|jr|jrs|jour|jours)\b', description)
    match_mois = re.search(r'(\d+)\s*mois\b', description)
    
    if match_j:
        return int(match_j.group(1))
    elif match_mois:
        return int(match_mois.group(1)) * 30  # approx. conversion
    return 0
def determiner_type(serv_orig: str, description: str) -> str:
    """Détermine le type d'option (data, voix, sms, mixte)"""
    serv_orig = str(serv_orig).lower() if pd.notna(serv_orig) else ""
    description = str(description).lower() if pd.notna(description) else ""

    types = set()
    keywords = {
        "data": ["data", "internet"],
        "voix": ["voix", "appel", "minute"],
        "sms": ["sms"]
    }

    for t, mots in keywords.items():
        if any(m in serv_orig for m in mots) or any(m in description for m in mots):
            types.add(t)

    return "_".join(sorted(types)) if types else "inconnu"

from typing import Dict, Any
import pandas as pd

def extract_option_details(row: pd.Series) -> Dict[str, Any]:
    """Extrait tous les détails d'une option à partir d'une ligne du DataFrame"""
    description = row.get('description', '')
    serv_orig = row.get('serv_orig', '')
    prix = row.get('prix', 0)
    
    # Conversion sécurisée de la date
    try:
        event_date = pd.to_datetime(row.get('event_date'), errors='coerce')
    except Exception:
        event_date = pd.NaT

    option_type = determiner_type(serv_orig, description)
    is_data = "data" in option_type
    is_voix = "voix" in option_type

    # Extraction de la durée
    duree_totale = extraire_duree(description)

    details = {
        'option_id': f"opt_{event_date.strftime('%Y-%m-%dT%H:%M:%S')}" if pd.notnull(event_date) else "opt_invalide",
        'name': str(description)[:100],
        'type': option_type,
        'duree_data': duree_totale if is_data else 0,
        'duree_voix': duree_totale if is_voix else 0,
        'data_volume': extraire_quantite(description) if is_data else 0,
        'voice_volume': extraire_quantite_voix(description) if is_voix else 0,
        'international': False,
        'promo': False,
        'prix': abs(float(prix)) if pd.notna(prix) else 0.0,
        'date_achat': event_date.strftime('%Y-%m-%d') if pd.notnull(event_date) else ""
    }

    serv_orig_lower = str(serv_orig).lower()
    if any(x in serv_orig_lower for x in ["int", "internat", "roam"]):
        details['international'] = True
    if any(x in serv_orig_lower for x in ["promo", "offre", "special", '_promo', 'Promo', 'PROMO']):
        details['promo'] = True

    return details
def load_csvs_with_clean_keys(folder_path, fichiers):
    dfs = {}
    for fichier in fichiers:
        chemin = os.path.join(folder_path, fichier)
        try:
            df = pd.read_csv(chemin)

            # Nettoyage du nom :
            # 1. Enlever la date (_MM_YYYY ou _YYYY-MM ou YYYY-MM ou YYYY_MM)
            nom_cle = re.sub(r'(_?\d{4}[-_]\d{2}|_?\d{2}[-_]\d{4})', '', fichier)
            # 2. Enlever l'extension .csv
            nom_cle = nom_cle.replace('.csv', '')
            # 3. Supprimer les mots 'df' et 'mois' s’ils apparaissent dans le nom
            nom_cle = re.sub(r'\b(df|mois)\b', '', nom_cle, flags=re.IGNORECASE)
            # 4. Nettoyer les underscores en trop
            nom_cle = nom_cle.strip('_').replace('__', '_')

            dfs[nom_cle] = df
            print(f"Chargé: {fichier} → clé: '{nom_cle}' (shape: {df.shape})")
        except Exception as e:
            print(f"Erreur en chargeant {fichier} : {e}")
    return dfs

def filtrer_clients(
    msisdn,
    date_debut,
    date_fin,
    folder_path
):
    from datetime import datetime
    import pandas as pd

    # Assure que date_debut et date_fin sont des objets datetime
    if isinstance(date_debut, str):
        date_debut = datetime.strptime(date_debut, '%Y-%m-%d')
    if isinstance(date_fin, str):
        date_fin = datetime.strptime(date_fin, '%Y-%m-%d')

    # Charger les fichiers (à adapter selon ta fonction existante)
    fichiers = detect_csvs_inclusive(folder_path, date_debut, date_fin)
    dfs = load_csvs_with_clean_keys(folder_path, fichiers)

    clients = dfs['df_client_info'] if 'df_client_info' in dfs else pd.DataFrame()
    segmentations = dfs['df_segmentation_mois'] if 'df_segmentation_mois' in dfs else pd.DataFrame()
    achats = dfs['achat'] if 'achat' in dfs else pd.DataFrame()
    recharges = dfs['recharge'] if 'recharge' in dfs else pd.DataFrame()
    spins = dfs['spins'] if 'spins' in dfs else pd.DataFrame()
    churn = dfs['churn_par_client_par_mois'] if 'churn_par_client_par_mois' in dfs else pd.DataFrame()
    consommations = dfs['consommation_mois'] if 'consommation_mois' in dfs else pd.DataFrame()

    

    

    result = []
    all_options = pd.DataFrame()
    clients_df = pd.DataFrame()

    
    rech_filtered = recharges[recharges['msisdn'] == msisdn] if not recharges.empty else pd.DataFrame()
    achat_filtered = achats[achats['msisdn'] == msisdn] if not achats.empty else pd.DataFrame()
    spin_filtered = spins[spins['msisdn'] == msisdn] if not spins.empty else pd.DataFrame()
    client_info = clients[clients['msisdn'] == msisdn] if not clients.empty else pd.DataFrame()
    consommations_info = consommations[consommations['msisdn'] == msisdn] if not consommations.empty else pd.DataFrame()
    churn_row = churn[(churn['msisdn'] == msisdn) & (churn['month'] == date_debut)] if not churn.empty else pd.DataFrame()

    churn_label = 'Non Churn'
    if not churn_row.empty and churn_row['churn'].values[0] == 1:
        churn_label = 'Churn'

    est_maxit = 'Non Maxit'
    if not client_info.empty and client_info['est_maxit'].values[0]:
        est_maxit = 'Maxit'

    segment_info = segmentations[segmentations['msisdn'] == msisdn]

    options_list = [extract_option_details(row) for _, row in achat_filtered.iterrows()]
    options_filtered = pd.DataFrame(options_list)
    options_filtered["msisdn"] = msisdn


    all_options = pd.concat([all_options, options_filtered], ignore_index=True)

    options_dict = {
            f"{row['option_id']}": row.drop(labels=["option_id"]).to_dict()
            for _, row in options_filtered.iterrows()
        }

    achats_dict = {
            f"{row['achat_id']}": row.drop(labels=["msisdn", "achat_id"]).to_dict()
            for _, row in achat_filtered.iterrows()
        }

    recharges_dict = {
            f"{row['recharge_id']}": row.drop(labels=["msisdn", "recharge_id"]).to_dict()
            for _, row in rech_filtered.iterrows()
        }

    jeux_dict = {
            f"{row['spin_id']}": row.drop(labels=["msisdn", "spin_id"]).to_dict()
            for _, row in spin_filtered.iterrows()
        }

    client_json = {
            "client_id": msisdn,
            "periode": {
                "date_debut": str(date_debut.date()),
                "date_fin": str(date_fin.date())
            },
            "client_info": client_info.to_dict(orient='records')[0] if not client_info.empty else {},
            "churn": churn_label,
            "segmentation": segment_info.to_dict(orient='records')[0] if not segment_info.empty else {},
            "profil_maxit": est_maxit,
            "consommations": consommations_info.to_dict(orient='records')[0] if not consommations_info.empty else {},
            "achats": achats_dict,
            "recharges": recharges_dict,
            "jeux": jeux_dict,
            "options": options_dict
        }

    clients_df = pd.concat([clients_df, client_info], ignore_index=True)

    clients_df = clients_df.reset_index(drop=True)


    clients_df.to_csv(f"clients_{msisdn}.csv", index=False)
    all_options.to_csv(f"options_{msisdn}.csv", index=False)

    return client_json, all_options, clients_df
def generer_rapport_marketing_client(json_client):
    from datetime import datetime
    from collections import Counter

    # Extraction des blocs
    client_info = json_client["client_info"]
    segmentation = json_client["segmentation"]
    achats = json_client.get("achats", {})
    recharges = json_client.get("recharges", {})
    jeux = json_client.get("jeux", {})
    options = json_client.get("options", {})
    consommations = json_client.get("consommations", {})
    churn = json_client["churn"]
    is_maxit = json_client["profil_maxit"]
    periode = json_client["periode"]

    # --- 1. Synthèse profil général ---
    rapport = f"📄 **Rapport Marketing - Client {json_client['client_id']}**\n\n"
    rapport += f"🔹 **Période analysée** : du {periode['date_debut']} au {periode['date_fin']}\n"
    rapport += f"🔸 **Type de client** : {client_info.get('type_client', 'N/A')}\n"
    rapport += f"🔸 **Profil MaxIt** : {'Oui' if is_maxit else 'Non'}\n"
    rapport += f"🔸 **Statut Churn** : {churn}\n"
    rapport += f"🔸 **Niveau d'engagement** : {segmentation.get('segment_engagement', 'Inconnu')} ({client_info.get('engagement_score', 0)} pts)\n"
    rapport += f"🔸 **Rentabilité** : {segmentation.get('segment_rentabilité', 'Inconnue')}\n"
    rapport += f"🔸 **Action dominante** : {client_info.get('action_majoritaire', 'N/A')} | Usage : {client_info.get('type_usage', 'N/A')}\n\n"

    # --- 2. Analyse comportementale détaillée ---
    total_achats = len(achats)
    total_recharges = len(recharges)
    total_jeux = len(jeux)
    total_actions = total_achats + total_recharges + total_jeux

    canaux_achat = [a["login"] for a in achats.values()]
    canaux_recharge = [r["login"] for r in recharges.values()]
    top_canal_achat = Counter(canaux_achat).most_common(1)
    top_canal_recharge = Counter(canaux_recharge).most_common(1)

    rapport += f"📊 **Comportements transactionnels**\n"
    rapport += f"- Nombre d'achats : {total_achats} | Montant total : {client_info.get('montant_total_achat', 0)} mM\n"
    rapport += f"- Nombre de recharges : {total_recharges} | Montant total : {client_info.get('montant_total_recharge', 0)} mM\n"
    rapport += f"- Nombre de participations aux jeux : {total_jeux}\n"
    if total_achats:
        rapport += f"- Canal d'achat dominant : {top_canal_achat[0][0]} ({top_canal_achat[0][1]} fois)\n"
    if total_recharges:
        rapport += f"- Canal de recharge dominant : {top_canal_recharge[0][0]} ({top_canal_recharge[0][1]} fois)\n"

    # --- 3. Analyse MaxIt ---
    actions_maxit = sum(1 for a in achats.values() if a["login"] == "maxit") + sum(1 for r in recharges.values() if r["login"] == "maxit")
    part_maxit = (actions_maxit / total_actions * 100) if total_actions > 0 else 0
    rapport += f"\n🧠 **Utilisation de MaxIt**\n"
    rapport += f"- Actions MaxIt : {actions_maxit} / {total_actions} ({part_maxit:.1f}%)\n"
    if is_maxit:
        if part_maxit < 50:
            rapport += "- 📌 **Client MaxIt peu actif** : Canal MaxIt sous-utilisé\n"
        else:
            rapport += "- ✅ **Client MaxIt actif**\n"
    else:
        rapport += "- ❌ **Client Non MaxIt** : potentiel d’acquisition important\n"

    # --- 4. Consommation ---
    rapport += f"\n📶 **Consommation du client**\n"
    rapport += f"- Données consommées : {consommations.get('data_usage', 0)} Mo\n"
    rapport += f"- Voix utilisée : {consommations.get('voice_usage', 0)} minutes\n"
    rapport += f"- SMS : {consommations.get('sms_usage', 0)} messages\n"

    # --- 5. Comportement sur les options ---
    volumes_options = Counter(o['data_volume'] for o in options.values() if 'data_volume' in o)
    rapport += f"\n📦 **Options achetées**\n"
    for vol, count in volumes_options.items():
        rapport += f"- Option {vol} Mo : {count} fois\n"

    # --- 6. Typologie de messages marketing à envisager ---
    rapport += f"\n📩 **Typologie des messages marketing à privilégier**\n"

    if not is_maxit:
        rapport += "- 📲 **Messages d'acquisition MaxIt** : promotion de l'app, lien de téléchargement, bonus 200 Mo\n"
    elif churn == "Churn":
        rapport += "- 🧲 **Messages de réactivation** : relance jeux, roue chance, pins, promo spéciale fidélisation\n"
    elif part_maxit < 40:
        rapport += "- 🚀 **Messages d’incitation à l’usage MaxIt** : rappeler les services, canaux, services WinWin\n"
    else:
        rapport += "- 🎯 **Messages de fidélisation** : marketplace, nouveaux services, avantages personnalisés\n"

    rapport += "- 🎮 **Jeux & gamification** : roue de la chance, pins à gagner, notifications hebdomadaires\n"
    rapport += "- 🎁 **Messages sur les options similaires** : à recommander via LLM2\n"
    rapport += "- 🛍️ **Marketplace & services partenaires** : coupons, réductions locales selon localisation\n"
    rapport += "- 🧩 **Personnalisation comportementale** : achat, recharge, promo, intérêt voix/data\n"

    return rapport
def generer_messages_options(options_similaires, consommation_client, achats_client=None):
    """
    Génère des messages marketing dynamiques et impactants adaptés à MaxIt,
    prenant en compte la consommation client et ses achats pour proposer
    des options plus avantageuses et des économies.

    Args:
        options_similaires (list of dict): options recommandées
        consommation_client (dict): profil avec 'data_volume', 'voice_volume', 'duree', 'depense_actuelle', ...
        achats_client (list of dict): options déjà achetées par le client (optionnel)

    Returns:
        list: messages marketing prêts à l’emploi
    """

    messages = []
    data_consomme = consommation_client.get('data_volume', 0)
    depense_actuelle = consommation_client.get('depense_actuelle', 0)  # en millimes

    # Préparer une liste d'achats clients pour comparer si fournie
    achats_client = achats_client.to_dict(orient='records')
    achats_client = achats_client or []

    for option in options_similaires:
        desc = option.get("name", "")
        typ = option.get("type", "").lower()
        data_vol = option.get("volume_data", 0)
        voix_vol = option.get("volume_voix", 0)
        duree = option.get("duree", 0)
        prix = option.get("prix", 0)
        promo = option.get("promo", False)
        international = option.get("international", False)

        prix_dinar = prix / 1000  # millimes → dinars
        suffixe_duree = f"valable {duree} jour{'s' if duree > 1 else ''}" if duree else ""
        suffixe_international = " 🌍 Disponible pour appels/data à l’international." if international else ""

        # Cas spécial pour "Internet Bel Milli"
        if "bel milli" in desc.lower():
            msg = (
                f"📶 {desc} à {prix_dinar:.3f} DT — {suffixe_duree}. "
                f"Option personnalisée : achetez ce dont vous avez besoin (20 Mo à 0.09 DT) via MaxIt !"
            )
            messages.append(msg)
            continue

        # Vérifier si option est plus avantageuse que la consommation et dépense actuelles
        if typ == "data":
            # Comparaison avec consommation et dépenses actuelles
            if data_vol >= data_consomme and prix < depense_actuelle:
                economie = round((depense_actuelle - prix) / 1000, 3)
                msg = (
                    f"💡 MaxIt vous recommande : au lieu de plusieurs petits achats, "
                    f"prenez '{desc}' ({suffixe_duree}) à {prix_dinar:.3f} DT. "
                    f"Vous économisez environ {economie:.3f} DT et profitez de plus de data ! 🚀"
                )
            else:
                # Message classique amélioré pour data
                if promo:
                    msg = (
                        f"🔥 Offre EXCLU MaxIt : {desc} à seulement {prix_dinar:.3f} DT ! "
                        f"{suffixe_duree} – Naviguez à fond, sans vous ruiner. {suffixe_international}"
                    )
                else:
                    msg = (
                        f"📶 {desc} à {prix_dinar:.3f} DT — {suffixe_duree}. "
                        f"Rechargez vos Gigas maintenant via MaxIt !{suffixe_international}"
                    )
        elif typ == "voix":
            # Message pour voix
            if promo:
                msg = (
                    f"📞 Offre spéciale appels : {desc} à prix promo {prix_dinar:.3f} DT ! "
                    f"{suffixe_duree} – Idéal pour rester en contact. {suffixe_international}"
                )
            else:
                msg = (
                    f"📞 {desc} disponible à {prix_dinar:.3f} DT – {suffixe_duree}. "
                    f"Activez-la directement sur MaxIt !{suffixe_international}"
                )
        else:
            # Autres types d'options
            msg = (
                f"📱 {desc} pour {prix_dinar:.3f} DT – {suffixe_duree}. "
                f"Une option complète, à activer via MaxIt. {suffixe_international}"
            )

        messages.append(msg.strip())

    return messages
import json
import ollama
from typing import Dict, List, Any
from pydantic import BaseModel, ValidationError
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modèle de sortie attendu du LLM
class MarketingMessageResponse(BaseModel):
    acquisition: List[str]
    jeux_et_fidelisation: List[str]
    options_recommandees: List[str]
    services_marketplace: List[str]
    messages_personnalises: List[str]
    messages_generaux: List[str]

def validate_client_report(report: str) -> bool:
    return "Profil MaxIt" in report and "Statut Churn" in report

def is_client_maxit(rapport: str) -> bool:
    return "Profil MaxIt : Oui" in rapport or "Profil MaxIt : True" in rapport

def generate_marketing_messages(
    rapport_client: str,
    messages_options: List[str],
    model: str = "qwen2.5:3b",
    max_retries: int = 3
) -> Dict[str, List[str]]:
    if not validate_client_report(rapport_client):
        raise ValueError("Le rapport client est incomplet.")

    est_maxit = is_client_maxit(rapport_client)

    # SYSTEM PROMPT
    system_prompt = (
        "Tu es un expert marketing senior d’Orange Tunisie. ;eviter de marquer nom de client;essayer de chercher et se baser bien sur l'application maxit de orange tunise et ses rubriques et ses services"
        "Tu conçois des campagnes mobiles (SMS, push, notifications) pour MaxIt, l’app Orange dédiée. "
        "Tu dois générer des messages concrets, engageants, et adaptés au profil du client pour augmenter son engagement."
    )

    # Instructions adaptées au profil MaxIt
    if est_maxit:
        consigne_acquisition = (
            "- Ce client utilise déjà MaxIt. Ne propose **aucun message d'acquisition**.\n"
            "- Concentre-toi sur la fidélisation, les jeux, les services digitaux et les programmes bonus."
        )
    else:
        consigne_acquisition = (
            "- Ce client n'est pas MaxIt. Tu dois proposer 1 à 2 messages d’acquisition dans la section 'acquisition'.\n"
            "- Mentionne le lien de téléchargement : https://www.orange.tn/maxit avec bonus d'installation 200 Mo."
        )

    # USER PROMPT
    prompt_user = f"""
🧠 Contexte :
Génère des messages marketing personnalisés pour un client Orange Tunisie, à partir du rapport ci-dessous.

📄 Rapport client :
{rapport_client}

📦 Messages d’options recommandées à intégrer dans "options_recommandees" (fournis par une autre fonction) :
{json.dumps(messages_options, indent=2, ensure_ascii=False)}

📌 Instructions :
{consigne_acquisition}
- Si le client utilise Flouci, USSD, Mobimoney... explique pourquoi MaxIt est meilleur : centralisé, rapide, suivi conso, bonus...
- S’il ne joue pas, propose la roue de la chance du jeudi, les pins et les bonus de fidélité.
- Propose les services digitaux comme Shahid VIP pour les fans de séries/films.
- Valorise les partenaires comme WinWin : coupons, bons plans locaux selon zone.
- Utilise un ton engageant et professionnel, messages courts, type push/mobile.
- Fournis les messages dans le format JSON ci-dessous.

🎯 Format de sortie STRICT :
{{
  "acquisition": ["..."],
  "jeux_et_fidelisation": ["..."],
  "options_recommandees": ["..."],
  "services_marketplace": ["..."],
  "messages_personnalises": ["..."],
  "messages_generaux": ["..."]
}}
"""

    for attempt in range(max_retries):
        try:
            logger.info(f"Tentative {attempt+1}/{max_retries} - Appel LLM...")

            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_user}
                ]
            )

            content = response['message']['content']
            result = json.loads(content)
            validated = MarketingMessageResponse(**result)

            # 🔁 Supprimer "acquisition" si MaxIt
            if est_maxit:
                validated.acquisition = []

            # ✅ Fusionner les messages générés avec ceux d’options
            final_result = validated.dict()
            final_result["options_recommandees"] = messages_options

            logger.info("✅ Dictionnaire final des messages marketing généré avec succès.")
            return final_result

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"⚠️ Erreur JSON/validation : {e}")
            if attempt == max_retries - 1:
                raise RuntimeError("Erreur persistante dans la génération des messages.")
        except Exception as e:
            logger.error(f"❌ Erreur LLM : {e}")
            if attempt == max_retries - 1:
                raise RuntimeError("Erreur critique LLM après plusieurs tentatives.")

    raise RuntimeError("Erreur LLM non résolue.")


import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def calculer_depense_totale(df):
    return int(df['prix'].sum())

def analyser_kpis_segment(all_options,clients_df):
    kpi = {}

    kpi["nb_clients"] = clients_df["msisdn"].nunique()
    kpi["taux_maxit"] = 100 * clients_df["est_maxit"].sum() / kpi["nb_clients"]
    kpi["taux_utilisateurs_actifs"] = 100 * clients_df["est_utilisateur_actif"].sum() / kpi["nb_clients"]
    kpi["achat_moyen"] = clients_df["montant_total_achat"].mean()
    kpi["recharge_moyenne"] = clients_df["montant_total_recharge"].mean()
    kpi["frequence_achat_moyenne"] = clients_df["nb_achat"].mean()
    kpi["frequence_recharge_moyenne"] = clients_df["nb_recharge"].mean()
    kpi["volume_data_moyen"] = clients_df["consommation_totale_Mo"].mean()

    kpi["type_action_majoritaire"] = clients_df["action_majoritaire"].value_counts(normalize=True).to_dict()
    kpi["offre_favorite"] = clients_df["achat_majoritaire"].value_counts().idxmax()

    # KPIs optionnels
    if not all_options.empty:
        kpi["top_options"] = all_options["name"].value_counts().head(3).to_dict()
        kpi["type_option_prefere"] = all_options["type"].value_counts(normalize=True).to_dict()

    return kpi
def construire_profil_segment(df_segment):
    df = df_segment.copy()

    # Conversion et tri
    df['date_achat'] = pd.to_datetime(df['date_achat'], errors='coerce')
    df = df.sort_values(by='date_achat')

    # Prochain achat
    df['next_achat'] = df['date_achat'].shift(-1)

    # Durée réelle
    df['duree_reelle'] = (df['next_achat'] - df['date_achat']).dt.days
    df['duree_reelle'] = df.apply(
        lambda row: row['duree_data'] if pd.isna(row['duree_reelle']) and row['type'] == 'data'
        else row['duree_voix'] if pd.isna(row['duree_reelle']) and row['type'] == 'voix'
        else row['duree_reelle'],
        axis=1
    )
    df['duree_reelle'] = df['duree_reelle'].fillna(0)

    # Calculs des indicateurs
    total_data = df[df['type'] == 'data']['data_volume'].sum()
    total_voix = df[df['type'] == 'voix']['voice_volume'].sum()
    total_depense = df['prix'].sum()

    profil_segment = {
        'data_volume': int(total_data),
        'voice_volume': int(total_voix),
        'duree': 30,  # Valeur par défaut (même logique que dans construire_profil_client)
        'international': 1 if df['name'].str.contains('international', case=False).any() else 0,
        'promo': 1 if df['prix'].min() == 0 else 0,
        'depense_actuelle': int(total_depense)
    }

    return profil_segment,df


import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def calculer_depense_totale(df):
    return int(df['prix'].sum())



def recommander_options_par_ratio_with_weight(df_client, df_catalogue):
    profil_client, df_client= construire_profil_segment(df_client)
    

    # On filtre si le client n'utilise pas l'international
    if not profil_client['international']:
        df_catalogue = df_catalogue[df_catalogue['international'] == False]
    indices_a_supprimer = []

    #for i, option in df_catalogue.iterrows():
       # if option['data_volume'] < consommation_data or option['voice_volume'] < consommation_voice:
           # indices_a_supprimer.append(i)

    # Supprimer les options qui ne conviennent pas
    df_catalogue = df_catalogue.drop(indices_a_supprimer)

        
    

    # On évite la division par zéro, on met un epsilon (petite valeur)
    epsilon = 1e-6

    client_vector = np.array([1, 1, 3, profil_client['international'], profil_client['promo']*2 ]).reshape(1, -1)
    # On met 1 dans le vecteur client car on va calculer ratio option/client => 1 correspond au profil client

    resultats = []

    # Calcul des durées réelles par option_id dans df_client
    durees_reelles = df_client.groupby('option_id')['duree_reelle'].sum().to_dict()

    for _, option in df_catalogue.iterrows():
        option_id = option['id']
        option['prix']=abs(option['prix'])

        data_volume = 0 if pd.isnull(option['data_volume']) else option['data_volume']
        voice_volume = 0 if pd.isnull(option['voice_volume']) else option['voice_volume']

        duree = durees_reelles.get(option_id, max(option['duree_data'], option['duree_voix']))

        # Calcul des ratios avec protection division par zéro
        ratio_data = data_volume / (profil_client['data_volume'] + epsilon)
        ratio_voix = voice_volume / (profil_client['voice_volume'] + epsilon)
        ratio_duree = duree / (profil_client['duree'] + epsilon)
        ratio_international = int(option['international'])
        ratio_promo = int(option['promo']) * 3
       
        option_vector = np.array([
            ratio_data,
            ratio_voix,
            ratio_duree,
            ratio_international,
            ratio_promo
        ]).reshape(1, -1)

        score_similarite = cosine_similarity(client_vector, option_vector)[0][0]

        resultats.append({
            'id': option['id'],
            'description': option['name'],
            'type': option['type'],
            'volume_data': data_volume,
            'volume_voix': voice_volume,
            'duree': duree,
            'prix': option['prix'],
            'promo': option['promo'],
            'international': option['international'],
            'score_similarite': score_similarite
        })

    

    prix_bel_milli = 0.09 * (profil_client['data_volume'] / 20)

    # Option Internet à la demande
    bel_milli = {
        'id': 'bel_milli',
        'description': 'Internet Bel Milli (à la demande)',
        'type': 'Data',
        'volume_data':profil_client['data_volume']  ,
        'volume_voix': 0,
        'duree': 30,
        'prix': prix_bel_milli,
        'promo': False,
        'international': False,
        'score_similarite': 0.95
    }
    resultats.append(bel_milli)
    

    resultats = [r for r in resultats if r['score_similarite'] >= 0.85]
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats=pd.DataFrame(resultats)
    

    return resultats, profil_client


def recommander_options_par_ratio_without_weight(df_client, df_catalogue):
    profil_client, df_client= construire_profil_segment(df_client)
    
    # On filtre si le client n'utilise pas l'international
    if not profil_client['international']:
        df_catalogue = df_catalogue[df_catalogue['international'] == False]
    indices_a_supprimer = []

    #for i, option in df_catalogue.iterrows():
       # if option['data_volume'] < consommation_data or option['voice_volume'] < consommation_voice:
           # indices_a_supprimer.append(i)

    # Supprimer les options qui ne conviennent pas
    df_catalogue = df_catalogue.drop(indices_a_supprimer)

        
    

    # On évite la division par zéro, on met un epsilon (petite valeur)
    epsilon = 1e-6

    client_vector = np.array([1, 1, 1, profil_client['international'], profil_client['promo'] ]).reshape(1, -1)
    # On met 1 dans le vecteur client car on va calculer ratio option/client => 1 correspond au profil client

    resultats = []

    # Calcul des durées réelles par option_id dans df_client
    durees_reelles = df_client.groupby('option_id')['duree_reelle'].sum().to_dict()

    for _, option in df_catalogue.iterrows():
        option_id = option['id']
        option['prix']=abs(option['prix'])

        data_volume = 0 if pd.isnull(option['data_volume']) else option['data_volume']
        voice_volume = 0 if pd.isnull(option['voice_volume']) else option['voice_volume']

        duree = durees_reelles.get(option_id, max(option['duree_data'], option['duree_voix']))

        # Calcul des ratios avec protection division par zéro
        ratio_data = data_volume / (profil_client['data_volume'] + epsilon)
        ratio_voix = voice_volume / (profil_client['voice_volume'] + epsilon)
        ratio_duree = duree / (profil_client['duree'] + epsilon)
        ratio_international = int(option['international'])
        ratio_promo = int(option['promo']) * 3
       
        option_vector = np.array([
            ratio_data,
            ratio_voix,
            ratio_duree,
            ratio_international,
            ratio_promo
        ]).reshape(1, -1)

        score_similarite = cosine_similarity(client_vector, option_vector)[0][0]

        resultats.append({
            'id': option['id'],
            'description': option['name'],
            'type': option['type'],
            'volume_data': data_volume,
            'volume_voix': voice_volume,
            'duree': duree,
            'prix': option['prix'],
            'promo': option['promo'],
            'international': option['international'],
            'score_similarite': score_similarite
        })

    

    

    

    resultats = [r for r in resultats if r['score_similarite'] >= 0.75]
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats=pd.DataFrame(resultats)
    

    return resultats, profil_client


def recommander(df_client, df_catalogue):

    recommandations_without_weight,profil_client=recommander_options_par_ratio_without_weight(df_client, df_catalogue)
    recommandations_with_weight,profil_client=recommander_options_par_ratio_with_weight(df_client, df_catalogue)
    recommandation = pd.concat([recommandations_without_weight, recommandations_with_weight], ignore_index=True).drop_duplicates()
    recommandation=recommandation.drop_duplicates(subset='id', keep='first')
    recommandation=recommandation.sort_values(by='score_similarite', ascending=False)

    return recommandation,profil_client
def dataframe_recommandations_vers_json(df_client, df_catalogue):
    """
    Returns recommendations and client profile as Python objects (not JSON strings)
    """
    df_recommandations, profil_client = recommander(df_client, df_catalogue)
    
    # Convert to dictionary format
    if df_recommandations.empty:
        recommendations = {"erreur": "Aucune recommandation disponible"}
    else:
        recommendations = {"recommandations des options": []}
        for _, row in df_recommandations.iterrows():
            recommandation = {
                "id": str(row.get('id', '')),
                "name": str(row.get('description', '')),  # Changed to 'name' to match your message function
                "type": str(row.get('type', '')).lower(),
                "volume_data": int(row.get('data_volume', 0)),
                "voice_volume": int(row.get('volume_voix', 0)),
                "duree": int(row.get('duree', 0)),
                "prix": int(row.get('prix', 0)),
                "promo": bool(row.get('promo', False)),
                "international": bool(row.get('international', False))
            }
            recommendations["recommandations des options"].append(recommandation)
    
    profil_client = {
        "data_volume": int(profil_client.get("data_volume", 0)),
        "voice_volume": int(profil_client.get("voice_volume", 0)),
        "duree": int(profil_client.get("duree", 0)),
        "international": int(profil_client.get("international", 0)),
        "promo": int(profil_client.get("promo", 0)),
        "depense_actuelle": int(profil_client.get("depense_actuelle", 0))
    }
    
    return recommendations["recommandations des options"], profil_client
def generer_messages_options_segment(options_similaires, consommation_client, achats_client=None):
    """
    Génère des messages marketing dynamiques et impactants adaptés à MaxIt,
    prenant en compte la consommation client et ses achats pour proposer
    des options plus avantageuses et des économies.

    Args:
        options_similaires (list of dict): options recommandées
        consommation_client (dict): profil avec 'data_volume', 'voice_volume', 'duree', 'depense_actuelle', ...
        achats_client (list of dict): options déjà achetées par le client (optionnel)

    Returns:
        list: messages marketing prêts à l’emploi
    """

    messages = []
    data_consomme = consommation_client.get('data_volume', 0)
    depense_actuelle = consommation_client.get('depense_actuelle', 0)  # en millimes

    # Préparer une liste d'achats clients pour comparer si fournie
    achats_client = achats_client.to_dict(orient='records')
    achats_client = achats_client or []

    for option in options_similaires:
        desc = option.get("name", "")
        typ = option.get("type", "").lower()
        data_vol = option.get("volume_data", 0)
        voix_vol = option.get("volume_voix", 0)
        duree = option.get("duree", 0)
        prix = option.get("prix", 0)
        promo = option.get("promo", False)
        international = option.get("international", False)

        prix_dinar = prix / 1000  # millimes → dinars
        suffixe_duree = f"valable {duree} jour{'s' if duree > 1 else ''}" if duree else ""
        suffixe_international = " 🌍 Disponible pour appels/data à l’international." if international else ""

        # Cas spécial pour "Internet Bel Milli"
        if "bel milli" in desc.lower():
            msg = (
                f"📶 {desc} à {prix_dinar:.3f} DT — {suffixe_duree}. "
                f"Option personnalisée : achetez ce dont vous avez besoin (20 Mo à 0.09 DT) via MaxIt !"
            )
            messages.append(msg)
            continue

        # Vérifier si option est plus avantageuse que la consommation et dépense actuelles
        if typ == "data":
            # Comparaison avec consommation et dépenses actuelles
            if data_vol >= data_consomme and prix < depense_actuelle:
                economie = round((depense_actuelle - prix) / 1000, 3)
                msg = (
                    f"💡 MaxIt vous recommande : au lieu de plusieurs petits achats, "
                    f"prenez '{desc}' ({suffixe_duree}) à {prix_dinar:.3f} DT. "
                    f"Vous économisez environ {economie:.3f} DT et profitez de plus de data ! 🚀"
                )
            else:
                # Message classique amélioré pour data
                if promo:
                    msg = (
                        f"🔥 Offre EXCLU MaxIt : {desc} à seulement {prix_dinar:.3f} DT ! "
                        f"{suffixe_duree} – Naviguez à fond, sans vous ruiner. {suffixe_international}"
                    )
                else:
                    msg = (
                        f"📶 {desc} à {prix_dinar:.3f} DT — {suffixe_duree}. "
                        f"Rechargez vos Gigas maintenant via MaxIt !{suffixe_international}"
                    )
        elif typ == "voix":
            # Message pour voix
            if promo:
                msg = (
                    f"📞 Offre spéciale appels : {desc} à prix promo {prix_dinar:.3f} DT ! "
                    f"{suffixe_duree} – Idéal pour rester en contact. {suffixe_international}"
                )
            else:
                msg = (
                    f"📞 {desc} disponible à {prix_dinar:.3f} DT – {suffixe_duree}. "
                    f"Activez-la directement sur MaxIt !{suffixe_international}"
                )
        else:
            # Autres types d'options
            msg = (
                f"📱 {desc} pour {prix_dinar:.3f} DT – {suffixe_duree}. "
                f"Une option complète, à activer via MaxIt. {suffixe_international}"
            )

        messages.append(msg.strip())
        

    return messages
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def construire_profil_client_client(df_client):
    df = df_client.copy()

    # Déterminer le type de chaque option (Voix ou Data)
    

    df['date_achat'] = pd.to_datetime(df['date_achat'], format='%Y-%m-%d')

    # Trier par option et date
    df = df.sort_values(by=['date_achat'])

    # Calculer la date du prochain achat par type d'option
    df['next_achat'] = df['date_achat'].shift(-1)

    # Calcul brut entre les achats
    df['duree_reelle'] = (df['next_achat'] - df['date_achat']).dt.days

    # Remplir les valeurs manquantes ou incohérentes avec la durée contractuelle
    df['duree_reelle'] = df.apply(
        lambda row: row['duree_data'] if pd.isna(row['duree_reelle']) and row['type'] == 'data'
        else row['duree_voix'] if pd.isna(row['duree_reelle']) and row['type'] == 'voix'
        else row['duree_reelle'],
        axis=1
    )

    # Juste au cas où il resterait des NaN
    df['duree_reelle'] = df['duree_reelle'].fillna(0)
    depense_actuelle = calculer_depense_totale(df)

    # Calcul du profil client
    profil_client = {
        'data_volume': df[df['type'] == 'data']['data_volume'].sum(),
        'voice_volume': df[df['type'] == 'voix']['voice_volume'].sum(),
        'duree': df[df['type'] == 'data']['duree_reelle'].sum(),
        'international': 1 if df['name'].str.contains('international', case=False).any() else 0,
        'promo': 1 if df['prix'].min() == 0 else 0,
        'depense_actuelle': depense_actuelle,
    }

    return profil_client, df


def recommander_options_par_ratio_with_weight_client(df_client, df_catalogue):
    profil_client, df_client = construire_profil_client(df_client)
    consommation_data =profil_client['data_volume']
    consommation_voice = profil_client['voice_volume']

    # On filtre si le client n'utilise pas l'international
    if not profil_client['international']:
        df_catalogue = df_catalogue[df_catalogue['international'] == False]
    indices_a_supprimer = []

    #for i, option in df_catalogue.iterrows():
       # if option['data_volume'] < consommation_data or option['voice_volume'] < consommation_voice:
           # indices_a_supprimer.append(i)

    # Supprimer les options qui ne conviennent pas
    df_catalogue = df_catalogue.drop(indices_a_supprimer)

        
    

    # On évite la division par zéro, on met un epsilon (petite valeur)
    epsilon = 1e-6

    client_vector = np.array([1, 1, 3, profil_client['international'], profil_client['promo']*2 ]).reshape(1, -1)
    # On met 1 dans le vecteur client car on va calculer ratio option/client => 1 correspond au profil client

    resultats = []

    # Calcul des durées réelles par option_id dans df_client
    durees_reelles = df_client.groupby('option_id')['duree_reelle'].sum().to_dict()

    for _, option in df_catalogue.iterrows():
        option_id = option['id']
        option['prix']=abs(option['prix'])

        data_volume = 0 if pd.isnull(option['data_volume']) else option['data_volume']
        voice_volume = 0 if pd.isnull(option['voice_volume']) else option['voice_volume']

        duree = durees_reelles.get(option_id, max(option['duree_data'], option['duree_voix']))

        # Calcul des ratios avec protection division par zéro
        ratio_data = data_volume / (profil_client['data_volume'] + epsilon)
        ratio_voix = voice_volume / (profil_client['voice_volume'] + epsilon)
        ratio_duree = duree / (profil_client['duree'] + epsilon)
        ratio_international = int(option['international'])
        ratio_promo = int(option['promo']) * 3
       
        option_vector = np.array([
            ratio_data,
            ratio_voix,
            ratio_duree,
            ratio_international,
            ratio_promo
        ]).reshape(1, -1)

        score_similarite = cosine_similarity(client_vector, option_vector)[0][0]

        resultats.append({
            'id': option['id'],
            'description': option['name'],
            'type': option['type'],
            'volume_data': data_volume,
            'volume_voix': voice_volume,
            'duree': duree,
            'prix': option['prix'],
            'promo': option['promo'],
            'international': option['international'],
            'score_similarite': score_similarite
        })

    

    prix_bel_milli = 0.09 * (profil_client['data_volume'] / 20)

    # Option Internet à la demande
    bel_milli = {
        'id': 'bel_milli',
        'description': 'Internet Bel Milli (à la demande)',
        'type': 'Data',
        'volume_data':profil_client['data_volume']  ,
        'volume_voix': 0,
        'duree': 30,
        'prix': prix_bel_milli,
        'promo': False,
        'international': False,
        'score_similarite': 0.95
    }
    resultats.append(bel_milli)
    

    resultats = [r for r in resultats if r['score_similarite'] >= 0.85]
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats=pd.DataFrame(resultats)
    

    return resultats, profil_client


def recommander_options_par_ratio_without_weight_client(df_client, df_catalogue):
    profil_client, df_client = construire_profil_client(df_client)
    consommation_data =profil_client['data_volume']
    consommation_voice = profil_client['voice_volume']

    # On filtre si le client n'utilise pas l'international
    if not profil_client['international']:
        df_catalogue = df_catalogue[df_catalogue['international'] == False]
    indices_a_supprimer = []

    #for i, option in df_catalogue.iterrows():
       # if option['data_volume'] < consommation_data or option['voice_volume'] < consommation_voice:
           # indices_a_supprimer.append(i)

    # Supprimer les options qui ne conviennent pas
    df_catalogue = df_catalogue.drop(indices_a_supprimer)

        
    

    # On évite la division par zéro, on met un epsilon (petite valeur)
    epsilon = 1e-6

    client_vector = np.array([1, 1, 1, profil_client['international'], profil_client['promo'] ]).reshape(1, -1)
    # On met 1 dans le vecteur client car on va calculer ratio option/client => 1 correspond au profil client

    resultats = []

    # Calcul des durées réelles par option_id dans df_client
    durees_reelles = df_client.groupby('option_id')['duree_reelle'].sum().to_dict()

    for _, option in df_catalogue.iterrows():
        option_id = option['id']
        option['prix']=abs(option['prix'])

        data_volume = 0 if pd.isnull(option['data_volume']) else option['data_volume']
        voice_volume = 0 if pd.isnull(option['voice_volume']) else option['voice_volume']

        duree = durees_reelles.get(option_id, max(option['duree_data'], option['duree_voix']))

        # Calcul des ratios avec protection division par zéro
        ratio_data = data_volume / (profil_client['data_volume'] + epsilon)
        ratio_voix = voice_volume / (profil_client['voice_volume'] + epsilon)
        ratio_duree = duree / (profil_client['duree'] + epsilon)
        ratio_international = int(option['international'])
        ratio_promo = int(option['promo']) * 3
       
        option_vector = np.array([
            ratio_data,
            ratio_voix,
            ratio_duree,
            ratio_international,
            ratio_promo
        ]).reshape(1, -1)

        score_similarite = cosine_similarity(client_vector, option_vector)[0][0]

        resultats.append({
            'id': option['id'],
            'description': option['name'],
            'type': option['type'],
            'volume_data': data_volume,
            'volume_voix': voice_volume,
            'duree': duree,
            'prix': option['prix'],
            'promo': option['promo'],
            'international': option['international'],
            'score_similarite': score_similarite
        })

    

    

    

    resultats = [r for r in resultats if r['score_similarite'] >= 0.75]
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats=pd.DataFrame(resultats)
    

    return resultats, profil_client


def recommander_client(df_client, df_catalogue):

    recommandations_without_weight,profil_client=recommander_options_par_ratio_without_weight(df_client, df_catalogue)
    recommandations_with_weight,profil_client=recommander_options_par_ratio_with_weight(df_client, df_catalogue)
    recommandation = pd.concat([recommandations_without_weight, recommandations_with_weight], ignore_index=True).drop_duplicates()
    recommandation=recommandation.drop_duplicates(subset='id', keep='first')
    recommandation=recommandation.sort_values(by='score_similarite', ascending=False)

    return recommandation,profil_client



def generer_rapport_marketing_segment(segment_id, clients_json):
    from collections import Counter, defaultdict
    import numpy as np

    # Initialisation
    rapport = f"📄 **Rapport Marketing Segment – `{segment_id}`**\n\n"
    rapport += f"🧑‍🤝‍🧑 **Nombre de clients dans le segment** : {len(clients_json)}\n\n"

    # === AGRÉGATION GLOBALE ===
    types_clients, engagements, rentabilites = Counter(), Counter(), Counter()
    churns, usages_types, actions_majoritaires = Counter(), Counter(), Counter()
    scores_engagement, maxit_flags = [], []

    achats_totaux, recharges_totales, jeux_totaux = 0, 0, 0
    montant_achats, montant_recharges = 0, 0

    canaux_achat, canaux_recharge = [], []
    conso_data, conso_voice, conso_sms = [], [], []
    volumes_options = Counter()

    for client in clients_json:
        info, seg = client["client_info"], client["segmentation"]
        achats, recharges = client.get("achats", {}), client.get("recharges", {})
        jeux, options = client.get("jeux", {}), client.get("options", {})
        consommation = client.get("consommations", {})

        # Profils
        types_clients[info.get("type_client", "N/A")] += 1
        engagements[seg.get("segment_engagement", "Inconnu")] += 1
        rentabilites[seg.get("segment_rentabilité", "Inconnue")] += 1
        churns[client.get("churn", "Inconnu")] += 1
        usages_types[info.get("type_usage", "N/A")] += 1
        actions_majoritaires[info.get("action_majoritaire", "N/A")] += 1
        scores_engagement.append(info.get("engagement_score", 0))
        maxit_flags.append(bool(client.get("profil_maxit", False)))

        # Transactions
        achats_totaux += len(achats)
        montant_achats += info.get("montant_total_achat", 0)
        recharges_totales += len(recharges)
        montant_recharges += info.get("montant_total_recharge", 0)
        jeux_totaux += len(jeux)

        canaux_achat += [a["login"] for a in achats.values()]
        canaux_recharge += [r["login"] for r in recharges.values()]

        # Consommation
        conso_data.append(consommation.get("data_usage", 0))
        conso_voice.append(consommation.get("voice_usage", 0))
        conso_sms.append(consommation.get("sms_usage", 0))

        # Options
        for o in options.values():
            if "data_volume" in o:
                volumes_options[o["data_volume"]] += 1

    # === PROFIL GLOBAL DU SEGMENT ===
    rapport += "🧬 **Profil général du segment**\n"
    rapport += f"- Type client dominant : {types_clients.most_common(1)[0][0]}\n"
    rapport += f"- Segment d'engagement majoritaire : {engagements.most_common(1)[0][0]} (score moyen : {np.mean(scores_engagement):.1f})\n"
    rapport += f"- Rentabilité dominante : {rentabilites.most_common(1)[0][0]}\n"
    rapport += f"- Statut Churn : {dict(churns)}\n"
    rapport += f"- Profil MaxIt : {int(sum(maxit_flags))} / {len(clients_json)} ({(np.mean(maxit_flags)*100):.1f}%)\n"
    rapport += f"- Type d’usage : {usages_types.most_common(1)[0][0]}\n"
    rapport += f"- Action majoritaire : {actions_majoritaires.most_common(1)[0][0]}\n\n"

    # === ANALYSE TRANSACTIONNELLE ===
    rapport += "💳 **Analyse des interactions transactionnelles**\n"
    rapport += f"- Achats totaux : {achats_totaux} | Montant cumulé : {montant_achats} mM\n"
    rapport += f"- Recharges totales : {recharges_totales} | Montant cumulé : {montant_recharges} mM\n"
    rapport += f"- Jeux / participation gamifiées : {jeux_totaux}\n"
    if canaux_achat:
        rapport += f"- Canal d’achat favori : {Counter(canaux_achat).most_common(1)[0]}\n"
    if canaux_recharge:
        rapport += f"- Canal de recharge favori : {Counter(canaux_recharge).most_common(1)[0]}\n"
    rapport += "\n"

    # === MAXIT ===
    total_actions = achats_totaux + recharges_totales + jeux_totaux
    actions_maxit = canaux_achat.count("maxit") + canaux_recharge.count("maxit")
    part_maxit = (actions_maxit / total_actions * 100) if total_actions else 0

    rapport += "📱 **Canal MaxIt**\n"
    rapport += f"- Part d’actions via MaxIt : {part_maxit:.1f}%\n"
    if np.mean(maxit_flags) < 0.3:
        rapport += "- ❌ Faible pénétration MaxIt : campagne d’acquisition requise\n"
    elif part_maxit < 30:
        rapport += "- 🚨 Faible usage malgré l’adoption : incitation nécessaire (jeux, bonus)\n"
    elif part_maxit > 70:
        rapport += "- ✅ Adoption forte : proposer fidélisation, services premium, notifications avancées\n"
    else:
        rapport += "- 🟡 Adoption moyenne : surveiller l’évolution / ciblage comportemental\n"
    rapport += "\n"

    # === CONSOMMATION MOYENNE ===
    rapport += "📶 **Usages moyens des services**\n"
    rapport += f"- Données : {np.mean(conso_data):.1f} Mo\n"
    rapport += f"- Voix : {np.mean(conso_voice):.1f} min\n"
    rapport += f"- SMS : {np.mean(conso_sms):.1f} msg\n\n"

    # === OPTIONS LES PLUS PRISEES ===
    rapport += "📦 **Options populaires dans le segment**\n"
    for vol, count in volumes_options.most_common(5):
        rapport += f"- {vol} Mo : {count} achats\n"
    rapport += "\n"

    # === STRATÉGIE MARKETING PERSONNALISÉE ===
    rapport += "📩 **Stratégies marketing recommandées**\n"
    churn_rate = churns.get("Churn", 0) / len(clients_json)

    if np.mean(maxit_flags) < 0.3:
        rapport += "- 🎯 Acquisition MaxIt : bonus 200Mo, gamification, messages courts avec lien direct\n"
    elif churn_rate > 0.3:
        rapport += "- 🧲 Réactivation : offres limitées, pins gratuits, roue de la chance\n"
    elif part_maxit < 40:
        rapport += "- 🚀 Promotion usages MaxIt : rappels des services, nouveau contenu, coupons exclusifs\n"
    else:
        rapport += "- 💎 Fidélisation : contenu VIP, challenges exclusifs, réduction locale via marketplace\n"

    rapport += "- 🧩 Personnalisation comportementale (Voix/Data, Jour/Nuit, Prépayé/Postpayé)\n"
    rapport += "- 🛍️ Mise en avant intelligente des options similaires (via LLM ou clustering)\n"
    rapport += "- 🔄 Segmentation dynamique pour ciblage évolutif\n"
    rapport += "- 📊 Intégration dans PowerBI pour surveillance KPI temps réel\n"
    taux_maxit = np.mean(maxit_flags)

    return rapport,taux_maxit
from typing import List, Dict
import json
import logging
import ollama
from pydantic import BaseModel, ValidationError

# Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Modèle de validation du JSON de sortie
class MarketingMessageResponse(BaseModel):
    acquisition: List[str]
    jeux_et_fidelisation: List[str]
    options_recommandees: List[str]
    services_marketplace: List[str]
    messages_personnalises: List[str]
    messages_generaux: List[str]

def generate_segment_marketing_messages(
    rapport_segment: str,
    messages_options_segment: List[str],
    taux_maxit: float,
    model: str = "qwen2.5:3b",
    max_retries: int = 3
) -> Dict[str, List[str]]:
    """
    Génère un dictionnaire de messages marketing adaptés à un segment client.
    """

    # Consignes MaxIt selon taux du segment
    if taux_maxit >= 0.6:
        consigne_acquisition = "- Le segment utilise déjà majoritairement MaxIt. **Pas de messages d'acquisition**."
    elif taux_maxit <= 0.3:
        consigne_acquisition = "- Faible usage MaxIt : inclure **2 messages d’acquisition** avec lien bonus 200 Mo."
    else:
        consigne_acquisition = "- Usage partiel MaxIt : inclure **1 message d’acquisition** + messages fidélisation."

    system_prompt = (
        "Tu es expert marketing d’Orange Tunisie ;essayer de chercher et se baser bien sur l'application maxit de orange tunise et ses rubriques et ses services.\n"
        "Tu conçois des messages push (SMS, notification) pour des SEGMENTS de clients mobiles.\n"
        "Tu dois proposer des messages courts, engageants, adaptés au profil d'usage global du segment.\n"
        "Ne mentionne pas de prénom, ne sois pas trop générique. Reste concret, mobile-first, actionnable."
    )

    prompt_user = f"""
📄 Rapport du segment :
{rapport_segment}

📦 Options recommandées dominantes :
{json.dumps(messages_options_segment, indent=2, ensure_ascii=False)}

📌 Consignes :
{consigne_acquisition}
- Utilise les bénéfices MaxIt (centralisation, rapidité, bonus, suivi conso)
- Oriente vers les jeux (roue, pins) si segment jeune ou faible fidélité
- Propose Shahid VIP, coupons WinWin selon le profil
- Fournis des messages courts, typés notification/push

🎯 Format de sortie STRICT :
{{
  "acquisition": ["..."],
  "jeux_et_fidelisation": ["..."],
  "options_recommandees": ["..."],
  "services_marketplace": ["..."],
  "messages_personnalises": ["..."],
  "messages_generaux": ["..."]
}}
"""

    for attempt in range(max_retries):
        try:
            logger.info(f"[Tentative {attempt+1}] Génération de messages segment via LLM...")

            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_user}
                ]
            )

            content = response['message']['content']
            result = json.loads(content)
            validated = MarketingMessageResponse(**result)

            # Fusion avec options proposées manuellement
            final_result = validated.dict()
            final_result["options_recommandees"] = messages_options_segment

            logger.info("✅ Messages marketing segment générés avec succès.")
            return final_result

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"❌ Erreur format JSON/validation LLM : {e}")
        except Exception as e:
            logger.error(f"❌ Erreur inconnue LLM : {e}")

    raise RuntimeError("🚫 Échec de la génération après plusieurs tentatives.")

def filtrer_clients_par_segments(
    segment_criteria,
    date_debut,
    date_fin,
    folder_path
):
    from datetime import datetime
    import pandas as pd

    # Assure que date_debut et date_fin sont des objets datetime
    if isinstance(date_debut, str):
        date_debut = datetime.strptime(date_debut, '%Y-%m-%d')
    if isinstance(date_fin, str):
        date_fin = datetime.strptime(date_fin, '%Y-%m-%d')

    # Charger les fichiers (à adapter selon ta fonction existante)
    fichiers = detect_csvs_inclusive(folder_path, date_debut, date_fin)
    dfs = load_csvs_with_clean_keys(folder_path, fichiers)

    clients = dfs['df_client_info'] if 'df_client_info' in dfs else pd.DataFrame()
    segmentations = dfs['df_segmentation_mois'] if 'df_segmentation_mois' in dfs else pd.DataFrame()
    achats = dfs['achat'] if 'achat' in dfs else pd.DataFrame()
    recharges = dfs['recharge'] if 'recharge' in dfs else pd.DataFrame()
    spins = dfs['spins'] if 'spins' in dfs else pd.DataFrame()
    churn = dfs['churn_par_client_par_mois'] if 'churn_par_client_par_mois' in dfs else pd.DataFrame()
    consommations = dfs['consommation_mois'] if 'consommation_mois' in dfs else pd.DataFrame()

    colonne_map = {
        "rentabilite": "segment_rentabilité",
        "engagement": "segment_engagement",
        "type_client": "segment_type_client",
        "type_interet": "segment_type_interet",
        "interet_international": "segment_interet_international",
        "interet_jeu": "segment_interet_jeu",
        "interet_promo": "segment_interet_promo",
        "action": "segment_action"
    }

    df_filtered = segmentations.copy()
    for critere, valeur in segment_criteria.items():
        if valeur and critere in colonne_map:
            col = colonne_map[critere]
            df_filtered = df_filtered[df_filtered[col] == valeur]

    msisdn_list = df_filtered["msisdn"].unique().tolist()
    segment_id = "_".join([str(segment_criteria[key]) for key in segment_criteria if segment_criteria[key]])

    result = []
    all_options = pd.DataFrame()
    clients_df = pd.DataFrame()

    # Filtrer les données globalement pour garder uniquement les msisdn d'intérêt
    rech_batch = recharges[recharges['msisdn'].isin(msisdn_list)] if not recharges.empty else pd.DataFrame()
    achat_batch = achats[achats['msisdn'].isin(msisdn_list)] if not achats.empty else pd.DataFrame()
    spin_batch = spins[spins['msisdn'].isin(msisdn_list)] if not spins.empty else pd.DataFrame()
    segment_batch = segmentations[segmentations['msisdn'].isin(msisdn_list)] if not segmentations.empty else pd.DataFrame()
    consommations_batch = consommations[consommations['msisdn'].isin(msisdn_list)] if not consommations.empty else pd.DataFrame()


    for msisdn in msisdn_list:
        rech_filtered = rech_batch[rech_batch['msisdn'] == msisdn] if not rech_batch.empty else pd.DataFrame()
        achat_filtered = achat_batch[achat_batch['msisdn'] == msisdn] if not achat_batch.empty else pd.DataFrame()
        spin_filtered = spin_batch[spin_batch['msisdn'] == msisdn] if not spin_batch.empty else pd.DataFrame()
        client_info = clients[clients['msisdn'] == msisdn] if not clients.empty else pd.DataFrame()
        consommations_info = consommations_batch[consommations_batch['msisdn'] == msisdn] if not consommations_batch.empty else pd.DataFrame()
        churn_row = churn[(churn['msisdn'] == msisdn) & (churn['month'] == date_debut)] if not churn.empty else pd.DataFrame()

        churn_label = 'Non Churn'
        if not churn_row.empty and churn_row['churn'].values[0] == 1:
            churn_label = 'Churn'

        est_maxit = 'Non Maxit'
        if not client_info.empty and client_info['est_maxit'].values[0]:
            est_maxit = 'Maxit'

        segment_info = segment_batch[segment_batch['msisdn'] == msisdn]

        options_list = [extract_option_details(row) for _, row in achat_filtered.iterrows()]
        options_filtered = pd.DataFrame(options_list)
        options_filtered["msisdn"] = msisdn


        all_options = pd.concat([all_options, options_filtered], ignore_index=True)

        options_dict = {
            f"{row['option_id']}": row.drop(labels=["option_id"]).to_dict()
            for _, row in options_filtered.iterrows()
        }

        achats_dict = {
            f"{row['achat_id']}": row.drop(labels=["msisdn", "achat_id"]).to_dict()
            for _, row in achat_filtered.iterrows()
        }

        recharges_dict = {
            f"{row['recharge_id']}": row.drop(labels=["msisdn", "recharge_id"]).to_dict()
            for _, row in rech_filtered.iterrows()
        }

        jeux_dict = {
            f"{row['spin_id']}": row.drop(labels=["msisdn", "spin_id"]).to_dict()
            for _, row in spin_filtered.iterrows()
        }

        client_json = {
            "client_id": msisdn,
            "periode": {
                "date_debut": str(date_debut.date()),
                "date_fin": str(date_fin.date())
            },
            "client_info": client_info.to_dict(orient='records')[0] if not client_info.empty else {},
            "churn": churn_label,
            "segmentation": segment_info.to_dict(orient='records')[0] if not segment_info.empty else {},
            "profil_maxit": est_maxit,
            "consommations": consommations_info.to_dict(orient='records')[0] if not consommations_info.empty else {},
            "achats": achats_dict,
            "recharges": recharges_dict,
            "jeux": jeux_dict,
            "options": options_dict
        }

        result.append(client_json)
        clients_df = pd.concat([clients_df, client_info], ignore_index=True)

    clients_df = clients_df.reset_index(drop=True)
    all_options = all_options.reset_index(drop=True)

    clients_df.to_csv(f"clients_{segment_id}.csv", index=False)
    all_options.to_csv(f"options_{segment_id}.csv", index=False)

    return result, all_options, clients_df,segment_id



import os
import re
from datetime import datetime

def detect_csvs_inclusive(folder_path, date_debut, date_fin):
    if isinstance(date_debut, str):
        date_debut = datetime.strptime(date_debut, "%Y-%m-%d")
    if isinstance(date_fin, str):
        date_fin = datetime.strptime(date_fin, "%Y-%m-%d")

    fichiers = os.listdir(folder_path)
    fichiers_selectionnes = []

    # Regex pour date YYYY-MM ou YYYY_MM
    pattern_yyyy_mm = re.compile(r'(\d{4})[-_](\d{2})')
    # Regex pour date MM-YYYY ou MM_YYYY
    pattern_mm_yyyy = re.compile(r'(\d{2})[-_](\d{4})')

    for fichier in fichiers:
        if not fichier.endswith(".csv"):
            continue
        
        match_yyyy_mm = pattern_yyyy_mm.search(fichier)
        match_mm_yyyy = pattern_mm_yyyy.search(fichier)

        date_fichier = None
        if match_yyyy_mm:
            annee, mois = match_yyyy_mm.groups()
            try:
                date_fichier = datetime.strptime(f"{annee}-{mois}-01", "%Y-%m-%d")
            except ValueError:
                pass
        elif match_mm_yyyy:
            mois, annee = match_mm_yyyy.groups()
            try:
                date_fichier = datetime.strptime(f"{annee}-{mois}-01", "%Y-%m-%d")
            except ValueError:
                pass

        if date_fichier:
            if date_debut <= date_fichier <= date_fin:
                fichiers_selectionnes.append(fichier)
        else:
            # Pas de date trouvée => on ajoute toujours
            fichiers_selectionnes.append(fichier)

    return fichiers_selectionnes
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def construire_profil_client_client(df_client):
    df = df_client.copy()

    # Déterminer le type de chaque option (Voix ou Data)
    

    df['date_achat'] = pd.to_datetime(df['date_achat'], format='%Y-%m-%d')

    # Trier par option et date
    df = df.sort_values(by=['date_achat'])

    # Calculer la date du prochain achat par type d'option
    df['next_achat'] = df['date_achat'].shift(-1)

    # Calcul brut entre les achats
    df['duree_reelle'] = (df['next_achat'] - df['date_achat']).dt.days

    # Remplir les valeurs manquantes ou incohérentes avec la durée contractuelle
    df['duree_reelle'] = df.apply(
        lambda row: row['duree_data'] if pd.isna(row['duree_reelle']) and row['type'] == 'data'
        else row['duree_voix'] if pd.isna(row['duree_reelle']) and row['type'] == 'voix'
        else row['duree_reelle'],
        axis=1
    )

    # Juste au cas où il resterait des NaN
    df['duree_reelle'] = df['duree_reelle'].fillna(0)
    depense_actuelle = calculer_depense_totale(df)

    # Calcul du profil client
    profil_client = {
        'data_volume': df[df['type'] == 'data']['data_volume'].sum(),
        'voice_volume': df[df['type'] == 'voix']['voice_volume'].sum(),
        'duree': df[df['type'] == 'data']['duree_reelle'].sum(),
        'international': 1 if df['name'].str.contains('international', case=False).any() else 0,
        'promo': 1 if df['prix'].min() == 0 else 0,
        'depense_actuelle': depense_actuelle,
    }

    return profil_client, df


def recommander_options_par_ratio_with_weight_client(df_client, df_catalogue):
    profil_client, df_client = construire_profil_client(df_client)
    consommation_data =profil_client['data_volume']
    consommation_voice = profil_client['voice_volume']

    # On filtre si le client n'utilise pas l'international
    if not profil_client['international']:
        df_catalogue = df_catalogue[df_catalogue['international'] == False]
    indices_a_supprimer = []

    #for i, option in df_catalogue.iterrows():
       # if option['data_volume'] < consommation_data or option['voice_volume'] < consommation_voice:
           # indices_a_supprimer.append(i)

    # Supprimer les options qui ne conviennent pas
    df_catalogue = df_catalogue.drop(indices_a_supprimer)

        
    

    # On évite la division par zéro, on met un epsilon (petite valeur)
    epsilon = 1e-6

    client_vector = np.array([1, 1, 3, profil_client['international'], profil_client['promo']*2 ]).reshape(1, -1)
    # On met 1 dans le vecteur client car on va calculer ratio option/client => 1 correspond au profil client

    resultats = []

    # Calcul des durées réelles par option_id dans df_client
    durees_reelles = df_client.groupby('option_id')['duree_reelle'].sum().to_dict()

    for _, option in df_catalogue.iterrows():
        option_id = option['id']
        option['prix']=abs(option['prix'])

        data_volume = 0 if pd.isnull(option['data_volume']) else option['data_volume']
        voice_volume = 0 if pd.isnull(option['voice_volume']) else option['voice_volume']

        duree = durees_reelles.get(option_id, max(option['duree_data'], option['duree_voix']))

        # Calcul des ratios avec protection division par zéro
        ratio_data = data_volume / (profil_client['data_volume'] + epsilon)
        ratio_voix = voice_volume / (profil_client['voice_volume'] + epsilon)
        ratio_duree = duree / (profil_client['duree'] + epsilon)
        ratio_international = int(option['international'])
        ratio_promo = int(option['promo']) * 3
       
        option_vector = np.array([
            ratio_data,
            ratio_voix,
            ratio_duree,
            ratio_international,
            ratio_promo
        ]).reshape(1, -1)

        score_similarite = cosine_similarity(client_vector, option_vector)[0][0]

        resultats.append({
            'id': option['id'],
            'description': option['name'],
            'type': option['type'],
            'volume_data': data_volume,
            'volume_voix': voice_volume,
            'duree': duree,
            'prix': option['prix'],
            'promo': option['promo'],
            'international': option['international'],
            'score_similarite': score_similarite
        })

    

    prix_bel_milli = 0.09 * (profil_client['data_volume'] / 20)

    # Option Internet à la demande
    bel_milli = {
        'id': 'bel_milli',
        'description': 'Internet Bel Milli (à la demande)',
        'type': 'Data',
        'volume_data':profil_client['data_volume']  ,
        'volume_voix': 0,
        'duree': 30,
        'prix': prix_bel_milli,
        'promo': False,
        'international': False,
        'score_similarite': 0.95
    }
    resultats.append(bel_milli)
    

    resultats = [r for r in resultats if r['score_similarite'] >= 0.85]
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats=pd.DataFrame(resultats)
    

    return resultats, profil_client


def recommander_options_par_ratio_without_weight_client(df_client, df_catalogue):
    profil_client, df_client = construire_profil_client(df_client)
    consommation_data =profil_client['data_volume']
    consommation_voice = profil_client['voice_volume']

    # On filtre si le client n'utilise pas l'international
    if not profil_client['international']:
        df_catalogue = df_catalogue[df_catalogue['international'] == False]
    indices_a_supprimer = []

    #for i, option in df_catalogue.iterrows():
       # if option['data_volume'] < consommation_data or option['voice_volume'] < consommation_voice:
           # indices_a_supprimer.append(i)

    # Supprimer les options qui ne conviennent pas
    df_catalogue = df_catalogue.drop(indices_a_supprimer)

        
    

    # On évite la division par zéro, on met un epsilon (petite valeur)
    epsilon = 1e-6

    client_vector = np.array([1, 1, 1, profil_client['international'], profil_client['promo'] ]).reshape(1, -1)
    # On met 1 dans le vecteur client car on va calculer ratio option/client => 1 correspond au profil client

    resultats = []

    # Calcul des durées réelles par option_id dans df_client
    durees_reelles = df_client.groupby('option_id')['duree_reelle'].sum().to_dict()

    for _, option in df_catalogue.iterrows():
        option_id = option['id']
        option['prix']=abs(option['prix'])

        data_volume = 0 if pd.isnull(option['data_volume']) else option['data_volume']
        voice_volume = 0 if pd.isnull(option['voice_volume']) else option['voice_volume']

        duree = durees_reelles.get(option_id, max(option['duree_data'], option['duree_voix']))

        # Calcul des ratios avec protection division par zéro
        ratio_data = data_volume / (profil_client['data_volume'] + epsilon)
        ratio_voix = voice_volume / (profil_client['voice_volume'] + epsilon)
        ratio_duree = duree / (profil_client['duree'] + epsilon)
        ratio_international = int(option['international'])
        ratio_promo = int(option['promo']) * 3
       
        option_vector = np.array([
            ratio_data,
            ratio_voix,
            ratio_duree,
            ratio_international,
            ratio_promo
        ]).reshape(1, -1)

        score_similarite = cosine_similarity(client_vector, option_vector)[0][0]

        resultats.append({
            'id': option['id'],
            'description': option['name'],
            'type': option['type'],
            'volume_data': data_volume,
            'volume_voix': voice_volume,
            'duree': duree,
            'prix': option['prix'],
            'promo': option['promo'],
            'international': option['international'],
            'score_similarite': score_similarite
        })

    

    

    

    resultats = [r for r in resultats if r['score_similarite'] >= 0.75]
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats=pd.DataFrame(resultats)
    

    return resultats, profil_client


def recommander_client(df_client, df_catalogue):

    recommandations_without_weight,profil_client=recommander_options_par_ratio_without_weight_client(df_client, df_catalogue)
    recommandations_with_weight,profil_client=recommander_options_par_ratio_with_weight_client(df_client, df_catalogue)
    recommandation = pd.concat([recommandations_without_weight, recommandations_with_weight], ignore_index=True).drop_duplicates()
    recommandation=recommandation.drop_duplicates(subset='id', keep='first')
    recommandation=recommandation.sort_values(by='score_similarite', ascending=False)

    return recommandation,profil_client
def dataframe_recommandations_vers_json_client(df_client, df_catalogue):
    """
    Returns recommendations and client profile as Python objects (not JSON strings)
    """
    df_recommandations, profil_client = recommander_client(df_client, df_catalogue)
    
    # Convert to dictionary format
    if df_recommandations.empty:
        recommendations = {"erreur": "Aucune recommandation disponible"}
    else:
        recommendations = {"recommandations des options": []}
        for _, row in df_recommandations.iterrows():
            recommandation = {
                "id": str(row.get('id', '')),
                "name": str(row.get('description', '')),  # Changed to 'name' to match your message function
                "type": str(row.get('type', '')).lower(),
                "volume_data": int(row.get('data_volume', 0)),
                "voice_volume": int(row.get('volume_voix', 0)),
                "duree": int(row.get('duree', 0)),
                "prix": int(row.get('prix', 0)),
                "promo": bool(row.get('promo', False)),
                "international": bool(row.get('international', False))
            }
            recommendations["recommandations des options"].append(recommandation)
    
    profil_client = {
        "data_volume": int(profil_client.get("data_volume", 0)),
        "voice_volume": int(profil_client.get("voice_volume", 0)),
        "duree": int(profil_client.get("duree", 0)),
        "international": int(profil_client.get("international", 0)),
        "promo": int(profil_client.get("promo", 0)),
        "depense_actuelle": int(profil_client.get("depense_actuelle", 0))
    }
    
    return recommendations["recommandations des options"], profil_client
def generer_messages_options_client(options_similaires, consommation_client, achats_client=None):
    """
    Génère des messages marketing dynamiques et impactants adaptés à MaxIt,
    prenant en compte la consommation client et ses achats pour proposer
    des options plus avantageuses et des économies.

    Args:
        options_similaires (list of dict): options recommandées
        consommation_client (dict): profil avec 'data_volume', 'voice_volume', 'duree', 'depense_actuelle', ...
        achats_client (list of dict): options déjà achetées par le client (optionnel)

    Returns:
        list: messages marketing prêts à l’emploi
    """

    messages = []
    data_consomme = consommation_client.get('data_volume', 0)
    depense_actuelle = consommation_client.get('depense_actuelle', 0)  # en millimes

    # Préparer une liste d'achats clients pour comparer si fournie
    achats_client = achats_client.to_dict(orient='records')
    achats_client = achats_client or []

    for option in options_similaires:
        desc = option.get("name", "")
        typ = option.get("type", "").lower()
        data_vol = option.get("volume_data", 0)
        voix_vol = option.get("volume_voix", 0)
        duree = option.get("duree", 0)
        prix = option.get("prix", 0)
        promo = option.get("promo", False)
        international = option.get("international", False)

        prix_dinar = prix / 1000  # millimes → dinars
        suffixe_duree = f"valable {duree} jour{'s' if duree > 1 else ''}" if duree else ""
        suffixe_international = " 🌍 Disponible pour appels/data à l’international." if international else ""

        # Cas spécial pour "Internet Bel Milli"
        if "bel milli" in desc.lower():
            msg = (
                f"📶 {desc} à {prix_dinar:.3f} DT — {suffixe_duree}. "
                f"Option personnalisée : achetez ce dont vous avez besoin (20 Mo à 0.09 DT) via MaxIt !"
            )
            messages.append(msg)
            continue

        # Vérifier si option est plus avantageuse que la consommation et dépense actuelles
        if typ == "data":
            # Comparaison avec consommation et dépenses actuelles
            if data_vol >= data_consomme and prix < depense_actuelle:
                economie = round((depense_actuelle - prix) / 1000, 3)
                msg = (
                    f"💡 MaxIt vous recommande : au lieu de plusieurs petits achats, "
                    f"prenez '{desc}' ({suffixe_duree}) à {prix_dinar:.3f} DT. "
                    f"Vous économisez environ {economie:.3f} DT et profitez de plus de data ! 🚀"
                )
            else:
                # Message classique amélioré pour data
                if promo:
                    msg = (
                        f"🔥 Offre EXCLU MaxIt : {desc} à seulement {prix_dinar:.3f} DT ! "
                        f"{suffixe_duree} – Naviguez à fond, sans vous ruiner. {suffixe_international}"
                    )
                else:
                    msg = (
                        f"📶 {desc} à {prix_dinar:.3f} DT — {suffixe_duree}. "
                        f"Rechargez vos Gigas maintenant via MaxIt !{suffixe_international}"
                    )
        elif typ == "voix":
            # Message pour voix
            if promo:
                msg = (
                    f"📞 Offre spéciale appels : {desc} à prix promo {prix_dinar:.3f} DT ! "
                    f"{suffixe_duree} – Idéal pour rester en contact. {suffixe_international}"
                )
            else:
                msg = (
                    f"📞 {desc} disponible à {prix_dinar:.3f} DT – {suffixe_duree}. "
                    f"Activez-la directement sur MaxIt !{suffixe_international}"
                )
        else:
            # Autres types d'options
            msg = (
                f"📱 {desc} pour {prix_dinar:.3f} DT – {suffixe_duree}. "
                f"Une option complète, à activer via MaxIt. {suffixe_international}"
            )

        messages.append(msg.strip())

    return messages
import json
import ollama
from typing import Dict, List, Any
from pydantic import BaseModel, ValidationError
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modèle de sortie attendu du LLM
class MarketingMessageResponse(BaseModel):
    acquisition: List[str]
    jeux_et_fidelisation: List[str]
    options_recommandees: List[str]
    services_marketplace: List[str]
    messages_personnalises: List[str]
    messages_generaux: List[str]

def validate_client_report(report: str) -> bool:
    return "Profil MaxIt" in report and "Statut Churn" in report

def is_client_maxit(rapport: str) -> bool:
    return "Profil MaxIt : Oui" in rapport or "Profil MaxIt : True" in rapport

def generate_marketing_messages_client(
    rapport_client: str,
    messages_options: List[str],
    model: str = "qwen2.5:3b",
    max_retries: int = 3
) -> Dict[str, List[str]]:
    if not validate_client_report(rapport_client):
        raise ValueError("Le rapport client est incomplet.")

    est_maxit = is_client_maxit(rapport_client)

    # SYSTEM PROMPT
    system_prompt = (
        "Tu es un expert marketing senior d’Orange Tunisie. ;eviter de marquer nom de client;essayer de chercher et se baser bien sur l'application maxit de orange tunise et ses rubriques et ses services"
        "Tu conçois des campagnes mobiles (SMS, push, notifications) pour MaxIt, l’app Orange dédiée. "
        "Tu dois générer des messages concrets, engageants, et adaptés au profil du client pour augmenter son engagement."
    )

    # Instructions adaptées au profil MaxIt
    if est_maxit:
        consigne_acquisition = (
            "- Ce client utilise déjà MaxIt. Ne propose **aucun message d'acquisition**.\n"
            "- Concentre-toi sur la fidélisation, les jeux, les services digitaux et les programmes bonus."
        )
    else:
        consigne_acquisition = (
            "- Ce client n'est pas MaxIt. Tu dois proposer 1 à 2 messages d’acquisition dans la section 'acquisition'.\n"
            "- Mentionne le lien de téléchargement : https://www.orange.tn/maxit avec bonus d'installation 200 Mo."
        )

    # USER PROMPT
    prompt_user = f"""
🧠 Contexte :
Génère des messages marketing personnalisés pour un client Orange Tunisie, à partir du rapport ci-dessous.

📄 Rapport client :
{rapport_client}

📦 Messages d’options recommandées à intégrer dans "options_recommandees" (fournis par une autre fonction) :
{json.dumps(messages_options, indent=2, ensure_ascii=False)}

📌 Instructions :
{consigne_acquisition}
- Si le client utilise Flouci, USSD, Mobimoney... explique pourquoi MaxIt est meilleur : centralisé, rapide, suivi conso, bonus...
- S’il ne joue pas, propose la roue de la chance du jeudi, les pins et les bonus de fidélité.
- Propose les services digitaux comme Shahid VIP pour les fans de séries/films.
- Valorise les partenaires comme WinWin : coupons, bons plans locaux selon zone.
- Utilise un ton engageant et professionnel, messages courts, type push/mobile.
- Fournis les messages dans le format JSON ci-dessous.

🎯 Format de sortie STRICT :
{{
  "acquisition": ["..."],
  "jeux_et_fidelisation": ["..."],
  "options_recommandees": ["..."],
  "services_marketplace": ["..."],
  "messages_personnalises": ["..."],
  "messages_generaux": ["..."]
}}
"""

    for attempt in range(max_retries):
        try:
            logger.info(f"Tentative {attempt+1}/{max_retries} - Appel LLM...")

            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_user}
                ]
            )

            content = response['message']['content']
            result = json.loads(content)
            validated = MarketingMessageResponse(**result)

            # 🔁 Supprimer "acquisition" si MaxIt
            if est_maxit:
                validated.acquisition = []

            # ✅ Fusionner les messages générés avec ceux d’options
            final_result = validated.dict()
            final_result["options_recommandees"] = messages_options

            logger.info("✅ Dictionnaire final des messages marketing généré avec succès.")
            return final_result

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"⚠️ Erreur JSON/validation : {e}")
            if attempt == max_retries - 1:
                raise RuntimeError("Erreur persistante dans la génération des messages.")
        except Exception as e:
            logger.error(f"❌ Erreur LLM : {e}")
            if attempt == max_retries - 1:
                raise RuntimeError("Erreur critique LLM après plusieurs tentatives.")

    raise RuntimeError("Erreur LLM non résolue.")
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def calculer_depense_totale(df):
    return int(df['prix'].sum())



def recommander_options_par_ratio_with_weight(df_client, df_catalogue):
    profil_client, df_client= construire_profil_segment(df_client)
    

    # On filtre si le client n'utilise pas l'international
    if not profil_client['international']:
        df_catalogue = df_catalogue[df_catalogue['international'] == False]
    indices_a_supprimer = []

    #for i, option in df_catalogue.iterrows():
       # if option['data_volume'] < consommation_data or option['voice_volume'] < consommation_voice:
           # indices_a_supprimer.append(i)

    # Supprimer les options qui ne conviennent pas
    df_catalogue = df_catalogue.drop(indices_a_supprimer)

        
    

    # On évite la division par zéro, on met un epsilon (petite valeur)
    epsilon = 1e-6

    client_vector = np.array([1, 1, 3, profil_client['international'], profil_client['promo']*2 ]).reshape(1, -1)
    # On met 1 dans le vecteur client car on va calculer ratio option/client => 1 correspond au profil client

    resultats = []

    # Calcul des durées réelles par option_id dans df_client
    durees_reelles = df_client.groupby('option_id')['duree_reelle'].sum().to_dict()

    for _, option in df_catalogue.iterrows():
        option_id = option['id']
        option['prix']=abs(option['prix'])

        data_volume = 0 if pd.isnull(option['data_volume']) else option['data_volume']
        voice_volume = 0 if pd.isnull(option['voice_volume']) else option['voice_volume']

        duree = durees_reelles.get(option_id, max(option['duree_data'], option['duree_voix']))

        # Calcul des ratios avec protection division par zéro
        ratio_data = data_volume / (profil_client['data_volume'] + epsilon)
        ratio_voix = voice_volume / (profil_client['voice_volume'] + epsilon)
        ratio_duree = duree / (profil_client['duree'] + epsilon)
        ratio_international = int(option['international'])
        ratio_promo = int(option['promo']) * 3
       
        option_vector = np.array([
            ratio_data,
            ratio_voix,
            ratio_duree,
            ratio_international,
            ratio_promo
        ]).reshape(1, -1)

        score_similarite = cosine_similarity(client_vector, option_vector)[0][0]

        resultats.append({
            'id': option['id'],
            'description': option['name'],
            'type': option['type'],
            'volume_data': data_volume,
            'volume_voix': voice_volume,
            'duree': duree,
            'prix': option['prix'],
            'promo': option['promo'],
            'international': option['international'],
            'score_similarite': score_similarite
        })

    

    prix_bel_milli = 0.09 * (profil_client['data_volume'] / 20)

    # Option Internet à la demande
    bel_milli = {
        'id': 'bel_milli',
        'description': 'Internet Bel Milli (à la demande)',
        'type': 'Data',
        'volume_data':profil_client['data_volume']  ,
        'volume_voix': 0,
        'duree': 30,
        'prix': prix_bel_milli,
        'promo': False,
        'international': False,
        'score_similarite': 0.95
    }
    resultats.append(bel_milli)
    

    resultats = [r for r in resultats if r['score_similarite'] >= 0.85]
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats=pd.DataFrame(resultats)
    

    return resultats, profil_client


def recommander_options_par_ratio_without_weight(df_client, df_catalogue):
    profil_client, df_client= construire_profil_segment(df_client)
    
    # On filtre si le client n'utilise pas l'international
    if not profil_client['international']:
        df_catalogue = df_catalogue[df_catalogue['international'] == False]
    indices_a_supprimer = []

    #for i, option in df_catalogue.iterrows():
       # if option['data_volume'] < consommation_data or option['voice_volume'] < consommation_voice:
           # indices_a_supprimer.append(i)

    # Supprimer les options qui ne conviennent pas
    df_catalogue = df_catalogue.drop(indices_a_supprimer)

        
    

    # On évite la division par zéro, on met un epsilon (petite valeur)
    epsilon = 1e-6

    client_vector = np.array([1, 1, 1, profil_client['international'], profil_client['promo'] ]).reshape(1, -1)
    # On met 1 dans le vecteur client car on va calculer ratio option/client => 1 correspond au profil client

    resultats = []

    # Calcul des durées réelles par option_id dans df_client
    durees_reelles = df_client.groupby('option_id')['duree_reelle'].sum().to_dict()

    for _, option in df_catalogue.iterrows():
        option_id = option['id']
        option['prix']=abs(option['prix'])

        data_volume = 0 if pd.isnull(option['data_volume']) else option['data_volume']
        voice_volume = 0 if pd.isnull(option['voice_volume']) else option['voice_volume']

        duree = durees_reelles.get(option_id, max(option['duree_data'], option['duree_voix']))

        # Calcul des ratios avec protection division par zéro
        ratio_data = data_volume / (profil_client['data_volume'] + epsilon)
        ratio_voix = voice_volume / (profil_client['voice_volume'] + epsilon)
        ratio_duree = duree / (profil_client['duree'] + epsilon)
        ratio_international = int(option['international'])
        ratio_promo = int(option['promo']) * 3
       
        option_vector = np.array([
            ratio_data,
            ratio_voix,
            ratio_duree,
            ratio_international,
            ratio_promo
        ]).reshape(1, -1)

        score_similarite = cosine_similarity(client_vector, option_vector)[0][0]

        resultats.append({
            'id': option['id'],
            'description': option['name'],
            'type': option['type'],
            'volume_data': data_volume,
            'volume_voix': voice_volume,
            'duree': duree,
            'prix': option['prix'],
            'promo': option['promo'],
            'international': option['international'],
            'score_similarite': score_similarite
        })

    

    

    

    resultats = [r for r in resultats if r['score_similarite'] >= 0.75]
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats=pd.DataFrame(resultats)
    

    return resultats, profil_client


def recommander(df_client, df_catalogue):

    recommandations_without_weight,profil_client=recommander_options_par_ratio_without_weight(df_client, df_catalogue)
    recommandations_with_weight,profil_client=recommander_options_par_ratio_with_weight(df_client, df_catalogue)
    recommandation = pd.concat([recommandations_without_weight, recommandations_with_weight], ignore_index=True).drop_duplicates()
    recommandation=recommandation.drop_duplicates(subset='id', keep='first')
    recommandation=recommandation.sort_values(by='score_similarite', ascending=False)

    return recommandation,profil_client
def dataframe_recommandations_vers_json(df_client, df_catalogue):
    """
    Returns recommendations and client profile as Python objects (not JSON strings)
    """
    df_recommandations, profil_client = recommander(df_client, df_catalogue)
    
    # Convert to dictionary format
    if df_recommandations.empty:
        recommendations = {"erreur": "Aucune recommandation disponible"}
    else:
        recommendations = {"recommandations des options": []}
        for _, row in df_recommandations.iterrows():
            recommandation = {
                "id": str(row.get('id', '')),
                "name": str(row.get('description', '')),  # Changed to 'name' to match your message function
                "type": str(row.get('type', '')).lower(),
                "volume_data": int(row.get('data_volume', 0)),
                "voice_volume": int(row.get('volume_voix', 0)),
                "duree": int(row.get('duree', 0)),
                "prix": int(row.get('prix', 0)),
                "promo": bool(row.get('promo', False)),
                "international": bool(row.get('international', False))
            }
            recommendations["recommandations des options"].append(recommandation)
    
    profil_client = {
        "data_volume": int(profil_client.get("data_volume", 0)),
        "voice_volume": int(profil_client.get("voice_volume", 0)),
        "duree": int(profil_client.get("duree", 0)),
        "international": int(profil_client.get("international", 0)),
        "promo": int(profil_client.get("promo", 0)),
        "depense_actuelle": int(profil_client.get("depense_actuelle", 0))
    }
    
    return recommendations["recommandations des options"], profil_client



import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings
import ollama
from ollama import Client
client = Client(host=settings.OLLAMA_HOST)
import pandas as pd
import re
from typing import Tuple, Optional
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
            # 3. Supprimer les mots 'df' et 'mois' s'ils apparaissent dans le nom
            nom_cle = re.sub(r'\b(df|mois)\b', '', nom_cle, flags=re.IGNORECASE)
            # 4. Nettoyer les underscores en trop
            nom_cle = nom_cle.strip('_').replace('__', '_')

            dfs[nom_cle] = df
            print(f"Chargé: {fichier} → clé: '{nom_cle}' (shape: {df.shape})")
        except Exception as e:
            print(f"Erreur en chargeant {fichier} : {e}")
    return dfs

def filtrer_clients_par_segments(segment_criteria, date_debut, date_fin,type, folder_path):
    from datetime import datetime
    import pandas as pd
    import numpy as np
    import os
    import logging

    # Configuration du logger
    logger = logging.getLogger(__name__)
    
    # Conversion des dates si nécessaire
    if isinstance(date_debut, str):
        date_debut = datetime.strptime(date_debut, '%Y-%m-%d')
    if isinstance(date_fin, str):
        date_fin = datetime.strptime(date_fin, '%Y-%m-%d')
        
    # Vérification du dossier de données
    if not os.path.exists(folder_path):
        error_msg = f"Le dossier de données n'existe pas: {folder_path}"
        logger.error(error_msg)
        return [], {}, pd.DataFrame(), "error_data_folder_not_found"

    # 1. Chargement sélectif des fichiers nécessaires
    try:
        fichiers = detect_csvs_inclusive(folder_path, date_debut, date_fin)
        logger.info(f"Fichiers détectés pour la période {date_debut} à {date_fin}: {fichiers}")
        
        if not fichiers:
            error_msg = f"Aucun fichier trouvé dans {folder_path} pour la période spécifiée"
            logger.error(error_msg)
            return [], {}, pd.DataFrame(), "error_no_files_found"
            
        dfs = load_csvs_with_clean_keys(folder_path, fichiers)
        logger.info(f"DataFrames chargés: {list(dfs.keys())}")
        
    except Exception as e:
        error_msg = f"Erreur lors du chargement des fichiers: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [], {}, pd.DataFrame(), f"error_loading_files: {str(e)}"

    # 2. Chargement sélectif des colonnes nécessaires
    colonnes_segmentation = ['msisdn', 'segment_rentabilité', 'segment_engagement', 
                            'segment_type_client', 'segment_type_interet', 
                            'segment_interet_international', 'segment_interet_jeu',
                            'segment_interet_promo', 'segment_action']
    
    # 3. Chargement des données avec sélection de colonnes
    segmentations = dfs.get('df_segmentation_mois', pd.DataFrame())
    logger.info(f"Colonnes disponibles dans les données de segmentation: {segmentations.columns.tolist() if not segmentations.empty else 'Aucune donnée de segmentation'}")
    
    if segmentations.empty:
        error_msg = "Aucune donnée de segmentation n'a été chargée. Vérifiez les fichiers df_segmentation_mois_*.csv"
        logger.error(error_msg)
        return [], {}, pd.DataFrame(), "error_no_segmentation_data"
        
    # Vérification et nettoyage des colonnes
    try:
        # Vérifier si la colonne msisdn existe, sinon essayer des alternatives courantes
        if 'msisdn' not in segmentations.columns:
            possible_msisdn_cols = [
                col for col in segmentations.columns 
                if any(x in str(col).lower() for x in ['msisdn', 'phone', 'numero', 'number', 'tel', 'mobile'])
            ]
            
            if possible_msisdn_cols:
                logger.warning(f"Colonne 'msisdn' non trouvée. Colonnes potentielles détectées: {possible_msisdn_cols}")
                # Utiliser la première colonne correspondante comme msisdn
                segmentations = segmentations.rename(columns={possible_msisdn_cols[0]: 'msisdn'})
                logger.info(f"Colonne renommée: '{possible_msisdn_cols[0]}' → 'msisdn'")
            else:
                error_msg = f"Aucune colonne 'msisdn' trouvée dans les données de segmentation. Colonnes disponibles: {segmentations.columns.tolist()}"
                logger.error(error_msg)
                return [], {}, pd.DataFrame(), "error_missing_msisdn"
        
        # Nettoyer les valeurs de msisdn (au cas où)
        segmentations['msisdn'] = segmentations['msisdn'].astype(str).str.strip()
        
        # Sélectionner uniquement les colonnes nécessaires
        colonnes_disponibles = [col for col in colonnes_segmentation if col in segmentations.columns]
        colonnes_manquantes = [col for col in colonnes_segmentation if col not in segmentations.columns]
        
        if colonnes_manquantes:
            logger.warning(f"Colonnes de segmentation manquantes: {colonnes_manquantes}")
            
        segmentations = segmentations[['msisdn'] + [col for col in colonnes_disponibles if col != 'msisdn']]
        
    except Exception as e:
        error_msg = f"Erreur lors du traitement des données de segmentation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [], {}, pd.DataFrame(), f"error_processing_segmentation: {str(e)}"
    
    # 4. Filtrage des segments
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
    colonne_map = {k: v for k, v in colonne_map.items() if k in segment_criteria}

    # Chargement et filtrage initial des clients par type (acquisition/maxit)
    clients = dfs.get('df_client_info', pd.DataFrame())
    if not clients.empty and 'type_client' in clients.columns and 'msisdn' in clients.columns:
        if type == 'acquisition':
            clients = clients[clients['type_client'] != 'maxit'].copy()
        else:
            clients = clients[clients['type_client'] == 'maxit'].copy()
        client_list = set(clients['msisdn'].astype(str).tolist())
    else:
        client_list = set()

    # 5. Filtrage vectorisé initial basé sur les critères de segmentation
    mask = pd.Series(True, index=segmentations.index)
    
    # Appliquer les critères de segmentation
    for critere, valeur in segment_criteria.items():
        if valeur and critere in colonne_map:
            col = colonne_map[critere]
            if col in segmentations.columns:
                mask &= (segmentations[col] == valeur)
    
    # Appliquer le masque de segmentation et filtrer par la liste des clients
    if client_list:  # Si on a des clients à filtrer
        mask &= segmentations['msisdn'].astype(str).isin(client_list)
    
    # Récupérer la liste finale des MSISDN uniques
    msisdn_list = segmentations.loc[mask, 'msisdn'].astype(str).unique().tolist()
    print(f"Nombre de clients sélectionnés: {len(msisdn_list)}")
    
    # 6. Si aucun client ne correspond
    if not msisdn_list:
        return [], pd.DataFrame(), pd.DataFrame(), "no_segment"
    colonnes_resultat = ['msisdn'] + [col for col in colonne_map.values() if col in segmentations.columns]
    df_filtre = segmentations[colonnes_resultat].copy()
    print("colonnes de filtrage",colonnes_resultat)
    

    # 7. Chargement des autres données uniquement pour les MSISDN sélectionnés
    
    if not clients.empty and 'msisdn' in clients.columns:
        clients = clients[clients['msisdn'].isin(msisdn_list)]
    consommations = dfs['consommation_mois'] if 'consommation_mois' in dfs else pd.DataFrame()
    # 8. Chargement des transactions avec sélection de colonnes
    transactions = {}
    for table in ['achat', 'recharge', 'spins', 'consommation_mois']:
        if table in dfs and not dfs[table].empty and 'msisdn' in dfs[table].columns:
            transactions[table] = dfs[table][dfs[table]['msisdn'].isin(msisdn_list)].copy()
        else:
            transactions[table] = pd.DataFrame()

    # 9. Traitement du churn
    churn = dfs.get('churn_par_client_par_mois', pd.DataFrame())
    if not churn.empty and 'msisdn' in churn.columns and 'month' in churn.columns:
        churn = churn[(churn['msisdn'].isin(msisdn_list)) & 
                     (churn['month'] == date_debut)]
        churn_dict = churn.set_index('msisdn')['churn'].to_dict()
    else:
        churn_dict = {}

    # 10. Préparation des données groupées
    grouped_data = {}
    for table in transactions:
        if not transactions[table].empty:
            try:
                grouped_data[table] = transactions[table].groupby('msisdn')
            except Exception as e:
                print(f"Erreur lors du groupement de {table}: {e}")
                grouped_data[table] = {}

    # 11. Traitement des options (une seule fois pour tous les clients)
    options_list = []
    if 'achat' in transactions and not transactions['achat'].empty:
        options_list = [extract_option_details(row) for _, row in transactions['achat'].iterrows()]
    
    options_df = pd.DataFrame(options_list)
    if not options_df.empty and 'achat' in transactions:
        options_df['msisdn'] = transactions['achat']['msisdn'].values[:len(options_df)]
    
    options_grouped = options_df.groupby('msisdn') if not options_df.empty and 'msisdn' in options_df.columns else {}

    # 12. Construction des résultats
    result = []
    clients_data = []
    
    for msisdn in msisdn_list:
        # Récupération des données groupées
        client_info = clients[clients['msisdn'] == msisdn].to_dict('records')[0] if not clients.empty else {}
        
        # Churn
        churn_label = 'Churn' if churn_dict.get(msisdn, 0) == 1 else 'Non Churn'
        est_maxit = 'Maxit' if client_info.get('est_maxit', False) else 'Non Maxit'
        
        # Récupération des transactions groupées
        def get_grouped_data(grouped, key):
            if key in grouped.groups:
                return grouped.get_group(key).to_dict('records')
            return {}
            
        achats = get_grouped_data(grouped_data.get('achat', {}), msisdn) if 'achat' in grouped_data else {}
        recharges = get_grouped_data(grouped_data.get('recharge', {}), msisdn) if 'recharge' in grouped_data else {}
        jeux = get_grouped_data(grouped_data.get('spins', {}), msisdn) if 'spins' in grouped_data else {}
        consommations_info = consommations[consommations['msisdn'] == msisdn] if not consommations.empty else pd.DataFrame()
        # Options
        options_dict = {}
        if not options_df.empty and msisdn in options_grouped.groups:
            try:
                options_data = options_grouped.get_group(msisdn)
                options_dict = {
                    str(row['option_id']): row.drop(['msisdn', 'option_id']).to_dict()
                    for _, row in options_data.iterrows()
                    if 'option_id' in row
                }
            except Exception as e:
                print(f"Erreur traitement options pour {msisdn}: {e}")

        # Construction du JSON du client
        client_json = {
            "client_id": msisdn,
            "periode": {
                "date_debut": str(date_debut.date()),
                "date_fin": str(date_fin.date())
            },
            "client_info": client_info,
            "churn": churn_label,
            "segmentation": segmentations[segmentations['msisdn'] == msisdn].to_dict('records')[0] if not segmentations.empty else {},
            "profil_maxit": est_maxit,
            "consommations": consommations_info.to_dict(orient='records')[0] if not consommations_info.empty else {},
            "achats": {str(a.get('achat_id', idx)): a for idx, a in enumerate(achats)},
            "recharges": {str(r.get('recharge_id', idx)): r for idx, r in enumerate(recharges)},
            "jeux": {str(j.get('spin_id', idx)): j for idx, j in enumerate(jeux)},
            "options": options_dict
        }

        result.append(client_json)
        if client_info:
            clients_data.append(client_info)
    print('filtrage completé')

    # 13. Préparation des données de sortie
    clients_df = pd.DataFrame(clients_data) if clients_data else pd.DataFrame()
    all_options = options_df if not options_df.empty else pd.DataFrame()
    segment_id = "_".join([f"{k}_{v}" for k, v in segment_criteria.items() if v])

    return result, all_options, clients_df, segment_id

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
    df['date_achat'] = pd.to_datetime(df['date_achat'], format='%Y-%m-%d')
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
    len_unique = len(df['msisdn'].unique())


    profil_segment = {
        'data_volume': int(total_data/len_unique),
        'voice_volume': int(total_voix/len_unique),
        'duree': 30,  # Valeur par défaut (même logique que dans construire_profil_client)
        'international': 1 if df['name'].str.contains('international', case=False).any() else 0,
        'promo': 1 if df['prix'].min() == 0 else 0,
        'depense_actuelle': int(total_depense/len_unique)
    }

    return profil_segment,df


import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def calculer_depense_totale(df):
    return int(df['prix'].sum())





def recommander_options_par_ratio_without_weight(df_client, df_catalogue):
    profil_client, df_client= construire_profil_segment(df_client)
    

    consommation_data = profil_client['data_volume']
    consommation_voice = profil_client['voice_volume']
    depense_actuelle = profil_client['depense_actuelle']
    duree_profil = profil_client['duree']  # en jours (ex. 30)

    # Filtrage de base (international)
    if not profil_client['international']:
        df_catalogue = df_catalogue[df_catalogue['international'] == False]

    epsilon = 1e-6
    resultats = []

    # Calcul des durées réelles consommées par option
    durees_reelles = df_client.groupby('option_id')['duree_reelle'].sum().to_dict()

    for _, option in df_catalogue.iterrows():
        option_id = option['id']
        option['prix'] = abs(option['prix'])

        data_volume = 0 if pd.isnull(option['data_volume']) else option['data_volume']
        voice_volume = 0 if pd.isnull(option['voice_volume']) else option['voice_volume']

        duree = durees_reelles.get(option_id, max(option['duree_data'], option['duree_voix'], duree_profil))

        # --- 🔥 Nouveau filtrage dur ---
        if data_volume < consommation_data:
            continue
        if option['prix'] < 0.2 * depense_actuelle:
            continue

        # --- Ratios par rapport à la période complète ---
        ratio_data = data_volume / (consommation_data + epsilon)
        ratio_voix = voice_volume / (consommation_voice + epsilon)
        ratio_prix = option['prix'] / (depense_actuelle + epsilon)
        ratio_duree = duree / (duree_profil + epsilon)

        option_vector = np.array([
            ratio_data,
            ratio_voix,
            ratio_prix,
            ratio_duree,
            int(option['international']),
            int(option['promo'])
        ]).reshape(1, -1)

        client_vector = np.array([
            1.0,  # consommation data
            1.0,  # consommation voix
            1.0,  # dépense
            1.0,  # durée
            int(profil_client['international']),
            int(profil_client['promo'])
        ]).reshape(1, -1)

        # Similarité cosinus
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

    # --- Ajout Bel Milli dynamique ---
    prix_bel_milli = 90 * (profil_client['data_volume'] / 20)

    if consommation_data < 110:
        duree = 1
    elif consommation_data < 220:
        duree = 2
    elif consommation_data < 310:
        duree = 4
    elif consommation_data < 1250:
        duree = 7
    else:
        duree = 30
    volume=(profil_client['depense_actuelle'] * 20) / 90
    bel_milli = {
        'id': 'bel_milli',
        'description': 'Internet Bil Milli (à la demande)',
        'type': 'data',
        'volume_data': profil_client['data_volume'],
        'volume_voix': 0,
        'duree': duree,
        'prix': profil_client['depense_actuelle'],
        'promo': False,
        'international': False,
        'score_similarite': 0.95
    }
    resultats.append(bel_milli)

    # --- Tri final ---
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats = pd.DataFrame(resultats)

    return resultats, profil_client


def recommander(df_client, df_catalogue):

    recommandations_without_weight,profil_client=recommander_options_par_ratio_without_weight(df_client, df_catalogue)
    recommandation=recommandations_without_weight.drop_duplicates(subset='id', keep='first')
    recommandation=recommandation.sort_values(by='score_similarite', ascending=False)
    recommandation=recommandation.head(5)

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
                "international": bool(row.get('international', False)),
                 "score_similarite": float(row.get('score_similarite', 0))
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
        list: messages marketing prêts à l'emploi
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
        suffixe_international = " 🌍 Disponible pour appels/data à l'international." if international else ""

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
def generer_rapport_marketing_segment(segment_id, clients_json, segment_type='acquisition'):
    from collections import Counter, defaultdict
    import numpy as np
    from datetime import datetime

    # Initialisation
    rapport = f"📄 **Rapport Marketing Segment – `{segment_id}`**\n\n"
    rapport += f"🧑‍🤝‍🧑 **Nombre de clients dans le segment** : {len(clients_json)}\n"
    rapport += f"🏷️ **Type de segment** : {segment_type.upper()}\n"
    rapport += f"📅 **Période d'analyse** : {datetime.now().strftime('%d/%m/%Y')}\n\n"

    # === AGRÉGATION GLOBALE ===
    types_clients, engagements, rentabilites = Counter(), Counter(), Counter()
    churns, usages_types, actions_majoritaires = Counter(), Counter(), Counter()
    scores_engagement, maxit_flags = [], []

    achats_totaux, recharges_totales, jeux_totaux = 0, 0, 0
    montant_achats, montant_recharges = 0, 0

    canaux_achat, canaux_recharge = [], []
    conso_data, conso_voice, conso_sms = [], [], []
    volumes_options = Counter()
    duree_moyenne_client = []

    for client in clients_json:
        info, seg = client.get("client_info", {}), client.get("segmentation", {})
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
        
        # Calcul de l'ancienneté
        date_activation = info.get("date_activation")
        if date_activation:
            try:
                date_act = datetime.strptime(date_activation, "%Y-%m-%d")
                duree_jours = (datetime.now() - date_act).days
                duree_moyenne_client.append(duree_jours)
            except:
                pass

        # Transactions
        achats_totaux += len(achats)
        montant_achats += float(info.get("montant_total_achat", 0))
        recharges_totales += len(recharges)
        montant_recharges += float(info.get("montant_total_recharge", 0))
        jeux_totaux += len(jeux)

        canaux_achat += [a.get("login") for a in achats.values() if a and "login" in a]
        canaux_recharge += [r.get("login") for r in recharges.values() if r and "login" in r]

        # Consommation
        if isinstance(consommation, list):
            # Si consommation est une liste, prendre le premier élément ou 0 si vide
            conso_data.append(float(consommation[0].get("data_usage", 0)) if consommation else 0.0)
        else:
            # Comportement original si c'est un dictionnaire
            conso_data.append(float(consommation.get("data_usage", 0)) if consommation else 0.0)
        if isinstance(consommation, list):
            # Si consommation est une liste, prendre le premier élément ou 0 si vide
            conso_voice.append(float(consommation[0].get("voice_usage", 0)) if consommation else 0.0)
        else:
            # Comportement original si c'est un dictionnaire
            conso_voice.append(float(consommation.get("voice_usage", 0)) if consommation else 0.0)
        if isinstance(consommation, list):
            # Si consommation est une liste, prendre le premier élément ou 0 si vide
            conso_sms.append(float(consommation[0].get("sms_usage", 0)) if consommation else 0.0)
        else:
            # Comportement original si c'est un dictionnaire
            conso_sms.append(float(consommation.get("sms_usage", 0)) if consommation else 0.0)

        # Options
        for o in options.values():
            if o and "data_volume" in o:
                volumes_options[o["data_volume"]] += 1

    # === PROFIL GLOBAL DU SEGMENT ===
    rapport += "## 🧬 PROFIL DU SEGMENT\n\n"
    
    # Section spécifique au type de segment
    if segment_type == 'acquisition':
        rapport += "### 🆕 PROFIL ACQUISITION\n"
        rapport += "- Clients nouvellement acquis (moins de 3 mois)\n"
        rapport += "- Objectif : Conversion et fidélisation rapide\n"
    else:
        rapport += "### 💎 PROFIL FIDÉLISATION\n"
        rapport += "- Clients actifs depuis plus de 3 mois\n"
        rapport += "- Objectif : Augmenter la valeur client et réduire le churn\n"
    
    rapport += f"\n📊 **Métriques clés**\n"
    rapport += f"- Type client dominant : {types_clients.most_common(1)[0][0] if types_clients else 'N/A'}\n"
    rapport += f"- Engagement moyen : {np.mean(scores_engagement):.1f}/10\n"
    if duree_moyenne_client:
        rapport += f"- Ancienneté moyenne : {np.mean(duree_moyenne_client):.1f} jours\n"
    rapport += f"- Taux de churn : {(churns.get('Oui', 0) / len(clients_json) * 100):.1f}%\n"
    rapport += f"- Adoption MaxIt : {(np.mean(maxit_flags) * 100):.1f}%\n\n"

    # === ANALYSE TRANSACTIONNELLE ===
    rapport += "## 💳 COMPORTEMENT TRANSACTIONNEL\n\n"
    
    if segment_type == 'acquisition':
        rapport += "### 🔍 Comportement des nouveaux clients\n"
    else:
        rapport += "### 🔄 Comportement des clients fidèles\n"
    
    rapport += f"🛍️ **Achats**\n"
    rapport += f"- Nombre total : {achats_totaux}\n"
    rapport += f"- Montant moyen : {(montant_achats / len(clients_json)):.2f} DT/client\n" if clients_json else "0 DT\n"
    
    rapport += f"\n💳 **Recharges**\n"
    rapport += f"- Nombre total : {recharges_totales}\n"
    rapport += f"- Montant moyen : {(montant_recharges / len(clients_json)):.2f} DT/client\n" if clients_json else "0 DT\n"
    
    if canaux_achat:
        canal_achat_principal = Counter(canaux_achat).most_common(1)[0][0]
        rapport += f"\n📱 **Canal d'achat principal** : {canal_achat_principal}\n"
    
    # Analyse spécifique par segment
    if segment_type == 'acquisition':
        if achats_totaux > 0 and recharges_totales/achats_totaux < 0.5:
            rapport += "\n⚠️ **Opportunité** : Taux de conversion achat->recharge faible. Envisagez des offres groupées.\n"
    else:
        if montant_achats > 0 and montant_recharges/montant_achats > 2:
            rapport += "\n✅ **Atout** : Excellente rétention avec un bon ratio recharges/achats\n"

    # === ANALYSE DE CONSOMMATION ===
    rapport += "\n## 📱 CONSOMMATION MOYENNE\n\n"
    
    if conso_data:
        rapport += f"📶 **Données mobiles** : {np.mean(conso_data):.1f} Mo\n"
    if conso_voice:
        rapport += f"📞 **Appels vocaux** : {np.mean(conso_voice):.1f} min\n"
    if conso_sms:
        rapport += f"✉️ **SMS** : {np.mean(conso_sms):.1f} messages\n"
    
    # Recommandations basées sur la consommation
    if conso_data and np.mean(conso_data) < 100:
        if segment_type == 'acquisition':
            rapport += "\n💡 **Suggestion** : Offres d'essai data pour booster l'utilisation\n"
        else:
            rapport += "\n💡 **Suggestion** : Pack data personnalisé selon les habitudes\n"

    # === MAXIT ET OPTIONS ===
    total_actions = achats_totaux + recharges_totales + jeux_totaux
    actions_maxit = canaux_achat.count("maxit") + canaux_recharge.count("maxit")
    part_maxit = (actions_maxit / total_actions * 100) if total_actions > 0 else 0

    rapport += "\n## 📱 ADOPTION MAXIT\n"
    rapport += f"- Part des actions via MaxIt : {part_maxit:.1f}%\n"
    
    # Analyse MaxIt par segment
    if segment_type == 'acquisition':
        if part_maxit < 30:
            rapport += "🎯 **Objectif** : Augmenter l'adoption de MaxIt via des offres d'accueil\n"
        else:
            rapport += "✅ **Atout** : Bonne adoption de MaxIt dès l'acquisition\n"
    else:
        if part_maxit < 40:
            rapport += "⚠️ **Attention** : Faible utilisation de MaxIt malgré l'ancienneté\n"
        else:
            rapport += "✅ **Atout** : Excellente rétention via MaxIt\n"

    # === OPTIONS POPULAIRES ===
    if volumes_options:
        rapport += "\n## ⭐ OPTIONS LES PLUS UTILISÉES\n"
        for vol, count in volumes_options.most_common(5):
            rapport += f"- {vol} Mo : {count} utilisations\n"

    # === STRATÉGIES MARKETING PERSONNALISÉES ===
    rapport += "\n## 🎯 STRATÉGIES MARKETING\n\n"
    
    if segment_type == 'acquisition':
        # Stratégies pour l'acquisition
        rapport += "### 🆕 STRATÉGIE ACQUISITION\n"
        if np.mean(maxit_flags) < 0.3:
            rapport += "1. **Campagne d'onboarding MaxIt**\n"
            rapport += "   - Offre de bienvenue 200 Mo gratuits\n"
            rapport += "   - Tutoriel interactif de l'application\n"
            rapport += "   - Message de bienvenue personnalisé\n\n"
        
        if churns.get("Oui", 0) / len(clients_json) > 0.3:
            rapport += "2. **Réduction du churn précoce**\n"
            rapport += "   - Offre spéciale à J+7 et J+30\n"
            rapport += "   - Support client proactif\n"
            rapport += "   - Enquête de satisfaction rapide\n\n"
        
        rapport += "3. **Fidélisation précoce**\n"
        rapport += "   - Programme de parrainage avec bonus doublé\n"
        rapport += "   - Défis mensuels avec récompenses\n"
        rapport += "   - Contenu exclusif pour les nouveaux membres\n"
        
    else:
        # Stratégies pour la fidélisation
        rapport += "### 💎 STRATÉGIE FIDÉLISATION\n"
        
        if part_maxit < 40:
            rapport += "1. **Boost d'adoption MaxIt**\n"
            rapport += "   - Campagne de rappel des fonctionnalités\n"
            rapport += "   - Bonus pour activation des notifications\n"
            rapport += "   - Tutoriel avancé des services exclusifs\n\n"
        
        if churns.get("Oui", 0) / len(clients_json) > 0.2:
            rapport += "2. **Prévention du churn**\n"
            rapport += "   - Détection proactive des signaux faibles\n"
    # Commun
    rapport += "- 🧩 Personnalisation comportementale (Voix/Data, Jour/Nuit, Prépayé/Postpayé)\n"
    rapport += "- 🛍️ Mise en avant intelligente des options similaires (LLM ou clustering)\n"
    rapport += "- 📊 Intégration dans PowerBI pour surveillance KPI temps réel\n"

    taux_maxit = np.mean(maxit_flags)

    return rapport, taux_maxit
from typing import List, Dict
import json
import logging

from pydantic import BaseModel, ValidationError
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ✅ Modèle de validation
class MarketingMessageResponse(BaseModel):
    acquisition: List[str]
    jeux_et_fidelisation: List[str]
    options_recommandees: List[str]
    services_marketplace: List[str]
    messages_personnalises: List[str]
    messages_generaux: List[str]
def extract_segment_details(rapport_segment: dict) -> dict:
    segment_id = rapport_segment.get("segment_id", "").lower()
    engagement_list = rapport_segment.get("engagement", [])
    rentabilite_list = rapport_segment.get("rentabilite", [])
    type_client = None
    engagement = None
    rentabilite = None
    action_majoritaire = None
    interet_principal = None

    # 🟡 Engagement
    if engagement_list:
        engagement = engagement_list[0].get("niveau", "").lower()

    # 🟡 Rentabilité
    if rentabilite_list:
        rentabilite = rentabilite_list[0].get("niveau", "").lower()

    # 🟡 Type client (ussd, app, etc.)
    if "orienté ussd" in segment_id:
        type_client = "orienté USSD"
    elif "orienté application" in segment_id:
        type_client = "orienté APPLICATION"
    elif "orienté boutique" in segment_id:
        type_client = "orienté BOUTIQUE"

    # 🟡 Action majoritaire (achat, recharge, etc.)
    if "action_achat" in segment_id:
        action_majoritaire = "achat"
    elif "action_recharge" in segment_id:
        action_majoritaire = "recharge"
    elif "action_roue chance" in segment_id:
        action_majoritaire = "roue chance"

    # 🟡 Intérêt principal (data ou voix)
    data = rapport_segment.get("conso_data_moyenne", 0)
    voix = rapport_segment.get("conso_voix_moyenne", 0)
    if data > voix:
        interet_principal = "data"
    elif voix > data:
        interet_principal = "voix"
    else:
        interet_principal = None

    return {
        "type_client": type_client,
        "engagement": engagement,
        "rentabilite": rentabilite,
        "interet_principal": interet_principal,
        "action_majoritaire": action_majoritaire
    }

def generate_segment_marketing_messages(
    rapport_segment: str,
    messages_options_segment: List[str],
    taux_maxit: float,
    model: str = "qwen2.5:3b",
    max_retries: int = 3
) -> Dict[str, List[str]]:
    """
    Génère des messages marketing personnalisés pour un segment client Orange Tunisie.
    Se concentre sur l'acquisition et la fidélisation via l'application MaxIt.
    """
    import time
    from typing import Dict, List
    import json
    import logging
    from pydantic import BaseModel, ValidationError
    
    logger = logging.getLogger(__name__)

    # Extraction des caractéristiques du segment
    segment = extract_segment_details(rapport_segment)
    type_client = segment.get('type_client')
    rentabilite = segment.get('rentabilite')
    engagement = segment.get('engagement')
    interet_principal = segment.get('interet_principal')
    international = segment.get('international', False)
    action_majoritaire = segment.get('action_majoritaire')

    # SYSTEM PROMPT — identité métier
    system_prompt = (
        "Tu es expert marketing chez Orange Tunisie, spécialisé dans l'analyse des segments clients. "
        "Ta mission est de concevoir des campagnes marketing personnalisées pour des segments de clients via l'application MaxIt. "
        "Garde un ton professionnel, clair et engageant, typique d'Orange Tunisie."
    )

    # Définition de la stratégie
    if taux_maxit >= 0.6 or (engagement and 'très engagé' in engagement):
        strategie = "fidelisation_avancee"
        consigne_acquisition = "- Segment utilisateur avancé de MaxIt. Mettre l'accent sur la fidélisation, l'upselling et les offres premium."
    elif taux_maxit <= 0.3 or (engagement and 'non engagé' in engagement):
        strategie = "acquisition_agressive"
        consigne_acquisition = "- Segment peu familier avec MaxIt. Messages d'acquisition avec avantages immédiats, bonus de bienvenue et démonstration de valeur ajoutée."
    else:
        strategie = "mixte"
        consigne_acquisition = "- Segment utilisateur occasionnel. Combinaison équilibrée d'acquisition et de fidélisation."

    # Ajustements basés sur les caractéristiques du segment
    if rentabilite == 'non rentable':
        consigne_acquisition += "\n- Segment non rentable : proposer des offres incitatives pour augmenter la valeur moyenne du panier."
    elif rentabilite == 'rentable':
        consigne_acquisition += "\n- Segment rentable : renforcer la fidélité et proposer des offres premium."

    if type_client == 'orienté USSD':
        consigne_acquisition += "\n- Client orienté USSD : mettre en avant la simplicité et les fonctionnalités basiques de MaxIt."
    elif type_client == 'orienté APLICATION':
        consigne_acquisition += "\n- Client orienté application : mettre en avant les fonctionnalités avancées et l'expérience utilisateur."

    if interet_principal == 'data':
        consigne_acquisition += "\n- Intérêt principal pour la data : proposer des offres data et des conseils d'optimisation."
    elif interet_principal == 'voix':
        consigne_acquisition += "\n- Intérêt principal pour la voix : mettre en avant les forfaits voix et les offres d'appels."

    # Construction du prompt utilisateur
    prompt_user = f"""
 CONTEXTE DU SEGMENT

{rapport_segment}

 CARACTÉRISTIQUES DU SEGMENT
- Taux d'adoption MaxIt: {taux_maxit*100:.1f}%
- Stratégie recommandée: {strategie.upper()}
- Type client: {type_client or 'Non spécifié'}
- Niveau d'engagement: {engagement or 'Non spécifié'}
- Intérêt principal: {interet_principal or 'Non spécifié'}
- Action majoritaire: {action_majoritaire or 'Non spécifiée'}

 OPTIONS RECOMMANDÉES
{json.dumps(messages_options_segment, indent=2, ensure_ascii=False) if messages_options_segment else "Aucune option spécifique recommandée"}

 CONSIGNES DE PERSONNALISATION
{consigne_acquisition}
- Mettre en avant les avantages concrets de MaxIt pour ce profil
- Adapter le ton et les canaux au segment cible
- Proposer des offres pertinentes selon le comportement
- Inclure des appels à l'action clairs et mesurables
- Utiliser des émoticônes avec modération (max 1 par message)
- Privilégier les messages courts et impactants (max 2 lignes)

 FORMAT DE SORTIE
{{
  "acquisition": ["Message 1", "Message 2"],
  "jeux_et_fidelisation": ["Message fidélité"],
  "options_recommandees": ["Message option 1"],
  "services_marketplace": ["Message partenaire"],
  "messages_personnalises": ["Message sur-mesure"],
  "messages_generaux": ["Message d'information"]
}}
""".strip()

    # Messages de secours en cas d'échec
    def generate_fallback_messages():
        return {
            'acquisition': [
                f"Découvrez MaxIt, l'application qui simplifie votre expérience mobile ! "
                f"Profitez d'offres exclusives et gérez facilement votre forfait.",
                "Rejoignez la communauté MaxIt et bénéficiez d'avantages uniques "
                "spécialement conçus pour vous !"
            ],
            'jeux_et_fidelisation': [
                "Tentez de gagner des récompenses exclusives avec la roue de la chance MaxIt !",
                "Plus vous utilisez MaxIt, plus vous gagnez d'avantages. Découvrez nos offres fidélité !"
            ],
            'options_recommandees': messages_options_segment or ["Découvrez nos offres personnalisées sur MaxIt !"],
            'services_marketplace': [
                "Découvrez nos offres partenaires exclusives sur MaxIt !",
                "Profitez de réductions exceptionnelles sur vos services préférés avec MaxIt."
            ],
            'messages_personnalises': [
                "Nous avons des offres spécialement conçues pour vous sur MaxIt !",
                "Votre profil unique mérite des avantages uniques. Découvrez-les sur MaxIt !"
            ],
            'messages_generaux': [
                "Téléchargez MaxIt dès maintenant pour une expérience client inégalée !",
                "Avec MaxIt, profitez du meilleur d'Orange Tunisie dans votre poche."
            ]
        }

    # Tentatives d'appel au modèle
    for attempt in range(max_retries):
        try:
            logger.info(f"Tentative {attempt+1}/{max_retries} - Appel LLM...")

            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_user}
                ],
                options={"temperature": 0.7, "max_tokens": 1000}
            )

            content = response['message']['content'].strip()
            
            # Extraction du JSON de la réponse
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            # Validation de la réponse
            result = json.loads(content)
            validated = MarketingMessageResponse(**result)
            
            # Fusion avec les options recommandées
            final_result = validated.dict()
            final_result["options_recommandees"] = messages_options_segment

            logger.info(" Messages marketing segment générés avec succès.")
            return final_result

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Erreur format JSON/validation LLM (tentative {attempt+1}): {e}")
            if attempt == max_retries - 1:  # Dernière tentative
                logger.warning("Utilisation des messages de secours...")
                return generate_fallback_messages()
                
        except Exception as e:
            logger.error(f"Erreur inconnue LLM (tentative {attempt+1}): {e}")
            if attempt == max_retries - 1:  # Dernière tentative
                logger.warning("Utilisation des messages de secours...")
                return generate_fallback_messages()
            
            # Délai entre les tentatives
            time.sleep(min(2 ** attempt, 10))  # Attente exponentielle avec un maximum de 10 secondes
    
    # En cas d'échec total
    return generate_fallback_messages()

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
        m = re.search(r'(\d+)\s*(j|jr|jrs)\b', description)
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
    match = re.search(r'(\d+)\s*(j|jr|jrs|jour|jours)\b', description)
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
        return mode.iloc[0]  # Plus sûr que [0]
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

def extract_option_details(row: pd.Series) -> dict:
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

    # Cas spécial pour "internet bil milli"
    if str(description).lower() == "internet bil milli":
        data_volume = abs(float(prix)) * 20 / 90  # volume calculé à partir du prix
    else:
        data_volume = extraire_quantite(description) if is_data else 0

    details = {
        'option_id': f"opt_{event_date.strftime('%Y-%m-%dT%H:%M:%S')}" if pd.notnull(event_date) else "opt_invalide",
        'name': str(description)[:100],
        'type': option_type,
        'duree_data': duree_totale if is_data else 0,
        'duree_voix': duree_totale if is_voix else 0,
        'data_volume': data_volume,
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
            # 3. Supprimer les mots 'df' et 'mois' s'ils apparaissent dans le nom
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

    # Vérifier si la colonne 'msisdn' existe dans le DataFrame segmentations
    if 'msisdn' not in segmentations.columns:
        # Essayer de trouver la colonne qui pourrait contenir les numéros de téléphone
        possible_msisdn_cols = [col for col in segmentations.columns if 'msisdn' in col.lower() or 'tel' in col.lower() or 'phone' in col.lower()]
        
        if possible_msisdn_cols:
            # Utiliser la première colonne correspondante comme msisdn
            segmentations = segmentations.rename(columns={possible_msisdn_cols[0]: 'msisdn'})
            logging.warning(f"Colonne 'msisdn' non trouvée. Utilisation de la colonne '{possible_msisdn_cols[0]}' à la place.")
        else:
            # Si aucune colonne potentielle n'est trouvée, créer une colonne vide
            segmentations['msisdn'] = ''
            logging.warning("Aucune colonne 'msisdn' ou similaire trouvée dans les données de segmentation.")
    
    # Filtrer les données de segmentation pour le msisdn donné
    try:
        segment_info = segmentations[segmentations['msisdn'] == msisdn]
    except Exception as e:
        logging.error(f"Erreur lors du filtrage des données de segmentation: {str(e)}")
        segment_info = pd.DataFrame()  # Retourner un DataFrame vide en cas d'erreur

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
        rapport += "- ❌ **Client Non MaxIt** : potentiel d'acquisition important\n"
    # Supposons que json_client['options'] contient toutes les options achetées
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



    # --- 4. Consommation ---
    rapport += f"\n📶 **Consommation du client**\n"
    rapport += f"- Données consommées : {total_data_mo} Mo\n"
    rapport += f"- Voix utilisée : {consommations.get('voice_usage', 0)} minutes\n"
    rapport += f"- SMS : {consommations.get('sms_usage', 0)} messages\n"

    # --- 5. Comportement sur les options ---
    from collections import Counter

    # Comptabiliser les options avec un traitement spécial pour 'internet bil milli'
    volumes_options = Counter()

    for o in options.values():
        if 'data_volume' in o:
            vol = o['data_volume']
            # Cas spécial pour "internet bil milli"
            if isinstance(o['name'], str) and o['name'].lower() == 'internet bil milli':
                vol = 'Internet bel milli'
            volumes_options[vol] += 1

    # Générer le texte pour le rapport
    rapport += f"\n📦 **Options achetées**\n"
    for vol, count in volumes_options.items():
        if isinstance(vol, (int, float)):
            rapport += f"- Option {int(vol)} Mo : {count} fois\n"
        else:
            rapport += f"- Option {vol} : {count} fois\n"


    # --- 6. Typologie de messages marketing à envisager ---
    rapport += f"\n📩 **Typologie des messages marketing à privilégier**\n"

    if not is_maxit:
        rapport += "- 📲 **Messages d'acquisition MaxIt** : promotion de l'app, lien de téléchargement, bonus 200 Mo\n"
    elif churn == "Churn":
        rapport += "- 🧲 **Messages de réactivation** : relance jeux, roue chance, pins, promo spéciale fidélisation\n"
    elif part_maxit < 40:
        rapport += "- 🚀 **Messages d'incitation à l'usage MaxIt** : rappeler les services, canaux, services WinWin\n"
    else:
        rapport += "- 🎯 **Messages de fidélisation** : marketplace, nouveaux services, avantages personnalisés\n"

    rapport += "- 🎮 **Jeux & gamification** : roue de la chance, pins à gagner, notifications hebdomadaires\n"
    rapport += "- 🎁 **Messages sur les options similaires** : à recommander via LLM2\n"
    rapport += "- 🛍️ **Marketplace & services partenaires** : coupons, réductions locales selon localisation\n"
    rapport += "- 🧩 **Personnalisation comportementale** : achat, recharge, promo, intérêt voix/data\n"

    return rapport

import os
import re
from datetime import datetime

def calculer_depense_totale(df):
    return int(df['prix'].sum())


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
    profil_client, df_client = construire_profil_client_client(df_client)
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

    

    

    resultats = [r for r in resultats if r['score_similarite'] >= 0.85]
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats=pd.DataFrame(resultats)
    

    return resultats, profil_client


def recommander_options_par_ratio_without_weight_client(df_client, df_catalogue):
    profil_client, df_client = construire_profil_client_client(df_client)

    consommation_data = profil_client['data_volume']
    consommation_voice = profil_client['voice_volume']
    depense_actuelle = profil_client['depense_actuelle']
    duree_profil = profil_client['duree']  # en jours (ex. 30)

    # Filtrage de base (international)
    if not profil_client['international']:
        df_catalogue = df_catalogue[df_catalogue['international'] == False]

    epsilon = 1e-6
    resultats = []

    # Calcul des durées réelles consommées par option
    durees_reelles = df_client.groupby('option_id')['duree_reelle'].sum().to_dict()

    for _, option in df_catalogue.iterrows():
        option_id = option['id']
        option['prix'] = abs(option['prix'])

        data_volume = 0 if pd.isnull(option['data_volume']) else option['data_volume']
        voice_volume = 0 if pd.isnull(option['voice_volume']) else option['voice_volume']

        duree = durees_reelles.get(option_id, max(option['duree_data'], option['duree_voix'], duree_profil))

        # --- 🔥 Nouveau filtrage dur ---
        if data_volume < consommation_data:
            continue
        if option['prix'] < 0.2 * depense_actuelle:
            continue

        # --- Ratios par rapport à la période complète ---
        ratio_data = data_volume / (consommation_data + epsilon)
        ratio_voix = voice_volume / (consommation_voice + epsilon)
        ratio_prix = option['prix'] / (depense_actuelle + epsilon)
        ratio_duree = duree / (duree_profil + epsilon)

        option_vector = np.array([
            ratio_data,
            ratio_voix,
            ratio_prix,
            ratio_duree,
            int(option['international']),
            int(option['promo'])
        ]).reshape(1, -1)

        client_vector = np.array([
            1.0,  # consommation data
            1.0,  # consommation voix
            1.0,  # dépense
            1.0,  # durée
            int(profil_client['international']),
            int(profil_client['promo'])
        ]).reshape(1, -1)

        # Similarité cosinus
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

    # --- Ajout Bel Milli dynamique ---
    prix_bel_milli = 90 * (profil_client['data_volume'] / 20)

    if consommation_data < 110:
        duree = 1
    elif consommation_data < 220:
        duree = 2
    elif consommation_data < 310:
        duree = 4
    elif consommation_data < 1250:
        duree = 7
    else:
        duree = 30
    volume=(profil_client['depense_actuelle'] * 20) / 90
    bel_milli = {
        'id': 'bel_milli',
        'description': 'Internet Bil Milli (à la demande)',
        'type': 'data',
        'volume_data': profil_client['data_volume'],
        'volume_voix': 0,
        'duree': duree,
        'prix': profil_client['depense_actuelle'],
        'promo': False,
        'international': False,
        'score_similarite': 0.95
    }
    resultats.append(bel_milli)

    # --- Tri final ---
    resultats = sorted(resultats, key=lambda x: x['score_similarite'], reverse=True)
    resultats = pd.DataFrame(resultats)

    return resultats, profil_client



def recommander_client(df_client, df_catalogue):

    recommandations_without_weight,profil_client=recommander_options_par_ratio_without_weight_client(df_client, df_catalogue)
    recommandation=recommandations_without_weight.drop_duplicates(subset='id', keep='first')
    recommandation=recommandation.sort_values(by='score_similarite', ascending=False)
    recommandation=recommandation.head(5)

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
                "international": bool(row.get('international', False)),
                "score_similarite": float(row.get('score_similarite', 0))
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
        list: messages marketing prêts à l'emploi
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
        suffixe_international = " 🌍 Disponible pour appels/data à l'international." if international else ""

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
import requests
from typing import Dict, List, Any
from pydantic import BaseModel, ValidationError
import logging
import time
from django.conf import settings
import ollama
# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
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

import json
import logging
from pydantic import ValidationError
from django.conf import settings
import ollama
from ollama import Client
import settings
logger = logging.getLogger(__name__)
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings
import ollama
from ollama import Client
import json
import logging
from typing import Dict, List
from pydantic import BaseModel, ValidationError
import requests
from django.conf import settings
import ollama
logger = logging.getLogger(__name__)

class MarketingMessageResponse(BaseModel):
    acquisition: List[str]
    jeux_et_fidelisation: List[str]
    options_recommandees: List[str]
    services_marketplace: List[str]
    messages_personnalises: List[str]
    messages_generaux: List[str]

def validate_client_report(report: str) -> bool:
    """Valide que le rapport client contient les infos nécessaires"""
    return "Profil MaxIt" in report and "Statut Churn" in report

def is_client_maxit(rapport: str) -> bool:
    """Détecte si le client est déjà utilisateur de MaxIt"""
    return "Profil MaxIt : Oui" in rapport or "Profil MaxIt : True" in rapport


def generate_marketing_messages_client(
    rapport_client: str,
    messages_options: List[str],
    model: str = "qwen2.5:3b",
    max_retries: int = 3
) -> Dict[str, List[str]]:
    """
    Génère des messages marketing MaxIt pour Orange Tunisie
    """

    if not validate_client_report(rapport_client):
        raise ValueError("Le rapport client est incomplet (Profil MaxIt ou Statut Churn manquant).")

    est_maxit = is_client_maxit(rapport_client)

    # 🧠 SYSTEM PROMPT — identité métier
    system_prompt = (
        "Tu es expert marketing chez Orange Tunisie. "
        "Tu conçois des messages professionnels, courts, engageants, à envoyer via SMS, notification ou push. "
        "Ta mission est d’augmenter l’adoption et l’usage de l’app MaxIt d’Orange Tunisie. "
        "Ne cite jamais le nom du client. Garde un ton clair, marketing, 100% Orange Tunisie. "
    )

    # 🧾 Instructions selon profil MaxIt
    if est_maxit:
        consigne_acquisition = (
            "- Ce client utilise déjà MaxIt. Ne propose **aucun message d'acquisition**.\n"
            "- Mets l'accent sur : fidélisation, jeux, services digitaux, bonus, marketplace et expérience personnalisée MaxIt."
        )
    else:
        consigne_acquisition = (
            "- Ce client n’est pas encore MaxIt. Propose 1 à 2 messages pour l’inciter à télécharger l’application.\n"
            "- Mentionne l’avantage d’installation (200 Mo offerts) et le lien : https://www.orange.tn/maxit"
        )

    # 👤 USER PROMPT
    prompt_user = f"""
🧠 Contexte :
Tu dois générer des messages marketing pour un client Orange Tunisie en te basant sur son profil.

📄 Rapport client :
{rapport_client}

🎯 Messages recommandés (à réutiliser dans la section 'options_recommandees') :
{json.dumps(messages_options, indent=2, ensure_ascii=False)}

📌 Consignes spécifiques :
{consigne_acquisition}
- Si le client utilise Flouci, USSD ou Mobimoney, montre que MaxIt est mieux : rapide, simple, tout-en-un, bonus...
- Si le client ne joue pas, propose la roue du jeudi, les pins, les défis MaxIt ou les gains fidélité.
- Mets en avant les avantages : recharge facile, suivi conso, promo sur options, services premium (Shahid VIP, Deezer...).
- Valorise les services partenaires comme WinWin (bons plans locaux, coupons...).
- Utilise un ton engageant, professionnel, tunisien, type push.
- Rends les messages impactants, courts et adaptés à un usage mobile.

📤 Format STRICT de sortie JSON :
{{
  "acquisition": ["..."],
  "jeux_et_fidelisation": ["..."],
  "options_recommandees": ["..."],
  "services_marketplace": ["..."],
  "messages_personnalises": ["..."],
  "messages_generaux": ["..."]
}}
    """.strip()

    for attempt in range(max_retries):
        try:
            logger.info(f"Appel au modèle {model}, tentative {attempt+1}/{max_retries}...")

            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_user}
                ]
            )

            content = response['message']['content'].strip()

            # Extraction du JSON potentiel
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            # Validation stricte via Pydantic
            parsed_json = json.loads(content)
            validated = MarketingMessageResponse(**parsed_json)

            # Nettoyage final si nécessaire
            if est_maxit:
                validated.acquisition = []

            result = validated.model_dump()
            result["options_recommandees"] = messages_options

            logger.info("✅ Messages marketing générés avec succès.")
            return result

        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Erreur JSON ou structure invalide : {e}")
        except Exception as e:
            logger.error(f"Erreur d’appel au modèle : {str(e)}")

        # Attente exponentielle avant nouvelle tentative
        time.sleep(min(2 ** attempt, 10))

    # Si toutes les tentatives échouent
    logger.warning("Échec après plusieurs tentatives, retour fallback.")
    return {
        "acquisition": [],
        "jeux_et_fidelisation": [],
        "options_recommandees": messages_options,
        "services_marketplace": [],
        "messages_personnalises": [],
        "messages_generaux": ["⚠️ Découvrez les avantages de l’application MaxIt sur https://www.orange.tn/maxit."]
    }
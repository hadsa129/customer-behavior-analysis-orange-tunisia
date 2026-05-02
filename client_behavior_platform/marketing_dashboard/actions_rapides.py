from typing import Tuple
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

def generate_consommations(achat_df: pd.DataFrame) -> pd.DataFrame:
    """Génère un DataFrame des consommations par mois par client"""
    if achat_df.empty:
        return pd.DataFrame(columns=['msisdn', 'mois_annee', 'data_usage', 'voice_usage', 'sms_usage'])
    
    df = achat_df.copy()
    df['event_date'] = pd.to_datetime(df['event_date'], errors='coerce')
    df['mois_annee'] = df['event_date'].dt.to_period('M').astype(str)

    volumes = df.apply(extract_volumes, axis=1, result_type='expand')
    volumes.columns = ['data_usage', 'voice_usage', 'sms_usage']
    df = pd.concat([df, volumes], axis=1)

    consommations = df.groupby(['msisdn', 'mois_annee'], as_index=False).agg({
        'data_usage': 'sum',
        'voice_usage': 'sum',
        'sms_usage': 'sum'
    })

    return consommations

import os
import pandas as pd
import re
from datetime import timedelta

def extract_duree(row):
    description = str(row['description']).lower()
    consommation = float(row.get('prix', 0)) // 90 * 20

    if "double validité" in description:
        return 60
    if "triple validité" in description:
        return 90

    if description != 'internet bil milli':
        m = re.search(r'(\d+)\s*(?:j|jr|jrs)\b', description)
        if m:
            return int(m.group(1))
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*go', description)
        if m:
            v = float(m.group(1).replace(',', '.'))
            if 1 <= v <= 42: return 30
            if v == 60: return 60
            if v == 100: return 90
            if v == 200: return 129
            if v == 500: return 365
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*mo', description)
        if m:
            v = float(m.group(1).replace(',', '.'))
            if v <= 100: return 1
            if 200 <= v <= 300: return 4
            if v > 300: return 7
    else:
        if consommation <= 100: return 1
        if 120 <= consommation <= 200: return 2
        if 220 <= consommation <= 300: return 4
        if 330 <= consommation <= 950: return 7
        if 950 <= consommation <= 55000: return 30
        return 60
    return 0

def calculer_churn_par_client(achat_df, recharge_df, roue_df, folder_path):
    # Conversion dates
    achat_df['event_date'] = pd.to_datetime(achat_df['event_date'], errors='coerce')
    recharge_df['event_date'] = pd.to_datetime(recharge_df['event_date'], errors='coerce')
    roue_df['entry_date_hist'] = pd.to_datetime(roue_df['entry_date_hist'], errors='coerce')

    # Appliquer extract_duree
    achat_df["duree_jours"] = achat_df.apply(extract_duree, axis=1)
    achat_df["valid_until"] = achat_df.apply(lambda x: x["event_date"] + timedelta(days=x["duree_jours"]), axis=1)
    achat_df["month"] = achat_df["event_date"].dt.to_period("M").dt.to_timestamp()

    # Dernier achat par mois
    last_achat = achat_df.sort_values("event_date").groupby(["msisdn", "month"]).tail(1)
    last_achat = last_achat[["msisdn", "month", "event_date", "valid_until", "duree_jours", "offer_name", "description"]]

    # Toutes les dates
    all_dates = pd.concat([
        achat_df['event_date'],
        recharge_df['event_date'],
        roue_df['entry_date_hist']
    ])
    start_date = all_dates.min().to_period("M").to_timestamp()
    end_date = all_dates.max().to_period("M").to_timestamp()
    all_months = pd.date_range(start=start_date, end=end_date, freq='MS')
    clients = pd.concat([achat_df['msisdn'], recharge_df['msisdn'], roue_df['msisdn']]).unique()

    # Base mois x clients
    df_base = pd.MultiIndex.from_product([clients, all_months], names=["msisdn", "month"]).to_frame(index=False)

    def extract_month(df, date_col):
        df = df.copy()
        df['month'] = pd.to_datetime(df[date_col]).dt.to_period("M").dt.to_timestamp()
        return df[["msisdn", "month"]].drop_duplicates()

    achat_months = extract_month(achat_df, "event_date")
    recharge_months = extract_month(recharge_df, "event_date")
    spin_months = extract_month(roue_df, "entry_date_hist")

    df_activity = pd.concat([achat_months, recharge_months, spin_months]).drop_duplicates()
    df_activity["activity"] = 1
    df_base = df_base.merge(df_activity, on=["msisdn", "month"], how="left")
    df_base["activity"] = df_base["activity"].fillna(0)

    # Joindre last valid_until
    df_base = df_base.merge(last_achat[["msisdn", "month", "valid_until"]], on=["msisdn", "month"], how="left")
    df_base["valid_until"] = df_base.groupby("msisdn")["valid_until"].ffill()
    df_base["month_end"] = df_base["month"] + pd.offsets.MonthEnd(0)
    df_base["covered"] = (df_base["valid_until"] >= df_base["month_end"]).astype(int)
    df_base["churn"] = ((df_base["activity"] == 0) & (df_base["covered"] == 0)).astype(int)

    # Nettoyage / conversion prix
    achat_df['prix'] = abs(achat_df['prix'])
    recharge_df['month'] = recharge_df['event_date'].dt.to_period("M").dt.to_timestamp()
    roue_df['month'] = roue_df['entry_date_hist'].dt.to_period("M").dt.to_timestamp()

    # Agrégations
    achat_agg = achat_df.groupby(["msisdn", "month"]).agg(
        achat_total=("prix", "sum"),
        achat_count=("prix", "count"),
        achat_type_count=("description", pd.Series.nunique)
    ).reset_index().astype({"achat_total": int, "achat_count": int, "achat_type_count": int})

    recharge_agg = recharge_df.groupby(["msisdn", "month"]).agg(
        recharge_total=("amount", "sum"),
        recharge_count=("amount", "count")
    ).reset_index().astype({"recharge_total": int, "recharge_count": int})

    spin_agg = roue_df.groupby(["msisdn", "month"]).agg(
        spin_count=("spin_number", "count")
    ).reset_index().astype({"spin_count": int})

    # Jointure
    df_base = df_base.merge(achat_agg, on=["msisdn", "month"], how="left")
    df_base = df_base.merge(recharge_agg, on=["msisdn", "month"], how="left")
    df_base = df_base.merge(spin_agg, on=["msisdn", "month"], how="left")
    df_base[["achat_total", "achat_count", "achat_type_count", 
             "recharge_total", "recharge_count", "spin_count"]] = df_base[[
        "achat_total", "achat_count", "achat_type_count", 
        "recharge_total", "recharge_count", "spin_count"
    ]].fillna(0).astype(int)

    # Sauvegarde
    output_path = os.path.join(folder_path, "churn_par_client_par_mois.csv")
    df_base.to_csv(output_path, index=False)
    print(f"✅ Fichier enregistré : {output_path}")
    return df_base
def creer_json(folder_path):
    clients = pd.read_csv(os.path.join(folder_path, "client_info.csv"))
    segmentations = pd.read_csv(os.path.join(folder_path, "segmentation.csv"))
    achats = pd.read_csv(os.path.join(folder_path, "achats.csv"))
    recharges = pd.read_csv(os.path.join(folder_path, "recharges.csv"))
    spins = pd.read_csv(os.path.join(folder_path, "spins.csv"))
    churn=calculer_churn_par_client(achats, recharges, spins, folder_path)
    consommations=generate_consommations(achats)
    msisdn_list = clients["msisdn"].unique().tolist()
    result = []
    all_options = pd.DataFrame()
    clients_df = pd.DataFrame()
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


    return result, all_options, clients_df
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
                                              for i in range(0, len(criteres), 2)]
            
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
            count = int(parse_number(parts[0].strip().split(' ')[0]))
            percentage = parse_number(parts[1].split('%')[0].strip()) if len(parts) > 1 else 0.0
            rapport['options_utilisees'].append({
                'nom': option_nom,
                'count': count,
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
        montant_total_achats += float(ci.get("montant_total_achat", 0))
        
        # Recharges
        total_recharges += len(recharges)
        montant_total_recharges += float(ci.get("montant_total_recharge", 0))
        
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
        if ci.get("est_maxit", False) or client.get("profil_maxit", False):
            profils_maxit += 1
        
        # Engagement & rentabilité
        engagements[seg.get("segment_engagement", "Inconnu")] += 1
        rentabilites[seg.get("segment_rentabilité", "Inconnu")] += 1
        types_clients[ci.get("type_client", "Inconnu")] += 1
    
    # Ajout des données calculées au rapport
    rapport.update({
        'total_achats_calc': total_achats,
        'montant_total_achats_calc': montant_total_achats,
        'total_recharges_calc': total_recharges,
        'montant_total_recharges_calc': montant_total_recharges,
        'panier_moyen_calc': montant_total_achats / total_achats if total_achats else 0,
        'recharge_moyenne_calc': montant_total_recharges / total_recharges if total_recharges else 0,
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
        'nb_achats_moyen': np.mean(total_achats),
        'nb_recharges_moyen': np.mean(total_recharges)
    
    })
    
    return rapport
def generer_rapport_marketing_segment_complet(clients_json):
   
    
    nb_clients = len(clients_json)
    rapport = f"📄 **Rapport Marketing**\n\n"
    rapport += f"📅 **Période d'analyse** : {datetime.now().strftime('%d/%m/%Y')}\n"
    rapport += f"👥 **Nombre de clients dans le segment** : {nb_clients}\n"
    
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
    
  
    # Construction du rapport markdown
    rapport += f"# 📊 RAPPORT D'ANALYSE DE SEGMENT\n\n"
    rapport += f"## 🏷️ IDENTIFIANT DU SEGMENT\n"
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
    if options_counter:
        rapport += "## ⭐ OPTIONS LES PLUS UTILISÉES\n"
        total_options = sum(options_counter.values())
        
        # Group options by type if possible
        options_par_type = {}
        for opt, count in options_counter.items():
            # Clean up option names
            option_name = str(opt).replace("Mo", "").strip()
            if option_name == "0":
                option_name = "Internet bel milli"
            
            # Categorize options
            if "internet" in option_name.lower() or "data" in option_name.lower() or option_name == "bel milli":
                categorie = "Données"
            elif "appel" in option_name.lower() or "min" in option_name.lower() or "sms" in option_name.lower():
                categorie = "Communication"
            else:
                categorie = "Autres"
            
            if categorie not in options_par_type:
                options_par_type[categorie] = []
            options_par_type[categorie].append((option_name, count))
        
        # Display options by category
        for categorie, options in options_par_type.items():
            rapport += f"### {categorie.upper()}\n"
            for opt, count in sorted(options, key=lambda x: x[1], reverse=True)[:5]:
                pourcentage = (count / total_options) * 100
                rapport += f"- **{opt}** : {count} utilisations ({pourcentage:.1f}%)\n"
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



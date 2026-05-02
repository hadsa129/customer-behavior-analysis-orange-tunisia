import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
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


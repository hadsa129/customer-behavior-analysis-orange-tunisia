import pandas as pd
from datetime import timedelta
import re

def extract_duree(row):
    """
    Extrait la durée en jours à partir de la description et des données de consommation.
    """
    description = str(row['description']).lower() if pd.notna(row.get('description')) else ''
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

def analyze_churn(achat_df, recharge_df, spin_df):
    """
    Analyse le taux de churn à partir des données d'achat, recharge et spins.
    
    Args:
        achat_df: DataFrame des achats
        recharge_df: DataFrame des recharges
        spin_df: DataFrame des spins (jeux)
        
    Returns:
        dict: Résultats de l'analyse de churn
    """
    # Convertir les dates
    achat_df['event_date'] = pd.to_datetime(achat_df['event_date'], errors='coerce')
    recharge_df['event_date'] = pd.to_datetime(recharge_df['event_date'], errors='coerce')
    spin_df['entry_date_hist'] = pd.to_datetime(spin_df['entry_date_hist'], errors='coerce')
    
    # Calculer les durées de validité
    achat_df["duree_jours"] = achat_df.apply(extract_duree, axis=1)
    achat_df["valid_until"] = achat_df.apply(
        lambda x: x["event_date"] + timedelta(days=x["duree_jours"]), 
        axis=1
    )
    
    # Calculer les mois d'activité
    achat_df["month"] = achat_df["event_date"].dt.to_period("M").dt.to_timestamp()
    last_achat = achat_df.sort_values("event_date").groupby(["msisdn", "month"]).tail(1)
    last_achat = last_achat[["msisdn", "month", "event_date", "valid_until", "duree_jours", "offer_name", "description"]]
    
    # Calculer la période d'analyse
    all_dates = pd.concat([
        achat_df['event_date'].dropna(),
        recharge_df['event_date'].dropna(),
        spin_df['entry_date_hist'].dropna()
    ])
    
    start_date = all_dates.min().to_period("M").to_timestamp()
    end_date = all_dates.max().to_period("M").to_timestamp()
    all_months = pd.date_range(start=start_date, end=end_date, freq='MS')
    
    # Liste unique des clients
    clients = pd.concat([
        achat_df['msisdn'].dropna(),
        recharge_df['msisdn'].dropna(),
        spin_df['msisdn'].dropna()
    ]).unique()
    
    # Créer la base de données pour l'analyse de churn
    df_base = pd.MultiIndex.from_product(
        [clients, all_months], 
        names=["msisdn", "month"]
    ).to_frame(index=False)
    
    # Marquer les mois d'activité
    def extract_month(df, date_col):
        df = df.copy()
        df['month'] = pd.to_datetime(df[date_col]).dt.to_period("M").dt.to_timestamp()
        return df[["msisdn", "month"]].drop_duplicates()
    
    achat_months = extract_month(achat_df, "event_date")
    recharge_months = extract_month(recharge_df, "event_date")
    spin_months = extract_month(spin_df, "entry_date_hist")
    
    df_activity = pd.concat([achat_months, recharge_months, spin_months]).drop_duplicates()
    df_activity["activity"] = 1
    
    # Fusionner avec la base
    df_base = df_base.merge(df_activity, on=["msisdn", "month"], how="left")
    df_base["activity"] = df_base["activity"].fillna(0)
    
    # Joindre les validités
    df_base = df_base.merge(
        last_achat[["msisdn", "month", "valid_until"]], 
        on=["msisdn", "month"], 
        how="left"
    )
    df_base["valid_until"] = df_base.groupby("msisdn")["valid_until"].ffill()
    
    # Calculer le churn
    df_base["month_end"] = df_base["month"] + pd.offsets.MonthEnd(0)
    df_base["covered"] = (df_base["valid_until"] >= df_base["month_end"]).astype(int)
    df_base["churn"] = ((df_base["activity"] == 0) & (df_base["covered"] == 0)).astype(int)
    
    # Agrégations pour les KPIs
    total_clients = len(clients)
    churn_rate = df_base["churn"].mean() * 100
    
    # Convertir les colonnes datetime en chaînes de caractères dans df_base
    for col in df_base.select_dtypes(include=['datetime64', 'datetimetz', 'timedelta']).columns:
        df_base[col] = df_base[col].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Convertir les index de date dans le résumé
    churn_summary = df_base.groupby('month')['churn'].mean().mul(100).round(2)
    if hasattr(churn_summary.index, 'strftime'):
        churn_summary.index = churn_summary.index.strftime('%Y-%m')
    
    # Préparer les résultats
    results = {
        'total_clients': int(total_clients),
        'churn_rate': round(float(churn_rate), 2),
        'start_date': start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else start_date,
        'end_date': end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else end_date,
        'analysis_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
        'churn_data': df_base.to_dict('records')[:30],  # Limiter pour la performance
        'churn_summary': churn_summary.to_dict(),
    }
    
    return results

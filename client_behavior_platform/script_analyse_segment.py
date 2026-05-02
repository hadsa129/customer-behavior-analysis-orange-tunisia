from help_functions import *
catalogue=pd.read_csv('catalogue.csv')
folder_path = "data_client"
segment_criteria = {
    "rentabilite": "non rentable",
    "engagement": "",
    "type_client": "",
    "type_interet": "",
    "interet_international": "",
    "interet_jeu": "",
    "interet_promo": "",
    "action": ""
}

from datetime import datetime

date_debut = datetime.strptime('2025-02-01', '%Y-%m-%d')
date_fin = datetime.strptime('2025-02-28', '%Y-%m-%d')
result, all_options, clients_df,segment_id=filtrer_clients_par_segments(
    segment_criteria,
    date_debut,
    date_fin,
    folder_path
)
profil_segment = construire_profil_segment(all_options)
options_list,consommation_client = dataframe_recommandations_vers_json(all_options, catalogue)
messages_options = generer_messages_options(options_list, consommation_client, all_options)

rapport_segment,taux_maxit = generer_rapport_marketing_segment(segment_id,result)
messages_segment = generate_segment_marketing_messages(
    rapport_segment,
    messages_options,
    taux_maxit
)






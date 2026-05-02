import pandas as pd
import numpy as np
import os
from help_functions import *
from datetime import datetime
import ollama
import pandas as pd
from typing import Tuple, List, Dict, Any
from datetime import datetime, timedelta
import re
import numpy as np
import json
import logging
import ollama
from pydantic import BaseModel, ValidationError
from sklearn.metrics.pairwise import cosine_similarity
catalogue=pd.read_csv('catalogue.csv')
folder_path = "data_client"
msisdn='000612967e78ea9c7cd3f9234577f0041de3e443'

date_debut = datetime.strptime('2025-02-01', '%Y-%m-%d')
date_fin = datetime.strptime('2025-02-28', '%Y-%m-%d')
client_json,all_options, clients_df=filtrer_clients(
    msisdn,
    date_debut,
    date_fin,
    folder_path
)
all_options.to_csv('all_options.csv', index=False)
rapport_client = generer_rapport_marketing_client(client_json)
options_list,consommation_client= dataframe_recommandations_vers_json_client(all_options, catalogue)
messages_options = generer_messages_options_client(options_list,consommation_client,  all_options)

# Génération du JSON marketing final
resultats_final = generate_marketing_messages_client(rapport_client, messages_options)
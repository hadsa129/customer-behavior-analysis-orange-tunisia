from pyhive import hive
import pandas as pd

def get_hive_connection():
    return hive.Connection(
        host='hive-server',   # Le nom du conteneur Hive
        port=10000,
        username='hiveuser',
        auth='NOSASL',
        database='default'
    )

def query_hive(query):
    conn = get_hive_connection()
    return pd.read_sql(query, conn)

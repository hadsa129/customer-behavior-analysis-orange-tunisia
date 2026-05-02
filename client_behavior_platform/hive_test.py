from pyhive import hive
import pandas as pd

def test_hive_connection():
    try:
        conn = hive.Connection(
            host="hive-server",   # nom du conteneur docker de Hive
            port=10000,
            username="hiveuser",
            auth="NOSASL",
            database="default"
        )
        df = pd.read_sql("SHOW TABLES", conn)
        print("✅ Connexion réussie à Hive !")
        print(df)
    except Exception as e:
        print("❌ Erreur de connexion Hive :", e)

if __name__ == "__main__":
    test_hive_connection()

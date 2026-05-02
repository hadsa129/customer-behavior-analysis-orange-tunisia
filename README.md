# Analyse du Comportement Client & Recommandation Personnalisée – Orange Tunisie

## 🎯 Objectif

Cette plateforme d'analyse avancée permet de comprendre le comportement des clients d'Orange Tunisie et de fournir des recommandations personnalisées. Elle combine des techniques de big data, de machine learning et d'IA pour offrir des insights actionnables aux équipes marketing.

## ✨ Fonctionnalités Principales

### 📊 Tableau de Bord Marketing
- Visualisation en temps réel des KPI clés
- Segmentation avancée des clients
- Suivi des campagnes marketing

### 🤖 Intelligence Artificielle
- Détection du churn client
- Système de recommandation personnalisé
- Analyse prédictive des comportements

### 📈 Analyse Avancée
- Traitement de données massives avec Apache Spark
- Rapports personnalisables
- Export des analyses en différents formats

## 🏗️ Architecture
- **Frontend** : HTML5, CSS3, JavaScript, Chart.js
- **Backend** : Django 5.2, Django REST Framework
- **Base de données** : PostgreSQL
- **Traitement des données** : Apache Spark, Pandas
- **Machine Learning** : Scikit-learn, XGBoost
- **IA** : LangChain, OpenAI, Ollama

## 📋 Prérequis

### Matériel
- Au moins 8 Go de RAM (16 Go recommandé)
- 20 Go d'espace disque disponible
- Processeur 64 bits (4 cœurs minimum)

### Logiciels
- Python 3.10+
- Java 11 (nécessaire pour Apache Spark)
- PostgreSQL 13+
- Apache Spark 3.3.1
- pip (gestionnaire de paquets Python)

## 🚀 Installation

### 1. Cloner le dépôt
```bash
git clone https://github.com/votre-utilisateur/spark_delta_hive_metastore.git
cd spark_delta_hive_metastore
```

### 2. Configuration de l'environnement

#### 2.1. Créer un environnement virtuel
```bash
# Sur Linux/Mac
python -m venv venv
source venv/bin/activate

# Sur Windows
python -m venv venv
.\venv\Scripts\activate
```

#### 2.2. Installer les dépendances
```bash
# Installer les dépendances de base
pip install -r requirements/requirements.txt

# Installer les dépendances de l'application Django
cd client_behavior_platform
pip install -r requirements.txt
```

### 3. Configuration de la base de données

#### 3.1. Installation de PostgreSQL
- Installer PostgreSQL 13+ depuis [le site officiel](https://www.postgresql.org/download/)
- Créer une nouvelle base de données

#### 3.2. Configuration des variables d'environnement
Créer un fichier `.env` à la racine du projet avec le contenu suivant :
```
# Configuration de la base de données
DB_NAME=votre_base_de_donnees
DB_USER=votre_utilisateur
DB_PASSWORD=votre_mot_de_passe
DB_HOST=localhost
DB_PORT=5432

# Clé secrète Django (à générer pour la production)
SECRET_KEY=votre_clé_secrète_très_longue_et_sécurisée

# Configuration pour Spark (optionnel)
SPARK_HOME=/chemin/vers/votre/installation/spark
PYSPARK_PYTHON=python3
```

### 4. Initialisation de la base de données
```bash
# Se placer dans le dossier du projet Django
cd client_behavior_platform

# Appliquer les migrations
python manage.py migrate

# Créer un superutilisateur (suivez les instructions)
python manage.py createsuperuser
```

## 🏃‍♂️ Lancer l'application

### 1. Mode développement
```bash
# Se placer dans le dossier du projet Django
cd client_behavior_platform

# Démarrer le serveur de développement
python manage.py runserver
```

L'application sera disponible à l'adresse : http://127.0.0.1:8000/

### 2. Mode production avec Gunicorn
```bash
# Installation de Gunicorn (si ce n'est pas déjà fait)
pip install gunicorn

# Lancer Gunicorn (depuis le dossier client_behavior_platform)
gunicorn client_behavior_platform.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### 3. Configuration du serveur web (Nginx + Gunicorn) - Optionnel pour la production

#### Installation de Nginx
```bash
# Sur Ubuntu/Debian
sudo apt update
sudo apt install nginx

# Sur CentOS/RHEL
sudo yum install nginx
```

#### Configuration de Nginx
Créer un fichier de configuration pour votre site dans `/etc/nginx/sites-available/` (ou `/etc/nginx/conf.d/` selon votre distribution) :

```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /chemin/vers/votre/projet/client_behavior_platform/static/;
    }
    
    location /media/ {
        alias /chemin/vers/votre/projet/client_behavior_platform/media/;
    }
}
```

#### Activer la configuration et redémarrer Nginx
```bash
# Sur Ubuntu/Debian
sudo ln -s /etc/nginx/sites-available/votre-site /etc/nginx/sites-enabled/
sudo nginx -t  # Tester la configuration
sudo systemctl restart nginx

# Sur CentOS/RHEL
sudo systemctl enable nginx
sudo systemctl start nginx
```

## 📦 Dépendances principales

### Backend
- Django 5.2.4 - Framework web Python
- Django REST Framework 3.16.0 - API REST pour Django
- Psycopg2 2.9.10 - Adaptateur PostgreSQL pour Python
- Pandas 2.3.1 - Manipulation de données
- Scikit-learn 1.7.1 - Machine Learning

### IA & Machine Learning
- LangChain 0.3.27 - Framework pour applications LLM
- OpenAI 1.97.1 - API OpenAI
- Ollama 0.5.1 - Intégration avec modèles LLM locaux
- XGBoost - Algorithmes de boosting

### Utilitaires
- NumPy 2.3.1 - Calcul numérique
- SciPy 1.16.0 - Outils scientifiques
- Matplotlib 3.10.3 - Visualisation de données
- Requests 2.32.4 - Requêtes HTTP
- python-dotenv 0.19.0 - Gestion des variables d'environnement
- Gunicorn 23.0.0 - Serveur WSGI HTTP pour production

## 🐳 Option Docker (Facultatif)

### Prérequis
- Docker 20.10+
- Docker Compose 2.0+

### Lancer avec Docker Compose
```bash
# Construire et démarrer les conteneurs
docker-compose up --build -d

# Arrêter les conteneurs
docker-compose down

# Voir les logs
docker-compose logs -f
```

### Commandes utiles
```bash
# Accéder au shell du conteneur principal
docker-compose exec web bash

# Exécuter des commandes de gestion Django
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# Redémarrer un service spécifique
docker-compose restart web
```

### Configuration Docker
Le fichier `docker-compose.yml` configure les services suivants :
- **web** : Application Django
- **db** : Base de données PostgreSQL
- **redis** : Cache et file d'attente (si configuré)
- **spark** : Cluster Spark (optionnel)

## 🌐 Accès
- Application web : http://localhost:8000
- Interface de marketing : http://localhost:8000/marketing-panel
- API REST : http://localhost:8000/api/

## 🎯 Introduction
Ce projet vise à concevoir une plateforme intelligente permettant d’analyser les comportements des clients Orange Tunisie, de prédire le churn, et de recommander automatiquement des offres personnalisées, en particulier via l’application Max It. Il s’inscrit dans la stratégie de transformation digitale de l’opérateur, avec un accent sur la personnalisation marketing et l’optimisation de l’engagement client.

---

## 📌 Objectifs du projet
### Objectifs métiers
- Analyser les comportements multi-canaux (Max It, USSD…)
- Segmenter dynamiquement les clients
- Prédire le churn
- Recommander des offres personnalisées
- Générer des messages marketing adaptés
- Aider les équipes marketing via des dashboards interactifs

### Objectifs techniques
- Architecture Big Data distribuée
- Modèles IA pour segmentation, churn, recommandation
- Intégration de LLM pour la génération de contenu marketing
- Dashboards décisionnels dynamiques

---

## 📂 Données d’entrée
- **Fichiers clients** : `clients_*.csv` (profils, usages, historique Max It…)
- **Fichiers options** : `options_*.csv` (options souscrites, historiques d’achats…)
- **Dossiers** : `data/`, `client_data/`, `segmentation_result/` (données brutes, résultats de segmentation…)
- **Sources** : exports CRM, logs applicatifs, historiques d’achats

---

## 🏗️ Architecture générale & pipeline
```
+------------------+        +------------------+        +----------------+        +------------------------+
|  Données Clients |  -->   | Analyse & Modèles|  -->   |   Recommandation|  -->  |  Dashboards & Messages |
+------------------+        +------------------+        +----------------+        
```

### Étapes principales
- **Préparation, segmentation et churn** : tout le pipeline principal de préparation des données, segmentation (KMeans) et prédiction du churn (Random Forest/XGBoost) est centralisé dans le notebook `prep_hive.ipynb`. Les scripts `script_analyse_client.py` et `script_analyse_segment.py` permettent d’exécuter séparément l’analyse comportementale, la segmentation et la prédiction du churn.
- **Essais de personnalisation marketing** : le notebook `langchain.ipynb` sert uniquement à tester des flux de génération de contenu marketing personnalisé (non utilisé dans le pipeline principal).
- **Déploiement & intégration** : tout le code de déploiement, l’intégration des modèles (analyse, churn, segmentation) et les dashboards sont regroupés dans le dossier `client_behavior_platform/`, notamment via l’application Django `marketing_dashboard` et la dockerisation (`docker-compose.yml`).
- **Visualisation** : dashboards interactifs accessibles via l’app Django (`marketing_dashboard/`) ou exports Power BI.

---

## 🧠 Modèles et intelligence artificielle
- **Segmentation** : KMeans (MLlib)
- **Churn** : XGBoost
- **Recommandation** : Similarité cosinus
- **LLM/Contenu marketing** : Qwen via LangChain, Ollama

---

## 🛠️ Plateforme technique
- **Django** : backend web, gestion des utilisateurs, dashboards (`client_behavior_platform/`, `marketing_dashboard/`)
- **Ollama** : serveur de LLM pour la génération de texte (`start_ollama.sh`)
- **Docker** : déploiement et orchestration (`Dockerfile`, `docker-compose.yml`)
- **Spark/Hive/Hadoop** : traitement Big Data (Dockerfiles spécifiques, dossiers `spark/`, `hadoop/`, `hive/`)
- **LangChain** : intégration LLM (notebooks/scripts dédiés)

---

## 🚀 Déploiement et utilisation
### Prérequis
- Docker / Docker Compose
- Python 3.10+
- Accès aux fichiers de données

### Lancement rapide
```bash
# Construire et démarrer les services
sudo docker-compose up --build

# Lancer Ollama (LLM)
bash start_ollama.sh

# Lancer le serveur Django
python manage.py runserver
```

### Interfaces accessibles après déploiement
Après le lancement des services, plusieurs interfaces sont disponibles :

- **Interface web marketing (`marketing_dashboard`)**  
  Accessible via navigateur à [http://localhost:8000](http://localhost:8000)  
  → Tableaux de bord, visualisation des segments, scores de churn, génération de messages marketing, rapports interactifs, KPIs, etc.

- **Interface d’administration Django**  
  Accessible via [http://localhost:8000/admin](http://localhost:8000/admin)  
  → Gestion des utilisateurs, des modèles, des droits d’accès et administration avancée de la plateforme.

- **API REST** (si exposée dans le projet)  
  → Pour l’intégration ou l’automatisation (à préciser selon les endpoints disponibles).

- **Accès aux notebooks analytiques**  
  → Pour les data scientists souhaitant exécuter ou adapter les notebooks comme `prep_hive.ipynb` (à préciser selon l’environnement Jupyter ou autre).

### 🖥️ Interface web – `marketing_dashboard`
L’application Django `marketing_dashboard` fournit une interface web complète, dédiée aux équipes marketing et administrateurs. Elle propose :

- **Analyse client** : fiche détaillée d’un client (historique, comportements, scores, recommandations personnalisées).
- **Analyse segment** : exploration de segments de clients, filtres avancés, rapports, recommandations groupées, génération de messages marketing pour un segment.
- **Analyse segmentation** : visualisation interactive des clusters/segments, statistiques globales, évolution des groupes.
- **Analyse churn** : accès aux scores de churn, listes de clients à risque, actions de rétention ciblées.
- **Tables** : accès aux tables de données (clients, options, historiques), recherche et export.
- **Historiques marketing** : suivi des campagnes envoyées, taux de clics, conversions, logs des messages.
- **Authentification** : gestion sécurisée de l’accès à la plateforme (login, gestion des rôles et droits d’accès).

L’accès à l’interface se fait via un navigateur, après le lancement du serveur Django (par défaut sur http://localhost:8000). L’interface est responsive et pensée pour une prise en main rapide par les équipes métier.

---

## 📊 Visualisation & dashboards
- Dashboards interactifs dans l’app Django (`marketing_dashboard/`)
- Exports pour Power BI dans `segmentation_result/` ou `churn_results/`
- Accès via interface web pour les équipes métier

---

## 🗂️ Fichiers principaux du projet
| Fichier/Dossier             | Rôle                                                      |
|-----------------------------|-----------------------------------------------------------|
| `Dockerfile`                | Image Docker principale                                   |
| `docker-compose.yml`        | Orchestration des services                                |
| `start_ollama.sh`           | Lancement du serveur LLM                                  |
| `marketing_analyst_bot.py`  | Génération de messages marketing via LLM                  |
| `script_analyse_client.py`  | Analyse comportementale et prédiction de churn            |
| `script_analyse_segment.py` | Segmentation clients                                      |
| `marketing_dashboard/`      | App Django, dashboards                                    |
| `requirements.txt`          | Dépendances Python                                        |
| `help_functions.py`         | Fonctions utilitaires                                     |
| `langchain.ipynb`           | Intégration LLM / génération de contenu                   |
| `data/`, `client_data/`     | Données d’entrée                                         |

---

## ✅ Résultats attendus & impact
- Hausse de l’adoption Max It
- Personnalisation marketing à grande échelle
- Réduction du churn
- Communication ciblée plus efficace
- Meilleure allocation des campagnes

---

## 👥 Contact / Contributeurs
Projet réalisé par Hadil Sahraoui dans le cadre du PFE chez Orange Tunisie.


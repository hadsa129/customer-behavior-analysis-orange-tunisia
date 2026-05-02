#!/bin/sh

# Démarrer le serveur Ollama en arrière-plan
ollama serve &

# Attendre que le serveur démarre
sleep 5

# Télécharger le modèle si nécessaire
OLLAMA_MMLOCK=1 OLLAMA_KEEP_ALIVE=5m ollama pull qwen2.5:3b

# Maintenir le conteneur en vie
tail -f /dev/null

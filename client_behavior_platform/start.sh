#!/bin/bash

# Attendre que ollama soit prêt
echo "⏳ Waiting for Ollama..."
until curl -s http://ollama:11434 > /dev/null; do
  sleep 2
done
echo "✅ Ollama is up!"

# Démarrage Django
python manage.py migrate
python manage.py runserver 0.0.0.0:8000 


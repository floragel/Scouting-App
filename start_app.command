#!/bin/bash

# Se déplacer dans le bon dossier pour que le script marche depuis n'importe où
cd "$(dirname "$0")"

echo "Démarrage de FRC Scouting App..."

# Activer l'environnement virtuel s'il existe
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "L'environnement virtuel 'venv' est introuvable."
fi

# Ouvrir le navigateur après 2 secondes (le temps que le serveur se lance)
(sleep 2 && open http://localhost:5002) &

# Lancer le serveur backend
python3 backend/app.py

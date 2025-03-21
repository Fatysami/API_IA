# Utiliser une image Python légère
FROM python:3.10-slim

# Définir le dossier de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le projet
COPY . .

# Exposer le port pour Railway
EXPOSE 8000

# Lancer l'application avec Uvicorn et une valeur par défaut pour $PORT
CMD ["sh", "-c", "uvicorn cv-analyser-pdf:app --host 0.0.0.0 --port ${PORT:-8000}"]

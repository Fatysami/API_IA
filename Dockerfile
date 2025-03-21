# Utiliser une image Python légère
FROM python:3.10-slim

# Installer les dépendances système nécessaires pour Tesseract OCR et pdf2image
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Définir le dossier de travail
WORKDIR /app

# Copier les fichiers de dépendances et installer les packages
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le code du projet
COPY . .

# Exposer le port pour l'API (Railway gère automatiquement la redirection)
EXPOSE 8000

# Ajouter un utilisateur non-root pour la sécurité
RUN useradd -m appuser
USER appuser

# Lancer l'application avec Uvicorn (et récupérer le bon port via $PORT)
CMD ["sh", "-c", "uvicorn cv-analyser-pdf:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

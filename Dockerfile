# Utiliser une image Python légère
FROM python:3.10-slim

# Installer les dépendances nécessaires pour Tesseract OCR et pdf2image
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Définir le dossier de travail
WORKDIR /app

# Copier les fichiers du projet
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exposer le port de l'API
EXPOSE 8000

# Lancer l'application avec Uvicorn
CMD ["uvicorn", "cv-analyser-pdf:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

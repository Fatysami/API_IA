import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import openai
import jwt
import datetime
import os
import json
import sys
from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# ✅ Charger les variables d'environnement
load_dotenv()

# ✅ Récupérer les variables
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# ✅ Charger les utilisateurs depuis .env
USERS = json.loads(os.getenv("USERS", "{}"))

# ✅ Définition de l'API FastAPI
app = FastAPI()

# ✅ Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Vérification du token JWT
def verify_api_key(api_key: str = Header(None)):
    if not api_key:
        raise HTTPException(status_code=403, detail="API-Key manquant")
    try:
        payload = jwt.decode(api_key, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token expiré")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Token invalide")

# ✅ Génération d'un token JWT sécurisé
@app.post("/generate-token/")
def generate_token(username: str = Form(...), password: str = Form(...)):
    if username not in USERS or USERS[username] != password:
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    token = jwt.encode({"sub": username, "exp": expiration}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}

# ✅ Extraction de texte depuis un PDF (OCR si nécessaire)
def extract_text_from_pdf(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        
        if not text.strip():
            text = ""
            images = convert_from_path(file.name)
            for img in images:
                text += pytesseract.image_to_string(img, lang="eng+fra")
                
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'extraction du texte: {str(e)}")

# ✅ Endpoint pour analyser un CV (PDF) avec OpenAI GPT-4
@app.post("/analyze-cv/")
async def analyze_cv(
    openai_api_key: str = Form(...),
    prompt: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(verify_api_key)
):
    try:
        text = extract_text_from_pdf(file.file)
        client = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}]
        )
        return {"filename": file.filename, "analysis": response.choices[0].message.content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

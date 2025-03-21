import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import openai
import jwt
import datetime
import os
import sys
from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from dotenv import load_dotenv

# ✅ Charger les variables d'environnement
load_dotenv()

# ✅ Forcer UTF-8 dans la console pour éviter les erreurs d'affichage
sys.stdout.reconfigure(encoding='utf-8')

# 🔐 Sécurité JWT
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"

# ✅ Configuration du hashage sécurisé des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """ Vérifie un mot de passe hashé """
    return pwd_context.verify(plain_password, hashed_password)

# ✅ Charger les utilisateurs depuis les variables d’environnement
users = {
    "AI_Analyzer": os.getenv("USER_AI_Analyzer"),
    "Admin": os.getenv("USER_Admin")
}

# ✅ Définition de l'API FastAPI
app = FastAPI()

# ✅ Configuration des CORS dynamiques
origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ✅ Vérification du token JWT
def verify_api_key(api_key: str = Header(None)):
    """ Vérifie que le token JWT est valide """
    if not api_key:
        raise HTTPException(status_code=403, detail="API-Key manquant dans les Headers")
    try:
        payload = jwt.decode(api_key, SECRET_KEY, algorithms=[ALGORITHM])
        if payload["sub"] not in users:
            raise HTTPException(status_code=403, detail="Utilisateur non autorisé")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Token expiré")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Token invalide")

# ✅ Génération d'un token JWT sécurisé
@app.post("/generate-token/")
def generate_token(username: str = Form(...), password: str = Form(...)):
    """ Génère un token JWT après vérification des identifiants """
    if username not in users or not verify_password(password, users[username]):
        raise HTTPException(status_code=403, detail="Identifiants incorrects")

    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    token = jwt.encode({"sub": username, "exp": expiration}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}

# ✅ Extraction de texte depuis un PDF (avec OCR via Docker)
def extract_text_from_pdf(file):
    print("📂 Lecture du fichier PDF...")
    try:
        with pdfplumber.open(file) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        
        if not text.strip():
            print("⚠️ Aucun texte brut trouvé, utilisation de l'OCR...")
            text = ""
            images = convert_from_path(file.name)
            for i, img in enumerate(images):
                print(f"🖼️ OCR sur la page {i + 1}...")
                text += pytesseract.image_to_string(img, lang="eng+fra")
                
        text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")
        print(f"✅ Texte extrait (UTF-8) : {text[:500]}...")
        return text.strip()
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'extraction du texte du PDF: {str(e)}")

# ✅ Endpoint pour analyser un CV (PDF) avec OpenAI GPT-4
@app.post("/analyze-cv/")
async def analyze_cv(
    openai_api_key: str = Form(...),
    prompt: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(verify_api_key)
):
    print(f"📂 Fichier reçu : {file.filename}")  
    try:
        file_content = file.file.read()
        print(f"📂 Taille du fichier : {len(file_content)} octets") 
        file.file.seek(0)  

        if not file_content:
            raise HTTPException(status_code=400, detail="Le fichier PDF est vide.")

        text = extract_text_from_pdf(file.file)

        client = openai.OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}]
        )

        return {"filename": file.filename, "analysis": response.choices[0].message.content}

    except Exception as e:
        print(f"❌ Erreur interne : {e}")  
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

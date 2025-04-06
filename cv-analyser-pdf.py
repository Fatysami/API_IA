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

# Extra AI libs
import google.generativeai as genai
import httpx

# ✅ Charger les variables d'environnement
load_dotenv()

# ✅ Config globale
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
USERS = json.loads(os.getenv("USERS", "{}"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "✅ API IA is running."}

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

@app.post("/generate-token/")
def generate_token(username: str = Form(...), password: str = Form(...)):
    if username not in USERS or USERS[username] != password:
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    token = jwt.encode({"sub": username, "exp": expiration}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}

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
        raise HTTPException(status_code=500, detail=f"Erreur d'extraction de texte : {e}")

@app.post("/analyze-cv/")
async def analyze_cv(
    ai_provider: str = Form("openai"),
    prompt: str = Form(...),
    file: UploadFile = File(...),
    openai_api_key: str = Form(None),
    gemini_api_key: str = Form(None),
    mistral_url: str = Form("http://localhost:11434/api/chat"),
    claude_api_key: str = Form(None),
    user: dict = Depends(verify_api_key)
):
    try:
        text = extract_text_from_pdf(file.file)

        # ✅ OPENAI
        if ai_provider == "openai":
            if not openai_api_key:
                raise HTTPException(status_code=422, detail="Clé API OpenAI manquante")
            client = openai.OpenAI(api_key=openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ]
            )
            return {"engine": "openai", "filename": file.filename, "analysis": response.choices[0].message.content}

        # ✅ GEMINI
        elif ai_provider == "gemini":
            if not gemini_api_key:
                raise HTTPException(status_code=422, detail="Clé API Gemini manquante")
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
            result = model.generate_content([prompt, text])
            return {"engine": "gemini", "filename": file.filename, "analysis": result.text}

        # ✅ CLAUDE (Anthropic)
        elif ai_provider == "claude":
            if not claude_api_key:
                raise HTTPException(status_code=422, detail="Clé API Claude manquante")
            headers = {
                "x-api-key": claude_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            body = {
                "model": "claude-3-opus-20240229",
                "max_tokens": 1000,
                "messages": [
                    {"role": "user", "content": f"{prompt}\n\n{text}"}
                ]
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
                output = resp.json()
            return {"engine": "claude", "filename": file.filename, "analysis": output['content'][0]['text']}

        # ✅ MISTRAL (via Ollama local ou autre)
        elif ai_provider == "mistral":
            payload = {
                "model": "mistral",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                "stream": False
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(mistral_url, json=payload)
                output = resp.json()
            return {"engine": "mistral", "filename": file.filename, "analysis": output['message']['content']}

        else:
            raise HTTPException(status_code=400, detail="Fournisseur IA non pris en charge.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur IA: {str(e)}")

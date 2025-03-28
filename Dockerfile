FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Utilise sh -c pour que ${PORT} soit interprété dynamiquement par Railway
CMD ["sh", "-c", "uvicorn cv-analyser-pdf:app --host 0.0.0.0 --port ${PORT:-8000}"]

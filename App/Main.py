import os
import re
import json
import datetime
import tempfile
import httpx
from fastapi import FastAPI, HTTPException, Request, Header, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from App.extractor import extract_fields, extract_with_model, load_model
from App.db import SessionLocal, init_db, save_feedback, save_paciente
from App.models import TrainingExample, Paciente
from dotenv import load_dotenv
from PIL import Image
import pytesseract
import requests
import base64
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
import random
import time
import uuid

# Cargar variables de entorno
load_dotenv()
API_KEY = os.getenv("API_KEY", "changeme")
MODEL_DIR = os.getenv("MODEL_DIR", "models/current")

MISTRAL_API_KEY = "Z69kMGdoqph9iQ2fN26ilZPho3X47QLn"
MISTRAL_URL = "https://api.mistral.ai/v1/ocr"

origins = [
    "http://localhost:5173",  # tu frontend
    "http://127.0.0.1:5173",  # opcional
    # "*" si quieres permitir cualquier origen (no recomendado en producción)
]

# URL de tu flujo en n8n (Webhook Node)
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://dalioss.com:5678/webhook-test/ace7ea80-c2c9-4b5d-b40a-d3df0062092f")

# Inicializar FastAPI
app = FastAPI(
    title="OCR -> Estructuración API",
    description="API para extracción y almacenamiento de historias clínicas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar modelo entrenado (si existe)
nlp = load_model(MODEL_DIR)


# ---------------------------
# MODELOS DE REQUEST
# ---------------------------
class PDFRequest(BaseModel):
    ruta_pdf: str

class TextIn(BaseModel):
    text: str


class FeedbackIn(BaseModel):
    text: str
    labels: dict   # {"nombre":"...", "edad":"...", ...}

class PacienteIn(BaseModel):
    id: str
    cedula: str = None
    nombre: str
    edad: int = None
    diagnostico: str = None
    fechaConsulta: datetime.datetime = None
    direccion: str = None
    telefono: str = None
    observaciones: str = None
    fechaAnalisis: datetime.datetime = None
    eps: str = None

# ---------------------------
# EVENTOS
# ---------------------------
@app.on_event("startup")
def startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------
# ENDPOINTS
# ---------------------------

def generar_id_unico():
    return f"HC-{uuid.uuid4()}"

@app.post("/procesar")
def procesar(payload: TextIn):
    text = payload.text

    # Intentar con modelo spaCy
    if nlp:
        parsed = extract_with_model(nlp, text)
    else:
        parsed = {}

    # Fallback por regex/reglas simples
    fallback = extract_fields(text)

    # Merge de resultados
    result = {**fallback, **{k: v for k, v in (parsed or {}).items() if v}}
    result["id"] = generar_id_unico()

    return result

@app.post("/feedback")
def feedback(payload: FeedbackIn, x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    save_feedback(payload.text, payload.labels)
    return {"status": "ok"}


@app.post("/retrain")
def retrain(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from train import train_from_db_and_save
    model_path = train_from_db_and_save()

    global nlp
    nlp = load_model(model_path)

    return {"status": "trained", "model_path": model_path}

import base64
from fastapi import HTTPException

@app.post("/ocr_pdf")
def ocr_pdf(payload: PDFRequest):
    ruta_pdf = payload.ruta_pdf

    if not os.path.isfile(ruta_pdf):
        raise HTTPException(status_code=400, detail=f"El archivo no existe: {ruta_pdf}")

    try:
        # Leer PDF y convertir a Base64
        with open(ruta_pdf, "rb") as f:
            pdf_bytes = f.read()
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # Crear JSON con el formato que Mistral espera
        payload_json = {
            "model": "mistral-ocr-latest",
            "document": {
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{pdf_b64}"
            },
            "include_image_base64": True
        }

        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }

        # Enviar a Mistral
        response = requests.post(MISTRAL_URL, json=payload_json, headers=headers)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return response.json()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error al comunicarse con Mistral: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

@app.get("/historiales")
def obtener_historiales(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    try:
        registros = db.query(Paciente).offset(skip).limit(limit).all()
        result = [
            {
                "id": r.id,
                "nombre": r.nombre,
                "edad": r.edad,
                "diagnostico": r.diagnostico,
                "fechaConsulta": r.fechaConsulta.strftime("%Y-%m-%d") if r.fechaConsulta else None,
                "direccion": r.direccion,
                "telefono": r.telefono,
                "observaciones": r.observaciones,
                "fechaAnalisis": r.fechaAnalisis.strftime("%Y-%m-%d %H:%M:%S") if r.fechaAnalisis else None
            }
            for r in registros
        ]
        return {"count": len(result), "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar la base de datos: {e}")

@app.post("/pacientes")
def crear_paciente(payload: PacienteIn, db: Session = Depends(get_db)):
    try:
        # Validar si enviaron ID
        if not payload.id:
            # Si no envían, generar uno
            payload.id = generar_id_unico()
        else:
            # Si envían ID, asegurarse que no exista
            existe = db.execute(
                text("SELECT 1 FROM pacientes WHERE id = :id"),
                {"id": payload.id}
            ).fetchone()
            if existe:
                # Generar uno nuevo hasta que no exista
                payload.id = generar_id_unico()

        # Guardar en la base de datos
        save_paciente(
            id=payload.id,
            nombre=payload.nombre,
            edad=payload.edad,
            diagnostico=payload.diagnostico,
            fechaConsulta=payload.fechaConsulta,
            direccion=payload.direccion,
            telefono=payload.telefono,
            observaciones=payload.observaciones,
            fechaAnalisis=payload.fechaAnalisis,
            cedula=payload.cedula,
            eps=payload.eps,
        )
        return {"status": "ok", "id_generado": payload.id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar paciente: {e}")
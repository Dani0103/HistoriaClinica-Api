import os
import datetime
from fastapi import FastAPI, HTTPException, Request, Header, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from App.extractor import extract_fields, extract_with_model, load_model
from App.db import SessionLocal, init_db, save_feedback, save_paciente, save_metric
from App.models import PacienteIn, Metric
from dotenv import load_dotenv
from PIL import Image
import requests
import base64
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid
from App.utils_metrics import compute_metrics
from App.schemas import PacienteCreate

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
    longitud = len(text)
    result = {}

    # Generar id único para esta historia
    historia_id = generar_id_unico()

    # ============================
    # 🔹 1️⃣ - Proceso con spaCy
    # ============================
    inicio_spacy = time.perf_counter()
    parsed_spacy = extract_with_model(nlp, text) if nlp else {}
    fin_spacy = time.perf_counter()
    duracion_spacy = fin_spacy - inicio_spacy

    # ============================
    # 🔹 2️⃣ - Proceso con regex
    # ============================
    inicio_regex = time.perf_counter()
    parsed_regex = extract_fields(text)
    fin_regex = time.perf_counter()
    duracion_regex = fin_regex - inicio_regex

    # ============================
    # 🔹 3️⃣ - Fusión final (prioriza spaCy si tiene valor)
    # ============================
    result = {**parsed_regex, **{k: v for k, v in parsed_spacy.items() if v}}
    result["id"] = historia_id

    # ============================
    # 🔹 4️⃣ - Métricas separadas
    # ============================
    try:
        acc_spacy, rec_spacy, f1_spacy = compute_metrics(parsed_spacy)
        acc_regex, rec_regex, f1_regex = compute_metrics(parsed_regex)

        # 🔹 Determinar el modelo con mejor desempeño (usamos F1)
        if f1_spacy > f1_regex:
            mejor_modelo = "spacy"
            mejor_accuracy, mejor_recall, mejor_f1, mejor_tiempo = acc_spacy, rec_spacy, f1_spacy, duracion_spacy
        elif f1_regex > f1_spacy:
            mejor_modelo = "regex"
            mejor_accuracy, mejor_recall, mejor_f1, mejor_tiempo = acc_regex, rec_regex, f1_regex, duracion_regex
        else:
            mejor_modelo = "empate"
            # Si empatan, guardamos el promedio
            mejor_accuracy = (acc_spacy + acc_regex) / 2
            mejor_recall = (rec_spacy + rec_regex) / 2
            mejor_f1 = (f1_spacy + f1_regex) / 2
            mejor_tiempo = (duracion_spacy + duracion_regex) / 2

        # Guardar solo el más acertado
        save_metric(mejor_modelo, mejor_tiempo, mejor_accuracy, mejor_recall, mejor_f1, longitud, historia_id)

    except Exception as e:
        print(f"⚠️ Error guardando métricas: {e}")

    # =============================
    # 🔹 Retornar la misma respuesta
    # =============================
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
def obtener_historiales(skip: int = 0, limit: int = 2000, db: Session = Depends(get_db)):
    try:
        registros = db.query(PacienteIn).offset(skip).limit(limit).all()
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
def crear_paciente(payload: PacienteCreate, db: Session = Depends(get_db)):
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
    
@app.get("/metrics")
def obtener_metrics(db: Session = Depends(get_db)):
    metrics = db.query(Metric).order_by(Metric.fecha.desc()).limit(2000).all()
    return [
        {
            "id": m.id,
            "historia_id": m.historia_id,
            "mejor_modelo": m.mejor_modelo,
            "tiempo": round(m.tiempo, 4),
            "accuracy": round(m.accuracy, 4),
            "recall": round(m.recall, 4),
            "f1": round(m.f1, 4),
            "longitud_texto": m.longitud_texto,
            "fecha": m.fecha.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for m in metrics
    ]
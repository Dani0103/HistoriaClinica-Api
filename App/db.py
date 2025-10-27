# app/db.py
import os
import json
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from App.models import Base, TrainingExample, Paciente
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./historia_clinica.db")
print("Usando DB en:", DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def save_feedback(text, labels: dict):
    db = SessionLocal()
    ex = TrainingExample(text=text, labels=json.dumps(labels))
    db.add(ex)
    db.commit()
    db.close()

def save_paciente(
    id: str,
    nombre: str,
    edad: int = None,
    diagnostico: str = None,
    fechaConsulta: datetime.datetime = None,
    direccion: str = None,
    telefono: str = None,
    observaciones: str = None,
    fechaAnalisis: datetime.datetime = None
):
    db = SessionLocal()
    paciente = Paciente(
        id=id,
        nombre=nombre,
        edad=edad,
        diagnostico=diagnostico,
        fechaConsulta=fechaConsulta,
        direccion=direccion,
        telefono=telefono,
        observaciones=observaciones,
        fechaAnalisis=fechaAnalisis
    )
    db.add(paciente)
    db.commit()
    db.close()

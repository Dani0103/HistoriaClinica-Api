# app/models.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime
import datetime

Base = declarative_base()

class TrainingExample(Base):
    __tablename__ = "training_examples"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    labels = Column(Text, nullable=False)  # JSON string: {"nombre": "...", ...}
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Paciente(Base):
    __tablename__ = "pacientes"
    id = Column(String(50), primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    edad = Column(Integer)
    diagnostico = Column(String(255))
    fechaConsulta = Column(DateTime)
    direccion = Column(String(255))
    telefono = Column(String(50))
    observaciones = Column(Text)
    fechaAnalisis = Column(DateTime)
    eps = Column(String(255))

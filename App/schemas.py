# App/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class PacienteCreate(BaseModel):
    id: Optional[str] = None
    cedula: Optional[str] = None
    nombre: str
    edad: Optional[int] = None
    diagnostico: Optional[str] = None
    fechaConsulta: Optional[datetime] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    observaciones: Optional[str] = None
    fechaAnalisis: Optional[datetime] = None
    eps: Optional[str] = None

# app/models.py
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, Text
from datetime import datetime, timezone

Base = declarative_base()


# =======================
# 📘 Training Example
# =======================
class TrainingExample(Base):
    __tablename__ = "training_examples"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    labels: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string: {"nombre": "...", ...}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# =======================
# 🧑‍⚕️ Paciente
# =======================
class PacienteIn(Base):
    __tablename__ = "pacientes"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    cedula: Mapped[str | None] = mapped_column(String(20), nullable=True)
    eps: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    edad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    diagnostico: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fechaConsulta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    fechaAnalisis: Mapped[datetime | None] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


# =======================
# 📊 Métricas
# =======================
class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    historia_id = mapped_column(String(100)) 
    mejor_modelo = mapped_column(String(20))
    tiempo: Mapped[float] = mapped_column(Float)
    accuracy: Mapped[float] = mapped_column(Float)
    recall: Mapped[float] = mapped_column(Float)
    f1: Mapped[float] = mapped_column(Float)
    longitud_texto: Mapped[int] = mapped_column(Integer)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

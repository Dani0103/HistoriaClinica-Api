# app/extractor.py
import os
import re

def load_model(model_dir):
    try:
        import spacy
        if os.path.isdir(model_dir):
            return spacy.load(model_dir)
        # fallback a modelo spaCy en español si está instalado
        try:
            return spacy.load("es_core_news_sm")
        except Exception:
            return None
    except Exception:
        return None

# heurísticas/reglas regexp básicas (útiles para probar rápido con OCR ruidoso)
def extract_fields(text: str):
    out = {
        "nombre": None,
        "edad": None,
        "diagnostico": None,
        "fechaConsulta": None,
        "direccion": None,
        "telefono": None,
        "observaciones": None,
        "cedula": None,
        "eps": None
    }

    def find(regex, flags=re.IGNORECASE | re.MULTILINE):
        m = re.search(regex, text, flags)
        return m.group(1).strip() if m else None

    # nombre del paciente (acepta "NOMBRE" o "NOMBRES")
    out["nombre"] = find(r"NOMBRES?[:\-\s]*([A-ZÁÉÍÓÚÑa-záéíóúñü\s]+)")

    # edad
    out["edad"] = find(r"EDAD[:\-\s]*(\d{1,3})")

    # diagnostico (acepta "DIAGNOSTICO", "DIAGNÓSTICO" y variantes)
    out["diagnostico"] = find(r"DIAGN[ÓO]STICO[:\-\s]*([\w\s\,\-\.\:]+)")

    # fallback → si no hay diagnóstico, tomar motivo de consulta
    if not out["diagnostico"]:
        motivo = re.search(r"MOTIVO DE CONSULTA[:\-\s]*(.+?)(?:\n##|\Z)", text, re.IGNORECASE | re.DOTALL)
        if motivo:
            out["diagnostico"] = motivo.group(1).strip()

    # fecha de consulta (acepta varias variantes: "FECHA:", "FECHA DE CONSULTA:", etc.)
    out["fechaConsulta"] = find(r"FECHA(?: DE CONSULTA)?[:\-\s]*([\d]{4}[-/]\d{2}[-/]\d{2})")

    # direccion
    out["direccion"] = find(r"DIRECCI[ÓO]N[:\-\s]*([^\n]+)")

    # telefono
    out["telefono"] = find(r"TEL[EÉ]FONO[:\-\s]*([\+\d\-\s\(\)]{7,20})")

    # cedula
    out["cedula"] = find(r"IDENTIFICACI[ÓO]N[:\-\s]*([0-9]{6,15})(?=\sEDAD)")

    # eps
    out["eps"] = find(r"EPS[:\-\s]*([A-ZÁÉÍÓÚÑa-záéíóúñü\s]+)")

    # observaciones → si hay campo dedicado
    obs = re.search(r"OBSERVACIONES[:\-\s]*(.+)", text, re.IGNORECASE | re.DOTALL)
    if obs:
        out["observaciones"] = obs.group(1).strip()
    else:
        # fallback → últimas 300 chars del texto
        out["observaciones"] = text.strip()[-300:]

    return out


# usar spaCy NER si existe un modelo entrenado
def extract_with_model(nlp, text: str):
    if not nlp:
        return {}
    doc = nlp(text)
    result = {}
    # Suponemos que durante training usamos etiquetas como: NOMBRE, DIAGNOSTICO, DIRECCION, FECHA, TELEFONO, EDAD
    for ent in doc.ents:
        label = ent.label_.upper()
        if label == "NOMBRE":
            result["nombre"] = ent.text
        elif label == "EDAD":
            result["edad"] = ent.text
        elif label == "DIAGNOSTICO":
            result["diagnostico"] = ent.text
        elif label in ("FECHA", "FECHACONSULTA"):
            result["fechaConsulta"] = ent.text
        elif label == "DIRECCION":
            result["direccion"] = ent.text
        elif label == "TELEFONO":
            result["telefono"] = ent.text
        elif label == "OBSERVACIONES":
            result["observaciones"] = ent.text
    return result

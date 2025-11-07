# app/extractor.py
import os
import re

def load_model(model_dir):
    try:
        import spacy
        if os.path.isdir(model_dir):
            print(f"✅ Cargando modelo spaCy desde: {model_dir}")
            return spacy.load(model_dir)

        print("⚠️ No existe modelo entrenado en el directorio, intentando usar 'es_core_news_sm'...")
        try:
            nlp = spacy.load("es_core_news_sm")
            print("✅ Modelo base 'es_core_news_sm' cargado correctamente.")
            return nlp
        except Exception as e:
            print(f"❌ No se pudo cargar el modelo base spaCy: {e}")
            return None

    except Exception as e:
        print(f"❌ Error cargando modelo spaCy: {e}")
        return None


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

    out["nombre"] = find(r"NOMBRES?[:\-\s]*([A-ZÁÉÍÓÚÑa-záéíóúñü\s]+)")
    out["edad"] = find(r"EDAD[:\-\s]*(\d{1,3})")
    out["diagnostico"] = find(r"DIAGN[ÓO]STICO[:\-\s]*([\w\s\,\-\.\:]+)")

    if not out["diagnostico"]:
        motivo = re.search(r"MOTIVO DE CONSULTA[:\-\s]*(.+?)(?:\n##|\Z)", text, re.IGNORECASE | re.DOTALL)
        if motivo:
            out["diagnostico"] = motivo.group(1).strip()

    out["fechaConsulta"] = find(r"FECHA(?: DE CONSULTA)?[:\-\s]*([\d]{4}[-/]\d{2}[-/]\d{2})")
    out["direccion"] = find(r"DIRECCI[ÓO]N[:\-\s]*([^\n]+)")
    out["telefono"] = find(r"TEL[EÉ]FONO[:\-\s]*([\+\d\-\s\(\)]{7,20})")
    out["cedula"] = find(r"IDENTIFICACI[ÓO]N[:\-\s]*([0-9]{6,15})")
    out["eps"] = find(r"EPS[:\-\s]*([A-ZÁÉÍÓÚÑa-záéíóúñü\s]+)")

    obs = re.search(r"OBSERVACIONES[:\-\s]*(.+)", text, re.IGNORECASE | re.DOTALL)
    out["observaciones"] = obs.group(1).strip() if obs else text.strip()[-300:]
    return out


def extract_with_model(nlp, text: str):
    if not nlp:
        return {}
    doc = nlp(text)
    result = {
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
        elif label in ("CEDULA", "IDENTIFICACION"):
            result["cedula"] = ent.text
        elif label == "EPS":
            result["eps"] = ent.text
    return result

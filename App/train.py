# app/train.py
import random
import os
import json
from db import SessionLocal
from models import TrainingExample

def load_examples_from_db():
    db = SessionLocal()
    rows = db.query(TrainingExample).all()
    db.close()
    data = []
    for r in rows:
        labels = json.loads(r.labels)
        entities = []
        # convertir labels a entidades (start,end,label)
        for field, value in labels.items():
            if not value:
                continue
            start = r.text.find(value)
            if start >= 0:
                end = start + len(value)
                # mapear campos a etiquetas de NER
                label = field.upper()  # e.g., "nombre" -> "NOMBRE"
                entities.append((start, end, label))
        if entities:
            data.append((r.text, {"entities": entities}))
    return data

def train_from_db_and_save(output_dir_base="models"):
    import spacy
    from spacy.util import minibatch, compounding

    TRAIN_DATA = load_examples_from_db()
    if not TRAIN_DATA:
        raise Exception("No hay ejemplos para entrenar")

    nlp = spacy.blank("es")  # nuevo pipeline
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner")
    else:
        ner = nlp.get_pipe("ner")

    # añadir labels
    for _, annotations in TRAIN_DATA:
        for ent in annotations.get("entities"):
            ner.add_label(ent[2])

    # iniciar entrenamiento
    optimizer = nlp.begin_training()
    n_iter = 30
    for itn in range(n_iter):
        random.shuffle(TRAIN_DATA)
        losses = {}
        batches = minibatch(TRAIN_DATA, size=compounding(2.0, 16.0, 1.001))
        for batch in batches:
            texts = [t for t, ann in batch]
            annotations = [ann for t, ann in batch]
            nlp.update(texts, annotations, sgd=optimizer, drop=0.35, losses=losses)
        print(f"Iter {itn+1}/{n_iter} Losses: {losses}")

    timestamp = int(__import__("time").time())
    out_dir = os.path.join(output_dir_base, f"ner_{timestamp}")
    os.makedirs(out_dir, exist_ok=True)
    nlp.to_disk(out_dir)

    # actualizar "current" (simbólico)
    current_dir = os.path.join(output_dir_base, "current")
    if os.path.exists(current_dir):
        # opcional: backup previo
        backup = os.path.join(output_dir_base, f"backup_{timestamp}")
        if os.path.exists(current_dir):
            os.rename(current_dir, backup)
    os.rename(out_dir, current_dir)
    return current_dir

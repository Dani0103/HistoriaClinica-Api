def _safe_div(n, d):
    return (n / d) if d else 0.0

def compute_metrics(result: dict):
    """Calcula accuracy, recall y f1 basados en presencia de campos clave"""
    requeridos = {"nombre", "edad", "diagnostico", "direccion", "telefono"}
    predichos = {k for k, v in result.items() if v and str(v).strip()}

    tp = len(requeridos & predichos)
    fp = len(predichos - requeridos)
    fn = len(requeridos - predichos)

    accuracy = _safe_div(tp, (tp + fp))
    recall = _safe_div(tp, (tp + fn))
    f1 = _safe_div(2 * accuracy * recall, (accuracy + recall))
    return accuracy, recall, f1

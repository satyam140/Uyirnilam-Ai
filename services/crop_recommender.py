import csv
import os

try:
    from sklearn.ensemble import RandomForestClassifier
except ImportError:
    RandomForestClassifier = None


DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "crop_training.csv")
FEATURES = ["N", "P", "K", "ph", "temperature", "humidity", "rainfall"]


def recommend_crop(values):
    if RandomForestClassifier is None:
        return {"recommended_crop": "Tomato", "confidence": 55, "note": "Fallback recommendation because the optional ML package is unavailable; not a guaranteed best crop."}
    rows = []
    with open(DATA_PATH, newline="", encoding="utf-8") as training_file:
        rows = list(csv.DictReader(training_file))
    model = RandomForestClassifier(n_estimators=40, random_state=42)
    model.fit([[float(row[feature]) for feature in FEATURES] for row in rows], [row["crop"] for row in rows])
    sample = [[float(values[feature]) for feature in FEATURES]]
    prediction = model.predict(sample)[0]
    confidence = round(float(max(model.predict_proba(sample)[0])) * 100)
    return {"recommended_crop": prediction.title(), "confidence": confidence, "note": "Model recommendation based on the provided conditions, not a guaranteed best crop."}

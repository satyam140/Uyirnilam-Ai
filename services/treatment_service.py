import json
import os


DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "treatments.json")


def get_treatment(condition):
    with open(DATA_PATH, encoding="utf-8") as treatment_file:
        treatments = json.load(treatment_file)
    return treatments.get(condition.strip().lower(), treatments["default"])

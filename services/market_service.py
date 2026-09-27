import json
import os


DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "market_demo.json")


def get_market_data(crop="tomato"):
    with open(DATA_PATH, encoding="utf-8") as market_file:
        markets = json.load(market_file)
    record = markets.get(crop.strip().lower(), markets["tomato"])
    change = round(((record["current_price"] - record["previous_price"]) / record["previous_price"]) * 100, 1)
    return {**record, "change_percent": change, "direction": "up" if change >= 0 else "down"}

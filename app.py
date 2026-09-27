import json
import math
import os
import re
import ssl
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config import Config
from services.market_service import get_market_data
from services.assistant_service import answer_question, answer_with_gemini
from services.crop_recommender import recommend_crop
from services.disease_ai import analyze_image
from services.treatment_service import get_treatment
from services.weather_service import demo_weather, get_weather
from services.storage import create_farmer, get_farmer, get_farmer_by_phone, get_farm, init_db, list_diagnoses, save_diagnosis, update_farm, update_language


def https_context():
    for certificate_path in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.exists(certificate_path):
            return ssl.create_default_context(cafile=certificate_path)
    return ssl.create_default_context()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    init_db(app.config["DEMO_MODE"])

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            farmer = get_farmer_by_phone(request.form.get("phone", "").strip())
            password = request.form.get("password", "")
            if farmer and (farmer["password_hash"] == "demo" or check_password_hash(farmer["password_hash"], password)):
                session["farmer_id"] = farmer["id"]
                if farm_needs_setup(farmer["id"]):
                    return redirect(url_for("farm"))
                return redirect(url_for("dashboard"))
            error = "We could not match those details. Try the demo account or register."
        return render_template("login.html", error=error)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        error = None
        if request.method == "POST":
            try:
                farmer_id = create_farmer(request.form["name"].strip(), request.form["phone"].strip(), generate_password_hash(request.form["password"]), request.form["location"].strip(), request.form.get("preferred_language", "Hindi"))
                session["farmer_id"] = farmer_id
                return redirect(url_for("farm"))
            except Exception:
                error = "That email or phone is already registered."
        return render_template("register.html", error=error)

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.post("/api/auth/register")
    def auth_register_api():
        payload = request.get_json(silent=True) or {}
        required = ("name", "phone", "password", "preferred_language")
        if any(not payload.get(key) for key in required):
            return jsonify({"error": "Name, mobile number, password and language are required."}), 400
        try:
            farmer_id = create_farmer(payload["name"].strip(), payload["phone"].strip(), generate_password_hash(payload["password"]), payload.get("location", ""), payload["preferred_language"])
        except Exception:
            return jsonify({"error": "That mobile number is already registered."}), 409
        session["farmer_id"] = farmer_id
        return jsonify({"registered": True, "farmer_id": farmer_id}), 201

    @app.post("/api/auth/login")
    def auth_login_api():
        payload = request.get_json(silent=True) or {}
        farmer = get_farmer_by_phone(payload.get("phone", "").strip())
        if not farmer or not (farmer["password_hash"] == "demo" or check_password_hash(farmer["password_hash"], payload.get("password", ""))):
            return jsonify({"error": "Invalid login details."}), 401
        session["farmer_id"] = farmer["id"]
        return jsonify({"logged_in": True, "farmer_id": farmer["id"]})

    @app.post("/api/auth/logout")
    def auth_logout_api():
        session.clear()
        return jsonify({"logged_out": True})

    @app.get("/dashboard")
    def dashboard():
        farmer = get_farmer(current_farmer_id()) or {}
        return render_template("dashboard.html", dashboard=dashboard_for_user(live=not app.config["TESTING"]), inputs=input_catalog(), assistant_language=farmer.get("preferred_language", "Hindi"))

    @app.route("/farm", methods=["GET", "POST"])
    def farm():
        farmer_id = session.get("farmer_id")
        if not farmer_id:
            return redirect(url_for("login"))
        saved = False
        if request.method == "POST":
            update_farm(farmer_id, {key: request.form.get(key, "").strip() for key in ("farm_name", "location", "area", "crop", "soil_type", "state", "district", "irrigation_type")})
            update_language(farmer_id, request.form.get("preferred_language", "Hindi"))
            return redirect(url_for("dashboard"))
        return render_template("setup-farm.html", farmer=get_farmer(farmer_id), farm=get_farm(farmer_id), saved=saved)

    @app.get("/api/farm")
    def farm_data():
        return jsonify({"farmer": get_farmer(current_farmer_id()), "farm": current_farm()})

    @app.post("/api/farm")
    @app.put("/api/farm")
    def farm_data_update():
        farmer_id = current_farmer_id()
        payload = request.get_json(silent=True) or {}
        required = ("farm_name", "location", "area", "crop", "soil_type")
        if any(not payload.get(key) for key in required):
            return jsonify({"error": "Farm name, location, area, crop and soil type are required."}), 400
        update_farm(farmer_id, payload)
        if payload.get("preferred_language"):
            update_language(farmer_id, payload["preferred_language"])
        return jsonify({"saved": True, "farm": current_farm()})

    @app.get("/recommendation")
    def recommendation():
        farm = current_farm()
        result = recommend_from_farm({"soil_type": farm["soil_type"], "location": farm["location"], "land_area": farm["area"], "current_crop": farm["crop"]})
        return render_template("recommendation.html", farm=farm, recommendations=result["recommendations"])

    @app.get("/crop-doctor")
    def crop_doctor():
        return render_template("crop-doctor.html")

    @app.get("/weather")
    def weather():
        farm = current_farm()
        return render_template("weather.html", weather=get_weather(farm["location"], farm["crop"], live=not app.config["TESTING"]))

    @app.get("/api/weather")
    def weather_data():
        farm = current_farm()
        return jsonify(get_weather(request.args.get("location", farm["location"]), farm["crop"], live=not app.config["TESTING"]))

    @app.get("/market")
    def market():
        return render_template("market.html", market=get_market_data(request.args.get("crop", "tomato")))

    @app.get("/api/market")
    def market_data():
        return jsonify(get_market_data(request.args.get("crop", "tomato")))

    @app.get("/assistant")
    def assistant():
        farmer = get_farmer(current_farmer_id())
        return render_template("assistant-mvp.html", language=farmer.get("preferred_language", "Hindi") if farmer else "Hindi")

    @app.post("/api/assistant")
    def assistant_data():
        payload = request.get_json(silent=True) or {}
        message = payload.get("message", "").strip()
        if not message:
            return jsonify({"error": "Please ask a question about your farm."}), 400
        farm = current_farm()
        diagnoses = list_diagnoses(current_farmer_id())
        latest = diagnoses[0] if diagnoses else {}
        language = payload.get("language") or (get_farmer(current_farmer_id()) or {}).get("preferred_language", "Hindi")
        language = normalize_language(language)
        weather = get_weather(farm["location"], farm["crop"], live=not app.config["TESTING"])
        context = {"farm_name": farm["farm_name"], "location": farm["location"], "crop": farm["crop"], "condition": latest.get("condition", "no saved diagnosis"), "severity": latest.get("severity", "unknown"), "language": language, "weather_summary": f"{weather['temperature']} C, {weather['humidity']}% humidity, {weather['rain_probability']}% rain probability"}
        result = answer_with_gemini(message, context, app.config["GEMINI_API_KEY"], app.config["GEMINI_MODEL"]) or answer_question(message, context)
        result["language"] = language
        return jsonify(result)

    @app.get("/report")
    def report():
        return render_template("report.html")

    @app.post("/api/crop-recommendation")
    def crop_recommendation():
        values = request.get_json(silent=True) or {}
        if "soil_type" in values:
            return jsonify(recommend_from_farm(values))
        required = ("N", "P", "K", "ph", "temperature", "humidity", "rainfall")
        if any(key not in values for key in required):
            return jsonify({"error": "Please provide N, P, K, pH, temperature, humidity and rainfall."}), 400
        try:
            return jsonify(recommend_crop(values))
        except (TypeError, ValueError):
            return jsonify({"error": "Crop conditions must be numeric values."}), 400

    @app.get("/api/treatment")
    def treatment_data():
        condition = request.args.get("condition", "Early Blight")
        return jsonify({"condition": condition, "guidance": get_treatment(condition)})

    @app.post("/api/analyze-crop")
    def analyze_crop():
        image = request.files.get("image")
        if image is None or not image.filename:
            return jsonify({"error": "Please upload a crop image."}), 400

        extension = os.path.splitext(image.filename)[1].lower()
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            return jsonify({"error": "Please upload a JPG, PNG or WEBP image."}), 400

        image_bytes = image.read()
        if not is_supported_image(image_bytes, extension):
            return jsonify({"error": "The uploaded file does not look like a valid crop image."}), 400

        upload_dir = os.path.join(app.root_path, "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(image.filename)}"
        with open(os.path.join(upload_dir, filename), "wb") as saved_image:
            saved_image.write(image_bytes)

        crop = request.form.get("crop", "Tomato").strip() or "Tomato"
        try:
            diagnosis = analyze_image(image_bytes, crop, app.config["DEMO_MODE"], app.config["CLAUDE_API_KEY"], app.config["CLAUDE_MODEL"])
        except Exception:
            if not app.config["DEMO_MODE"]:
                return jsonify({"error": "Live crop analysis is unavailable. Turn on demo mode or check the Claude configuration."}), 503
            diagnosis = analyze_image(image_bytes, crop, True)
        treatment = get_treatment(diagnosis.get("condition", "unknown"))
        diagnosis.update({"organic_treatment": treatment["organic"], "chemical_treatment": treatment["chemical"], "prevention": treatment["prevention"], "image_filename": filename})
        return jsonify(diagnosis)

    @app.get("/api/diagnoses")
    def diagnoses():
        farmer_id = session.get("farmer_id") or get_farmer_by_phone("demo@uyirnilam.local")["id"]
        return jsonify(list_diagnoses(farmer_id))

    @app.post("/api/diagnoses/save")
    def save_diagnosis_api():
        diagnosis = request.get_json(silent=True) or {}
        required = ("crop", "condition", "confidence", "severity", "symptoms", "explanation")
        if any(key not in diagnosis for key in required):
            return jsonify({"error": "This diagnosis is missing required details."}), 400
        farmer_id = session.get("farmer_id") or get_farmer_by_phone("demo@uyirnilam.local")["id"]
        diagnosis_id = save_diagnosis(farmer_id, diagnosis)
        return jsonify({"saved": True, "diagnosis_id": diagnosis_id}), 201

    @app.get("/api/dashboard")
    def dashboard_data():
        return jsonify(demo_dashboard())

    @app.get("/api/inputs")
    def inputs_data():
        return jsonify(input_catalog())

    @app.get("/api/nearby-shops")
    def nearby_shops():
        try:
            latitude = float(request.args.get("lat", ""))
            longitude = float(request.args.get("lon", ""))
            radius = min(max(int(request.args.get("radius", "10000")), 1000), 50000)
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError
        except (TypeError, ValueError):
            location = request.args.get("location", "").strip()
            if not location:
                return jsonify({"error": "A valid location or latitude and longitude are required."}), 400
            coordinates = geocode_location(location)
            if coordinates is None:
                return jsonify({"error": f"We could not locate {location}. Try adding the city or district."}), 404
            latitude, longitude = coordinates
            radius = min(max(int(request.args.get("radius", "10000")), 1000), 50000)

        queries = (
            f"[out:json][timeout:10];nwr(around:{radius},{latitude},{longitude})[shop~\"^(agrarian|farm|garden_centre|fertilizer|fertiliser|seed|agricultural_supplies)$\",i];out center tags;",
            f"[out:json][timeout:10];nwr(around:{radius},{latitude},{longitude})[name~\"(agro|krishi|fertilizer|fertiliser|seed|कृषि|खाद)\",i];out center tags;",
        )
        payload = None
        for query in queries:
            for endpoint in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter"):
                try:
                    request_data = Request(endpoint, data=urlencode({"data": query}).encode("utf-8"), headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "UyirnilamAI/1.0"}, method="POST")
                    with urlopen(request_data, timeout=15, context=https_context()) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                    break
                except Exception:
                    continue
            if payload is not None and payload.get("elements"):
                break
            payload = None
        if payload is None:
            return jsonify({"error": "Live shop search is temporarily unavailable. Try again shortly."}), 503

        shops = []
        seen = set()
        for element in payload.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name") or tags.get("official_name")
            point = element.get("center", element)
            shop_latitude, shop_longitude = point.get("lat"), point.get("lon")
            if not name or shop_latitude is None or shop_longitude is None or name.casefold() in seen:
                continue
            shop_type = " ".join((tags.get(key, "") for key in ("shop", "name", "official_name", "description"))).casefold()
            if not any(keyword in shop_type for keyword in ("agro", "farm", "garden", "seed", "fertil", "krishi", "कृषि", "खाद")):
                continue
            seen.add(name.casefold())
            distance = distance_km(latitude, longitude, float(shop_latitude), float(shop_longitude))
            address = ", ".join(part for part in (tags.get("addr:street"), tags.get("addr:suburb"), tags.get("addr:city")) if part)
            shops.append({"name": name, "distance_km": round(distance, 1), "address": address or "Address listed at the shop", "map_url": f"https://www.openstreetmap.org/?mlat={shop_latitude}&mlon={shop_longitude}#map=18/{shop_latitude}/{shop_longitude}"})
        shops.sort(key=lambda shop: shop["distance_km"])
        return jsonify({"shops": shops[:12], "latitude": latitude, "longitude": longitude, "source": "OpenStreetMap contributors"})

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "uyirnilam-ai", "demo_mode": app.config["DEMO_MODE"]})

    return app


def is_supported_image(image_bytes, extension):
    if not image_bytes:
        return False
    if extension in {".jpg", ".jpeg"}:
        return image_bytes.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    return image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP"


def demo_diagnosis(image_filename, crop):
    treatment = get_treatment("Early Blight")
    return {
        "crop": crop.title(),
        "condition": "Early Blight",
        "condition_type": "disease",
        "confidence": 92,
        "severity": "Medium",
        "symptoms": ["Brown lesions detected", "Yellowing around affected areas", "Leaf tissue damage visible"],
        "explanation": "The visible pattern is consistent with early blight. Lesions are present, but widespread tissue damage is not evident.",
        "immediate_actions": ["Remove badly affected leaves and keep them away from the field.", "Water at the soil line and avoid wetting the leaves.", "Check nearby plants again within two days."],
        "organic_treatment": treatment["organic"],
        "chemical_treatment": treatment["chemical"],
        "prevention": treatment["prevention"],
        "image_filename": image_filename,
    }


def dashboard_for_user(live=True):
    farmer_id = session.get("farmer_id")
    if farmer_id:
        farm = get_farm(farmer_id)
        farmer = get_farmer(farmer_id)
        if farm and farmer:
            return demo_dashboard(farmer["name"], farm, live=live)
    demo_farmer = get_farmer_by_phone("demo@uyirnilam.local")
    demo_farm = get_farm(demo_farmer["id"]) if demo_farmer else None
    return demo_dashboard(demo_farmer["name"] if demo_farmer else "Farmer", demo_farm, live=live)


def current_farmer_id():
    if session.get("farmer_id"):
        return session["farmer_id"]
    demo_farmer = get_farmer_by_phone("demo@uyirnilam.local")
    return demo_farmer["id"] if demo_farmer else None


def current_farm():
    farmer_id = current_farmer_id()
    farm = get_farm(farmer_id) if farmer_id else None
    return farm or {"farm_name": "Green Valley Farm", "location": "Pune", "area": "2.5 acres", "crop": "Tomato", "soil_type": "Black Soil", "state": "Maharashtra", "district": "Pune"}


def farm_needs_setup(farmer_id):
    farm = get_farm(farmer_id)
    if not farm:
        return True
    return (
        farm["farm_name"].endswith("'s Farm")
        and farm["area"] == "1 acre"
        and farm["crop"] == "Tomato"
        and farm["soil_type"] == "Don't Know"
        and farm["irrigation_type"] == "Unknown"
    )


def normalize_language(language):
    names = {"hindi": "Hindi", "english": "English", "marathi": "Marathi", "tamil": "Tamil", "telugu": "Telugu"}
    return names.get(str(language).strip().lower(), "Hindi")


def distance_km(latitude_one, longitude_one, latitude_two, longitude_two):
    earth_radius_km = 6371
    latitude_delta = math.radians(latitude_two - latitude_one)
    longitude_delta = math.radians(longitude_two - longitude_one)
    haversine = math.sin(latitude_delta / 2) ** 2 + math.cos(math.radians(latitude_one)) * math.cos(math.radians(latitude_two)) * math.sin(longitude_delta / 2) ** 2
    return earth_radius_km * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


INDIA_LOCATION_ALIASES = {
    "uttarpradesh": "Uttar Pradesh",
    "uttar pradesh": "Uttar Pradesh",
    "gujrat": "Gujarat",
    "madhyapradesh": "Madhya Pradesh",
    "madhya pradesh": "Madhya Pradesh",
    "karnatka": "Karnataka",
    "kerla": "Kerala",
    "orissa": "Odisha",
    "pondicherry": "Puducherry",
}


def normalize_india_location(location):
    normalized = " ".join(str(location).split())
    for alias, state_name in INDIA_LOCATION_ALIASES.items():
        normalized = re.sub(rf"(?i)\b{re.escape(alias)}\b", state_name, normalized)
    return normalized if re.search(r"(?i)\bindia\b", normalized) else f"{normalized}, India"


def geocode_location(location):
    location = normalize_india_location(location)
    request_url = "https://nominatim.openstreetmap.org/search?" + urlencode({"q": location, "format": "jsonv2", "limit": 1})
    try:
        request_data = Request(request_url, headers={"User-Agent": "UyirnilamAI/1.0 (nearby agricultural shops)"})
        with urlopen(request_data, timeout=12, context=https_context()) as response:
            results = json.loads(response.read().decode("utf-8"))
        if not results:
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return None


def input_catalog():
    return [
        {"type": "Fertilizer", "name": "Neem-coated Urea", "pack": "45 kg bag", "price": "₹266", "support": "Government-supported fertilizer", "tag": "Nitrogen", "details": "Neem-coated urea supplies nitrogen for leafy growth and is sold at the notified maximum retail price.", "use": "Apply only according to soil and crop need. Do not mix with seed or store in damp conditions.", "source": "Government-notified MRP"},
        {"type": "Fertilizer", "name": "DAP", "pack": "50 kg bag", "price": "₹1,350", "support": "Government-supported fertilizer", "tag": "N + P", "details": "Diammonium phosphate supplies phosphorus and nitrogen for root development and early crop growth.", "use": "Use after a soil test or local agronomy advice. Confirm the current printed MRP at the shop.", "source": "Government-supported input"},
        {"type": "Fertilizer", "name": "Muriate of Potash", "pack": "50 kg bag", "price": "₹1,700", "support": "Government-supported fertilizer", "tag": "Potassium", "details": "MOP supplies potassium, which supports crop strength, water balance and produce quality.", "use": "Apply to the soil as recommended for your crop. Avoid over-application near young plants.", "source": "Government-supported input"},
        {"type": "Fertilizer", "name": "NPK 10:26:26", "pack": "50 kg bag", "price": "₹1,470", "support": "Balanced government-supported fertilizer", "tag": "Multi-nutrient", "details": "A compound fertilizer supplying nitrogen, phosphorus and potassium for balanced crop nutrition.", "use": "Choose the grade with local soil guidance and keep the bag sealed until application.", "source": "Government-supported input"},
        {"type": "Fertilizer", "name": "Single Super Phosphate", "pack": "50 kg bag", "price": "₹500", "support": "Phosphorus and sulphur fertilizer", "tag": "P + S", "details": "SSP provides phosphorus, sulphur and calcium and is commonly used for soil fertility support.", "use": "Work into the soil before planting or follow the crop-specific recommendation.", "source": "Government-supported input"},
        {"type": "Pesticide", "name": "Neem oil", "pack": "1 litre", "price": "₹280", "support": "Organic crop-care option", "tag": "Bio-control", "details": "A plant-based pest management option for early-stage soft-bodied insect pressure.", "use": "Dilute and apply only at the label rate. Test a small area first and avoid spraying in strong sun.", "source": "Approved bio-input category"},
        {"type": "Pesticide", "name": "Trichoderma", "pack": "1 kg", "price": "₹180", "support": "Biological disease management", "tag": "Soil health", "details": "A biological soil-care input used to support management of some soil-borne fungal problems.", "use": "Follow the packet label and keep away from incompatible chemical treatments.", "source": "Approved bio-input category"},
        {"type": "Pesticide", "name": "Yellow sticky traps", "pack": "10 traps", "price": "₹120", "support": "Non-chemical pest monitoring", "tag": "Pest check", "details": "A non-chemical monitoring tool that helps identify and track flying insect pressure.", "use": "Place above the crop canopy and replace when the sticky surface is full of insects or dust.", "source": "Non-chemical crop-care input"},
        {"type": "Pesticide", "name": "Pseudomonas fluorescens", "pack": "1 kg", "price": "₹220", "support": "Biological crop protection", "tag": "Bio-control", "details": "A biological input used in integrated crop protection and disease management programs.", "use": "Use according to the product label and local agriculture officer guidance.", "source": "Approved bio-input category"},
    ]


def recommend_from_farm(values):
    soil = values.get("soil_type", "Don't Know").lower()
    location = values.get("location", "").lower()
    current_crop = values.get("current_crop", "").lower()
    region = "Maharashtra" if any(place in location for place in ("maharashtra", "pune", "nagpur", "nashik")) else values.get("location", "your region")
    rules = {
        "black soil": [("Soybean", 92, f"Suitable for {soil.title()} and commonly cultivated in {region}."), ("Chickpea", 86, "A practical rotation option after many summer crops."), ("Sunflower", 79, "Can suit well-drained black soil with good sunlight.")],
        "alluvial soil": [("Wheat", 91, "Often suitable for fertile alluvial soil."), ("Chickpea", 84, "A suitable lower-water rotation option."), ("Mustard", 78, "A common cool-season option for this soil.")],
        "red soil": [("Groundnut", 89, "Can perform well in well-drained red soil."), ("Millet", 84, "A resilient option for lighter soils."), ("Pigeon Pea", 80, "Useful as a rotation crop in many regions.")],
    }
    recommendations = rules.get(soil, [("Soybean", 78, f"A general option to discuss with a local expert in {region}."), ("Chickpea", 74, "A practical rotation crop when soil information is limited."), ("Millet", 70, "Often considered when water availability is uncertain.")])
    recommendations = [item for item in recommendations if item[0].lower() != current_crop]
    return {"recommendations": [{"crop": crop, "score": score, "reason": reason} for crop, score, reason in recommendations[:3]], "note": "Suitability indicators are model and rule-based guidance, not guaranteed yield or profit."}


def demo_dashboard(farmer_name="Ravi Kumar", farm_record=None, live=False):
    farm_record = farm_record or {"farm_name": "Green Valley Farm", "location": "Pune", "area": "2.5 acres", "crop": "Tomato"}
    crop = farm_record["crop"]
    market = get_market_data(crop)
    weather = get_weather(farm_record["location"], crop, live=live)
    return {
        "farmer": farmer_name,
        "farm": {"name": farm_record["farm_name"], "location": farm_record["location"], "area": farm_record["area"], "crop": crop},
        "weather": {"temperature": weather["temperature"], "humidity": weather["humidity"], "rain_probability": weather["rain_probability"], "summary": weather["forecast"][0]["summary"]},
        "irrigation": weather["irrigation"],
        "health": [
            {"crop": "Tomato", "status": "Healthy", "detail": "Last checked 2 days ago"},
            {"crop": "Chilli", "status": "Needs attention", "detail": "Review a recent crop check"},
        ],
        "market": {"crop": market["crop"], "market": market["market"], "price": f"₹{market['current_price']:,}", "unit": market["unit"], "change": f"{market['change_percent']:+.1f}%"},
        "recent_checks": [
            {"crop": crop, "condition": "No diagnosis yet", "severity": "Check needed", "date": "Today"},
            {"crop": "Chilli", "condition": "No diagnosis yet", "severity": "Check needed", "date": "08 Sep 2026"},
        ],
    }


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["DEBUG"])

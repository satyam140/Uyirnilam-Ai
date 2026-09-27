import hashlib
import json
import os


DEMO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "diagnosis_demo.json")


def analyze_image(image_bytes, crop, demo_mode=True, api_key="", model="claude-sonnet-4-20250514"):
    if not demo_mode and api_key:
        return analyze_with_claude(image_bytes, crop, api_key, model)
    return analyze_demo_image(image_bytes, crop)


def analyze_demo_image(image_bytes, crop):
    with open(DEMO_PATH, encoding="utf-8") as demo_file:
        scenarios = json.load(demo_file)
    keys = list(scenarios)
    digest = hashlib.sha256(image_bytes).digest()
    scenario = scenarios[keys[int.from_bytes(digest[:4], "big") % len(keys)]]
    result = {**scenario, "crop": crop.title()}
    result["demo_note"] = "Demo mode uses the image fingerprint to select a representative result. Configure Claude Vision for image-based identification."
    return result


def analyze_with_claude(image_bytes, crop, api_key, model):
    import base64
    import json as json_module
    from urllib.request import Request, urlopen

    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    media_type = image_media_type(image_bytes)
    prompt = f"""Analyze this {crop} crop image. Return only valid JSON with these keys: crop, condition, condition_type, confidence, severity, symptoms, explanation, immediate_actions. condition_type must be disease, pest, healthy, or unknown. confidence must be a number from 0 to 100. If uncertain, use unknown and a low confidence. Do not provide pesticide dosage."""
    request = Request("https://api.anthropic.com/v1/messages", method="POST")
    request.add_header("x-api-key", api_key)
    request.add_header("anthropic-version", "2023-06-01")
    request.add_header("content-type", "application/json")
    payload = {"model": model, "max_tokens": 900, "temperature": 0, "system": "You are a cautious crop image assistant. Never invent certainty.", "messages": [{"role": "user", "content": [{"type": "image", "source": {"type": "base64", "media_type": media_type, "data": encoded_image}}, {"type": "text", "text": prompt}]}]}
    with urlopen(request, data=json_module.dumps(payload).encode("utf-8"), timeout=25) as response:
        body = json_module.loads(response.read().decode("utf-8"))
    text = next(item["text"] for item in body.get("content", []) if item.get("type") == "text")
    parsed = json_module.loads(text.replace("```json", "").replace("```", "").strip())
    return normalize_diagnosis(parsed, crop)


def image_media_type(image_bytes):
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def normalize_diagnosis(diagnosis, crop):
    allowed_types = {"disease", "pest", "healthy", "unknown"}
    allowed_severity = {"Low", "Medium", "High"}
    condition_type = diagnosis.get("condition_type", "unknown")
    if condition_type not in allowed_types:
        condition_type = "unknown"
    try:
        confidence = max(0, min(100, int(diagnosis.get("confidence", 0))))
    except (TypeError, ValueError):
        confidence = 0
    if confidence < 50:
        condition_type = "unknown"
    return {
        "crop": crop.title(),
        "condition": diagnosis.get("condition", "Unable to confidently identify the condition") if condition_type != "unknown" else "Unknown condition",
        "condition_type": condition_type,
        "confidence": confidence,
        "severity": diagnosis.get("severity") if diagnosis.get("severity") in allowed_severity else "Low",
        "symptoms": list(diagnosis.get("symptoms", []))[:6],
        "explanation": diagnosis.get("explanation", "The image needs a closer inspection by a local agricultural expert."),
        "immediate_actions": list(diagnosis.get("immediate_actions", ["Take a clearer photo in daylight.", "Check nearby plants.", "Consult a local agricultural expert if symptoms spread."]))[:5],
    }

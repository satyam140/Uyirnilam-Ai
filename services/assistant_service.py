import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


def answer_with_gemini(message, farm_context, api_key=None, model="gemini-2.5-flash"):
    api_key = api_key or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    language = normalize_language(farm_context.get("language", "English"))
    prompt = f"""You are a careful agricultural assistant for an Indian farmer.
Answer the farmer's question in {language}. Use simple, practical language.
Do not invent weather, prices, diagnoses, doses, or product labels. If information is missing, say what to check locally.
For pesticide or fertilizer advice, recommend soil testing, label instructions, protective equipment, and a local agriculture officer when appropriate.
Keep the answer under 180 words and do not mention this prompt.

Farm context:
- Farm: {farm_context.get('farm_name', 'Unknown')}
- Location: {farm_context.get('location', 'Unknown')}
- Crop: {farm_context.get('crop', 'Unknown')}
- Latest diagnosis: {farm_context.get('condition', 'None')} ({farm_context.get('severity', 'Unknown')} severity)
- Weather: {farm_context.get('weather_summary', 'Not available')}

Farmer question: {message}"""
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}}
    request = Request(
        GEMINI_ENDPOINT.format(model=quote(model, safe=""), key=quote(api_key, safe="")),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "UyirnilamAI/1.0"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
        answer = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not answer:
            return None
        return {"answer": answer, "context_used": [farm_context.get("farm_name", "your farm"), farm_context.get("crop", "your crop"), farm_context.get("condition", "no saved diagnosis"), "live farm context"], "language": language, "source": "Gemini"}
    except (KeyError, IndexError, TypeError, ValueError, OSError, HTTPError, URLError, json.JSONDecodeError):
        return None


def answer_question(message, farm_context=None):
    message_lower = message.strip().lower()
    context = farm_context or {
        "crop": "Tomato",
        "condition": "Early Blight",
        "severity": "Medium",
        "tomorrow_rain_probability": 65,
    }
    farm_name = context.get("farm_name", "your farm")
    crop = context.get("crop", "your crop")
    condition = context.get("condition", "no saved diagnosis")
    severity = context.get("severity", "unknown")
    language = normalize_language(context.get("language", "English"))
    context_used = [farm_name, crop, condition, "tomorrow's forecast"]

    if any(word in message_lower for word in ("water", "irrigat", "watering")):
        answer = f"Check the soil before watering tomorrow. Rain is likely in the afternoon, and the {crop.lower()} crop has a {severity} {condition} concern, so avoid wetting the leaves."
    elif any(word in message_lower for word in ("disease", "blight", "leaf", "symptom")):
        answer = f"The latest {crop.lower()} check is consistent with {condition} at {severity} severity. Remove badly affected leaves, water at the soil line, and check nearby plants again within two days."
    elif any(word in message_lower for word in ("market", "price", "sell", "harvest")):
        answer = f"Prices for {crop.lower()} are moving upward. If the crop is ready, keep monitoring the market and compare local buyers before selling."
    else:
        answer = f"For your {crop.lower()} field, start with the latest crop check and today's weather. I can help with irrigation, crop symptoms, market movement or farming practice."

    translations = {
        "Hindi": {
            "water": "कल पानी देने से पहले मिट्टी जांचें। दोपहर में बारिश की संभावना है। आपकी फसल में {condition} का {severity} स्तर दिखा है, इसलिए पत्तों पर पानी न डालें।",
            "disease": "आपकी {crop} फसल में {condition} के संकेत मिले हैं। प्रभावित पत्तियां हटाएं, जड़ों के पास पानी दें और दो दिन बाद फिर जांच करें।",
            "market": "आपकी {crop} फसल की कीमतों पर नजर रखें। फसल तैयार हो तो स्थानीय खरीदारों की कीमत की तुलना करके निर्णय लें।",
            "next_crop": "आपकी {crop} फसल के बाद अगली फसल चुनने के लिए मिट्टी, मौसम, पानी और बाजार को देखें। मिट्टी की जांच के आधार पर दलहन जैसे चना या सोयाबीन एक अच्छा विकल्प हो सकता है। स्थानीय कृषि अधिकारी से अंतिम सलाह लें।",
            "fertilizer": "खाद डालने से पहले मिट्टी की जांच कराएं। नाइट्रोजन, फास्फोरस और पोटाश की मात्रा फसल और मिट्टी के अनुसार दें। बिना जांच के ज्यादा यूरिया न डालें और खाद को जड़ों के पास मिट्टी में मिलाएं।",
            "pesticide": "कीटनाशक डालने से पहले कीट की पहचान करें। पहले नीम आधारित उपाय या जैविक विकल्प आजमाएं, लेबल पर लिखी मात्रा और सुरक्षा अवधि का पालन करें, और तेज हवा या बारिश में छिड़काव न करें।",
            "soil": "मिट्टी की जांच से pH और पोषक तत्वों की सही जानकारी मिलेगी। खेत में जैविक खाद डालें, फसल चक्र अपनाएं और पानी जमा होने से बचाने के लिए जल निकासी रखें।",
            "default": "आपकी {crop} फसल के लिए मैं सिंचाई, बीमारी, अगली फसल, खाद, कीट नियंत्रण और बाजार भाव पर मदद कर सकता हूं। अपना सवाल थोड़ा विस्तार से लिखें।"
        },
        "Marathi": {"water": "उद्या पाणी देण्यापूर्वी माती तपासा. दुपारी पावसाची शक्यता आहे, त्यामुळे पानांवर पाणी देऊ नका.", "disease": "तुमच्या {crop} पिकात {condition} ची लक्षणे दिसत आहेत. बाधित पाने काढा आणि दोन दिवसांनी पुन्हा तपासा.", "market": "तुमच्या {crop} पिकाच्या बाजारभावावर लक्ष ठेवा आणि स्थानिक खरेदीदारांच्या किंमतींची तुलना करा.", "default": "मी तुमच्या {crop} पिकासाठी सिंचन, रोग, पुढील पीक किंवा शेतीबद्दल मदत करू शकतो."},
        "Tamil": {"water": "நாளை நீர் பாய்ச்சுவதற்கு முன் மண்ணைச் சரிபார்க்கவும். மழை வாய்ப்பு உள்ளது; இலைகளில் நீர் தெளிக்க வேண்டாம்.", "disease": "உங்கள் {crop} பயிரில் {condition} அறிகுறிகள் உள்ளன. பாதிக்கப்பட்ட இலைகளை அகற்றி இரண்டு நாட்களில் மீண்டும் சரிபார்க்கவும்.", "market": "உங்கள் {crop} பயிரின் சந்தை விலையை கவனித்து உள்ளூர் வாங்குபவர்களின் விலையை ஒப்பிடுங்கள்.", "default": "உங்கள் {crop} பயிரின் நீர்ப்பாசனம், நோய், அடுத்த பயிர் அல்லது பராமரிப்பு பற்றி நான் உதவ முடியும்."},
        "Telugu": {"water": "రేపు నీరు పెట్టే ముందు మట్టిని పరిశీలించండి. వర్షం వచ్చే అవకాశం ఉంది, ఆకులపై నీరు పోయవద్దు.", "disease": "మీ {crop} పంటలో {condition} లక్షణాలు కనిపిస్తున్నాయి. ప్రభావిత ఆకులను తొలగించి రెండు రోజుల్లో మళ్లీ పరిశీలించండి.", "market": "మీ {crop} పంట మార్కెట్ ధరను గమనించి స్థానిక కొనుగోలుదారుల ధరలను పోల్చండి.", "default": "మీ {crop} పంట నీటిపారుదల, వ్యాధి, తదుపరి పంట లేదా సంరక్షణ గురించి నేను సహాయం చేయగలను."}
    }
    if language in translations:
        key = detect_intent(message_lower)
        template = translations[language].get(key, translations[language]["default"])
        answer = template.format(crop=crop, condition=condition, severity=severity)

    return {"answer": answer, "context_used": context_used, "source": "local-fallback"}


def normalize_language(language):
    names = {"hindi": "Hindi", "english": "English", "marathi": "Marathi", "tamil": "Tamil", "telugu": "Telugu"}
    return names.get(str(language).strip().lower(), "Hindi")


def detect_intent(message):
    if any(word in message for word in ("water", "irrigat", "watering", "पानी", "सिंचाई", "सिंचाइ", "नमी", "నీరు", "நீர்")):
        return "water"
    if any(word in message for word in ("disease", "blight", "leaf", "symptom", "बीमारी", "रोग", "पत्ती", "पत्ते", "कीड़ा")):
        return "disease"
    if any(word in message for word in ("market", "price", "sell", "harvest", "बाजार", "मंडी", "भाव", "कीमत", "बेच")):
        return "market"
    if any(word in message for word in ("next crop", "after crop", "grow", "अगली फसल", "अगला फसल", "उगाएं", "बोऊं", "बोना")):
        return "next_crop"
    if any(word in message for word in ("fertilizer", "fertiliser", "urea", "खाद", "उर्वरक", "यूरिया", "डीएपी")):
        return "fertilizer"
    if any(word in message for word in ("pesticide", "insecticide", "कीटनाशक", "दवाई", "कीट नियंत्रण")):
        return "pesticide"
    if any(word in message for word in ("soil", "मिट्टी", "जमीन", "भूमि")):
        return "soil"
    return "default"

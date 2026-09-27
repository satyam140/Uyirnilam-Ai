from io import BytesIO

from app import create_app


def test_health_endpoint():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"
    assert response.json["service"] == "uyirnilam-ai"


def test_landing_page_loads():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"UYIRNILAM" in response.data
    assert b"Check my crop" in response.data


def test_dashboard_has_demo_farm_context():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    page = client.get("/dashboard")
    data = client.get("/api/dashboard")

    assert page.status_code == 200
    assert b"Green Valley Farm" in page.data
    assert data.status_code == 200
    assert data.json["farmer"] == "Ravi Kumar"
    assert data.json["irrigation"]["status"] == "Moderate irrigation recommended"


def test_crop_doctor_rejects_invalid_image():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().post(
        "/api/analyze-crop",
        data={"image": (BytesIO(b"not-an-image"), "leaf.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "valid crop image" in response.json["error"]


def test_crop_doctor_returns_structured_demo_diagnosis():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().post(
        "/api/analyze-crop",
        data={"image": (BytesIO(b"\xff\xd8\xff\xe0demo"), "tomato.jpg"), "crop": "Tomato"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.json["condition"] == "Early Blight"
    assert response.json["confidence"] == 92
    assert len(response.json["immediate_actions"]) == 3


def test_different_images_do_not_return_the_same_demo_diagnosis():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    first = client.post("/api/analyze-crop", data={"image": (BytesIO(b"\xff\xd8\xff\xe0demo1"), "first.jpg")}, content_type="multipart/form-data")
    second = client.post("/api/analyze-crop", data={"image": (BytesIO(b"\xff\xd8\xff\xe0demo2"), "second.jpg")}, content_type="multipart/form-data")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json["condition"] != second.json["condition"]


def test_weather_api_returns_actionable_irrigation_advice():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().get("/api/weather?location=Pune")

    assert response.status_code == 200
    assert response.json["location"] == "Pune"
    assert response.json["irrigation"]["status"] == "Moderate irrigation recommended"
    assert "rain_probability" in response.json["irrigation"]["rule_inputs"]


def test_treatment_api_uses_controlled_guidance():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().get("/api/treatment?condition=Early%20Blight")

    assert response.status_code == 200
    assert response.json["guidance"]["organic"]["name"] == "Neem-based care"
    assert "label" in response.json["guidance"]["chemical"]["frequency"]


def test_market_api_returns_trend_data():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().get("/api/market?crop=tomato")

    assert response.status_code == 200
    assert response.json["market"] == "Pune APMC"
    assert response.json["current_price"] == 2450
    assert len(response.json["history"]) == 7
    assert response.json["direction"] == "up"


def test_assistant_uses_farm_context():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().post(
        "/api/assistant",
        json={"message": "Should I irrigate my tomato field tomorrow?"},
    )

    assert response.status_code == 200
    assert "मिट्टी" in response.json["answer"]
    assert "Early Blight" in response.json["context_used"]


def test_assistant_rejects_empty_message():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().post("/api/assistant", json={"message": ""})

    assert response.status_code == 400


def test_demo_login_and_farm_profile_load():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    login = client.post("/login", data={"phone": "demo@uyirnilam.local", "password": "demo"})
    farm = client.get("/farm")

    assert login.status_code == 302
    assert farm.status_code == 200
    assert b"Green Valley Farm" in farm.data


def test_diagnosis_can_be_saved_and_listed():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    payload = {"crop": "Tomato", "condition": "Early Blight", "confidence": 92, "severity": "Medium", "symptoms": ["Brown lesions"], "explanation": "Visible symptoms are consistent."}
    saved = client.post("/api/diagnoses/save", json=payload)
    listed = client.get("/api/diagnoses")

    assert saved.status_code == 201
    assert saved.json["saved"] is True
    assert listed.status_code == 200
    assert listed.json[0]["condition"] == "Early Blight"


def test_crop_recommendation_returns_model_result():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().post("/api/crop-recommendation", json={"N": 30, "P": 35, "K": 28, "ph": 6.3, "temperature": 27, "humidity": 68, "rainfall": 82})

    assert response.status_code == 200
    assert response.json["recommended_crop"]
    assert "not a guaranteed" in response.json["note"]


def test_report_and_assistant_pages_load():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()

    report = client.get("/report")
    assistant = client.get("/assistant")

    assert report.status_code == 200
    assert b"Green Valley" in report.data
    assert assistant.status_code == 200
    assert b"Uyirnilam Assistant" in assistant.data


def test_profile_recommendation_returns_simple_crop_options():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().post("/api/crop-recommendation", json={"soil_type": "Black Soil", "location": "Pune, Maharashtra", "land_area": "2.5 acres", "current_crop": "Tomato"})

    assert response.status_code == 200
    assert response.json["recommendations"][0]["crop"] == "Soybean"
    assert len(response.json["recommendations"]) == 3


def test_hindi_assistant_response_is_available():
    app = create_app()
    app.config.update(TESTING=True)
    response = app.test_client().post("/api/assistant", json={"message": "मेरी अगली फसल कौन सी होनी चाहिए?", "language": "Hindi"})

    assert response.status_code == 200
    assert "फसल" in response.json["answer"]
    assert response.json["language"] == "Hindi"


def test_hindi_profile_assistant_response_is_hindi():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    client.post("/api/auth/register", json={"name": "Hindi Farmer", "phone": "hindi-profile-test", "password": "test", "preferred_language": "hindi", "location": "Pune"})

    response = client.post("/api/assistant", json={"message": "मेरी फसल के लिए क्या करूं?"})

    assert response.status_code == 200
    assert response.json["language"] == "Hindi"
    assert "फसल" in response.json["answer"]


def test_hindi_assistant_handles_common_farm_questions():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    questions = {
        "मेरी फसल में पानी कब दूं?": "मिट्टी",
        "अगली फसल कौन सी बोऊं?": "अगली फसल",
        "कौन सी खाद डालूं?": "खाद",
        "कीटनाशक कैसे डालूं?": "कीटनाशक",
        "मेरी मिट्टी के लिए सलाह दें": "मिट्टी",
    }
    for question, expected in questions.items():
        response = client.post("/api/assistant", json={"message": question, "language": "Hindi"})
        assert response.status_code == 200
        assert response.json["language"] == "Hindi"
        assert expected in response.json["answer"]


def test_mvp_auth_and_farm_api_contracts():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    login = client.post("/api/auth/login", json={"phone": "demo@uyirnilam.local", "password": "demo"})
    farm = client.get("/api/farm")
    recommendation_page = client.get("/recommendation")

    assert login.status_code == 200
    assert farm.status_code == 200
    assert farm.json["farm"]["soil_type"]
    assert recommendation_page.status_code == 200
    assert b"What should you" in recommendation_page.data


def test_farm_setup_continue_redirects_to_dashboard():
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    client.post("/api/auth/login", json={"phone": "demo@uyirnilam.local", "password": "demo"})

    response = client.post("/farm", data={
        "farm_name": "Green Valley Farm",
        "state": "Maharashtra",
        "district": "Pune",
        "location": "Pune",
        "area": "2.5 acres",
        "crop": "Tomato",
        "soil_type": "Black Soil",
        "irrigation_type": "Drip",
        "preferred_language": "Hindi",
    })

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

# Uyirnilam AI

**Smarter farming. Sustainable tomorrow.**

Uyirnilam AI is a farmer-focused Smart India Hackathon 2026 prototype for early crop disease and pest detection. The product is designed to turn a crop observation into an understandable, practical next decision.

## Current Status

Phase 1 and the first dashboard slice are complete:

- Flask application foundation and app factory
- Demo-mode configuration via environment variables
- Farmer-focused responsive landing page
- Health API at `GET /api/health`
- Smoke tests for the landing page and health route
- Demo farmer dashboard at `/dashboard`
- Dashboard API at `GET /api/dashboard`
- Farm summary, weather, irrigation, crop health, market and recent-check cards
- Crop Doctor upload page at `/crop-doctor`
- Validated demo analysis API at `POST /api/analyze-crop`
- Demo analysis selects different representative diagnoses from the uploaded image fingerprint; it does not claim to visually identify arbitrary crops.
- Live image identification is available when `DEMO_MODE=false` and `CLAUDE_API_KEY` is configured.
- Weather and irrigation page at `/weather`
- Weather API at `GET /api/weather`
- Controlled treatment guidance at `GET /api/treatment?condition=Early%20Blight`
- Market intelligence page at `/market` with seven-day Chart.js trend
- Context-aware assistant at `/assistant`
- Gemini farmer-assistant integration using the farmer's preferred language, with local fallback guidance
- SQLite farm profile, session authentication, and diagnosis history
- Random Forest crop recommendation API at `POST /api/crop-recommendation`
- Printable farm report at `/report`

The remaining product areas are live Claude Vision integration and live external weather/market adapters. Demo mode already provides fallback behavior for the complete judge workflow.

## Architecture

The planned stack follows the SIH presentation:

- **Frontend:** HTML, CSS, JavaScript, Chart.js
- **Backend:** Python, Flask, REST APIs
- **Database:** PostgreSQL in live deployments; SQLite is the local Phase 1 default
- **AI:** Claude Vision for crop analysis, Gemini for the farmer assistant
- **External data:** OpenWeatherMap and configured market sources
- **Reports:** jsPDF and html2canvas in the browser

The application will use a live-or-demo service boundary. With `DEMO_MODE=true`, local realistic data keeps the complete demo usable when internet services are unavailable.

## Project Structure

```text
uyirnilam/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── routes/
├── services/
├── models/
├── data/
├── ml/
├── templates/
├── static/
└── tests/
```

## Run Locally

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Open `http://127.0.0.1:5000` in a browser. Check the service with `http://127.0.0.1:5000/api/health`.

## Environment Variables

Copy `.env.example` to `.env`. Keep API keys out of source control.

- `DEMO_MODE=true` uses local fallback data and is the recommended hackathon setting.
- `DEMO_MODE=false` enables configured live integrations as they are implemented.
- `DATABASE_URL` defaults to a local SQLite database during early development and will be used for PostgreSQL in the full prototype.
- `CLAUDE_API_KEY`, `GEMINI_API_KEY`, and `OPENWEATHER_API_KEY` are optional until their live services are enabled.

### Enable Gemini farmer chat

Create a new key in Google AI Studio and put it in your local `.env` file. Do not commit the file:

```bash
GEMINI_API_KEY=your-rotated-key
GEMINI_MODEL=gemini-2.5-flash
```

Restart Flask after changing `.env`. Gemini receives the farmer's preferred language, crop, latest diagnosis, and weather summary. If the key is missing or Gemini is unavailable, the existing local multilingual answers are used.

## Test

```bash
python -m pytest -q
```

## Planned Development Phases

1. Project setup and Flask server
2. Nature-themed frontend foundation
3. Dashboard and demo farmer
4. Crop Doctor upload and image validation
5. Demo diagnosis service and result page
6. Controlled treatment, weather and irrigation decisions
7. Market intelligence and context-aware assistant
8. Farm persistence, authentication, crop recommendation and reports
6. Claude Vision integration boundary
7. Severity and controlled treatment engine
8. Weather and irrigation decision logic
9. Market intelligence and trend chart
10. Context-aware farmer assistant
11. Farm monitoring and persistence
12. Report generation
13. Session authentication
14. Full demo workflow, testing and deployment documentation

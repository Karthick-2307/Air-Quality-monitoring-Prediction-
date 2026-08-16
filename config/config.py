
import os
from dotenv import load_dotenv

load_dotenv()

class Config:

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    DATABASE_PATH = os.path.join(BASE_DIR, "data", "air_quality.db")

    DATA_DIR = os.path.join(BASE_DIR, "data")
    MODELS_DIR = os.path.join(BASE_DIR, "models")

    OPEN_METEO_BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
    OPEN_METEO_TIMEOUT = 15

    GEOCODING_BASE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    GEOCODING_TIMEOUT = 10

    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "5000"))
    SERVER_THREADS = int(os.getenv("SERVER_THREADS", "8"))
    LIVE_REFRESH_INTERVAL = int(os.getenv("LIVE_REFRESH_INTERVAL", "30"))

    OPENAQ_BASE_URL = "https://api.openaq.org/v3"
    OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")

    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_API_URL = os.getenv(
        "AI_API_URL",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent",
    )

    ML_TEST_SPLIT = 0.2
    ML_RANDOM_STATE = 42

    SYNC_PAST_DAYS = 7
    SYNC_FORECAST_DAYS = 3

    POLLUTANTS = {
        "pm2_5": {"name": "PM2.5", "unit": "µg/m³", "label": "PM2.5"},
        "pm10": {"name": "PM10", "unit": "µg/m³", "label": "PM10"},
        "carbon_monoxide": {"name": "CO", "unit": "µg/m³", "label": "CO"},
        "nitrogen_dioxide": {"name": "NO2", "unit": "µg/m³", "label": "NO2"},
        "sulphur_dioxide": {"name": "SO2", "unit": "µg/m³", "label": "SO2"},
        "ozone": {"name": "O3", "unit": "µg/m³", "label": "O3"},
    }

    AQI_BREAKPOINTS = {
        "pm2_5": [
            (0, 30, 0, 50),
            (31, 60, 51, 100),
            (61, 90, 101, 200),
            (91, 120, 201, 300),
            (121, 250, 301, 400),
            (251, 500, 401, 500),
        ],
        "pm10": [
            (0, 50, 0, 50),
            (51, 100, 51, 100),
            (101, 250, 101, 200),
            (251, 350, 201, 300),
            (351, 430, 301, 400),
            (431, 600, 401, 500),
        ],
        "nitrogen_dioxide": [
            (0, 40, 0, 50),
            (41, 80, 51, 100),
            (81, 180, 101, 200),
            (181, 280, 201, 300),
            (281, 400, 301, 400),
            (401, 600, 401, 500),
        ],
        "sulphur_dioxide": [
            (0, 40, 0, 50),
            (41, 80, 51, 100),
            (81, 380, 101, 200),
            (381, 800, 201, 300),
            (801, 1600, 301, 400),
            (1601, 2000, 401, 500),
        ],
        "carbon_monoxide": [
            (0, 1.0, 0, 50),
            (1.1, 2.0, 51, 100),
            (2.1, 10.0, 101, 200),
            (10.1, 17.0, 201, 300),
            (17.1, 34.0, 301, 400),
            (34.1, 50.0, 401, 500),
        ],
        "ozone": [
            (0, 50, 0, 50),
            (51, 100, 51, 100),
            (101, 168, 101, 200),
            (169, 208, 201, 300),
            (209, 748, 301, 400),
            (749, 1000, 401, 500),
        ],
    }

    AQI_CATEGORIES = [
        {"range": (0, 50), "category": "Good", "color": "#00e400"},
        {"range": (51, 100), "category": "Satisfactory", "color": "#ffff00"},
        {"range": (101, 200), "category": "Moderate", "color": "#ff7e00"},
        {"range": (201, 300), "category": "Poor", "color": "#ff0000"},
        {"range": (301, 400), "category": "Very Poor", "color": "#8f3f97"},
        {"range": (401, 500), "category": "Severe", "color": "#7e0023"},
    ]

    CITIES = {
        "Delhi": {"lat": 28.6139, "lon": 77.2090},
        "Mumbai": {"lat": 19.0760, "lon": 72.8777},
        "Bengaluru": {"lat": 12.9716, "lon": 77.5946},
        "Chennai": {"lat": 13.0827, "lon": 80.2707},
        "Kolkata": {"lat": 22.5726, "lon": 88.3639},
        "Hyderabad": {"lat": 17.3850, "lon": 78.4867},
        "Coimbatore": {"lat": 11.0168, "lon": 76.9558},
        "Pune": {"lat": 18.5204, "lon": 73.8567},
        "Ahmedabad": {"lat": 23.0225, "lon": 72.5714},
        "Jaipur": {"lat": 26.9124, "lon": 75.7873},
        "Lucknow": {"lat": 26.8467, "lon": 80.9462},
        "Surat": {"lat": 21.1702, "lon": 72.8311},
    }

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = DevelopmentConfig() if Config.FLASK_ENV == "development" else ProductionConfig()
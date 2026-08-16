
import requests
from datetime import datetime

from config.config import config
from database import db
from services.air_quality_service import air_quality_service
from services.location_service import location_service

class AIServiceError(Exception):
    pass

class AIService:

    def __init__(self):
        self.api_key = config.AI_API_KEY
        self.api_url = config.AI_API_URL

    def is_configured(self):
        return bool(self.api_key and self.api_key != "your_ai_api_key_here")

    def get_grounded_data(self, city, lat=None, lon=None):
        if lat and lon:
            latitude = float(lat)
            longitude = float(lon)
        else:
            coords = location_service.get_city_coordinates(city)
            if not coords:
                raise AIServiceError(f"City '{city}' not found.")
            latitude = coords["latitude"]
            longitude = coords["longitude"]

        try:
            data = air_quality_service.get_current_air_quality(latitude, longitude, city)
        except Exception:
            latest = db.get_latest_measurements(city)
            data = {
                "city": city,
                "latitude": latitude,
                "longitude": longitude,
                "pollutants": {
                    key: {"name": info["name"], "value": latest[key]["value"], "unit": info["unit"]}
                    for key, info in config.POLLUTANTS.items()
                    if key in latest
                },
                "source": "Cached data",
                "timestamp": datetime.now().isoformat(),
            }
            data["aqi"] = air_quality_service.calculate_indian_aqi(data["pollutants"])

        predictions = db.get_predictions(city, limit=1)
        prediction = predictions[0] if predictions else None

        return {
            "location": city,
            "timestamp": data.get("timestamp", datetime.now().isoformat()),
            "pollutants": data.get("pollutants", {}),
            "aqi": data.get("aqi", {}),
            "source": data.get("source", "Unknown"),
            "prediction": prediction,
        }

    def build_prompt(self, action, grounded_data):
        pollutant_lines = []
        for key, info in grounded_data["pollutants"].items():
            value = info.get("value")
            if value is not None:
                pollutant_lines.append(f"{info['name']}: {value:.1f} {info['unit']}")

        pollutants_str = "\n".join(pollutant_lines) if pollutant_lines else "No pollutant data available"

        aqi_value = grounded_data["aqi"].get("value") if grounded_data.get("aqi") else None
        aqi_category = grounded_data["aqi"].get("category") if grounded_data.get("aqi") else "Unknown"

        prediction_str = "No prediction available"
        if grounded_data.get("prediction"):
            pred = grounded_data["prediction"]
            prediction_str = f"Predicted PM2.5: {pred['predicted_pm25']:.1f} µg/m³ (Model: {pred['model_name']})"

        base_context = f"""
Location: {grounded_data['location']}
Timestamp: {grounded_data['timestamp']}
Data Source: {grounded_data['source']}

Pollutant Measurements:
{pollutants_str}

AQI (Indian CPCB): {aqi_value if aqi_value is not None else 'Not available'}
AQI Category: {aqi_category}

{prediction_str}
"""

        if action == "explain_current":
            return f"""
You are an air quality expert. Explain the current air quality situation based ONLY on the following real data.
Do not invent any values. Keep your response concise (150-200 words) and easy to understand.

{base_context}

Explain what the AQI value and pollutant levels mean for the general population.
"""
        elif action == "explain_prediction":
            return f"""
You are an air quality expert. Explain the PM2.5 prediction based ONLY on the following real data.
Do not invent any values. Keep your response concise (150-200 words).

{base_context}

Explain what the predicted PM2.5 level means and what factors might influence it.
"""
        elif action == "health_precautions":
            return f"""
You are a public health educator. Provide general health precautions based ONLY on the following real air quality data.
Do not invent any values. Keep your response concise (150-200 words).
Do NOT diagnose diseases or provide personalized medical treatment.

{base_context}

Provide general health precautions appropriate for the current AQI category.
"""
        else:
            return f"Explain the following air quality data:\n{base_context}"

    def call_ai(self, action, city, lat=None, lon=None):
        if not self.is_configured():
            raise AIServiceError(
                "AI API is not configured. Please add your AI_API_KEY to the .env file. "
                "Get a free Gemini key at https://aistudio.google.com"
            )

        grounded_data = self.get_grounded_data(city, lat, lon)

        prompt = self.build_prompt(action, grounded_data)

        try:
            headers = {
                "Content-Type": "application/json",
            }
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 500,
                }
            }

            url = f"{self.api_url}?key={self.api_key}"
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "candidates" in data and data["candidates"]:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            else:
                raise AIServiceError("AI returned an empty response.")

        except requests.exceptions.Timeout:
            raise AIServiceError("AI request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            raise AIServiceError("No internet connection. Cannot reach AI service.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AIServiceError("Invalid AI API key. Please check your .env file.")
            elif e.response.status_code == 429:
                raise AIServiceError("AI rate limit exceeded. Please try again later.")
            else:
                raise AIServiceError(f"AI API error: {e}")
        except Exception as e:
            raise AIServiceError(f"Unexpected AI error: {str(e)}")

ai_service = AIService()
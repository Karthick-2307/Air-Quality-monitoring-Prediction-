
import requests
from datetime import datetime, timedelta

from config.config import config
from database import db

class AirQualityServiceError(Exception):
    pass

class AirQualityService:

    def __init__(self):
        self.base_url = config.OPEN_METEO_BASE_URL
        self.timeout = config.OPEN_METEO_TIMEOUT

    def check_internet(self):
        try:
            requests.get("https://www.google.com", timeout=5)
            return True
        except requests.RequestException:
            return False

    def fetch_air_quality(self, latitude, longitude, city="Unknown", past_days=None, forecast_days=None):
        if past_days is None:
            past_days = config.SYNC_PAST_DAYS
        if forecast_days is None:
            forecast_days = config.SYNC_FORECAST_DAYS

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
            "current": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
            "past_days": past_days,
            "forecast_days": forecast_days,
            "timezone": "auto",
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            raise AirQualityServiceError("API request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            raise AirQualityServiceError("No internet connection. Please check your network.")
        except requests.exceptions.HTTPError as e:
            raise AirQualityServiceError(f"API returned HTTP error: {e}")
        except requests.exceptions.JSONDecodeError:
            raise AirQualityServiceError("Invalid response from API.")
        except Exception as e:
            raise AirQualityServiceError(f"Unexpected error fetching data: {str(e)}")

        if "current" not in data or "hourly" not in data:
            raise AirQualityServiceError("API response missing expected data fields.")

        return {
            "city": city,
            "latitude": latitude,
            "longitude": longitude,
            "current": data.get("current", {}),
            "hourly": data.get("hourly", {}),
            "source": "Open-Meteo (CAMS model estimate)",
            "fetched_at": datetime.now().isoformat(),
        }

    def process_and_store(self, data):
        city = data["city"]
        latitude = data["latitude"]
        longitude = data["longitude"]
        source = data["source"]

        measurements = []
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])

        pollutant_map = {
            "pm2_5": "pm2_5",
            "pm10": "pm10",
            "carbon_monoxide": "carbon_monoxide",
            "nitrogen_dioxide": "nitrogen_dioxide",
            "sulphur_dioxide": "sulphur_dioxide",
            "ozone": "ozone",
        }

        for i, timestamp in enumerate(times):
            for api_key, internal_key in pollutant_map.items():
                values = hourly.get(api_key, [])
                if i < len(values) and values[i] is not None:
                    measurements.append({
                        "city": city,
                        "latitude": latitude,
                        "longitude": longitude,
                        "station": "Open-Meteo grid cell",
                        "pollutant": internal_key,
                        "value": values[i],
                        "unit": "µg/m³",
                        "timestamp": timestamp,
                        "source": source,
                    })

        current = data.get("current", {})
        current_time = current.get("time", datetime.now().isoformat())
        for api_key, internal_key in pollutant_map.items():
            value = current.get(api_key)
            if value is not None:
                measurements.append({
                    "city": city,
                    "latitude": latitude,
                    "longitude": longitude,
                    "station": "Open-Meteo grid cell",
                    "pollutant": internal_key,
                    "value": value,
                    "unit": "µg/m³",
                    "timestamp": current_time,
                    "source": source,
                })

        records_added = db.insert_measurements_bulk(measurements)

        db.log_sync(city, "success", records_added, f"Fetched {len(measurements)} measurements")

        return records_added

    def get_current_air_quality(self, latitude, longitude, city="Unknown"):
        data = self.fetch_air_quality(latitude, longitude, city, past_days=1, forecast_days=0)
        current = data["current"]

        pollutants = {}
        for key, info in config.POLLUTANTS.items():
            value = current.get(key)
            if value is not None:
                pollutants[key] = {
                    "name": info["name"],
                    "value": value,
                    "unit": info["unit"],
                    "label": info["label"],
                }

        aqi_result = self.calculate_indian_aqi(pollutants)

        return {
            "city": city,
            "latitude": latitude,
            "longitude": longitude,
            "pollutants": pollutants,
            "aqi": aqi_result,
            "source": data["source"],
            "fetched_at": data["fetched_at"],
            "timestamp": current.get("time", datetime.now().isoformat()),
        }

    def calculate_indian_aqi(self, pollutants):
        sub_indices = {}
        available_pollutants = []

        for key, data in pollutants.items():
            if key in config.AQI_BREAKPOINTS and data["value"] is not None:
                value = data["value"]
                if key == "carbon_monoxide":
                    value = value / 1000.0

                sub_index = self._compute_sub_index(key, value)
                if sub_index is not None:
                    sub_indices[key] = sub_index
                    available_pollutants.append(key)

        has_pm = "pm2_5" in available_pollutants or "pm10" in available_pollutants
        if len(available_pollutants) < 3 or not has_pm:
            return {
                "value": None,
                "category": "Insufficient data",
                "sub_indices": sub_indices,
                "note": "AQI requires at least 3 pollutants including PM2.5 or PM10",
            }

        aqi_value = max(sub_indices.values())

        category = "Unknown"
        for cat in config.AQI_CATEGORIES:
            if cat["range"][0] <= aqi_value <= cat["range"][1]:
                category = cat["category"]
                break

        return {
            "value": aqi_value,
            "category": category,
            "sub_indices": sub_indices,
            "note": "Indian AQI (CPCB methodology) - maximum of pollutant sub-indices",
        }

    def _compute_sub_index(self, pollutant, concentration):
        breakpoints = config.AQI_BREAKPOINTS.get(pollutant, [])
        for bp in breakpoints:
            c_low, c_high, aqi_low, aqi_high = bp
            if c_low <= concentration <= c_high:
                sub_index = ((aqi_high - aqi_low) / (c_high - c_low)) * (concentration - c_low) + aqi_low
                return round(sub_index, 1)
        return None

    def get_aqi_category_info(self, aqi_value):
        for cat in config.AQI_CATEGORIES:
            if cat["range"][0] <= aqi_value <= cat["range"][1]:
                return cat
        return {"range": (0, 0), "category": "Unknown", "color": "#808080"}

air_quality_service = AirQualityService()
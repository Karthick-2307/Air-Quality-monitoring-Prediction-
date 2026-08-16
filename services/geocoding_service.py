
import requests
from config.config import config
from database import db

class GeocodingServiceError(Exception):
    pass

class GeocodingService:

    def __init__(self):
        self.base_url = config.GEOCODING_BASE_URL
        self.timeout = config.GEOCODING_TIMEOUT

    def search_location(self, query, limit=10):
        if not query or not query.strip():
            return []

        query = query.strip()

        try:
            results = self._search_online(query, limit)
            if results:
                for loc in results:
                    db.cache_location(loc)
                return results
        except GeocodingServiceError:
            pass

        cached = db.search_cached_locations(query, limit)
        if cached:
            return cached

        builtin = self._search_builtin(query, limit)
        return builtin

    def _search_online(self, query, limit):
        params = {
            "name": query,
            "count": limit,
            "language": "en",
            "format": "json",
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            raise GeocodingServiceError("Geocoding request timed out.")
        except requests.exceptions.ConnectionError:
            raise GeocodingServiceError("No internet connection for geocoding.")
        except requests.exceptions.HTTPError as e:
            raise GeocodingServiceError(f"Geocoding API returned HTTP error: {e}")
        except requests.exceptions.JSONDecodeError:
            raise GeocodingServiceError("Invalid response from geocoding API.")
        except Exception as e:
            raise GeocodingServiceError(f"Unexpected geocoding error: {str(e)}")

        results = []
        for item in data.get("results", []):
            results.append({
                "name": item.get("name", ""),
                "country": item.get("country", ""),
                "country_code": item.get("country_code", ""),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
                "population": item.get("population"),
                "timezone": item.get("timezone", ""),
                "admin1": item.get("admin1", ""),
                "admin2": item.get("admin2", ""),
            })

        return results

    def _search_builtin(self, query, limit):
        query_lower = query.lower()
        results = []
        for name, coords in config.CITIES.items():
            if query_lower in name.lower():
                results.append({
                    "name": name,
                    "country": "India",
                    "country_code": "IN",
                    "latitude": coords["lat"],
                    "longitude": coords["lon"],
                    "population": None,
                    "timezone": "Asia/Kolkata",
                    "admin1": "",
                    "admin2": "",
                })
                if len(results) >= limit:
                    break
        return results

    def get_coordinates(self, name, country=None):
        results = self.search_location(name, limit=10)
        if not results:
            return None

        if country:
            for loc in results:
                if country.lower() in loc.get("country", "").lower():
                    return {"latitude": loc["latitude"], "longitude": loc["longitude"]}

        first = results[0]
        return {"latitude": first["latitude"], "longitude": first["longitude"]}

geocoding_service = GeocodingService()
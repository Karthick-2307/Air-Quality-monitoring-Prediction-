
import math
from config.config import config

class LocationServiceError(Exception):
    pass

class LocationService:

    def __init__(self):
        self.cities = config.CITIES

    def search_city(self, query):
        if not query:
            return []

        query_lower = query.strip().lower()
        results = []

        for name, coords in self.cities.items():
            if query_lower in name.lower():
                results.append({
                    "name": name,
                    "latitude": coords["lat"],
                    "longitude": coords["lon"],
                })

        return results

    def get_city_coordinates(self, city_name):
        city = self.cities.get(city_name)
        if city:
            return {"latitude": city["lat"], "longitude": city["lon"]}
        return None

    def validate_coordinates(self, latitude, longitude):
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError):
            raise LocationServiceError("Invalid coordinates provided.")

        if not (-90 <= lat <= 90):
            raise LocationServiceError("Latitude must be between -90 and 90.")
        if not (-180 <= lon <= 180):
            raise LocationServiceError("Longitude must be between -180 and 180.")

        return True

    def get_all_cities(self):
        return [
            {"name": name, "latitude": coords["lat"], "longitude": coords["lon"]}
            for name, coords in self.cities.items()
        ]

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371.0

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def find_nearest_city(self, latitude, longitude):
        if not self.cities:
            return None

        nearest = None
        min_distance = float("inf")

        for name, coords in self.cities.items():
            distance = self.haversine_distance(
                latitude, longitude, coords["lat"], coords["lon"]
            )
            if distance < min_distance:
                min_distance = distance
                nearest = {
                    "name": name,
                    "latitude": coords["lat"],
                    "longitude": coords["lon"],
                    "distance_km": round(distance, 1),
                }

        return nearest

location_service = LocationService()
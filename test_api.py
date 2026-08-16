
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config.config import config
from database import db
from services.air_quality_service import air_quality_service, AirQualityServiceError
from services.location_service import location_service

def test_database():
    print("=" * 60)
    print("TEST 1: Database Initialization")
    print("=" * 60)

    db.init_db()
    print(f"✅ Database initialized at: {config.DATABASE_PATH}")

    with db.get_db() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t["name"] for t in tables]
        print(f"   Tables found: {table_names}")

        expected = ["measurements", "predictions", "model_metrics", "sync_log"]
        for table in expected:
            if table in table_names:
                print(f"   ✅ Table '{table}' exists")
            else:
                print(f"   ❌ Table '{table}' MISSING!")

    return True

def test_internet():
    print("\n" + "=" * 60)
    print("TEST 2: Internet Connectivity")
    print("=" * 60)

    online = air_quality_service.check_internet()
    if online:
        print("✅ Internet connection available")
    else:
        print("⚠️  No internet connection - will test offline mode")
    return online

def test_open_meteo_api():
    print("\n" + "=" * 60)
    print("TEST 3: Open-Meteo API - Fetch Delhi Air Quality")
    print("=" * 60)

    coords = location_service.get_city_coordinates("Delhi")
    if not coords:
        print("❌ Delhi not found in city database!")
        return False

    print(f"   Delhi coordinates: {coords['latitude']}, {coords['longitude']}")

    try:
        data = air_quality_service.fetch_air_quality(
            coords["latitude"], coords["longitude"], "Delhi",
            past_days=1, forecast_days=0
        )
        print(f"✅ API fetch successful")
        print(f"   Source: {data['source']}")
        print(f"   Fetched at: {data['fetched_at']}")

        current = data.get("current", {})
        print(f"   Current PM2.5: {current.get('pm2_5')} µg/m³")
        print(f"   Current PM10: {current.get('pm10')} µg/m³")
        print(f"   Current NO2: {current.get('nitrogen_dioxide')} µg/m³")

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        print(f"   Hourly records: {len(times)} timestamps")

        return data
    except AirQualityServiceError as e:
        print(f"❌ API fetch failed: {e}")
        return None

def test_store_data(data):
    print("\n" + "=" * 60)
    print("TEST 4: Store Data in SQLite")
    print("=" * 60)

    if not data:
        print("⚠️  Skipping - no data to store")
        return False

    try:
        records = air_quality_service.process_and_store(data)
        print(f"✅ Stored {records} measurements in database")

        count = db.get_measurement_count("Delhi")
        print(f"   Total measurements for Delhi: {count}")

        cities = db.get_cities()
        print(f"   Cities in database: {cities}")

        return records > 0
    except Exception as e:
        print(f"❌ Failed to store data: {e}")
        return False

def test_aqi_calculation():
    print("\n" + "=" * 60)
    print("TEST 5: Indian AQI Calculation (CPCB)")
    print("=" * 60)

    sample_pollutants = {
        "pm2_5": {"name": "PM2.5", "value": 75.0, "unit": "µg/m³"},
        "pm10": {"name": "PM10", "value": 120.0, "unit": "µg/m³"},
        "nitrogen_dioxide": {"name": "NO2", "value": 45.0, "unit": "µg/m³"},
        "sulphur_dioxide": {"name": "SO2", "value": 30.0, "unit": "µg/m³"},
        "carbon_monoxide": {"name": "CO", "value": 1500.0, "unit": "µg/m³"},
        "ozone": {"name": "O3", "value": 60.0, "unit": "µg/m³"},
    }

    result = air_quality_service.calculate_indian_aqi(sample_pollutants)
    print(f"   AQI value: {result['value']}")
    print(f"   AQI category: {result['category']}")
    print(f"   Sub-indices: {result['sub_indices']}")
    print(f"   Note: {result['note']}")

    if result["value"] is not None:
        print("✅ AQI calculation successful")
        return True
    else:
        print("❌ AQI calculation returned None")
        return False

def test_offline_fallback():
    print("\n" + "=" * 60)
    print("TEST 6: Cached Data (Offline Mode Support)")
    print("=" * 60)

    latest = db.get_latest_measurements("Delhi")
    if latest:
        print(f"✅ Cached data available for Delhi")
        for pollutant, measurement in latest.items():
            print(f"   {pollutant}: {measurement['value']} {measurement['unit']} @ {measurement['timestamp']}")
        return True
    else:
        print("⚠️  No cached data available yet")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("AIR QUALITY DASHBOARD - VERIFICATION TESTS")
    print("=" * 60)

    test_database()
    online = test_internet()

    data = None
    if online:
        data = test_open_meteo_api()
        test_store_data(data)
    else:
        print("\n⚠️  Offline mode - skipping API tests, testing cached data only")

    test_aqi_calculation()
    test_offline_fallback()

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
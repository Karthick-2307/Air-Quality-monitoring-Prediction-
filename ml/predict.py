
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.prediction_service import prediction_service, PredictionServiceError

def predict(city, period="next_day"):
    try:
        result = prediction_service.predict_future(city, period)
        print(f"✅ Prediction for {city}:")
        print(f"   Predicted PM2.5: {result['prediction']:.1f} µg/m³")
        print(f"   Model: {result['model']}")
        print(f"   Period: {result['period']}")
        return result
    except PredictionServiceError as e:
        print(f"❌ {e}")
        return None

if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else None
    period = sys.argv[2] if len(sys.argv) > 2 else "next_day"

    if not city:
        print("Usage: python -m ml.predict [city] [period]")
        print("Example: python -m ml.predict Delhi next_day")
    else:
        predict(city, period)
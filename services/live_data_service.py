
import json
import time
from datetime import datetime

from services.air_quality_service import air_quality_service, AirQualityServiceError
from services.location_service import location_service, LocationServiceError

class LiveDataService:

    def __init__(self):
        self.refresh_interval = 30

    def stream_air_quality(self, latitude, longitude, city="Unknown"):
        while True:
            try:
                data = air_quality_service.get_current_air_quality(
                    latitude, longitude, city
                )

                try:
                    air_quality_service.process_and_store(
                        air_quality_service.fetch_air_quality(
                            latitude, longitude, city, past_days=1, forecast_days=0
                        )
                    )
                except AirQualityServiceError:
                    pass

                event_data = {
                    "type": "air_quality",
                    "data": data,
                    "timestamp": datetime.now().isoformat(),
                }
                yield f"data: {json.dumps(event_data)}\n\n"

            except (AirQualityServiceError, LocationServiceError) as e:
                event_data = {
                    "type": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
                yield f"data: {json.dumps(event_data)}\n\n"

            except Exception as e:
                event_data = {
                    "type": "error",
                    "error": f"Unexpected error: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
                yield f"data: {json.dumps(event_data)}\n\n"

            time.sleep(self.refresh_interval)

live_data_service = LiveDataService()
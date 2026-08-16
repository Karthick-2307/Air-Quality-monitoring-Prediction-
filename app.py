
import os
from datetime import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for, session

from config.config import config
from database import db
from services.air_quality_service import air_quality_service, AirQualityServiceError
from services.location_service import location_service, LocationServiceError
from services.geocoding_service import geocoding_service, GeocodingServiceError
from services.live_data_service import live_data_service
from services.prediction_service import prediction_service, PredictionServiceError
from services.ai_service import ai_service, AIServiceError
from services.data_import_service import data_import_service, DataImportError

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["DEBUG"] = config.FLASK_DEBUG

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", error_code=500, error_message="Internal server error"), 500

def get_data_status(city=None):
    measurement_count = db.get_measurement_count(city)
    last_sync = db.get_last_sync_time(city)

    if air_quality_service.check_internet():
        if measurement_count > 0:
            return {
                "status": "online",
                "label": "🟢 ONLINE",
                "message": f"Online — Data synchronized {last_sync or 'recently'}",
                "last_sync": last_sync,
            }
        else:
            return {
                "status": "online",
                "label": "🟢 ONLINE",
                "message": "Online — No data synchronized yet",
                "last_sync": None,
            }
    else:
        if measurement_count > 0:
            return {
                "status": "cached",
                "label": "🟡 USING CACHED DATA",
                "message": f"Offline Mode — Showing cached data from {last_sync or 'unknown time'}",
                "last_sync": last_sync,
            }
        else:
            return {
                "status": "no_data",
                "label": "🔴 NO DATA AVAILABLE",
                "message": "No air-quality data is available offline. Please connect to the internet and synchronize data.",
                "last_sync": None,
            }

@app.route("/")
def index():
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    cities = location_service.get_all_cities()
    data_status = get_data_status()
    return render_template(
        "dashboard.html",
        cities=cities,
        data_status=data_status,
        active_page="dashboard",
    )

@app.route("/live-data")
def live_data():
    cities = location_service.get_all_cities()
    data_status = get_data_status()
    return render_template(
        "live_data.html",
        cities=cities,
        data_status=data_status,
        active_page="live_data",
    )

@app.route("/historical")
def historical():
    cities = db.get_cities()
    data_status = get_data_status()
    return render_template(
        "historical.html",
        cities=cities,
        data_status=data_status,
        active_page="historical",
    )

@app.route("/prediction")
def prediction():
    cities = db.get_cities()
    data_status = get_data_status()
    return render_template(
        "prediction.html",
        cities=cities,
        data_status=data_status,
        active_page="prediction",
    )

@app.route("/ai-assistant")
def ai_assistant():
    cities = location_service.get_all_cities()
    data_status = get_data_status()
    return render_template(
        "ai_assistant.html",
        cities=cities,
        data_status=data_status,
        active_page="ai_assistant",
    )

@app.route("/sources")
def sources():
    return render_template("sources.html", active_page="sources")

@app.route("/about")
def about():
    return render_template("about.html", active_page="about")

@app.route("/api/cities")
def api_cities():
    cities = location_service.get_all_cities()
    return jsonify({"cities": cities})

@app.route("/api/search-city")
def api_search_city():
    query = request.args.get("q", "")
    limit = request.args.get("limit", 10, type=int)

    try:
        results = geocoding_service.search_location(query, limit)
        return jsonify({"results": results})
    except GeocodingServiceError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/nearest-city")
def api_nearest_city():
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if not lat or not lon:
        return jsonify({"error": "Please provide lat and lon parameters."}), 400

    try:
        location_service.validate_coordinates(lat, lon)
        nearest = location_service.find_nearest_city(float(lat), float(lon))
        return jsonify({"city": nearest})
    except LocationServiceError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/current-air-quality")
def api_current_air_quality():
    city = request.args.get("city", "")
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    try:
        if lat and lon:
            location_service.validate_coordinates(lat, lon)
            latitude = float(lat)
            longitude = float(lon)
            if not city:
                nearest = location_service.find_nearest_city(latitude, longitude)
                city = nearest["name"] if nearest else f"({latitude:.2f}, {longitude:.2f})"
        elif city:
            coords = location_service.get_city_coordinates(city)
            if not coords:
                coords = geocoding_service.get_coordinates(city)
            if not coords:
                return jsonify({"error": f"Location '{city}' not found."}), 404
            latitude = coords["latitude"]
            longitude = coords["longitude"]
        else:
            return jsonify({"error": "Please provide a city or coordinates."}), 400

        data = air_quality_service.get_current_air_quality(latitude, longitude, city)

        try:
            air_quality_service.process_and_store(
                air_quality_service.fetch_air_quality(latitude, longitude, city, past_days=1, forecast_days=0)
            )
        except AirQualityServiceError as e:
            pass

        return jsonify(data)

    except LocationServiceError as e:
        return jsonify({"error": str(e)}), 400
    except GeocodingServiceError as e:
        return jsonify({"error": str(e)}), 400
    except AirQualityServiceError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route("/api/sync")
def api_sync():
    city = request.args.get("city", "")
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    try:
        if lat and lon:
            location_service.validate_coordinates(lat, lon)
            latitude = float(lat)
            longitude = float(lon)
            if not city:
                nearest = location_service.find_nearest_city(latitude, longitude)
                city = nearest["name"] if nearest else f"({latitude:.2f}, {longitude:.2f})"
        elif city:
            coords = location_service.get_city_coordinates(city)
            if not coords:
                coords = geocoding_service.get_coordinates(city)
            if not coords:
                return jsonify({"error": f"Location '{city}' not found."}), 404
            latitude = coords["latitude"]
            longitude = coords["longitude"]
        else:
            return jsonify({"error": "Please provide a city or coordinates."}), 400

        if not air_quality_service.check_internet():
            return jsonify({"error": "No internet connection. Using cached data."}), 503

        data = air_quality_service.fetch_air_quality(latitude, longitude, city)
        records_added = air_quality_service.process_and_store(data)

        return jsonify({
            "success": True,
            "city": city,
            "records_added": records_added,
            "message": f"Successfully synchronized {records_added} measurements for {city}",
            "synced_at": datetime.now().isoformat(),
        })

    except LocationServiceError as e:
        return jsonify({"error": str(e)}), 400
    except GeocodingServiceError as e:
        return jsonify({"error": str(e)}), 400
    except AirQualityServiceError as e:
        db.log_sync(city, "failed", 0, str(e))
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route("/api/stream")
def api_stream():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    city = request.args.get("city", "Unknown")

    if not lat or not lon:
        return jsonify({"error": "Please provide lat and lon parameters."}), 400

    try:
        location_service.validate_coordinates(lat, lon)
    except LocationServiceError as e:
        return jsonify({"error": str(e)}), 400

    from flask import Response

    def generate():
        yield "retry: 30000\n\n"
        for event in live_data_service.stream_air_quality(
            float(lat), float(lon), city
        ):
            yield event

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

@app.route("/api/measurements")
def api_measurements():
    city = request.args.get("city")
    pollutant = request.args.get("pollutant")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    limit = request.args.get("limit", type=int)

    measurements = db.get_measurements(
        city=city,
        pollutant=pollutant,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

    return jsonify({"measurements": measurements})

@app.route("/api/data-status")
def api_data_status():
    city = request.args.get("city")
    status = get_data_status(city)
    return jsonify(status)

@app.route("/api/data-quality")
def api_data_quality():
    city = request.args.get("city")
    report = db.get_data_quality_report(city)
    return jsonify(report)

@app.route("/api/cities-in-db")
def api_cities_in_db():
    cities = db.get_cities()
    return jsonify({"cities": cities})

@app.route("/api/historical-data")
def api_historical_data():
    city = request.args.get("city", "")
    range_type = request.args.get("range", "7d")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not city:
        return jsonify({"error": "Please provide a city."}), 400

    from datetime import datetime, timedelta
    now = datetime.now()

    if range_type == "24h":
        start = (now - timedelta(hours=24)).isoformat()
        end = now.isoformat()
    elif range_type == "7d":
        start = (now - timedelta(days=7)).isoformat()
        end = now.isoformat()
    elif range_type == "30d":
        start = (now - timedelta(days=30)).isoformat()
        end = now.isoformat()
    elif range_type == "custom" and start_date and end_date:
        start = f"{start_date}T00:00:00"
        end = f"{end_date}T23:59:59"
    else:
        start = (now - timedelta(days=7)).isoformat()
        end = now.isoformat()

    measurements = db.get_measurements(city=city, start_date=start, end_date=end)

    if not measurements:
        return jsonify({"error": "No historical data available for this city and time range.", "has_data": False})

    import pandas as pd
    import numpy as np

    df = pd.DataFrame(measurements)

    pivot = df.pivot_table(
        index="timestamp",
        columns="pollutant",
        values="value",
        aggfunc="mean",
    ).reset_index()

    pivot["timestamp"] = pd.to_datetime(pivot["timestamp"])
    pivot = pivot.sort_values("timestamp")

    trend_data = []
    pollutant_names = {
        "pm2_5": "PM2.5",
        "pm10": "PM10",
        "nitrogen_dioxide": "NO2",
        "sulphur_dioxide": "SO2",
        "carbon_monoxide": "CO",
        "ozone": "O3",
    }

    for col in pivot.columns:
        if col != "timestamp" and col in pollutant_names:
            trend_data.append({
                "x": pivot["timestamp"].dt.strftime("%Y-%m-%d %H:%M").tolist(),
                "y": pivot[col].fillna(0).tolist(),
                "type": "scatter",
                "mode": "lines",
                "name": pollutant_names[col],
            })

    trend_chart = {
        "data": trend_data,
        "layout": {
            "title": f"Pollutant Trends - {city}",
            "xaxis": {"title": "Time"},
            "yaxis": {"title": "Concentration (µg/m³)"},
            "height": 400,
        },
    }

    corr_cols = [col for col in pivot.columns if col != "timestamp" and col in pollutant_names]
    if len(corr_cols) >= 2:
        corr_df = pivot[corr_cols].corr()
        correlation_chart = {
            "data": [{
                "z": corr_df.values.tolist(),
                "x": [pollutant_names[c] for c in corr_df.columns],
                "y": [pollutant_names[c] for c in corr_df.columns],
                "type": "heatmap",
                "colorscale": "RdBu_r",
                "zmin": -1,
                "zmax": 1,
            }],
            "layout": {
                "title": "Pollutant Correlation Heatmap",
                "height": 400,
            },
        }
    else:
        correlation_chart = None

    dist_data = []
    for col in corr_cols:
        dist_data.append({
            "x": pivot[col].dropna().tolist(),
            "type": "histogram",
            "name": pollutant_names[col],
            "opacity": 0.7,
        })

    distribution_chart = {
        "data": dist_data,
        "layout": {
            "title": "Pollutant Distributions",
            "xaxis": {"title": "Concentration (µg/m³)"},
            "yaxis": {"title": "Frequency"},
            "barmode": "overlay",
            "height": 400,
        },
    }

    extremes = {
        "highest_pm25": pivot["pm2_5"].max() if "pm2_5" in pivot.columns else None,
        "highest_pm25_date": pivot.loc[pivot["pm2_5"].idxmax(), "timestamp"].strftime("%Y-%m-%d %H:%M") if "pm2_5" in pivot.columns and not pivot["pm2_5"].isna().all() else None,
        "highest_pm10": pivot["pm10"].max() if "pm10" in pivot.columns else None,
        "highest_pm10_date": pivot.loc[pivot["pm10"].idxmax(), "timestamp"].strftime("%Y-%m-%d %H:%M") if "pm10" in pivot.columns and not pivot["pm10"].isna().all() else None,
        "lowest_pm25": pivot["pm2_5"].min() if "pm2_5" in pivot.columns else None,
        "lowest_pm25_date": pivot.loc[pivot["pm2_5"].idxmin(), "timestamp"].strftime("%Y-%m-%d %H:%M") if "pm2_5" in pivot.columns and not pivot["pm2_5"].isna().all() else None,
        "lowest_pm10": pivot["pm10"].min() if "pm10" in pivot.columns else None,
        "lowest_pm10_date": pivot.loc[pivot["pm10"].idxmin(), "timestamp"].strftime("%Y-%m-%d %H:%M") if "pm10" in pivot.columns and not pivot["pm10"].isna().all() else None,
    }

    return jsonify({
        "has_data": True,
        "city": city,
        "trend_chart": trend_chart,
        "correlation_chart": correlation_chart,
        "distribution_chart": distribution_chart,
        "extremes": extremes,
        "record_count": len(measurements),
    })

@app.route("/api/predict")
def api_predict():
    city = request.args.get("city", "")
    period = request.args.get("period", "next_day")

    if not city:
        return jsonify({"error": "Please provide a city."}), 400

    try:
        result = prediction_service.predict_future(city, period)
        return jsonify(result)
    except PredictionServiceError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

@app.route("/api/ai")
def api_ai():
    action = request.args.get("action", "explain_current")
    city = request.args.get("city", "")
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if not city:
        return jsonify({"error": "Please provide a city."}), 400

    try:
        response = ai_service.call_ai(action, city, lat, lon)
        return jsonify({"response": response})
    except AIServiceError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"AI request failed: {str(e)}"}), 500

@app.route("/api/import-csv")
def api_import_csv():
    filename = request.args.get("file", "")
    city = request.args.get("city")

    if not filename:
        return jsonify({"error": "Please provide a file parameter."}), 400

    filepath = os.path.join(config.DATA_DIR, filename)

    try:
        result = data_import_service.import_csv(filepath, city)
        return jsonify(result)
    except DataImportError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Import failed: {str(e)}"}), 500

@app.route("/api/import-report")
def api_import_report():
    report = data_import_service.get_import_report()
    return jsonify({"files": report})

@app.route("/api/export-csv")
def api_export_csv():
    import io
    import csv as csv_module

    city = request.args.get("city")
    pollutant = request.args.get("pollutant")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    measurements = db.get_measurements(
        city=city,
        pollutant=pollutant,
        start_date=start_date,
        end_date=end_date,
    )

    if not measurements:
        return jsonify({"error": "No data to export."}), 404

    output = io.StringIO()
    writer = csv_module.DictWriter(
        output,
        fieldnames=["city", "latitude", "longitude", "station", "pollutant", "value", "unit", "timestamp", "source"],
    )
    writer.writeheader()
    writer.writerows(measurements)

    from flask import Response
    filename = f"air_quality_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

if __name__ == "__main__":
    db.init_db()

    print("=" * 60)
    print("Air Quality Monitoring and Prediction Dashboard")
    print("=" * 60)
    print(f"Database: {config.DATABASE_PATH}")
    print(f"Server: http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"Access from network: http://<your-ip>:{config.SERVER_PORT}")
    print(f"Threads: {config.SERVER_THREADS}")
    print(f"Live refresh interval: {config.LIVE_REFRESH_INTERVAL}s")
    print("=" * 60)

    if config.FLASK_DEBUG:
        app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, debug=True, threaded=True)
    else:
        from waitress import serve
        serve(
            app,
            host=config.SERVER_HOST,
            port=config.SERVER_PORT,
            threads=config.SERVER_THREADS,
        )

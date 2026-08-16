import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from config.config import config


def get_db_path():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    return config.DATABASE_PATH


def init_db():
    db_path = get_db_path()
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

    with open(schema_path, "r") as f:
        schema_sql = f.read()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_measurement(city, latitude, longitude, station, pollutant, value, unit, timestamp, source):
    with get_db() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO measurements
            (city, latitude, longitude, station, pollutant, value, unit, timestamp, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (city, latitude, longitude, station, pollutant, value, unit, timestamp, source),
        )


def insert_measurements_bulk(measurements):
    if not measurements:
        return 0

    with get_db() as db:
        db.executemany(
            """
            INSERT OR IGNORE INTO measurements
            (city, latitude, longitude, station, pollutant, value, unit, timestamp, source)
            VALUES (:city, :latitude, :longitude, :station, :pollutant, :value, :unit, :timestamp, :source)
            """,
            measurements,
        )
        return db.total_changes


def get_measurements(city=None, pollutant=None, start_date=None, end_date=None, limit=None):
    query = "SELECT * FROM measurements WHERE 1=1"
    params = []

    if city:
        query += " AND city = ?"
        params.append(city)

    if pollutant:
        query += " AND pollutant = ?"
        params.append(pollutant)

    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)

    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)

    query += " ORDER BY timestamp"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with get_db() as db:
        rows = db.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_latest_measurements(city=None):
    query = """
        SELECT m.* FROM measurements m
        INNER JOIN (
            SELECT pollutant, MAX(timestamp) as max_ts
            FROM measurements
            WHERE 1=1
        """
    params = []
    if city:
        query += " AND city = ?"
        params.append(city)
    query += """
            GROUP BY pollutant
        ) latest ON m.pollutant = latest.pollutant AND m.timestamp = latest.max_ts
    """
    if city:
        query += " WHERE m.city = ?"
        params.append(city)

    with get_db() as db:
        rows = db.execute(query, params).fetchall()
        return {row["pollutant"]: dict(row) for row in rows}


def get_cities():
    with get_db() as db:
        rows = db.execute("SELECT DISTINCT city FROM measurements ORDER BY city").fetchall()
        return [row["city"] for row in rows]


def get_available_pollutants(city=None):
    query = "SELECT DISTINCT pollutant FROM measurements"
    params = []
    if city:
        query += " WHERE city = ?"
        params.append(city)
    query += " ORDER BY pollutant"

    with get_db() as db:
        rows = db.execute(query, params).fetchall()
        return [row["pollutant"] for row in rows]


def get_date_range(city=None):
    query = "SELECT MIN(timestamp) as min_ts, MAX(timestamp) as max_ts FROM measurements"
    params = []
    if city:
        query += " WHERE city = ?"
        params.append(city)

    with get_db() as db:
        row = db.execute(query, params).fetchone()
        return {"min": row["min_ts"], "max": row["max_ts"]}


def get_measurement_count(city=None):
    query = "SELECT COUNT(*) as count FROM measurements"
    params = []
    if city:
        query += " WHERE city = ?"
        params.append(city)

    with get_db() as db:
        row = db.execute(query, params).fetchone()
        return row["count"]


def insert_prediction(city, predicted_pm25, model_name, prediction_time):
    with get_db() as db:
        db.execute(
            """
            INSERT INTO predictions (city, predicted_pm25, model_name, prediction_time)
            VALUES (?, ?, ?, ?)
            """,
            (city, predicted_pm25, model_name, prediction_time),
        )


def get_predictions(city=None, limit=None):
    query = "SELECT * FROM predictions"
    params = []
    if city:
        query += " WHERE city = ?"
        params.append(city)
    query += " ORDER BY created_at DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with get_db() as db:
        rows = db.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def insert_model_metrics(model_name, mae, rmse, r2):
    with get_db() as db:
        db.execute(
            """
            INSERT INTO model_metrics (model_name, mae, rmse, r2)
            VALUES (?, ?, ?, ?)
            """,
            (model_name, mae, rmse, r2),
        )


def get_model_metrics():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM model_metrics ORDER BY trained_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_latest_metrics_for_model(model_name):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM model_metrics WHERE model_name = ? ORDER BY trained_at DESC LIMIT 1",
            (model_name,),
        ).fetchone()
        return dict(row) if row else None


def log_sync(city, status, records_added=0, message=""):
    with get_db() as db:
        db.execute(
            """
            INSERT INTO sync_log (city, status, records_added, message)
            VALUES (?, ?, ?, ?)
            """,
            (city, status, records_added, message),
        )


def get_sync_logs(limit=10):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM sync_log ORDER BY synced_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_last_sync_time(city=None):
    query = "SELECT MAX(synced_at) as last_sync FROM sync_log WHERE status = 'success'"
    params = []
    if city:
        query += " AND city = ?"
        params.append(city)

    with get_db() as db:
        row = db.execute(query, params).fetchone()
        return row["last_sync"] if row else None


def cache_location(location):
    with get_db() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO locations
            (name, country, country_code, latitude, longitude, population, timezone, admin1, admin2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                location.get("name", ""),
                location.get("country"),
                location.get("country_code"),
                location.get("latitude"),
                location.get("longitude"),
                location.get("population"),
                location.get("timezone"),
                location.get("admin1"),
                location.get("admin2"),
            ),
        )


def search_cached_locations(query, limit=10):
    with get_db() as db:
        rows = db.execute(
            """
            SELECT * FROM locations
            WHERE name LIKE ? OR admin1 LIKE ? OR admin2 LIKE ?
            ORDER BY population DESC NULLS LAST
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [dict(row) for row in rows]


def get_cached_location_count():
    with get_db() as db:
        row = db.execute("SELECT COUNT(*) as count FROM locations").fetchone()
        return row["count"]


def get_data_quality_report(city=None):
    report = {
        "total_records": get_measurement_count(city),
        "cities": get_cities(),
        "date_range": get_date_range(city),
        "available_pollutants": get_available_pollutants(city),
    }

    query = "SELECT COUNT(*) as count FROM measurements WHERE value IS NULL"
    params = []
    if city:
        query += " AND city = ?"
        params.append(city)
    with get_db() as db:
        row = db.execute(query, params).fetchone()
        report["missing_values"] = row["count"]

    query = """
        SELECT COUNT(*) as count FROM (
            SELECT city, pollutant, timestamp, source, COUNT(*) as cnt
            FROM measurements
            WHERE 1=1
    """
    if city:
        query += " AND city = ?"
    query += """
            GROUP BY city, pollutant, timestamp, source
            HAVING cnt > 1
        )
    """
    with get_db() as db:
        row = db.execute(query, params).fetchone()
        report["duplicate_records"] = row["count"]

    return report
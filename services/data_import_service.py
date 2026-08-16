
import os
from datetime import datetime

import pandas as pd
import numpy as np

from config.config import config
from database import db

class DataImportError(Exception):
    pass

class DataImportService:

    COLUMN_MAPPINGS = {
        "date": ["date", "datetime", "timestamp", "time", "Date", "DateTime", "Timestamp", "local_time", "Local Time"],
        "city": ["city", "City", "location", "Location", "station", "Station", "area", "Area"],
        "pm2_5": ["pm2.5", "pm25", "PM2.5", "pm2_5", "PM25", "PM2.5 (ug/m3)", "pm2_5_value"],
        "pm10": ["pm10", "PM10", "PM10 (ug/m3)", "pm10_value"],
        "nitrogen_dioxide": ["no2", "NO2", "nitrogen_dioxide", "NO2 (ug/m3)", "no2_value"],
        "sulphur_dioxide": ["so2", "SO2", "sulphur_dioxide", "SO2 (ug/m3)", "so2_value"],
        "carbon_monoxide": ["co", "CO", "carbon_monoxide", "CO (mg/m3)", "co_value"],
        "ozone": ["o3", "O3", "ozone", "O3 (ug/m3)", "o3_value"],
    }

    def __init__(self):
        self.data_dir = config.DATA_DIR

    def find_csv_files(self):
        if not os.path.exists(self.data_dir):
            return []

        csv_files = []
        for file in os.listdir(self.data_dir):
            if file.endswith(".csv"):
                csv_files.append(os.path.join(self.data_dir, file))

        return csv_files

    def detect_columns(self, df):
        mapping = {}
        columns_lower = {col.lower(): col for col in df.columns}

        for standard_name, possible_names in self.COLUMN_MAPPINGS.items():
            for possible in possible_names:
                if possible in df.columns:
                    mapping[standard_name] = possible
                    break
                elif possible.lower() in columns_lower:
                    mapping[standard_name] = columns_lower[possible.lower()]
                    break

        return mapping

    def clean_data(self, df, mapping):
        df = df.copy()

        if "date" in mapping:
            date_col = mapping["date"]
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=[date_col])

        pollutant_cols = ["pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "carbon_monoxide", "ozone"]
        for col in pollutant_cols:
            if col in mapping:
                actual_col = mapping[col]
                df[actual_col] = pd.to_numeric(df[actual_col], errors="coerce")

        df = df.drop_duplicates()

        pollutant_actual_cols = [mapping[col] for col in pollutant_cols if col in mapping]
        if pollutant_actual_cols:
            df = df.dropna(subset=pollutant_actual_cols, how="all")

        return df

    def import_csv(self, filepath, city_name=None):
        if not os.path.exists(filepath):
            raise DataImportError(f"File not found: {filepath}")

        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            raise DataImportError(f"Failed to read CSV file: {str(e)}")

        if df.empty:
            raise DataImportError("CSV file is empty.")

        mapping = self.detect_columns(df)

        if "date" not in mapping:
            raise DataImportError(
                "Could not detect a date/time column. "
                "Please ensure your CSV has a column named 'date', 'datetime', or 'timestamp'."
            )

        df = self.clean_data(df, mapping)

        if df.empty:
            raise DataImportError("No valid data rows after cleaning.")

        if not city_name:
            if "city" in mapping:
                city_name = str(df[mapping["city"]].iloc[0])
            else:
                city_name = os.path.splitext(os.path.basename(filepath))[0]

        measurements = []
        date_col = mapping["date"]
        pollutant_cols = ["pm2_5", "pm10", "nitrogen_dioxide", "sulphur_dioxide", "carbon_monoxide", "ozone"]

        for _, row in df.iterrows():
            timestamp = row[date_col]
            if pd.isna(timestamp):
                continue

            timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S") if hasattr(timestamp, "strftime") else str(timestamp)

            for col in pollutant_cols:
                if col in mapping:
                    actual_col = mapping[col]
                    value = row.get(actual_col)
                    if pd.notna(value):
                        measurements.append({
                            "city": city_name,
                            "latitude": 0.0,
                            "longitude": 0.0,
                            "station": "Kaggle dataset",
                            "pollutant": col,
                            "value": float(value),
                            "unit": "µg/m³",
                            "timestamp": timestamp_str,
                            "source": "Kaggle historical dataset",
                        })

        if not measurements:
            raise DataImportError("No valid pollutant measurements found in the CSV.")

        records_added = db.insert_measurements_bulk(measurements)

        return {
            "success": True,
            "file": os.path.basename(filepath),
            "city": city_name,
            "records_added": records_added,
            "total_rows": len(df),
            "columns_detected": mapping,
            "message": f"Successfully imported {records_added} measurements for {city_name}",
        }

    def get_import_report(self):
        csv_files = self.find_csv_files()
        report = []

        for filepath in csv_files:
            try:
                df = pd.read_csv(filepath, nrows=5)
                mapping = self.detect_columns(df)
                report.append({
                    "file": os.path.basename(filepath),
                    "path": filepath,
                    "columns": list(df.columns),
                    "detected_mapping": mapping,
                    "preview_rows": len(df),
                })
            except Exception as e:
                report.append({
                    "file": os.path.basename(filepath),
                    "path": filepath,
                    "error": str(e),
                })

        return report

data_import_service = DataImportService()
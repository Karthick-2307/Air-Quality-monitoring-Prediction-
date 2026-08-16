
import os
import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from config.config import config
from database import db

class PredictionServiceError(Exception):
    pass

class PredictionService:

    def __init__(self):
        self.models = {}
        self.feature_importance = {}
        self.metrics = {}

    def get_training_data(self, city):
        measurements = db.get_measurements(city=city)

        if not measurements:
            return None

        df = pd.DataFrame(measurements)

        pivot = df.pivot_table(
            index="timestamp",
            columns="pollutant",
            values="value",
            aggfunc="mean",
        ).reset_index()

        pivot["timestamp"] = pd.to_datetime(pivot["timestamp"])

        pivot = pivot.sort_values("timestamp").reset_index(drop=True)

        if "pm2_5" not in pivot.columns:
            return None

        pivot = pivot.dropna(subset=["pm2_5"])

        if len(pivot) < 50:
            return None

        return pivot

    def engineer_features(self, df):
        df = df.copy()

        df["hour"] = df["timestamp"].dt.hour
        df["day"] = df["timestamp"].dt.day
        df["month"] = df["timestamp"].dt.month
        df["day_of_week"] = df["timestamp"].dt.dayofweek

        df["pm2_5_lag_1"] = df["pm2_5"].shift(1)
        df["pm2_5_lag_3"] = df["pm2_5"].shift(3)
        df["pm2_5_lag_6"] = df["pm2_5"].shift(6)
        df["pm2_5_lag_24"] = df["pm2_5"].shift(24)

        df["pm2_5_rolling_3"] = df["pm2_5"].shift(1).rolling(window=3, min_periods=1).mean()
        df["pm2_5_rolling_6"] = df["pm2_5"].shift(1).rolling(window=6, min_periods=1).mean()

        df = df.dropna()

        return df

    def train_models(self, city):
        df = self.get_training_data(city)
        if df is None:
            raise PredictionServiceError(
                "Insufficient historical data to generate a reliable prediction. "
                "Please synchronize data first."
            )

        df = self.engineer_features(df)

        if len(df) < 50:
            raise PredictionServiceError(
                "Insufficient historical data to generate a reliable prediction. "
                "Please synchronize data first."
            )

        feature_cols = [
            "pm10", "nitrogen_dioxide", "sulphur_dioxide", "carbon_monoxide", "ozone",
            "hour", "day", "month", "day_of_week",
            "pm2_5_lag_1", "pm2_5_lag_3", "pm2_5_lag_6", "pm2_5_lag_24",
            "pm2_5_rolling_3", "pm2_5_rolling_6",
        ]

        available_features = [col for col in feature_cols if col in df.columns]

        if len(available_features) < 5:
            raise PredictionServiceError(
                "Insufficient feature data for training. Please synchronize more data."
            )

        X = df[available_features].values
        y = df["pm2_5"].values

        split_idx = int(len(df) * (1 - config.ML_TEST_SPLIT))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        if len(X_train) < 30 or len(X_test) < 10:
            raise PredictionServiceError(
                "Insufficient data for train/test split. Please synchronize more data."
            )

        results = {}
        models = {}

        lr = LinearRegression()
        lr.fit(X_train, y_train)
        lr_pred = lr.predict(X_test)
        lr_mae = mean_absolute_error(y_test, lr_pred)
        lr_rmse = np.sqrt(mean_squared_error(y_test, lr_pred))
        lr_r2 = r2_score(y_test, lr_pred)

        models["Linear Regression"] = lr
        results["Linear Regression"] = {
            "mae": lr_mae,
            "rmse": lr_rmse,
            "r2": lr_r2,
            "predictions": lr_pred,
        }

        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=config.ML_RANDOM_STATE,
            n_jobs=-1,
        )
        rf.fit(X_train, y_train)
        rf_pred = rf.predict(X_test)
        rf_mae = mean_absolute_error(y_test, rf_pred)
        rf_rmse = np.sqrt(mean_squared_error(y_test, rf_pred))
        rf_r2 = r2_score(y_test, rf_pred)

        models["Random Forest"] = rf
        results["Random Forest"] = {
            "mae": rf_mae,
            "rmse": rf_rmse,
            "r2": rf_r2,
            "predictions": rf_pred,
        }

        self.models = models
        self.feature_importance = {
            "features": available_features,
            "importance": rf.feature_importances_.tolist(),
        }

        for model_name, metrics in results.items():
            db.insert_model_metrics(model_name, metrics["mae"], metrics["rmse"], metrics["r2"])

        best_model = min(results, key=lambda k: results[k]["rmse"])

        actual_vs_predicted = self._build_actual_vs_predicted_chart(
            y_test, results["Linear Regression"]["predictions"], results["Random Forest"]["predictions"]
        )
        feature_importance_chart = self._build_feature_importance_chart(
            available_features, rf.feature_importances_
        )

        return {
            "city": city,
            "best_model": best_model,
            "metrics": [
                {
                    "model_name": name,
                    "mae": m["mae"],
                    "rmse": m["rmse"],
                    "r2": m["r2"],
                    "best": name == best_model,
                }
                for name, m in results.items()
            ],
            "actual_vs_predicted_chart": actual_vs_predicted,
            "feature_importance_chart": feature_importance_chart,
            "test_size": len(y_test),
            "train_size": len(y_train),
            "features_used": available_features,
        }

    def predict_future(self, city, period="next_day"):
        training_results = self.train_models(city)

        df = self.get_training_data(city)
        df = self.engineer_features(df)

        latest = df.iloc[-1:].copy()

        if period == "next_hour":
            hours_ahead = 1
        elif period == "next_day":
            hours_ahead = 24
        elif period == "next_3_days":
            hours_ahead = 72
        else:
            hours_ahead = 24

        best_model_name = training_results["best_model"]
        model = self.models[best_model_name]

        feature_cols = training_results["features_used"]

        X_future = latest[feature_cols].values

        predictions = []
        current_features = X_future.copy()

        for i in range(hours_ahead):
            pred = model.predict(current_features)[0]
            predictions.append(max(0, pred))

            if "pm2_5_lag_1" in feature_cols:
                idx = feature_cols.index("pm2_5_lag_1")
                current_features[0, idx] = pred
            if "pm2_5_lag_3" in feature_cols:
                idx = feature_cols.index("pm2_5_lag_3")
                if i >= 2:
                    current_features[0, idx] = predictions[-3]
            if "pm2_5_lag_6" in feature_cols:
                idx = feature_cols.index("pm2_5_lag_6")
                if i >= 5:
                    current_features[0, idx] = predictions[-6]
            if "pm2_5_lag_24" in feature_cols:
                idx = feature_cols.index("pm2_5_lag_24")
                if i >= 23:
                    current_features[0, idx] = predictions[-24]

        final_prediction = predictions[-1] if predictions else None

        if final_prediction is not None:
            db.insert_prediction(
                city,
                final_prediction,
                best_model_name,
                datetime.now().isoformat(),
            )

        return {
            "city": city,
            "prediction": final_prediction,
            "model": best_model_name,
            "period": period,
            "hours_ahead": hours_ahead,
            "note": f"Predicted PM2.5 for {city} using {best_model_name}. "
                    "This is an ML estimate, not an official forecast.",
            "metrics": training_results["metrics"],
            "actual_vs_predicted_chart": training_results["actual_vs_predicted_chart"],
            "feature_importance_chart": training_results["feature_importance_chart"],
        }

    def _build_actual_vs_predicted_chart(self, y_test, lr_pred, rf_pred):
        n = len(y_test)
        x = list(range(n))

        return {
            "data": [
                {
                    "x": x,
                    "y": y_test.tolist(),
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "Actual",
                    "line": {"color": "#2c3e50", "width": 2},
                },
                {
                    "x": x,
                    "y": lr_pred.tolist(),
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "Linear Regression",
                    "line": {"color": "#3498db", "width": 2, "dash": "dash"},
                },
                {
                    "x": x,
                    "y": rf_pred.tolist(),
                    "type": "scatter",
                    "mode": "lines+markers",
                    "name": "Random Forest",
                    "line": {"color": "#e74c3c", "width": 2, "dash": "dot"},
                },
            ],
            "layout": {
                "title": "Actual vs Predicted PM2.5 (Test Set)",
                "xaxis": {"title": "Sample Index"},
                "yaxis": {"title": "PM2.5 (µg/m³)"},
                "legend": {"x": 0, "y": 1},
                "height": 400,
            },
        }

    def _build_feature_importance_chart(self, features, importance):
        pairs = sorted(zip(features, importance), key=lambda x: x[1], reverse=True)
        sorted_features = [p[0] for p in pairs]
        sorted_importance = [p[1] for p in pairs]

        return {
            "data": [
                {
                    "x": sorted_importance,
                    "y": sorted_features,
                    "type": "bar",
                    "orientation": "h",
                    "marker": {"color": "#3498db"},
                }
            ],
            "layout": {
                "title": "Feature Importance (Random Forest)",
                "xaxis": {"title": "Importance"},
                "yaxis": {"title": "Feature"},
                "height": 400,
            },
        }

prediction_service = PredictionService()

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from config.config import config
from database import db

def load_training_data(city):
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

def engineer_features(df):
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

    return df.dropna()

def train_models(city):
    df = load_training_data(city)
    if df is None:
        print(f"❌ Insufficient data for {city}")
        return None

    df = engineer_features(df)

    feature_cols = [
        "pm10", "nitrogen_dioxide", "sulphur_dioxide", "carbon_monoxide", "ozone",
        "hour", "day", "month", "day_of_week",
        "pm2_5_lag_1", "pm2_5_lag_3", "pm2_5_lag_6", "pm2_5_lag_24",
        "pm2_5_rolling_3", "pm2_5_rolling_6",
    ]
    available_features = [col for col in feature_cols if col in df.columns]

    X = df[available_features].values
    y = df["pm2_5"].values

    split_idx = int(len(df) * (1 - config.ML_TEST_SPLIT))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_metrics = {
        "mae": mean_absolute_error(y_test, lr_pred),
        "rmse": np.sqrt(mean_squared_error(y_test, lr_pred)),
        "r2": r2_score(y_test, lr_pred),
    }

    rf = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=config.ML_RANDOM_STATE,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_metrics = {
        "mae": mean_absolute_error(y_test, rf_pred),
        "rmse": np.sqrt(mean_squared_error(y_test, rf_pred)),
        "r2": r2_score(y_test, rf_pred),
    }

    db.insert_model_metrics("Linear Regression", lr_metrics["mae"], lr_metrics["rmse"], lr_metrics["r2"])
    db.insert_model_metrics("Random Forest", rf_metrics["mae"], rf_metrics["rmse"], rf_metrics["r2"])

    print(f"✅ Trained models for {city}")
    print(f"   Linear Regression: MAE={lr_metrics['mae']:.2f}, RMSE={lr_metrics['rmse']:.2f}, R²={lr_metrics['r2']:.4f}")
    print(f"   Random Forest:     MAE={rf_metrics['mae']:.2f}, RMSE={rf_metrics['rmse']:.2f}, R²={rf_metrics['r2']:.4f}")

    return {
        "city": city,
        "linear_regression": lr_metrics,
        "random_forest": rf_metrics,
        "features": available_features,
        "train_size": len(X_train),
        "test_size": len(X_test),
    }

if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else None

    if city:
        train_models(city)
    else:
        cities = db.get_cities()
        for c in cities:
            train_models(c)
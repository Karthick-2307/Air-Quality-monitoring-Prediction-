CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    station TEXT,
    pollutant TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(city, pollutant, timestamp, source)
);

CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    predicted_pm25 REAL NOT NULL,
    model_name TEXT NOT NULL,
    prediction_time TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS model_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    mae REAL NOT NULL,
    rmse REAL NOT NULL,
    r2 REAL NOT NULL,
    trained_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city TEXT NOT NULL,
    status TEXT NOT NULL,
    records_added INTEGER DEFAULT 0,
    message TEXT,
    synced_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    country TEXT,
    country_code TEXT,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    population INTEGER,
    timezone TEXT,
    admin1 TEXT,
    admin2 TEXT,
    searched_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(name, country, latitude, longitude)
);

CREATE INDEX IF NOT EXISTS idx_measurements_city ON measurements(city);
CREATE INDEX IF NOT EXISTS idx_measurements_timestamp ON measurements(timestamp);
CREATE INDEX IF NOT EXISTS idx_measurements_pollutant ON measurements(pollutant);
CREATE INDEX IF NOT EXISTS idx_predictions_city ON predictions(city);
CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(name);
CREATE INDEX IF NOT EXISTS idx_locations_country ON locations(country);
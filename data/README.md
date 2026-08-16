# Data Directory

This directory stores the SQLite database and any CSV files for import.

## Database

The SQLite database (air_quality.db) is created automatically when the application first runs.

## Kaggle Dataset Import

To import a Kaggle air-quality dataset:

1. Download your Kaggle CSV file
2. Place it in this directory (e.g., data/your_dataset.csv)
3. Use the API endpoint: GET http://127.0.0.1:5000/api/import-csv?file=your_dataset.csv

### Column Mapping

The importer automatically detects columns with these names:

- date: date, datetime, timestamp, time, Date, DateTime
- city: city, City, location, station, area
- pm2_5: pm2.5, PM2.5, pm25, pm2_5
- pm10: pm10, PM10
- no2: no2, NO2, nitrogen_dioxide
- so2: so2, SO2, sulphur_dioxide
- co: co, CO, carbon_monoxide
- o3: o3, O3, ozone

If your dataset uses different column names, edit the COLUMN_MAPPINGS dict in services/data_import_service.py.
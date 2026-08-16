# Air Quality Monitoring and Prediction Dashboard

A locally hosted, offline-first web application for monitoring and predicting air quality. Built with Flask, SQLite, and scikit-learn.

## Project Overview

This intermediate-level college mini-project demonstrates a full-stack web application that:
- Retrieves real air-quality data from the Open-Meteo API
- Stores data locally in SQLite for offline use
- Analyzes historical pollution trends with interactive charts
- Trains machine learning models to predict PM2.5 levels
- Provides optional AI-powered explanations

## Problem Statement

Air pollution is a major health concern, especially in Indian cities. This project provides a tool to monitor real air quality, analyze historical trends, and predict future PM2.5 levels using machine learning.

## Features

- Real-time air quality monitoring (Open-Meteo API)
- Browser geolocation for automatic location detection
- City search for manual location selection
- Indian AQI calculation (CPCB methodology)
- Historical data analysis with Plotly charts
- Machine learning predictions (Linear Regression & Random Forest)
- Model evaluation (MAE, RMSE, R²)
- Offline-first architecture with SQLite caching
- Data synchronization with graceful fallback
- Optional AI-powered explanations
- CSV data export

## Architecture

```
User → Flask App → Open-Meteo API → Validate → Store in SQLite → Display Dashboard
```

When offline:
```
User → Flask App → SQLite cached data → Display most recent data → Show "Offline Mode"
```

## Technology Stack

- **Backend:** Python, Flask
- **Frontend:** HTML5, CSS3, JavaScript, Plotly.js
- **Data Processing:** Pandas, NumPy
- **Machine Learning:** Scikit-learn
- **Database:** SQLite
- **External API:** Open-Meteo Air Quality API
- **AI (optional):** Google Gemini API

## Dataset Information

### Open-Meteo API
- No API key required
- CAMS atmospheric-model output (modeled estimate, not ground sensor)
- 11 km resolution over Europe, 45 km globally
- Pollutants: PM2.5, PM10, CO, NO2, SO2, O3

### Kaggle Dataset (Optional)
Place your Kaggle CSV in the `data/` directory. The importer auto-detects column names. See `data/README.md` for details.

## Installation

### Prerequisites
- Python 3.8+
- VS Code (or any code editor)

### Setup

1. **Clone or create the project directory:**
```bash
cd air_quality_monitor
```

2. **Create a virtual environment:**
```bash
python -m venv venv
```

3. **Activate the environment:**
   - Windows:
   ```bash
   venv\Scripts\activate
   ```
   - macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

5. **Configure environment variables:**
   - Copy `.env.example` to `.env`
   - Add your AI API key (optional)

6. **Run the application:**
```bash
python app.py
```

7. **Open in browser:**
```
http://127.0.0.1:5000
```

## Environment Variables

Create a `.env` file in the project root:

```env
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_secret_key
AI_API_KEY=your_gemini_api_key  # Optional
AI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent
```

## Database Setup

The SQLite database is created automatically on first run at `data/air_quality.db`.

Tables:
- `measurements` - air quality measurements
- `predictions` - ML predictions
- `model_metrics` - model evaluation metrics
- `sync_log` - synchronization history

## Kaggle Dataset Import

1. Place your CSV in `data/`
2. Import via API:
```
GET http://127.0.0.1:5000/api/import-csv?file=your_dataset.csv
```

## ML Training

Train models from the command line:
```bash
python -m ml.train_model Delhi
```

Or train for all cities:
```bash
python -m ml.train_model
```

Evaluate models:
```bash
python -m ml.evaluate
```

## Running the Application

```bash
python app.py
```

Open: http://127.0.0.1:5000

## Offline Mode

The application automatically detects internet connectivity:
- **Online:** Fetches live data from Open-Meteo
- **Offline:** Uses cached data from SQLite
- **No data:** Shows "No air-quality data is available offline"

## AI Integration

1. Get a free Gemini API key at https://aistudio.google.com
2. Add it to `.env`:
```
AI_API_KEY=your_key_here
```
3. Use the AI Assistant page for explanations

The AI key is never exposed to the frontend.

## Limitations

- Open-Meteo data is a modeled estimate, not ground-sensor readings
- Indian AQI is computed manually using CPCB methodology
- ML predictions are educational estimates, not official forecasts
- Browser geolocation requires HTTPS or localhost
- AI responses are for general awareness, not medical advice

## Future Enhancements

- IoT air-quality sensors
- Mobile application
- Weather API integration
- Advanced time-series models (LSTM, Prophet)
- Pollution heat maps
- Regional-language support
- SMS/email alerts
- Government monitoring-data integration
- Real-time sensor networks
- Cloud deployment

## License

This project is for educational purposes.
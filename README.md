# Trucking Route Manager

## Overview

This API provides a comprehensive Electronic Logging Device (ELD) system for tracking driver hours, trips, and compliance with Hours of Service (HOS) regulations. The system includes features for route calculation, status logging, and daily log generation.

## Features

- **Trip Management**: Calculate optimal routes with distance and duration estimates
- **Status Tracking**: Record driver status changes (Driving, On Duty, Off Duty, Sleeper Berth)
- **Daily Logs**: Automatic generation of compliant daily logs
- **HOS Compliance**: Enforcement of driving hour limits
- **Visualization**: Interactive maps of routes with waypoints

## API Endpoints

### Trip Management

#### `POST /trips/calculate_route/`
Calculate a route between current location, pickup, and dropoff points.

**Request Body:**
```json
{
  "current_location": [longitude, latitude],
  "pickup_location": [longitude, latitude],
  "dropoff_location": [longitude, latitude]
}
```

**Response:**
```json
{
  "route_geojson": {...},
  "total_distance_km": 123.45,
  "total_duration_hours": 2.5,
  "waypoints": [...],
  "rest_stops": [...],
  "map_html": "...",
  "trip_id": 1
}
```

### Status Logging

#### `POST /statuslogs/`
Record a new status change.

**Request Body:**
```json
{
  "status": "driving|on_duty|off_duty|sleeper_berth",
  "time": "ISO-8601 timestamp"
}
```

**Response:**
```json
{
  "id": 1,
  "status": "driving",
  "time": "2025-03-28T12:00:00",
  "end_time": null
}
```

#### `GET /statuslogs/`
Get all status logs for the current day.

### Daily Logs

#### `GET /dailylogs/`
Get all daily logs (optionally filtered by date parameter).

**Query Parameter:**
- `date`: Filter logs by date (YYYY-MM-DD format)

#### `POST /dailylogs/`
Create a new daily log (automatically calculates hours and mileage).

#### `GET /dailylogs/generate_report/`
Generate a detailed daily log report for today.

## Models

### Trip
- Tracks route information including:
  - Start/end coordinates
  - Distance (km) and duration (hours)
  - Start/end times
  - Calculated route geometry

### StatusLog
- Records driver status changes:
  - Status type (Driving, On Duty, Off Duty, Sleeper Berth)
  - Timestamps for status changes
  - Duration calculations

### DailyLog
- Aggregates daily driving information:
  - Driving hours
  - On-duty hours
  - Off-duty hours
  - Sleeper berth hours
  - Total miles driven
  - Cumulative mileage

## Setup Instructions

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables**:
   Create a `.env` file with:
   ```
   OPENROUTESERVICE_API_KEY=your_api_key_here
   ```

3. **Database setup**:
   ```bash
   python manage.py migrate
   ```

4. **Run the server**:
   ```bash
   python manage.py runserver
   ```

## Technical Details

### Route Calculation
- Uses OpenRouteService API for route optimization
- Automatically calculates rest stops every 4 hours of driving
- Generates interactive Folium maps with route visualization

### Hours of Service Compliance
- Enforces 11-hour daily driving limit
- Tracks all status changes with duration calculations
- Prevents overlapping or invalid status entries

### Daily Log Generation
- Automatically calculates:
  - Hours in each status category
  - Miles driven
  - Cumulative mileage
- Generates PDF-ready reports

## Example Usage

### Calculating a Route
```python
import requests

response = requests.post(
    "http://localhost:8000/api/trips/calculate_route/",
    json={
        "current_location": [-118.243683, 34.052235],  # Los Angeles
        "pickup_location": [-117.161084, 32.715738],   # San Diego
        "dropoff_location": [-121.4944, 38.5816]       # Sacramento
    }
)
print(response.json())
```

### Recording a Status Change
```python
response = requests.post(
    "http://localhost:8000/api/statuslogs/",
    json={
        "status": "driving",
        "time": "2025-03-28T08:00:00Z"
    }
)
print(response.json())
```

### Generating a Daily Report
```python
response = requests.get("http://localhost:8000/api/dailylogs/generate_report/")
print(response.json())
```

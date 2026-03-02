📡 RRH62000 Indoor Air Quality Monitoring System

A real-time indoor air quality monitoring system built around the RRH62000 sensor, providing continuous environmental monitoring, live visualization, and exposure-aware alerting.

🏗 System Architecture
RRH62000 Sensor
       │
       ▼
Sensor Logger
 ├──► rrh62000_YYYY-MM-DD_HH.csv
 └──► latest.csv  (symlink to current hour file)
       │
       ├──► Watchdog
       │     └──► alerts_YYYYMMDD_HH.csv
       │
       └──► Dashboard (live graphs + alerts)

📁 File Structure
project/
├── sensor_logger.py
├── watchdog.py
├── dashboard.py
├── rrh62000_YYYY-MM-DD_HH.csv
├── latest.csv
└── alerts/
    └── alerts_YYYYMMDD_HH.csv

1️⃣ Sensor Logger

Purpose:
Reads data from the RRH62000 sensor over I²C and logs it to rotating hourly CSV files.

Key Features:

1 Hz data acquisition

Automatic hourly file rotation

Header auto-creation

Maintains latest.csv symlink

Calculates custom EU-weighted IAQ index (IAQ_CUSTOM)

Output Files:

Type	Example
Hourly Data Log	rrh62000_2026-03-02_14.csv
Live Pointer	latest.csv → rrh62000_2026-03-02_14.csv

All other services read latest.csv for consistency.

IAQ_CUSTOM Calculation:

Parameter	Reference	Weight
PM2.5	25 µg/m³	40%
PM10	50 µg/m³	20%
TVOC	300 µg/m³	20%
CO₂	1000 ppm	20%

Index Scale:

0–40 → Excellent

40–70 → Good

70–100 → Moderate

100–150 → Poor

150+ → Very Poor

2️⃣ Watchdog

Purpose:
Continuously monitors live data and detects threshold violations.

How It Works:

Reads latest.csv

Computes rolling average (last N samples)

Compares against predefined limits

Tracks exposure duration

Logs alerts if limits are exceeded

Alert Logging:

Stored hourly in alerts/alerts_YYYYMMDD_HH.csv

Each alert entry includes:

Timestamp

Parameter name

Rolling average

Limit value

Exposure duration

Sample window size

GPIO Alert:

LED flashes on configured GPIO pin if any parameter exceeds limits

Alert entry written to CSV

3️⃣ Dashboard

Purpose:
Live graphical display of:

Particulate levels

Gas concentrations

Temperature & humidity

IAQ_CUSTOM

Active alerts

Features:

Dark theme

Live updating (~1 second interval)

Reads only last N rows (performance optimized)

Bottom-corner alert panel

Follows hourly files via latest.csv

Alert Display Example:

ALERTS: 
PM2.5_KCl = 45.3 (limit 20) [120s]
eCO2_ppm = 1300 (limit 1000) [60s]


Alerts clear automatically when conditions return to normal.

🔄 Hourly Rotation Mechanism

Every hour, the Sensor Logger:

Creates a new hourly CSV file

Writes header

Updates latest.csv symlink

Watchdog and Dashboard automatically follow the new file — no restart required.

⚙ Configuration Points
Script	Configurable Parameters
Logger	LOG_INTERVAL, IAQ weighting, I²C bus & address
Watchdog	SAMPLE_WINDOW, CHECK_INTERVAL, Limit thresholds, GPIO pin
Dashboard	MAX_POINTS, Update interval, Grid layout, Colour map, Alert position
🛠 Recommended Deployment

Run all three services via systemd:

rrh62000-stack.service

rrh62000-dashboard.service

Start order:

Logger

Watchdog

Dashboard

🧠 Summary

The RRH62000 Indoor Air Quality Monitoring System provides:

Continuous environmental monitoring

Health-weighted air quality modelling

Live visualisation

Exposure-aware alerting

Robust hourly file rotation

Efficient runtime behavior

Long-term unattended operation on embedded hardware📡 RRH62000 Indoor Air Quality Monitoring System
Overview

This project is a real-time indoor air quality monitoring system built around the RRH62000 sensor.

It consists of three coordinated Python services:

Sensor Logger – Collects and logs raw sensor data

Watchdog – Monitors values and generates alerts

Dashboard – Displays live graphs and alerts

All services operate together to provide continuous environmental monitoring.

🏗 System Architecture
RRH62000 Sensor
        │
        ▼
Sensor Logger  ─────►  rrh62000_YYYY-MM-DD_HH.csv
        │
        └────► latest.csv (symlink to current hour file)
                        │
                        ├────► Watchdog
                        │          └──► alerts_YYYYMMDD_HH.csv
                        │
                        └────► Dashboard (live graphs + alerts)

📁 File Structure
project/
│
├── sensor_logger.py
├── watchdog.py
├── dashboard.py
│
├── rrh62000_YYYY-MM-DD_HH.csv
├── latest.csv
│
└── alerts/
      └── alerts_YYYYMMDD_HH.csv

1️⃣ Sensor Logger
Purpose

Reads data from the RRH62000 sensor over I²C and logs it to rotating hourly CSV files.

Key Features

1 Hz data acquisition

Automatic hourly file rotation

Header auto-creation

Maintains latest.csv symlink

Calculates custom EU-weighted IAQ index (IAQ_CUSTOM)

Output Files
Hourly Data Log
rrh62000_2026-03-02_14.csv

Live Pointer
latest.csv → rrh62000_2026-03-02_14.csv


All other services read latest.csv for consistency.

IAQ_CUSTOM Calculation

The custom IAQ index is based on EU / WHO reference limits:

Parameter	Reference	Weight
PM2.5	25 µg/m³	40%
PM10	50 µg/m³	20%
TVOC	300 µg/m³	20%
CO₂	1000 ppm	20%

The index is scaled to:

0–40 → Excellent

40–70 → Good

70–100 → Moderate

100–150 → Poor

150 → Very Poor

2️⃣ Watchdog
Purpose

Continuously monitors live data and detects threshold violations.

How It Works

Reads latest.csv

Computes rolling average (last N samples)

Compares against predefined limits

Tracks exposure duration

Logs alerts if limits exceeded

Alert Logging

Alerts are stored hourly in:

alerts/alerts_YYYYMMDD_HH.csv


Each alert entry includes:

Timestamp

Parameter name

Rolling average

Limit value

Exposure duration

Sample window size

GPIO Alert

If any parameter exceeds limits:

LED flashes on configured GPIO pin

Alert entry is written to CSV

3️⃣ Dashboard
Purpose

Provides a live graphical display of:

Particulate levels

Gas concentrations

Temperature & humidity

IAQ_CUSTOM

Active alerts

Features

Dark theme

Live updating (every ~1 second)

Only reads last N rows (performance optimized)

Bottom-corner alert panel

Automatically follows hourly file via latest.csv

Alert Display

If alerts are active:

ALERTS:
PM2.5_KCl = 45.3 (limit 20) [120s]
eCO2_ppm = 1300 (limit 1000) [60s]


Alerts automatically clear when conditions return to normal.

🔄 Hourly Rotation Mechanism

Every hour:

Sensor Logger creates new hourly file

Header is written

latest.csv is updated to point to new file

Watchdog and Dashboard automatically follow the new file

No restart required.

⚙ Configuration Points

Each script contains configurable parameters:

Logger

LOG_INTERVAL

IAQ weighting

I2C bus & address

Watchdog

SAMPLE_WINDOW

CHECK_INTERVAL

Limit thresholds

GPIO pin

Dashboard

MAX_POINTS

Update interval

Grid layout

Colour map

Alert position


🛠 Recommended Deployment

Run all three via systemd:

rrh62000-stack.service

rrh62000-dashboard.service

Start order:

Logger

Watchdog

Dashboard



🧠 Summary

This system provides:

Continuous environmental monitoring

Health-weighted air quality modelling

Live visualisation

Exposure-aware alerting

Robust file rotation

Efficient runtime behaviour

It is structured for long-term unattended operation on embedded hardware.

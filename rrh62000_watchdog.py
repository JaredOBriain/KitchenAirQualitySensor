#!/usr/bin/env python3
"""
RRH62000 Watchdog Service
-------------------------
• Monitors latest hourly sensor CSV
• Computes rolling averages
• Checks limits with exposure tracking
• Logs alerts to hourly rotating alert CSV
• Flashes GPIO LED on alert
"""

import os
import csv
import time
from datetime import datetime
from collections import deque, defaultdict
import RPi.GPIO as GPIO


# =============================
# CONFIGURATION
# =============================

SAMPLE_WINDOW = 60          # Rolling sample window
CHECK_INTERVAL = 10         # Seconds between evaluations


LED_GPIO = 16
LED_FLASH_COUNT = 3
LED_ON_TIME = 0.2
LED_OFF_TIME = 0.2

ALERT_CSV_DIR = "./alerts"
os.makedirs(ALERT_CSV_DIR, exist_ok=True)


# =============================
# LIMIT DEFINITIONS
# =============================

LIMITS = {

    # Environmental
    "Temperature_C": {"max": 35.0},
    "Humidity_pct": {"max": 70.0},

    # Particulate Matter (KCl)
    "PM1_KCl": {"max": 15.0},
    "PM2.5_KCl": {"max": 20.0},
    "PM10_KCl": {"max": 50.0},

    # Particulate Matter (Smoke)
    "PM1_Smoke": {"max": 20.0},
    "PM2.5_Smoke": {"max": 20.0},
    "PM10_Smoke": {"max": 50.0},

    # Gases
    "TVOC_ppm": {"max": 300},
    "eCO2_ppm": {"max": 1000},

    # Custom IAQ
    "IAQ_CUSTOM": {"max": 100}
}


# Tracks consecutive over-limit samples
exposure_counters = defaultdict(int)


# =============================
# ALERT CSV HANDLING
# =============================

def get_alert_csv_path():
    """Return hourly alert CSV filename."""
    filename = f"alerts_{datetime.now():%Y%m%d_%H}.csv"
    return os.path.join(ALERT_CSV_DIR, filename)


def write_alerts_to_csv(alerts):
    """Append alert entries to hourly CSV."""
    if not alerts:
        return

    csv_path = get_alert_csv_path()
    file_exists = os.path.isfile(csv_path)

    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "parameter",
                "average_value",
                "limit",
                "exposure_samples",
                "sample_window"
            ])

        timestamp = datetime.now().isoformat()

        for alert in alerts:
            writer.writerow([
                timestamp,
                alert["parameter"],
                f"{alert['avg']:.4f}",
                alert["limit"],
                alert["exposure_samples"],
                SAMPLE_WINDOW
            ])


# =============================
# LED CONTROL
# =============================

def setup_led():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_GPIO, GPIO.OUT)
    GPIO.output(LED_GPIO, GPIO.LOW)


def flash_led(times):
    for _ in range(times):
        GPIO.output(LED_GPIO, GPIO.HIGH)
        time.sleep(LED_ON_TIME)
        GPIO.output(LED_GPIO, GPIO.LOW)
        time.sleep(LED_OFF_TIME)


# =============================
# CSV PROCESSING
# =============================



def read_last_samples(filename):
    """Read last N samples into deques."""
    buffers = {k: deque(maxlen=SAMPLE_WINDOW) for k in LIMITS}

    with open(filename, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for field in buffers:
                try:
                    buffers[field].append(float(row[field]))
                except (ValueError, KeyError):
                    pass

    return buffers


def compute_averages(buffers):
    """Compute rolling averages."""
    return {
        k: sum(v) / len(v)
        for k, v in buffers.items()
        if v
    }


# =============================
# LIMIT CHECKING
# =============================

def check_limits_with_exposure(averages):
    """Check limits and apply exposure tracking."""
    alerts = []

    for field, avg in averages.items():
        cfg = LIMITS.get(field, {})
        max_limit = cfg.get("max")

        violated = max_limit is not None and avg > max_limit

        if violated:
            exposure_counters[field] += 1
        else:
            exposure_counters[field] = 0

        if violated:
            alerts.append({
                "parameter": field,
                "avg": avg,
                "limit": max_limit,
                "exposure_samples": exposure_counters[field]
            })

    return alerts


# =============================
# MAIN LOOP
# =============================

def main():
    print("RRH62000 Watchdog Started")
    setup_led()

    while True:
        try:
            csv_file = "latest.csv"

            if not os.path.exists(csv_file):
                time.sleep(CHECK_INTERVAL)
                continue


            buffers = read_last_samples(csv_file)
            averages = compute_averages(buffers)
            alerts = check_limits_with_exposure(averages)

            if alerts:
                write_alerts_to_csv(alerts)
                flash_led(LED_FLASH_COUNT)

        except Exception as e:
            print("Watchdog error:", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

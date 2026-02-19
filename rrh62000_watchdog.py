#!/usr/bin/env python3

import csv
import time
import os
import RPi.GPIO as GPIO


from collections import deque
from datetime import datetime
from collections import deque, defaultdict

# Tracks consecutive over-limit samples
exposure_counters = defaultdict(int)

# -------- ALERT CSV CONFIG --------
ALERT_CSV_DIR = "./alerts"
os.makedirs(ALERT_CSV_DIR, exist_ok=True)

# ---------------------------------

# -------- LED CONFIG --------
LED_GPIO = 16          # BCM numbering
LED_FLASH_COUNT = 3
LED_ON_TIME = 0.2      # seconds
LED_OFF_TIME = 0.2
# ---------------------------

# -------- USER CONFIG --------

# Number of samples used to compute rolling average
SAMPLE_WINDOW = 60            # e.g. last 60 seconds

# How often the watchdog evaluates limits
CHECK_INTERVAL = 10           # seconds

# Directory where CSV files are stored
CSV_DIRECTORY = "."

# Alert thresholds
# exposure_samples = number of consecutive watchdog checks
# before alerting (CHECK_INTERVAL × exposure_samples seconds)

LIMITS = {

    # -------------------------
    # Environmental
    # -------------------------
    "Temperature_C": {
        "max": 35.0
    },

    "Humidity_pct": {
        "max": 70.0
    },

    # -------------------------
    # Particulate Matter (KCl reference)
    # -------------------------
    "PM1_KCl": {
        "max": 15.0,
      #  "exposure_samples": 60    # ~10 minutes
    },

    "PM2.5_KCl": {
        "max": 20.0,
      #  "exposure_samples": 15    # ~2.5 minutes
    },

    "PM10_KCl": {
        "max": 50.0,
      #  "exposure_samples": 15
    },

    # -------------------------
    # Particulate Matter (Smoke reference)
    # -------------------------
    "PM1_Smoke": {
        "max": 20.0,
      #  "exposure_samples": 60
    },

    "PM2.5_Smoke": {
        "max": 20.0,
      #  "exposure_samples": 15
    },

    "PM10_Smoke": {
        "max": 50.0,
      #  "exposure_samples": 15
    },

    # -------------------------
    # Gases
    # -------------------------
    "TVOC_ugm3": {
        "max": 300,
      #  "exposure_samples": 6    # ~1 minutes
    },

    "eCO2_ppm": {
        "max": 1000,
      #  "exposure_samples": 6    # ~1 minutes
    },

    # -------------------------
    # Air Quality Index
    # -------------------------
    "IAQ": {
        "max": 5,
      #  "exposure_samples": 30    # ~5 minutes
    },

    "Relative_IAQ": {
        "max": 200
    },
}

# -----------------------------
def get_alert_csv_path():
    now = datetime.now()
    filename = f"alerts_{now.strftime('%Y%m%d_%H')}.csv"
    return os.path.join(ALERT_CSV_DIR, filename)

def write_alerts_to_csv(alerts):
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
                alert.get("exposure_samples", ""),
                SAMPLE_WINDOW
            ])



def setup_led():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_GPIO, GPIO.OUT)
    GPIO.output(LED_GPIO, GPIO.LOW)

def flash_led(times=3):
    for _ in range(times):
        GPIO.output(LED_GPIO, GPIO.HIGH)
        time.sleep(LED_ON_TIME)
        GPIO.output(LED_GPIO, GPIO.LOW)
        time.sleep(LED_OFF_TIME)

def latest_csv_file():
    files = [f for f in os.listdir(CSV_DIRECTORY)
             if f.startswith("rrh62000_") and f.endswith(".csv")]
    return max(files) if files else None

def read_last_samples(filename, window):
    buffers = {k: deque(maxlen=window) for k in LIMITS.keys()}

    with open(os.path.join(CSV_DIRECTORY, filename), newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for field in buffers:
                try:
                    buffers[field].append(float(row[field]))
                except (ValueError, KeyError):
                    pass

    return buffers

def compute_averages(buffers):
    averages = {}
    for k, values in buffers.items():
        if values:
            averages[k] = sum(values) / len(values)
    return averages

def check_limits_with_exposure(averages):
    alerts = []

    for field, avg in averages.items():
        cfg = LIMITS.get(field, {})
        max_limit = cfg.get("max")
        min_limit = cfg.get("min")
        exposure_required = cfg.get("exposure_samples")

        violated = False
        direction = ""

        if max_limit is not None and avg > max_limit:
            violated = True
            direction = "HIGH"
        elif min_limit is not None and avg < min_limit:
            violated = True
            direction = "LOW"

        if violated:
            # Increment exposure counter
            exposure_counters[field] += 1
        else:
            # Reset if back to normal
            exposure_counters[field] = 0

        # Decide whether to alert
        if violated:
            if exposure_required:
                if exposure_counters[field] >= exposure_required:
                    alerts.append({
                        "parameter": field,
                        "avg": avg,
                        "limit": limit,
                        "exposure_samples": exposure_counters[field]
                    })

            else:
                # Immediate alert
                alerts.append({
                    "parameter": field,
                    "avg": avg,
                    "limit": max_limit,
                    "exposure_samples": exposure_counters[field]
                })


    return alerts


def main():
    print("RRH62000 Watchdog started")
    setup_led()
    while True:
        try:
            csv_file = latest_csv_file()
            if not csv_file:
                time.sleep(CHECK_INTERVAL)
                continue

            buffers = read_last_samples(csv_file, SAMPLE_WINDOW)
            averages = compute_averages(buffers)
            alerts = check_limits_with_exposure(averages)

            if alerts:
                #print(f"[{datetime.now().isoformat()}] ALERTS:")
                #for a in alerts:
                #    print("  ", a)
                #print("-" * 40)
                write_alerts_to_csv(alerts)
                flash_led(LED_FLASH_COUNT)
        except Exception as e:
            print("Watchdog error:", e)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
RRH62000 Sensor Logger
----------------------
• Reads data via I2C (1 Hz)
• Logs hourly CSV files (rotated by hour)
• Automatically writes headers for new files
• Maintains stable latest.csv symlink
• Calculates custom Indoor Air Quality (IAQ_CUSTOM)
"""

import os
import csv
import time
import struct
from datetime import datetime
from smbus2 import SMBus, i2c_msg


# =============================
# CONFIGURATION
# =============================

I2C_BUS = 1
SENSOR_ADDR = 0x69
FRAME_LEN = 37
LOG_INTERVAL = 1  # seconds


# =============================
# CSV FIELD DEFINITIONS
# =============================

FIELDNAMES = [
    "timestamp",
    "status",
    "NC_0.3", "NC_0.5", "NC_1.0", "NC_2.5", "NC_4.0",
    "PM1_KCl", "PM2.5_KCl", "PM10_KCl",
    "PM1_Smoke", "PM2.5_Smoke", "PM10_Smoke",
    "Temperature_C", "Humidity_pct",
    "TVOC_ppm", "eCO2_ppm",
    "IAQ", "Relative_IAQ",
    "IAQ_CUSTOM",
    "crc"
]


# =============================
# I2C HELPERS
# =============================

def read_frame(bus):
    """Read one full sensor frame."""
    msg = i2c_msg.read(SENSOR_ADDR, FRAME_LEN)
    bus.i2c_rdwr(msg)
    return list(msg)


def u16(data, index):
    return struct.unpack(">H", bytes(data[index:index+2]))[0]


def s16(data, index):
    return struct.unpack(">h", bytes(data[index:index+2]))[0]


# =============================
# IAQ CUSTOM CALCULATION
# =============================

def calculate_custom_iaq(pm25, pm10, tvoc, eco2):
    """
    EU-weighted Indoor Air Quality Index.
    Returns 0–150+ scale.
    """

    # Reference limits (EU / WHO)
    PM25_REF = 25.0
    PM10_REF = 50.0
    TVOC_REF = 300.0
    CO2_REF = 1000.0

    # Normalized pollutant burden
    pm25_score = min(pm25 / PM25_REF, 1.5)
    pm10_score = min(pm10 / PM10_REF, 1.5)
    tvoc_score = min(tvoc / TVOC_REF, 1.5)
    co2_score = min(eco2 / CO2_REF, 1.5)

    # Weighted health model
    burden = (
        0.40 * pm25_score +
        0.20 * pm10_score +
        0.20 * tvoc_score +
        0.20 * co2_score
    )

    return round(burden * 100, 2)


# =============================
# FRAME PARSER
# =============================

def parse_frame(data):
    """Convert raw frame into structured dictionary."""

    values = {
        "timestamp": datetime.now().isoformat(),

        "status": u16(data, 0),

        "NC_0.3": u16(data, 2) * 0.1,
        "NC_0.5": u16(data, 4) * 0.1,
        "NC_1.0": u16(data, 6) * 0.1,
        "NC_2.5": u16(data, 8) * 0.1,
        "NC_4.0": u16(data, 10) * 0.1,

        "PM1_KCl": u16(data, 12) * 0.1,
        "PM2.5_KCl": u16(data, 14) * 0.1,
        "PM10_KCl": u16(data, 16) * 0.1,

        "PM1_Smoke": u16(data, 18) * 0.1,
        "PM2.5_Smoke": u16(data, 20) * 0.1,
        "PM10_Smoke": u16(data, 22) * 0.1,

        "Temperature_C": s16(data, 24) * 0.01,
        "Humidity_pct": u16(data, 26) * 0.01,

        "TVOC_ppm": u16(data, 28) * 10 * 0.001 * 0.5,
        "eCO2_ppm": u16(data, 30),

        "IAQ": u16(data, 32) * 0.01,
        "Relative_IAQ": u16(data, 34),

        "crc": data[36],
    }

    # Calculate custom IAQ
    values["IAQ_CUSTOM"] = calculate_custom_iaq(
    values["PM2.5_KCl"],
    values["PM10_KCl"],
    values["TVOC_ppm"],
    values["eCO2_ppm"]
)

    # Round floats
    for k, v in values.items():
        if isinstance(v, float):
            values[k] = round(v, 4)

    return values


# =============================
# CSV HANDLING
# =============================

def current_csv_filename():
    return f"rrh62000_{datetime.now():%Y-%m-%d_%H}.csv"


def ensure_csv_header(filename):
    if not os.path.exists(filename):
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def append_csv(filename, data):
    with open(filename, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(data)


def update_latest_symlink(current_file):
    latest_name = "latest.csv"
    try:
        if os.path.exists(latest_name) or os.path.islink(latest_name):
            os.remove(latest_name)
        os.symlink(current_file, latest_name)
    except Exception:
        pass


# =============================
# MAIN LOOP
# =============================

def main():
    with SMBus(I2C_BUS) as bus:

        current_file = current_csv_filename()
        ensure_csv_header(current_file)
        update_latest_symlink(current_file)

        while True:
            start_time = time.time()

            try:
                frame = read_frame(bus)
                values = parse_frame(frame)

                new_file = current_csv_filename()

                if new_file != current_file:
                    current_file = new_file
                    ensure_csv_header(current_file)
                    update_latest_symlink(current_file)

                append_csv(current_file, values)

            except Exception as e:
                print("Sensor error:", e)

            elapsed = time.time() - start_time
            time.sleep(max(0, LOG_INTERVAL - elapsed))


if __name__ == "__main__":
    main()

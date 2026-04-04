#!/usr/bin/env python3
"""
RRH62000 Live Dashboard
-----------------------
• Displays live sensor data
• Uses hourly rotating CSV
• Shows alert panel
• Dark themed
"""

import os
import math
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime


# =============================
# CONFIGURATION
# =============================

MAX_POINTS = 90
UPDATE_INTERVAL_MS = 1100
NUM_COLUMNS = 3
ALERT_DIR = "./alerts"

EXCLUDE_PREFIXES = ["NC_"]
EXCLUDE_COLUMNS = ["status", "crc", "Relative_IAQ", "IAQ"]  # remove old IAQ


# =============================
# VISUAL STYLE
# =============================

plt.style.use("dark_background")

BACKGROUND_COLOR = "#121212"
GRID_COLOR = "#333333"
TEXT_COLOR = "#E0E0E0"

COLOR_MAP = {
    "PM1": "#4FC3F7",
    "PM2.5": "#29B6F6",
    "PM10": "#0288D1",
    "TVOC": "#FF7043",
    "eCO2": "#AB47BC",
    "IAQ_CUSTOM": "#66BB6A",
    "Temperature": "#FFA726",
    "Humidity": "#26A69A"
}

UNIT_MAP = {
    "PM1": "µg/m³",
    "PM2.5": "µg/m³",
    "PM10": "µg/m³",
    "TVOC": "µg/m³",
    "eCO2": "ppm",
    "IAQ_CUSTOM": "index",
    "Temperature": "°C",
    "Humidity": "%"
}


# =============================
# FILE HELPERS
# =============================
def read_latest_data():
    filename = "latest.csv"

    try:
        if not os.path.exists(filename):
            return None

        from collections import deque
        from io import StringIO

        with open(filename, "r") as f:
            lines = f.readlines()

        if len(lines) <= 1:
            return None

        header = lines[0]
        data_lines = lines[-MAX_POINTS:]

        csv_content = header + "".join(data_lines)

        df = pd.read_csv(StringIO(csv_content))
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        return df

    except Exception:
        return None


def get_latest_alerts():
    try:
        if not os.path.isdir(ALERT_DIR):
            return []

        filename = f"alerts_{datetime.now():%Y%m%d_%H}.csv"
        path = os.path.join(ALERT_DIR, filename)

        if not os.path.exists(path):
            return []

        df = pd.read_csv(path)

        if df.empty:
            return []

        recent = df.tail(5)

        return [
            {
                "parameter": row["parameter"],
                "avg": row["average_value"],
                "limit": row["limit"],
                "exposure_samples": row.get("exposure_samples", 0)
            }
            for _, row in recent.iterrows()
        ]

    except Exception:
        return []


# =============================
# PLOT HELPERS
# =============================

def get_plot_columns(df):
    return [
        col for col in df.columns
        if col != "timestamp"
        and col not in EXCLUDE_COLUMNS
        and not any(col.startswith(p) for p in EXCLUDE_PREFIXES)
    ]


def get_color(col):
    for key in COLOR_MAP:
        if key in col:
            return COLOR_MAP[key]
    return "#90CAF9"


def get_unit(col):
    for key in UNIT_MAP:
        if key in col:
            return UNIT_MAP[key]
    return ""


# =============================
# INITIAL SETUP
# =============================

df_init = read_latest_data()
if df_init is None:
    print("No data available.")
    exit()

plot_columns = get_plot_columns(df_init)

num_plots = len(plot_columns)
num_rows = math.ceil(num_plots / NUM_COLUMNS)

fig, axes = plt.subplots(num_rows, NUM_COLUMNS, figsize=(14, 3 * num_rows))
fig.subplots_adjust(top=0.92, hspace=0.75, wspace=0.25)
fig.patch.set_facecolor(BACKGROUND_COLOR)

axes = axes.flatten()

lines = []

for i, col in enumerate(plot_columns):
    ax = axes[i]
    color = get_color(col)
    unit = get_unit(col)

    line, = ax.plot([], [], linewidth=2.2, color=color)
    lines.append(line)

    ax.set_facecolor("#1E1E1E")
    ax.grid(True, color=GRID_COLOR, alpha=0.3)

    
    
    if(col == "TVOC_ppm"):
        ax.set_title(
        f"TVOC ({unit})",
        fontsize=11,
        fontweight="bold",
        color=color,
        pad=8)
    else:
        ax.set_title(
        f"{col} ({unit})",
        fontsize=11,
        fontweight="bold",
        color=color,
        pad=8
        )

    ax.tick_params(axis="x", rotation=45, colors=TEXT_COLOR)
    ax.tick_params(axis="y", colors=TEXT_COLOR)

    for spine in ax.spines.values():
        spine.set_color("#444444")

# Hide unused axes
for j in range(num_plots, len(axes)):
    axes[j].set_visible(False)


# =============================
# ALERT BOX
# =============================

alert_box = fig.text(
    0.68,
    0.12,
    "",
    ha="left",
    va="bottom",
    fontsize=11,
    fontweight="bold",
    color="white",
    bbox=dict(
        facecolor="#B71C1C",
        edgecolor="white",
        linewidth=1.5,
        alpha=0.9,
        boxstyle="round,pad=0.6"
    )
)
alert_box.set_visible(False)


# =============================
# ANIMATION LOOP
# =============================

def update(frame):
    df = read_latest_data()
    if df is None:
        return

    timestamps = df["timestamp"]

    for i, col in enumerate(plot_columns):
        
        if(col == "TVOC_ppm"):
            lines[i].set_data(timestamps, df[col]*1000*2)
            axes[i].set_xlim(timestamps.min(), timestamps.max())
            axes[i].relim()
            axes[i].autoscale_view()
        else:
            lines[i].set_data(timestamps, df[col])
            axes[i].set_xlim(timestamps.min(), timestamps.max())
            axes[i].relim()
            axes[i].autoscale_view()
        
        
        

    alerts = get_latest_alerts()

    if alerts:
        alert_lines = [
            f"{a['parameter']} = {a['avg']} "
            f"(limit {a['limit']}) "
            f"[{int(a['exposure_samples']) * 10}s]"
            for a in alerts
        ]

        alert_box.set_text("ALERTS:\n" + "\n".join(alert_lines))
        alert_box.set_visible(True)
    else:
        alert_box.set_visible(False)


ani = FuncAnimation(
    fig,
    update,
    interval=UPDATE_INTERVAL_MS,
    cache_frame_data=False
)

manager = plt.get_current_fig_manager()
manager.full_screen_toggle()

plt.show()

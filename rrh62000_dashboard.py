import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime
import math
import os

# ---------------- CONFIG ----------------
CSV_FILE = "./sensor_logs/latest.csv"   # change to your log file path
MAX_POINTS = 90
UPDATE_INTERVAL_MS = 1100
EXCLUDE_PREFIXES = ["NC_"]  # remove number concentration
EXCLUDE_COLUMNS = [
    "status",
    "crc",
    "Relative_IAQ"
]
NUM_COLUMNS = 3
# ----------------------------------------


plt.style.use("dark_background")

BACKGROUND_COLOR = "#121212"
GRID_COLOR = "#333333"
TEXT_COLOR = "#E0E0E0"

# Gas colour map
COLOR_MAP = {
    "PM1": "#4FC3F7",
    "PM2.5": "#29B6F6",
    "PM10": "#0288D1",
    "TVOC": "#FF7043",
    "eCO2": "#AB47BC",
    "IAQ": "#66BB6A",
    "Temperature": "#FFA726",
    "Humidity": "#26A69A"
}

# Unit map
UNIT_MAP = {
    "PM1": "µg/m³",
    "PM2.5": "µg/m³",
    "PM10": "µg/m³",
    "TVOC": "µg/m³",
    "eCO2": "ppm",
    "IAQ": "index",
    "Temperature": "°C",
    "Humidity": "%"
}

def current_csv_filename():
    now = datetime.now()
    return f"rrh62000_{now:%Y-%m-%d_%H}.csv"

def read_latest_data():
    
    CSV_FILE = current_csv_filename()
    
    try:
        df = pd.read_csv(CSV_FILE)
        df = df.tail(MAX_POINTS)
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        return df
    except:
        return None

def get_plot_columns(df):
    cols = []
    for col in df.columns:
        if col == "timestamp":
            continue
        if col in EXCLUDE_COLUMNS:
            continue
        if any(col.startswith(p) for p in EXCLUDE_PREFIXES):
            continue
        cols.append(col)
    return cols


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


# ---------- Initial Setup ----------

df_init = read_latest_data()
if df_init is None:
    print("No data.")
    exit()

plot_columns = get_plot_columns(df_init)

num_plots = len(plot_columns)
num_rows = math.ceil(num_plots / NUM_COLUMNS)

fig, axes = plt.subplots(
    num_rows,
    NUM_COLUMNS,
    figsize=(14, 3 * num_rows)
)

fig.subplots_adjust(
    top=0.92,
    hspace=0.75,
    wspace=0.25
)


fig.patch.set_facecolor(BACKGROUND_COLOR)

axes = axes.flatten()

lines = []

for i, col in enumerate(plot_columns):
    ax = axes[i]

    color = get_color(col)
    unit = get_unit(col)

    line, = ax.plot([], [], linewidth=2.2, color=color)
    lines.append(line)

    # Style ONCE (not in update loop)
    ax.set_facecolor("#1E1E1E")
    ax.grid(True, color=GRID_COLOR, alpha=0.3)

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


# ---------- Animation ----------

def update(frame):
    df = read_latest_data()
    if df is None:
        return

    time = df["timestamp"]

    for i, col in enumerate(plot_columns):
        lines[i].set_data(time, df[col])
        axes[i].set_xlim(time.min(), time.max())
        axes[i].relim()
        axes[i].autoscale_view()

    fig.canvas.draw_idle()


ani = FuncAnimation(
    fig,
    update,
    interval=UPDATE_INTERVAL_MS,
    cache_frame_data=False
)


manager = plt.get_current_fig_manager()
manager.full_screen_toggle()

plt.show()
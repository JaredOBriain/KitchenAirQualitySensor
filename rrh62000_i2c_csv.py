#!/usr/bin/env python3

from smbus2 import SMBus, i2c_msg
import struct
import time
import csv
import os
from datetime import datetime



I2C_BUS = 1
SENSOR_ADDR = 0x69
FRAME_LEN = 37
#CSV_FILE = "rrh62000_data.csv"

def read_frame(bus):
    msg = i2c_msg.read(SENSOR_ADDR, FRAME_LEN)
    bus.i2c_rdwr(msg)
    return list(msg)

def u16(d, i):
    return struct.unpack(">H", bytes(d[i:i+2]))[0]

def s16(d, i):
    return struct.unpack(">h", bytes(d[i:i+2]))[0]

def parse_frame(d):
    raw = {
        "timestamp": datetime.now().isoformat(),

        "status": u16(d, 0),

        "NC_0.3": u16(d, 2) * 0.1,
        "NC_0.5": u16(d, 4) * 0.1,
        "NC_1.0": u16(d, 6) * 0.1,
        "NC_2.5": u16(d, 8) * 0.1,
        "NC_4.0": u16(d, 10) * 0.1,

        "PM1_KCl": u16(d, 12) * 0.1,
        "PM2.5_KCl": u16(d, 14) * 0.1,
        "PM10_KCl": u16(d, 16) * 0.1,

        "PM1_Smoke": u16(d, 18) * 0.1,
        "PM2.5_Smoke": u16(d, 20) * 0.1,
        "PM10_Smoke": u16(d, 22) * 0.1,

        "Temperature_C": s16(d, 24) * 0.01,
        "Humidity_pct": u16(d, 26) * 0.01,

        "TVOC_ppm": u16(d, 28) * 10*0.001*0.5,
        "eCO2_ppm": u16(d, 30),
        "IAQ": u16(d, 32) * 0.01,
        "Relative_IAQ": u16(d, 34),

        "crc": d[36],
    }
    return {k: format_value(v, 4) for k, v in raw.items()}

def format_value(val, decimals=4):
    if isinstance(val, float):
        return round(val, decimals)
    return val


def ensure_csv_header(filename, fieldnames):
    if not os.path.exists(filename):
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


def append_csv(filename, data):
    with open(filename, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data.keys())
        writer.writerow(data)

def current_csv_filename():
    now = datetime.now()
    return f"rrh62000_{now:%Y-%m-%d_%H}.csv"


def main():
    with SMBus(I2C_BUS) as bus:
        # Ensure CSV header exists
        
        #ensure_csv_header(current_csv_filename(), parse_frame([0]*FRAME_LEN).keys())
        current_file = current_csv_filename()
        fieldnames = parse_frame([0]*FRAME_LEN).keys()
        ensure_csv_header(current_file, fieldnames)


        last_print_time = 0
        print_interval = 10      # seconds
        log_interval = 1         # seconds

        while True:
            start_time = time.time()

            try:
                frame = read_frame(bus)
                values = parse_frame(frame)

                # Always log to CSV (every second)
                #append_csv(current_csv_filename(), values)

                new_file = current_csv_filename()

                # If hour changed, ensure new file has header
                if new_file != current_file:
                    current_file = new_file
                    ensure_csv_header(current_file, fieldnames)

                append_csv(current_file, values)

                
                # Print summary every 10 seconds
                if start_time - last_print_time >= print_interval:
                    #print("RRH62000 Summary:")
        
                    #for k, v in values.items():
                    #    print(f"  {k:16s}: {v}")
                    #print("-" * 50)

                    last_print_time = start_time

            except Exception as e:
                print("Sensor error:", e)

            # Maintain 1-second logging interval
            elapsed = time.time() - start_time
            sleep_time = max(0, log_interval - elapsed)
            time.sleep(sleep_time)
 

if __name__ == "__main__":
    main()


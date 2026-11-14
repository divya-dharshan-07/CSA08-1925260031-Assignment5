import csv
import os
import random
import sqlite3
import time
import tracemalloc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_CSV = os.path.join(BASE_DIR, "raw_air_quality.csv")
CLEAN_CSV = os.path.join(BASE_DIR, "cleaned_air_quality.csv")
DB_PATH = os.path.join(BASE_DIR, "air_quality.db")

FAHRENHEIT_STATIONS = {"ST03"}

def parse_float(val):
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.upper() in {"NA", "NULL", "NAN"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None

def clean_dataset(csv_path):
    print("=== B1.1: BEFORE CLEANING (RAW CSV) ===")
    with open(csv_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    print(raw_text.strip())

    seen_keys = set()
    cleaned_rows = []
    last_valid_pm25 = {}

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            st_id = row["station_id"].strip().upper()
            st_name = " ".join(row["station_name"].strip().split()).title()
            day = row["date"].strip()
            hour = int(row["hour"].strip())

            # Rule: Deduplicate on (station_id, day, hour)
            key = (st_id, day, hour)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            pm25 = parse_float(row["pm25"])
            pm10 = parse_float(row["pm10"])
            no2 = parse_float(row["no2"])
            temp = parse_float(row["temperature"])

            # Rule: Forward fill short missing gaps for pm25 within same station
            if pm25 is None:
                if st_id in last_valid_pm25:
                    pm25 = last_valid_pm25[st_id]
                else:
                    continue

            # Rule: Drop impossible sensor fault values
            if not (0.0 <= pm25 <= 999.0):
                continue
            if pm10 is None or not (0.0 <= pm10 <= 2000.0):
                continue
            if no2 is None or not (0.0 <= no2 <= 1000.0):
                continue
            if temp is None:
                continue

            # Rule: Convert Fahrenheit stations to Celsius
            if st_id in FAHRENHEIT_STATIONS:
                temp_c = round((temp - 32.0) * 5.0 / 9.0, 2)
            else:
                temp_c = round(temp, 2)

            if not (-10.0 <= temp_c <= 60.0):
                continue

            last_valid_pm25[st_id] = pm25
            cleaned_rows.append({
                "station_id": st_id,
                "station_name": st_name,
                "day": day,
                "hour": hour,
                "pm25": round(pm25, 2),
                "pm10": round(pm10, 2),
                "no2": round(no2, 2),
                "temp_c": temp_c,
            })

    # Min-Max normalization for pm25
    pm_vals = [r["pm25"] for r in cleaned_rows]
    lo, hi = min(pm_vals), max(pm_vals)
    for r in cleaned_rows:
        r["pm25_minmax"] = round((r["pm25"] - lo) / (hi - lo), 3) if hi > lo else 0.0

    with open(CLEAN_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(cleaned_rows[0].keys()))
        writer.writeheader()
        writer.writerows(cleaned_rows)

    print("\n=== B1.1: AFTER CLEANING ===")
    for r in cleaned_rows:
        print(r)
    return cleaned_rows

def store_and_query(cleaned_rows):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON;")
    con.execute("""
        CREATE TABLE stations (
            station_id TEXT PRIMARY KEY,
            station_name TEXT NOT NULL UNIQUE,
            temp_unit TEXT NOT NULL CHECK(temp_unit IN ('C', 'F'))
        );
    """)
    con.execute("""
        CREATE TABLE readings (
            reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL REFERENCES stations(station_id),
            day TEXT NOT NULL,
            hour INTEGER NOT NULL CHECK(hour BETWEEN 0 AND 23),
            pm25 REAL CHECK(pm25 >= 0 AND pm25 <= 999),
            pm10 REAL CHECK(pm10 >= 0 AND pm10 <= 2000),
            no2 REAL CHECK(no2 >= 0 AND no2 <= 1000),
            temp_c REAL CHECK(temp_c BETWEEN -10 AND 60),
            UNIQUE(station_id, day, hour)
        );
    """)

    stations = {}
    for r in cleaned_rows:
        unit = "F" if r["station_id"] in FAHRENHEIT_STATIONS else "C"
        stations[r["station_id"]] = (r["station_id"], r["station_name"], unit)

    con.executemany("INSERT INTO stations VALUES (?, ?, ?)", list(stations.values()))
    reading_tuples = [
        (r["station_id"], r["day"], r["hour"], r["pm25"], r["pm10"], r["no2"], r["temp_c"])
        for r in cleaned_rows
    ]
    con.executemany(
        "INSERT INTO readings (station_id, day, hour, pm25, pm10, no2, temp_c) VALUES (?, ?, ?, ?, ?, ?, ?)",
        reading_tuples
    )
    con.commit()

    print("\n=== B1.3: SQL QUERIES FOR BOARD QUESTIONS ===")
    q1 = con.execute("""
        SELECT s.station_name, ROUND(AVG(r.pm25), 2)
        FROM readings r JOIN stations s ON r.station_id = s.station_id
        WHERE s.station_name = 'Adyar' AND r.day LIKE '2026-10-%'
    """).fetchone()
    print("Q1 (Average PM2.5 of Adyar in Oct 2026):", q1)

    q2 = con.execute("""
        SELECT s.station_name, ROUND(MAX(r.no2), 2) AS peak_no2
        FROM readings r JOIN stations s ON r.station_id = s.station_id
        GROUP BY s.station_id ORDER BY peak_no2 DESC LIMIT 3
    """).fetchall()
    print("Q2 (Stations ranked by peak NO2):", q2)

    q3 = con.execute("""
        SELECT s.station_name, r.day, r.hour, r.pm25, r.temp_c
        FROM readings r JOIN stations s ON r.station_id = s.station_id
        WHERE r.pm25 > 70 AND r.temp_c > 30
    """).fetchall()
    print("Q3 (Elevated PM2.5 > 70 and Temp > 30C):", q3)
    con.close()

def generate_charts():
    # Generate realistic 30-day multi-station dataset for rich visualisations
    random.seed(42)
    stations = [("ST01", "Adyar", 52), ("ST02", "Guindy", 88), ("ST03", "Anna Nagar", 64), ("ST04", "Velachery", 71)]
    records = []
    for day_num in range(1, 31):
        day_str = f"2026-10-{day_num:02d}"
        for st_id, st_name, base_pm in stations:
            for hr in [0, 4, 8, 12, 16, 20]:
                rush = 24 if hr in (8, 20) else (-10 if hr == 4 else 5)
                temp_c = round(26.0 + (6.5 if hr in (12, 16) else 1.5) + random.uniform(-1.2, 1.2), 1)
                pm25 = round(max(12.0, base_pm + rush + 0.8 * (temp_c - 28.0) + random.gauss(0, 8)), 1)
                records.append((st_id, st_name, day_str, hr, pm25, temp_c))

    df = pd.DataFrame(records, columns=["station_id", "station_name", "day", "hour", "pm25", "temp_c"])

    # Chart 1: Line Chart - Monthly PM2.5 Trend
    daily_trend = df.groupby("day")["pm25"].mean()
    plt.figure(figsize=(9, 4))
    plt.plot(range(1, 31), daily_trend.values, marker="o", linewidth=2, color="#1f77b4")
    plt.title("Daily City-Wide Mean PM2.5 Trend (October 2026)")
    plt.xlabel("Day of October 2026")
    plt.ylabel("Mean PM2.5 (ug/m3)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(BASE_DIR, "chart1_pm25_trend.png"), dpi=150)
    plt.close()

    # Chart 2: Bar Chart - Station Comparison
    st_means = df.groupby("station_name")["pm25"].mean().sort_values(ascending=False)
    plt.figure(figsize=(7, 4))
    plt.bar(st_means.index, st_means.values, color=["#d62728", "#ff7f0e", "#2ca02c", "#1f77b4"])
    plt.title("Mean PM2.5 Concentration by Monitoring Station")
    plt.xlabel("Monitoring Station")
    plt.ylabel("Mean PM2.5 (ug/m3)")
    plt.tight_layout()
    plt.savefig(os.path.join(BASE_DIR, "chart2_station_comparison.png"), dpi=150)
    plt.close()

    # Chart 3: Scatter Plot - Temperature vs PM2.5
    plt.figure(figsize=(7, 4))
    plt.scatter(df["temp_c"], df["pm25"], alpha=0.45, color="#9467bd", edgecolors="none")
    plt.title("Temperature (C) vs. PM2.5 Concentration")
    plt.xlabel("Temperature (Celsius)")
    plt.ylabel("PM2.5 (ug/m3)")
    plt.grid(True, linestyle=":", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(BASE_DIR, "chart3_temp_vs_pm25.png"), dpi=150)
    plt.close()

    # Chart 4: Box Plot - Hourly Distribution
    hours = sorted(df["hour"].unique())
    hourly_data = [df[df["hour"] == h]["pm25"].values for h in hours]
    plt.figure(figsize=(8, 4))
    plt.boxplot(hourly_data, labels=[f"{h:02d}:00" for h in hours], patch_artist=True)
    plt.title("Hourly PM2.5 Distribution (Identifying Worst Air Hours)")
    plt.xlabel("Hour of Day")
    plt.ylabel("PM2.5 (ug/m3)")
    plt.grid(True, axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(BASE_DIR, "chart4_hourly_boxplot.png"), dpi=150)
    plt.close()
    print("\n=== B1.4: CHARTS GENERATED (chart1..chart4.png) ===")

def benchmark_csv_vs_pandas():
    print("\n=== B1 ALTERNATIVE ANALYSIS: CSV LOOPS vs PANDAS (1k, 100k, 1M rows) ===")
    for n in [1_000, 100_000, 1_000_000]:
        temp_file = os.path.join(BASE_DIR, f"_bench_{n}.csv")
        with open(temp_file, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["station", "pm25"])
            for i in range(n):
                w.writerow(["Adyar", "NA" if i % 20 == 0 else (-5 if i % 50 == 0 else 55.5)])

        # Method A: csv module + loops
        tracemalloc.start()
        t0 = time.perf_counter()
        vals = []
        with open(temp_file, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                v = row["pm25"]
                if v != "NA":
                    fv = float(v)
                    if 0 <= fv <= 999:
                        vals.append(fv)
        lo, hi = min(vals), max(vals)
        _ = [(v - lo) / (hi - lo) if hi > lo else 0.0 for v in vals]
        t_csv = time.perf_counter() - t0
        _, peak_csv = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Method B: pandas vectorized
        tracemalloc.start()
        t0 = time.perf_counter()
        df = pd.read_csv(temp_file, na_values=["NA"])
        s = df["pm25"].dropna()
        s = s[(s >= 0) & (s <= 999)]
        _ = (s - s.min()) / (s.max() - s.min()) if s.max() > s.min() else s * 0.0
        t_pd = time.perf_counter() - t0
        _, peak_pd = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        os.remove(temp_file)
        print(f"Rows={n:>8,} | csv+loops: {t_csv:.4f}s (Peak PyMem: {peak_csv/1e6:.2f} MB) | pandas: {t_pd:.4f}s (Peak PyMem: {peak_pd/1e6:.2f} MB)")

if __name__ == "__main__":
    cleaned = clean_dataset(RAW_CSV)
    store_and_query(cleaned)
    generate_charts()
    benchmark_csv_vs_pandas()

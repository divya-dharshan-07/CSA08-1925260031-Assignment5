import cProfile
import csv
import io
import pstats
import random
import sqlite3
import statistics
import time
import tracemalloc
import pandas as pd

def generate_synthetic_rows(num_stations, hours_per_station=8760):
    random.seed(123)
    rows = []
    for s in range(1, num_stations + 1):
        st_name = f"Station_{s:03d}"
        base = 40.0 + (s % 40)
        for h in range(hours_per_station):
            day_idx = h // 24
            month = (day_idx // 30) + 1
            day_in_m = (day_idx % 30) + 1
            day_str = f"2026-{min(month, 12):02d}-{day_in_m:02d}"
            pm25 = round(base + (h % 24) * 0.6 + random.uniform(-5, 5), 2)
            rows.append((st_name, day_str, pm25))
    return rows

def method_python_loops_store(rows):
    groups = {}
    for st, day, pm in rows:
        groups.setdefault((st, day), []).append(pm)
    return {k: round(statistics.mean(v), 4) for k, v in groups.items()}

def method_python_loops_onepass(rows):
    sums = {}
    counts = {}
    for st, day, pm in rows:
        key = (st, day)
        sums[key] = sums.get(key, 0.0) + pm
        counts[key] = counts.get(key, 0) + 1
    return {k: round(sums[k] / counts[k], 4) for k in sums}

def method_pandas(df):
    res = df.groupby(["station", "day"], sort=False)["pm25"].mean()
    return {idx: round(val, 4) for idx, val in res.items()}

def method_sql(con):
    cur = con.execute("SELECT station, day, ROUND(AVG(pm25), 4) FROM aq GROUP BY station, day")
    return {(r[0], r[1]): r[2] for r in cur.fetchall()}

def verify_correctness():
    print("=== B3.1: CORRECTNESS ON SMALL DATA ===")
    sample = [
        ("Adyar", "2026-10-01", 48.0),
        ("Adyar", "2026-10-01", 52.0),
        ("Guindy", "2026-10-01", 95.0),
        ("Guindy", "2026-10-01", 105.0),
    ]
    res_py = method_python_loops_store(sample)
    res_onepass = method_python_loops_onepass(sample)
    res_pd = method_pandas(pd.DataFrame(sample, columns=["station", "day", "pm25"]))

    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE aq (station TEXT, day TEXT, pm25 REAL)")
    con.executemany("INSERT INTO aq VALUES (?, ?, ?)", sample)
    res_sql = method_sql(con)
    con.close()

    assert res_py == res_pd == res_sql == res_onepass, "Mismatch across methods!"
    print("All methods agree identically:", res_sql)

def run_scaling_benchmarks():
    print("\n=== B3.2 & ALTERNATIVE ANALYSIS: SCALING BENCHMARK (1, 12, 120 STATIONS) ===")
    for n_stations in [1, 12, 120]:
        rows = generate_synthetic_rows(n_stations, hours_per_station=8760)
        n_rows = len(rows)

        # 1. Python loops (store all + statistics.mean)
        tracemalloc.start()
        t0 = time.perf_counter()
        _ = method_python_loops_store(rows)
        t_py_store = time.perf_counter() - t0
        _, mem_py_store = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 2. Python loops (one-pass running sum & count)
        tracemalloc.start()
        t0 = time.perf_counter()
        _ = method_python_loops_onepass(rows)
        t_py_onepass = time.perf_counter() - t0
        _, mem_py_onepass = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 3. Pandas groupby
        df = pd.DataFrame(rows, columns=["station", "day", "pm25"])
        t0 = time.perf_counter()
        _ = method_pandas(df)
        t_pd = time.perf_counter() - t0

        # 4. SQL GROUP BY
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE aq (station TEXT, day TEXT, pm25 REAL)")
        con.executemany("INSERT INTO aq VALUES (?, ?, ?)", rows)
        t0 = time.perf_counter()
        _ = method_sql(con)
        t_sql = time.perf_counter() - t0
        con.close()

        print(
            f"Stations={n_stations:>3} ({n_rows:>9,} rows) | "
            f"Py(store+mean): {t_py_store:.4f}s [{mem_py_store/1e6:.2f}MB] | "
            f"Py(1-pass): {t_py_onepass:.4f}s [{mem_py_onepass/1e6:.2f}MB] | "
            f"Pandas: {t_pd:.4f}s | SQL: {t_sql:.4f}s"
        )

def run_cprofile():
    print("\n=== B3.3: cPROFILE REPORT ON PLAIN-PYTHON VERSION (12 STATIONS) ===")
    rows = generate_synthetic_rows(12, hours_per_station=8760)
    profiler = cProfile.Profile()
    profiler.enable()
    _ = method_python_loops_store(rows)
    profiler.disable()

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("tottime")
    ps.print_stats(10)
    print(s.getvalue())

if __name__ == "__main__":
    verify_correctness()
    run_scaling_benchmarks()
    run_cprofile()

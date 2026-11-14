import csv
import io

RAW = """station,date,pm25
Adyar,2026-10-01,48
Adyar,2026-10-02,NA
Adyar,2026-10-03,
Guindy,2026-10-01,95
Guindy,2026-10-02,-5
Guindy,2026-10-03,121
"""

def load_clean(text):
    """Returns (station, date, pm25) tuples for valid, non-negative readings only."""
    rows = []
    # TODO 1: Read the text with csv.DictReader; skip rows whose pm25 is empty, 'NA' or
    # negative; convert pm25 to float
    reader = csv.DictReader(io.StringIO(text.strip()))
    for row in reader:
        raw_val = (row.get("pm25") or "").strip()
        if raw_val == "" or raw_val.upper() == "NA":
            continue
        try:
            val = float(raw_val)
        except ValueError:
            continue
        if val < 0 or val > 999:
            continue
        rows.append((row["station"].strip(), row["date"].strip(), val))
    return rows

def min_max(values):
    # TODO 2: Scale each value to the range 0-1 using (v - min) / (max - min), rounded
    # to 3 decimals
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.0 for _ in values]
    return [round((v - lo) / (hi - lo), 3) for v in values]

clean = load_clean(RAW)
print(clean)
print(min_max([pm for _, _, pm in clean]))

# Additional test row with pm25 > 999 (sensor fault ceiling check)
RAW_WITH_SPIKE = RAW + "Anna Nagar,2026-10-04,1450\n"
clean_spike_tested = load_clean(RAW_WITH_SPIKE)
print("After adding spike row (pm25=1450):", clean_spike_tested)

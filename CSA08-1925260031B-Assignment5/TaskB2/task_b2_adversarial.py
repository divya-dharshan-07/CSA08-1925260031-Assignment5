import csv
import io
import sqlite3
import time

REQUIRED_COLS = {"station", "date", "pm25"}

def safe_ingest_csv(raw_bytes, encoding="utf-8"):
    try:
        text = raw_bytes.decode(encoding)
    except UnicodeDecodeError as e:
        return f"REJECTED [Encoding Error]: {e}"

    if not text.strip():
        return "REJECTED [Empty File]: Input contains 0 bytes/lines."

    first_line = text.splitlines()[0]
    if "," not in first_line and (";" in first_line or "\t" in first_line):
        return f"REJECTED [Wrong Delimiter]: Expected ',' but detected '{first_line}'."

    reader = csv.DictReader(io.StringIO(text))
    headers = set(reader.fieldnames or [])
    missing = REQUIRED_COLS - headers
    if missing:
        return f"REJECTED [Missing Column(s)]: Missing {sorted(missing)} in headers {sorted(headers)}."

    rows = list(reader)
    return f"ACCEPTED: {len(rows)} rows parsed cleanly."

def test_adversarial_files():
    print("=== 1. ADVERSARIAL FILE INPUTS ===")
    cases = {
        "Missing Column (no pm25)": ("station,date\nAdyar,2026-10-01\n".encode("utf-8"), "utf-8"),
        "Wrong Delimiter (semicolon)": ("station;date;pm25\nAdyar;2026-10-01;48\n".encode("utf-8"), "utf-8"),
        "Different Encoding (Latin-1)": ("station,date,pm25\nStätion_Nord,2026-10-01,52\n".encode("latin-1"), "utf-8"),
        "Empty File (0 bytes)": (b"", "utf-8"),
    }
    for label, (payload, enc) in cases.items():
        print(f"- {label:30s} -> {safe_ingest_csv(payload, enc)}")

def test_sql_injection():
    print("\n=== 2. SQL INJECTION: STRING CONCATENATION (+) vs PARAMETERIZED (?) ===")
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE aq (station TEXT, day TEXT, pm25 REAL)")
    con.executemany("INSERT INTO aq VALUES (?, ?, ?)", [
        ("Adyar", "2026-10-01", 48.0),
        ("Guindy", "2026-10-01", 95.0),
        ("St. Thomas Mount", "2026-10-01", 72.0),
    ])

    malicious_input = "Adyar' OR '1'='1"
    # Unsafe concatenation
    unsafe_sql = "SELECT station, pm25 FROM aq WHERE station = '" + malicious_input + "'"
    unsafe_rows = con.execute(unsafe_sql).fetchall()
    print(f"Unsafe (+) Query : {unsafe_sql}")
    print(f"Unsafe (+) Result: {unsafe_rows}  <-- DATA LEAK! Returned entire table!")

    # Safe parameterized query
    safe_rows = con.execute("SELECT station, pm25 FROM aq WHERE station = ?", (malicious_input,)).fetchall()
    print(f"Safe (?) Result  : {safe_rows}  <-- SAFE! Treated literally as station name.")

    # Legitimate station name containing an apostrophe
    apostrophe_station = "St. Thomas Mount"
    legit_rows = con.execute("SELECT station, pm25 FROM aq WHERE station = ?", (apostrophe_station,)).fetchall()
    print(f"Legit quote name : {legit_rows}")
    con.close()

POSITIVE = {"good", "clean", "fast", "helpful", "improved"}
NEGATIVE = {"bad", "dirty", "slow", "rude", "smoke", "broken"}
NEGATORS = {"not", "never", "no"}

def score(text):
    words = text.lower().replace(".", " ").replace(",", " ").replace("!", " ").split()
    total = 0
    for i, w in enumerate(words):
        val = 1 if w in POSITIVE else (-1 if w in NEGATIVE else 0)
        if val != 0 and i > 0 and words[i - 1] in NEGATORS:
            val = -val
        total += val
    return total

def label(text):
    s = score(text)
    return "positive" if s > 0 else "negative" if s < 0 else "neutral"

def test_adversarial_sentiment():
    print("\n=== 3. ADVERSARIAL SENTIMENT INPUTS ===")
    adversarial_sentences = [
        ("Sarcasm", "Oh great, another wonderful morning choking on thick black smoke, so helpful!", "negative"),
        ("Double Negative", "The air quality is not never bad here anymore.", "positive"),
        ("Mixed Opinion", "The new sensor display is fast and helpful, though the factory smoke is bad.", "mixed/negative"),
    ]
    for category, text, expected in adversarial_sentences:
        pred = label(text)
        print(f"- [{category:15s}] Predicted={pred:8s} | Expected={expected:14s} | Text: {text}")

def benchmark_executemany_vs_loop():
    print("\n=== 4. ALTERNATIVE ANALYSIS: executemany() vs execute() IN LOOP ===")
    for n in [1_000, 20_000, 100_000]:
        rows = [("Adyar", "2026-10-01", float(i % 150)) for i in range(n)]

        con1 = sqlite3.connect(":memory:")
        con1.execute("CREATE TABLE aq (station TEXT, day TEXT, pm25 REAL)")
        t0 = time.perf_counter()
        for r in rows:
            con1.execute("INSERT INTO aq VALUES (?, ?, ?)", r)
        con1.commit()
        t_loop = time.perf_counter() - t0
        con1.close()

        con2 = sqlite3.connect(":memory:")
        con2.execute("CREATE TABLE aq (station TEXT, day TEXT, pm25 REAL)")
        t0 = time.perf_counter()
        con2.executemany("INSERT INTO aq VALUES (?, ?, ?)", rows)
        con2.commit()
        t_many = time.perf_counter() - t0
        con2.close()

        print(f"Rows={n:>7,} | execute() loop: {t_loop:.4f}s | executemany(): {t_many:.4f}s (Speedup: {t_loop/t_many:.2f}x)")

if __name__ == "__main__":
    test_adversarial_files()
    test_sql_injection()
    test_adversarial_sentiment()
    benchmark_executemany_vs_loop()

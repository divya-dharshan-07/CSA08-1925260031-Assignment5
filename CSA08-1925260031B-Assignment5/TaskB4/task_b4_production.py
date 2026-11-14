import csv
import os
import random
import re
import sqlite3
import time
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPLAINTS_CSV = os.path.join(BASE_DIR, "complaints_50.csv")

POSITIVE = {"good", "clean", "fast", "helpful", "improved"}
NEGATIVE = {"bad", "dirty", "slow", "rude", "smoke", "broken"}
NEGATORS = {"not", "never", "no"}
STOPWORDS = {"the", "is", "in", "at", "and", "to", "a", "of", "for", "on", "with", "was", "were", "are", "this", "that", "it", "by", "from", "all", "has", "have"}

def score(text):
    words = re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()
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

def extractive_summary_freq(corpus_texts, top_k=3):
    all_sentences = []
    word_freq = Counter()
    for text in corpus_texts:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        for s in sents:
            all_sentences.append(s)
            tokens = [w for w in re.sub(r"[^a-z0-9\s]", " ", s.lower()).split() if w not in STOPWORDS and len(w) > 2]
            word_freq.update(tokens)

    scored = []
    for idx, s in enumerate(all_sentences):
        tokens = [w for w in re.sub(r"[^a-z0-9\s]", " ", s.lower()).split() if w not in STOPWORDS and len(w) > 2]
        sent_score = sum(word_freq[w] for w in tokens) / (len(tokens) ** 0.5 + 1e-9)
        scored.append((sent_score, idx, s))

    top = sorted(scored, key=lambda x: x[0], reverse=True)[:top_k]
    top_ordered = [s for _, _, s in sorted(top, key=lambda x: x[1])]
    return top_ordered

def extractive_summary_first_k(corpus_texts, top_k=3):
    first_sents = []
    for text in corpus_texts:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        if sents:
            first_sents.append(sents[0])
        if len(first_sents) == top_k:
            break
    return first_sents

def evaluate_50_complaints():
    print("=== B4.1: SENTIMENT & EXTRACTIVE SUMMARY ON 50 COMPLAINTS ===")
    rows = []
    with open(COMPLAINTS_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((r["complaint"], r["human_label"]))

    agreed = 0
    disagreements = []
    for text, human in rows:
        pred = label(text)
        if pred == human:
            agreed += 1
        else:
            disagreements.append((pred, human, text))

    print(f"Human Agreement: {agreed}/{len(rows)} ({agreed/len(rows)*100:.1f}%)")
    print("Sample Disagreements:")
    for pred, human, text in disagreements[:3]:
        print(f"  - Pred={pred:8s} vs Human={human:8s} | {text}")

    corpus = [t for t, _ in rows]
    t0 = time.perf_counter()
    freq_sum = extractive_summary_freq(corpus, top_k=3)
    t_freq = time.perf_counter() - t0

    t0 = time.perf_counter()
    first_sum = extractive_summary_first_k(corpus, top_k=3)
    t_first = time.perf_counter() - t0

    print(f"\nFrequency-Based Top-3 Summary ({t_freq*1000:.3f} ms):")
    for s in freq_sum:
        print(f"  * {s}")
    print(f"First-K Baseline Summary ({t_first*1000:.3f} ms):")
    for s in first_sum:
        print(f"  * {s}")

def benchmark_index_effect():
    print("\n=== B4.2: COMPOSITE INDEX (station, day) QUERY BENCHMARK ===")
    random.seed(99)
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE readings (station TEXT, day TEXT, quarter_hour INT, pm25 REAL)")
    batch = []
    for st in range(1, 113):
        st_name = f"ST_{st:03d}"
        for d in range(1, 31):
            day_str = f"2026-10-{d:02d}"
            for q in range(96):
                batch.append((st_name, day_str, q, round(random.uniform(25, 140), 1)))
    con.executemany("INSERT INTO readings VALUES (?, ?, ?, ?)", batch)
    con.commit()

    query = "SELECT day, AVG(pm25), MAX(pm25) FROM readings WHERE station = 'ST_085' AND day BETWEEN '2026-10-10' AND '2026-10-20' GROUP BY day"

    t0 = time.perf_counter()
    for _ in range(100):
        con.execute(query).fetchall()
    t_no_idx = (time.perf_counter() - t0) / 100.0

    t_idx_build0 = time.perf_counter()
    con.execute("CREATE INDEX idx_readings_station_day ON readings(station, day)")
    con.commit()
    t_idx_build = time.perf_counter() - t_idx_build0

    t0 = time.perf_counter()
    for _ in range(100):
        con.execute(query).fetchall()
    t_with_idx = (time.perf_counter() - t0) / 100.0

    print(f"Rows in table          : {len(batch):,}")
    print(f"Index creation time    : {t_idx_build*1000:.2f} ms")
    print(f"Avg query WITHOUT index: {t_no_idx*1000:.4f} ms")
    print(f"Avg query WITH index   : {t_with_idx*1000:.4f} ms (Speedup: {t_no_idx/t_with_idx:.1f}x faster)")
    con.close()

if __name__ == "__main__":
    evaluate_50_complaints()
    benchmark_index_effect()

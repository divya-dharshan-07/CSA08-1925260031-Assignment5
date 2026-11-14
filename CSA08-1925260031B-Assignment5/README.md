# CSA08 - Python Programming: Assignment 5 (CO5)
**Data Acquisition, Cleaning, Analysis and AI Applications**

- **Student Name:** Divya Dharshan
- **Register Number:** 1925260031B
- **Repository Name:** `CSA08-1925260031B-Assignment5`
- **Python Version:** Python 3.15.2

## Libraries Used (`requirements.txt`)
- `pandas` (Data manipulation, grouping, and benchmark comparison)
- `matplotlib` (Data visualization and chart generation)
- Standard Library: `csv`, `sqlite3`, `statistics`, `re`, `time`, `timeit`, `cProfile`, `pstats`, `logging`, `math`, `random`

## Repository Structure
```
CSA08-1925260031B-Assignment5/
├── README.md
├── requirements.txt
├── PartA_Design/
│   ├── TaskA1/TaskA1_Data_Acquisition_Design.md
│   ├── TaskA2/TaskA2_Cleaning_Normalisation_Design.md
│   ├── TaskA3/TaskA3_Analysis_Visualisation_Design.md
│   ├── TaskA4/TaskA4_Debugging_Profiling_Plan.md
│   └── TaskA5/TaskA5_AI_Application_Design.md
├── TaskB1/
│   ├── raw_air_quality.csv
│   ├── task_b1_complete_code.py
│   ├── task_b1_pipeline.py
│   ├── air_quality.db
│   ├── cleaned_air_quality.csv
│   ├── chart1_pm25_trend.png
│   ├── chart2_station_comparison.png
│   ├── chart3_temp_vs_pm25.png
│   ├── chart4_hourly_boxplot.png
│   └── output_log.txt
├── TaskB2/
│   ├── task_b2_complete_code.py
│   ├── task_b2_adversarial.py
│   └── output_log.txt
├── TaskB3/
│   ├── task_b3_benchmark.py
│   └── output_log.txt
└── TaskB4/
    ├── complaints_50.csv
    ├── task_b4_complete_code.py
    ├── task_b4_production.py
    └── output_log.txt
```

## Commands to Run Each Program
```bash
# Install dependencies
pip install -r requirements.txt

# Task B1: Complete the Code & Full Cleaning/SQL/Visualisation Pipeline
python TaskB1/task_b1_complete_code.py
python TaskB1/task_b1_pipeline.py

# Task B2: Complete the Code & Adversarial Testing
python TaskB2/task_b2_complete_code.py
python TaskB2/task_b2_adversarial.py

# Task B3: Loops vs Pandas vs SQL Benchmark & cProfile
python TaskB3/task_b3_benchmark.py

# Task B4: Complete the Code & 50-Complaint Evaluation + Index Benchmark
python TaskB4/task_b4_complete_code.py
python TaskB4/task_b4_production.py
```

## Summary of Results
- **Part A (Tasks A1–A5):** Complete architectural design, normalized SQLite schema (`stations` and `readings`), SIMATS-standard algorithmic pseudocode, cleaning/normalization rules, debugging/profiling plans, and lexicon-based NLP + rule-based chatbot specifications.
- **Task B1:** Cleaned raw multi-station CSV containing missing values (`NA`, blanks), sensor faults (`-5`, `1450`), duplicates, and Fahrenheit temperatures; loaded into SQLite (`air_quality.db`); generated 4 analytical charts (`chart1`–`chart4`); benchmarked `csv` loops vs `pandas` up to 1,000,000 rows.
- **Task B2:** Verified resilience against missing columns, wrong delimiters, Latin-1 encoding, and empty files; demonstrated SQL injection defense using parameterized `?` queries; identified sentiment scorer edge cases (sarcasm, double negatives, mixed sentiment).
- **Task B3:** Verified numerical parity across plain Python loops, `pandas.groupby`, and SQL `GROUP BY`; benchmarked scaling across 1, 12, and 120 stations (~1.05M rows) and profiled bottlenecks via `cProfile`.
- **Task B4:** Evaluated lexicon sentiment scorer and extractive summarizer on 50 citizen complaints (~82% human agreement); measured composite index `(station, day)` query speedup (~8x–12x faster); formulated production architecture for 112 stations at 15-minute intervals and 50,000 monthly complaints.

> **Note on Progressive Git Commits:** Commit each folder (`PartA_Design`, `TaskB1`, `TaskB2`, `TaskB3`, `TaskB4`) individually with descriptive commit messages rather than a single bulk upload.

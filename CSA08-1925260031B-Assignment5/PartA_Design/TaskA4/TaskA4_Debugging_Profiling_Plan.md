# TASK A4 – PLAN DEBUGGING AND PROFILING (4 Marks | K4 – Analyse)

## A4.1 – Debugging Plan (2 Marks)
1. **`print()` Statements (Quick Ad-Hoc Inspection):**
   - Used during initial prototyping on small sample files to inspect raw split tokens, verify Fahrenheit-to-Celsius conversion formulas on sample records, and confirm row counts before/after filtering.
2. **`assert` Statements (Design-by-Contract Invariants):**
   - Embedded directly in the cleaning pipeline to catch silent corruption immediately:
     - `assert 0.0 <= pm25 <= 999.0, f"Invalid PM2.5 leaked: {pm25}"`
     - `assert -10.0 <= temp_c <= 60.0, f"Unconverted Fahrenheit suspected: {temp_c}"`
     - `assert len(iso_date) == 10 and iso_date[4] == "-", f"Malformed date: {iso_date}"`
3. **`logging` Module (Structured Severity-Based Audit Trail):**
   - Configured with `logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")`:
     - `DEBUG`: Trace individual row transformations and forward-fill steps.
     - `INFO`: Record batch file ingestion counts and database commit milestones.
     - `WARNING`: Log dropped sensor faults (`pm25 = -5.0` or `1450.0`) and duplicate keys without halting execution.
     - `ERROR`: Capture malformed CSV schemas or encoding failures.
4. **`pdb` / IDE Debugger (Interactive Step-Through):**
   - Use `breakpoint()` (Python 3.7+ `pdb`) or VS Code breakpoints when complex edge cases occur (e.g., consecutive missing values crossing midnight boundaries) to inspect local variables (`p row`, `p prev_pm25`), step line-by-line (`n`), and inspect call frames (`w`).

---

## A4.2 – Profiling Plan (2 Marks)
1. **`time.perf_counter()` (Macro Wall-Clock Benchmarking):**
   - Wrap major pipeline stages (`acquire_and_clean()`, `sqlite_executemany()`, `sql_query()`, `plot_charts()`) with `t0 = time.perf_counter()` and `elapsed = time.perf_counter() - t0` to measure end-to-end execution latency at 1, 12, and 120 stations.
2. **`timeit` (Micro-Benchmarking Alternatives):**
   - Isolate competing implementations (e.g., `csv.DictReader` vs. `csv.reader`, or `executemany()` vs. looped `execute()`) over repeated trials (`number=100`) with garbage collection controlled to obtain low-variance microsecond timings.
3. **`cProfile` + `pstats` (Function-Level Hotspot Profiling):**
   - Run `cProfile.run("run_pipeline()", "profile.stats")` and sort by `cumtime` and `tottime` (`pstats.Stats("profile.stats").sort_stats("tottime").print_stats(15)`) to pinpoint exact functions consuming CPU time (e.g., `datetime.strptime`, string `.strip()`, or `sqlite3` cursor calls).

---

## Algorithmic Pseudocode (SIMATS Engineering Standard)
```text
ALGORITHM InstrumentedCleaningPipeline
INPUT: inputFile (file path), logLevel (logging level)
OUTPUT: cleanedData (list), elapsedSeconds (float)

BEGIN
    CONFIGURE LOGGER WITH LEVEL logLevel
    SET startTime <- CALL PERF_COUNTER()
    CREATE cleanedData AS empty LIST

    FOR EACH row IN READ_CSV(inputFile) DO
        IF row.pm25 < 0 OR row.pm25 > 999 THEN
            LOG WARNING "Dropped out-of-range PM2.5: " + row.pm25
            CONTINUE
        ENDIF
        ASSERT row.pm25 >= 0 AND row.pm25 <= 999
        APPEND row TO cleanedData
    ENDFOR

    SET elapsedSeconds <- CALL PERF_COUNTER() - startTime
    LOG INFO "Cleaned " + LENGTH(cleanedData) + " rows in " + elapsedSeconds + "s"
    RETURN cleanedData, elapsedSeconds
END
```

---

## Alternative Concept & Complexity Analysis
**Alternative Concept (`print()` Statements for All Debugging vs. `logging` + Debugger):**
If thousands of `print()` calls are left inside row-processing loops instead of using `logging` and `pdb`:
- **Extra Time Added by Thousands of Calls:**
  - Every `print()` executes a synchronous system call (`write()` to `stdout` / terminal buffer) and forces terminal scrolling/rendering. For $n = 100,000$ rows, 100,000 `print()` statements add **0.5 to 3.0 seconds** of I/O blocking overhead ($O(n)$ system calls), often exceeding the actual computation time ($0.08$ seconds).
  - By contrast, when `logging` is set to `WARNING` or `ERROR`, `logger.debug()` checks an integer threshold in memory (`if self.isEnabledFor(DEBUG)`) and returns immediately in nanoseconds without formatting strings or performing I/O.
- **How Each Approach Is Switched Off in Production:**
  - **`print()`:** Must be manually commented out or deleted across every source file (error-prone and clutters git diffs), or overridden by reassigning `builtins.print = lambda *a, **k: None`.
  - **`logging`:** Switched off cleanly in **one line** at startup (`logging.getLogger().setLevel(logging.WARNING)` or `logging.disable(logging.CRITICAL)`) without touching application logic.
  - **`assert`:** Disabled globally at runtime by launching Python with the optimize flag (`python -O script.py`), which sets `__debug__ = False` and strips assert bytecode at compile time.
  - **`pdb`:** Setting environment variable `PYTHONBREAKPOINT=0` disables all `breakpoint()` calls in production.

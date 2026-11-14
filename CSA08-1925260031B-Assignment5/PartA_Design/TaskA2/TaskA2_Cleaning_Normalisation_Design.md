# TASK A2 – DESIGN THE CLEANING AND NORMALISATION (5 Marks | K4 – Analyse)

## A2.1 – Cleaning Rules & Justification (2 Marks)
1. **Missing Values (`""`, `"NA"`, `"null"`, `"NaN"`):**
   - *Rule:* For short gaps ($\le 2$ consecutive hours) within the same station and day, apply **forward fill** (`ffill`) using the previous valid hourly reading; for longer gaps or isolated single-row tasks, **impute with the station's daily median** (or drop if the entire day is missing).
   - *Justification:* Air pollution exhibits strong short-term temporal autocorrelation over 1–2 hours, making forward fill accurate without distorting diurnal curves; median imputation resists skew from pollution spikes.
2. **Impossible Values (Sensor Faults):**
   - *Rule:* Treat any value outside valid physical bounds ($PM_{2.5} \notin [0, 999]$, $PM_{10} \notin [0, 2000]$, $NO_2 \notin [0, 1000]$, $T_C \notin [-10, 60]$) as invalid (`NULL`/dropped).
   - *Justification:* Negative concentrations are physically impossible, and extreme spikes ($>999$) indicate electrical hardware saturation rather than true ambient air quality.
3. **Duplicate Rows:**
   - *Rule:* Deduplicate on composite natural key `(station_id, date, hour)`, retaining the first valid occurrence.
   - *Justification:* Network retries duplicate identical telemetry packets; keeping duplicates artificially inflates sample counts ($N$) and biases weighted averages.
4. **Fahrenheit Temperatures:**
   - *Rule:* For stations flagged with unit `'F'` (or detected where $T > 55$), convert to Celsius using $T_C = \frac{5}{9}(T_F - 32)$ rounded to 2 decimal places.
   - *Justification:* Mixing $^\circ F$ ($86^\circ$) and $^\circ C$ ($30^\circ$) corrupts city-wide temperature averages and correlation analyses with $PM_{2.5}$.

---

## A2.2 – Normalisation Design (2 Marks)
1. **Min–Max Normalisation ($[0, 1]$ scaling):**
   $$x_{\text{norm}} = \frac{x - x_{\min}}{x_{\max} - x_{\min}}$$
   - *When Appropriate:* Use when bounded inputs in $[0, 1]$ are required—such as feeding $PM_{2.5}$, $PM_{10}$, $NO_2$, and temperature into distance-based algorithms (k-NN), neural networks, or composite Air Quality Index (AQI) visual gauges where there are no extreme outliers.
2. **Z-Score Standardisation (Zero mean, unit variance):**
   $$z = \frac{x - \mu}{\sigma}$$
   - *When Appropriate:* Use when comparing deviations across stations with different baseline pollution levels, detecting statistical anomalies ($|z| > 3$), or training linear/logistic regression models when extreme pollution episodes (Diwali/industrial spikes) would compress Min–Max values near $0$.

---

## A2.3 – Standard Formats (1 Mark)
- **Dates:** ISO-8601 `YYYY-MM-DD` (e.g., `2026-10-01`) and 24-hour integer `hour` in `0..23`.
- **Station Names:** Stripped of leading/trailing whitespace, collapsed internal spaces, and Title Case (e.g., `"  anna   nagar "` $\rightarrow$ `"Anna Nagar"`).
- **Numbers:** IEEE-754 floating-point (`REAL`) rounded to **2 decimal places** for raw sensor measurements (`48.25`) and **3 decimal places** for normalized scores (`0.644`).

---

## Algorithmic Pseudocode (SIMATS Engineering Standard)
```text
ALGORITHM CleanAndNormaliseReadings
INPUT: rawRows (list of records), fahrenheitStations (set of station IDs)
OUTPUT: cleanRows (list of validated, normalised records)

BEGIN
    CREATE seenKeys AS empty SET
    CREATE validRows AS empty LIST
    SET prevPm25 <- NULL

    FOR EACH row IN rawRows DO
        SET stName <- TRIM(row.station_name) IN TITLE_CASE
        SET isoDate <- FORMAT_ISO_DATE(row.date)
        SET key <- (row.station_id, isoDate, row.hour)

        IF key IN seenKeys THEN
            CONTINUE
        ENDIF
        ADD key TO seenKeys

        IF row.pm25 IS EMPTY OR row.pm25 = "NA" THEN
            IF prevPm25 IS NOT NULL THEN
                SET pmVal <- prevPm25
            ELSE
                CONTINUE
            ENDIF
        ELSE
            SET pmVal <- PARSE_FLOAT(row.pm25)
        ENDIF

        IF pmVal < 0 OR pmVal > 999 THEN
            CONTINUE
        ENDIF
        SET prevPm25 <- pmVal

        SET tempVal <- PARSE_FLOAT(row.temperature)
        IF row.station_id IN fahrenheitStations THEN
            SET tempVal <- ROUND((tempVal - 32.0) * 5.0 / 9.0, 2)
        ENDIF

        APPEND (row.station_id, stName, isoDate, row.hour, ROUND(pmVal, 2), tempVal) TO validRows
    ENDFOR

    FIND minPm <- MINIMUM(pm25 IN validRows)
    FIND maxPm <- MAXIMUM(pm25 IN validRows)
    FOR EACH rec IN validRows DO
        SET rec.pm25_norm <- ROUND((rec.pm25 - minPm) / (maxPm - minPm), 3)
    ENDFOR

    RETURN validRows
END
```

---

## Alternative Concept & Complexity Analysis
**Alternative Concept (Dropping Missing Rows vs. Forward Fill vs. Median Imputation):**
If missing readings are simply dropped (`if pm25 in ("", "NA"): continue`) instead of imputed:
- **Effect on Daily Averages:** If sensor dropouts occur randomly, the sample mean remains unbiased; however, if sensors fail systematically during peak afternoon heat or rush-hour congestion, dropping rows **downward-biases daily averages** and reduces sample size $n$, widening confidence intervals.
- **Time Complexity:**
  - *Dropping Missing Rows:* Single linear pass checking for empty/NA values: **$O(n)$**.
  - *Forward Fill (`ffill`):* Single linear pass maintaining `last_valid` state variable: **$O(n)$**.
  - *Median Imputation:* Requires collecting $n$ valid values and either sorting ($O(n \log n)$) or using quickselect ($O(n)$ average, $O(n^2)$ worst case); standard `statistics.median()` sorts the slice in **$O(n \log n)$**.
- **Space Complexity:**
  - *Dropping / Forward Fill:* Streaming $O(1)$ auxiliary memory per station.
  - *Median Imputation:* Requires storing all $n$ values in memory to find the middle element: **$O(n)$ auxiliary space**.

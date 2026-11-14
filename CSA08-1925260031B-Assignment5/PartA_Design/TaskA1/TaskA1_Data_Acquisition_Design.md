# TASK A1 – DESIGN THE DATA ACQUISITION (7 Marks | K3 – Apply)

## A1.1 – Inspect the Source (2 Marks)
Each of the 12 air-quality monitoring stations transmits a daily CSV file with comma-separated headers:
`station_id,station_name,date,hour,pm25,pm10,no2,temperature`

### Expected Data-Quality Problems & Examples
1. **Missing Values (`NA`, `null`, blank cells):** Sensor dropouts leave empty strings or literal `"NA"`.
   - *Example:* `ST01,Adyar,2026-10-02,14,NA,88.0,32.1,31.5` or `ST01,Adyar,2026-10-03,09,,76.4,29.0,30.2`
2. **Impossible / Out-of-Range Values (Sensor Faults):** Negative pollutant concentrations or values exceeding physical sensor ceilings ($PM_{2.5} > 999\ \mu g/m^3$, $PM_{10} > 2000\ \mu g/m^3$, $NO_2 > 1000\ \mu g/m^3$, or temperature outside $[-10^\circ C, 60^\circ C]$).
   - *Example:* `ST02,Guindy,2026-10-02,11,-5.0,110.2,41.0,32.0` and `ST02,Guindy,2026-10-04,16,1450.0,120.5,45.2,33.1`
3. **Inconsistent Temperature Units (Fahrenheit vs. Celsius):** Two stations report temperature in Fahrenheit ($^\circ F$) instead of Celsius ($^\circ C$).
   - *Example:* `ST05,Anna Nagar,2026-10-01,13,62.0,104.0,38.0,89.6` ($89.6^\circ F = 32.0^\circ C$)
4. **Duplicate Rows:** Retransmission glitches repeat identical `(station_id, date, hour)` records.
   - *Example:* Two identical rows for `ST01,Adyar,2026-10-01,08,48.0,82.0,27.5,29.4`
5. **Inconsistent Formatting (Dates, Casing, Whitespace):** Mixed date formats (`01/10/2026` vs `2026-10-01`) and trailing spaces/lowercase names (`" adyar "` vs `"Adyar"`).

---

## A1.2 – Design the Storage (3 Marks)
A normalized two-table SQLite relational schema eliminates redundant station metadata and enforces referential and domain integrity:

### Table 1: `stations`
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `station_id` | `TEXT` | `PRIMARY KEY` | Unique station code (e.g., `ST01`) |
| `station_name` | `TEXT` | `NOT NULL UNIQUE` | Standardized Title Case name (e.g., `Adyar`) |
| `temp_unit` | `TEXT` | `NOT NULL CHECK(temp_unit IN ('C','F'))` | Native sensor unit before normalization |

### Table 2: `readings`
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `reading_id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Surrogate row identifier |
| `station_id` | `TEXT` | `NOT NULL REFERENCES stations(station_id)` | Foreign key linking to `stations` |
| `day` | `TEXT` | `NOT NULL` | ISO-8601 date (`YYYY-MM-DD`) |
| `hour` | `INTEGER` | `NOT NULL CHECK(hour BETWEEN 0 AND 23)` | Hour of day (`0`–`23`) |
| `pm25` | `REAL` | `CHECK(pm25 >= 0 AND pm25 <= 999)` | Fine particulate matter ($\mu g/m^3$) |
| `pm10` | `REAL` | `CHECK(pm10 >= 0 AND pm10 <= 2000)` | Coarse particulate matter ($\mu g/m^3$) |
| `no2` | `REAL` | `CHECK(no2 >= 0 AND no2 <= 1000)` | Nitrogen dioxide ($\mu g/m^3$) |
| `temp_c` | `REAL` | `CHECK(temp_c BETWEEN -10 AND 60)` | Normalized Celsius temperature |
| — | — | `UNIQUE(station_id, day, hour)` | Prevents duplicate hourly entries |

**CSV-to-SQLite Mapping:** `station_id` and cleaned `station_name` map to `stations`; `date` is parsed to ISO `YYYY-MM-DD` (`day`); `hour` is cast to `INTEGER`; `pm25`, `pm10`, and `no2` are cast to `REAL`; `temperature` is converted to Celsius if `temp_unit == 'F'` and stored in `temp_c`.

---

## A1.3 – CSV or SQL? (2 Marks)
| Typical Board Question | Reading Raw CSV Files | Querying Indexed SQLite Database |
| :--- | :--- | :--- |
| **1. Average $PM_{2.5}$ of Adyar in October** | Must open all 31 daily CSV files for Adyar, parse strings, filter invalid values, and accumulate sum/count in Python ($O(N)$ I/O + parsing). | Single indexed lookup `SELECT AVG(pm25) FROM readings WHERE station_id='ST01' AND day LIKE '2026-10-%'` ($O(\log N + k)$). |
| **2. Top 3 stations with highest peak $NO_2$** | Must scan all $12 \times 365 = 4,380$ daily CSV files across all directories and track maximums in dictionaries. | `SELECT station_id, MAX(no2) FROM readings GROUP BY station_id ORDER BY MAX(no2) DESC LIMIT 3` executed in C inside SQLite engine. |
| **3. Hours where $PM_{2.5} > 150$ and Temp $> 35^\circ C$** | Must apply unit conversion and dual conditional filtering on every line of every CSV repeatedly. | Pre-cleaned `temp_c` allows direct `SELECT * FROM readings WHERE pm25 > 150 AND temp_c > 35` using B-tree index scan. |

---

## Algorithmic Pseudocode (SIMATS Engineering Standard)
```text
ALGORITHM AcquireAndStoreAirQuality
INPUT: csvFileList (list of daily CSV file paths), dbPath (string)
OUTPUT: insertedCount (integer)

BEGIN
    OPEN SQLite connection conn TO dbPath
    EXECUTE SQL "PRAGMA foreign_keys = ON"
    CREATE TABLE IF NOT EXISTS stations (station_id TEXT PRIMARY KEY, station_name TEXT, temp_unit TEXT)
    CREATE TABLE IF NOT EXISTS readings (reading_id INTEGER PRIMARY KEY, station_id TEXT, day TEXT, hour INTEGER, pm25 REAL, pm10 REAL, no2 REAL, temp_c REAL, UNIQUE(station_id, day, hour))
    SET insertedCount <- 0

    FOR EACH filePath IN csvFileList DO
        OPEN filePath FOR READING AS csvFile
        READ headerRow FROM csvFile
        FOR EACH rawRow IN csvFile DO
            CALL CleanRecord(rawRow) RETURNING cleanedRecord, isValid
            IF isValid = TRUE THEN
                INSERT OR IGNORE INTO readings VALUES (cleanedRecord)
                IF rowInserted = TRUE THEN
                    SET insertedCount <- insertedCount + 1
                ENDIF
            ENDIF
        ENDFOR
        CLOSE csvFile
    ENDFOR

    COMMIT transaction ON conn
    CLOSE conn
    RETURN insertedCount
END
```

---

## Alternative Concept & Complexity Analysis
**Alternative Concept (CSV-Only + pandas DataFrame per Question):**
If no SQLite database is maintained and every query loads raw CSV files into a `pandas.DataFrame` on demand:
```python
df = pd.concat([pd.read_csv(f) for f in glob.glob("data/*.csv")], ignore_index=True)
# Re-clean on every run, then filter:
avg_pm25 = df[(df["station_name"] == "Adyar") & (df["date"].str.startswith("2026-10"))]["pm25"].mean()
```
- **Time Complexity per Question:**
  - *CSV + pandas:* Must read every file from disk, parse text into floats/strings, and perform a full boolean mask scan of all $n$ rows: **$O(n)$ per query** (plus high constant factor for CSV parsing).
  - *Indexed SQLite:* Data is parsed once during ingestion. A query filtered by an indexed `(station_id, day)` B-tree traverses height $\log_B(n)$ to locate the $k$ matching rows: **$O(\log n + k)$ per query**.
- **Space Complexity (Disk vs. Memory):**
  - *CSV + pandas:* Requires storing uncompressed text CSVs on disk *and* loading the entire $n$-row dataset into RAM simultaneously ($O(n)$ memory), risking `MemoryError` as stations grow.
  - *Indexed SQLite:* Stores compact binary pages + B-tree indexes on disk ($O(n)$ disk) while streaming only query results into RAM (**$O(1)$ or $O(k)$ working memory**).

# TASK A3 – DESIGN THE ANALYSIS AND VISUALISATION (5 Marks | K4 – Analyse)

## A3.1 – Chart Choices & Justification (3 Marks)
1. **Trend of $PM_{2.5}$ over a Month $\rightarrow$ Line Chart:**
   - *Justification:* Time (`day` 1 to 30/31) is a continuous ordered variable. A line chart connects sequential daily means, immediately revealing multi-day pollution episodes, weekend dips, and upward/downward trajectories.
2. **Comparison of Stations $\rightarrow$ Bar Chart (Grouped/Sorted Vertical Bar Chart):**
   - *Justification:* Station names (`Adyar`, `Guindy`, `Anna Nagar`, etc.) are discrete categorical entities. Comparing bar lengths from a zero baseline enables exact visual comparison of mean or peak pollutant levels across stations.
3. **Relationship between Temperature and $PM_{2.5}$ $\rightarrow$ Scatter Plot:**
   - *Justification:* Both temperature ($^\circ C$) and $PM_{2.5}$ ($\mu g/m^3$) are continuous numerical variables. Plotting $(T_i, PM_{2.5,i})$ pairs exposes linear/non-linear correlation, thermal inversion clusters, and bivariate outliers.
4. **Hours with the Worst Air $\rightarrow$ Box Plot (grouped by Hour `0`–`23`):**
   - *Justification:* Each hour of the day contains dozens of observations across days and stations. A box plot displays the median, interquartile range (IQR), and extreme spike whiskers for every hour (`0`–`23`), showing both typical rush-hour peaks and variability better than a single average.

---

## A3.2 – Design the Summary Table (2 Marks)
### Daily Station Summary Table (`daily_station_summary`)
| Column | Type | Description |
| :--- | :--- | :--- |
| `station_id` | `TEXT` | Station identifier (`PK` part 1) |
| `station_name` | `TEXT` | Standardized station name |
| `day` | `TEXT` | ISO date `YYYY-MM-DD` (`PK` part 2) |
| `min_pm25` | `REAL` | Minimum valid hourly $PM_{2.5}$ on that day |
| `max_pm25` | `REAL` | Maximum valid hourly $PM_{2.5}$ on that day |
| `mean_pm25` | `REAL` | Arithmetic mean of valid $PM_{2.5}$ readings |
| `valid_count` | `INTEGER` | Count of non-null, valid hourly readings (`0`–`24`) |

**How It Is Produced:** Executed directly inside SQLite via aggregation over indexed columns and materialized into a summary table or view:
```sql
SELECT r.station_id, s.station_name, r.day,
       ROUND(MIN(r.pm25), 2) AS min_pm25,
       ROUND(MAX(r.pm25), 2) AS max_pm25,
       ROUND(AVG(r.pm25), 2) AS mean_pm25,
       COUNT(r.pm25) AS valid_count
FROM readings r
JOIN stations s ON r.station_id = s.station_id
GROUP BY r.station_id, r.day
ORDER BY r.day, r.station_id;
```

---

## Algorithmic Pseudocode (SIMATS Engineering Standard)
```text
ALGORITHM GenerateDailySummarySQL
INPUT: dbConnection (active SQLite connection)
OUTPUT: summaryRows (list of daily summary tuples)

BEGIN
    DEFINE query <- "SELECT station_id, day, MIN(pm25), MAX(pm25), ROUND(AVG(pm25), 2), COUNT(pm25) FROM readings GROUP BY station_id, day ORDER BY day, station_id"
    EXECUTE query ON dbConnection RETURNING cursor
    FETCH ALL summaryRows FROM cursor
    RETURN summaryRows
END
```

---

## Alternative Concept & Complexity Analysis
**Alternative Concept (Python Loops after Reading All Rows vs. SQL `GROUP BY`):**
```python
# Python loop alternative:
groups = {}
for station, day, pm25 in all_rows:
    groups.setdefault((station, day), []).append(pm25)
summary = [(st, d, min(vals), max(vals), sum(vals)/len(vals), len(vals))
           for (st, d), vals in groups.items()]
```
- **Time Complexity:**
  - *Python Loops:* Reading $n$ rows into Python objects and hashing into dictionaries takes **$O(n)$** expected time (plus sorting keys $O(G \log G)$ where $G = \text{stations} \times \text{days}$), but incurs high Python bytecode interpretation overhead per row.
  - *SQL `GROUP BY`:* If an index exists on `(station_id, day)`, SQLite performs a sequential index scan in **$O(n)$** compiled C time without sorting; without an index, SQLite sorts in **$O(n \log n)$** C time—typically 5x–15x faster than pure Python loops.
- **Memory Complexity:**
  - *Python Loops (storing all rows):* Stores every raw tuple and list of values in Python heap memory: **$O(n)$ RAM**.
  - *SQL `GROUP BY` (with index):* Streams groups one bucket at a time in C, holding only accumulators (`min`, `max`, `sum`, `count`) for the current group and output table: **$O(G)$ output memory** (where $G \ll n$).

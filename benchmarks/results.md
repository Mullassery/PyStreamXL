# Benchmark Results

**Environment:** Apple Silicon (aarch64-apple-darwin), Python 3.13, Rust 1.96, macOS  
**File contents:** 10 columns — ID, Name, Value, Score, Category, Flag, Amount, Date, Code, Notes  
**Methods:**
- `streamxl` — `streamxl.read()` Rust streaming engine
- `openpyxl (read_only)` — `load_workbook(read_only=True)` + `iter_rows()`
- `openpyxl (full load)` — `load_workbook()` + `iter_rows()`

---

## 10,000 rows × 10 cols (0.5 MB)

| Library | Time | Peak RAM | Rows/sec |
|---------|------|----------|----------|
| **streamxl** | **0.40s** | 2.8 MB | **25,080/s** |
| openpyxl (read_only) | 1.52s | 1.5 MB | 6,570/s |
| openpyxl (full load) | 1.94s | 38.4 MB | 5,164/s |

streamxl: **3.8× faster** than read_only · **4.9× faster** than full load

---

## 50,000 rows × 10 cols (2.6 MB)

| Library | Time | Peak RAM | Rows/sec |
|---------|------|----------|----------|
| **streamxl** | **1.81s** | 13.8 MB | **27,572/s** |
| openpyxl (read_only) | 7.72s | 4.3 MB | 6,473/s |
| openpyxl (full load) | 9.83s | 186.3 MB | 5,085/s |

streamxl: **4.3× faster** than read_only · **5.4× faster** than full load

---

## 100,000 rows × 10 cols (5.2 MB)

| Library | Time | Peak RAM | Rows/sec |
|---------|------|----------|----------|
| **streamxl** | **3.59s** | 27.5 MB | **27,873/s** |
| openpyxl (read_only) | 15.80s | 8.1 MB | 6,331/s |
| openpyxl (full load) | 19.77s | 372.5 MB | 5,059/s |

streamxl: **4.4× faster** than read_only · **5.5× faster** than full load

---

## 250,000 rows × 10 cols (13.2 MB)

| Library | Time | Peak RAM | Rows/sec |
|---------|------|----------|----------|
| **streamxl** | **9.04s** | 68.7 MB | **27,651/s** |
| openpyxl (read_only) | 40.46s | 19.6 MB | 6,178/s |
| openpyxl (full load) | 50.67s | **911.3 MB** | 4,934/s |

streamxl: **4.5× faster** than read_only · **5.6× faster** than full load

---

## Summary

| Rows | streamxl | openpyxl read_only | openpyxl full | Speedup vs read_only | Memory (full load) |
|------|----------|--------------------|---------------|---------------------|--------------------|
| 10k  | 0.40s | 1.52s | 1.94s | 3.8× | 38 MB |
| 50k  | 1.81s | 7.72s | 9.83s | 4.3× | 186 MB |
| 100k | 3.59s | 15.80s | 19.77s | 4.4× | 373 MB |
| 250k | 9.04s | 40.46s | 50.67s | 4.5× | **911 MB** |

**Consistent ~4–5× speed advantage. openpyxl full load approaches 1 GB RAM at 250k rows.**

---

## Reproduce

```bash
# Install deps
pip install openpyxl streamxl

# Generate a test file
python -c "
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.append(['ID','Name','Value','Score','Category','Flag','Amount','Date','Code','Notes'])
for i in range(1, 100001):
    ws.append([i, f'User_{i}', i*1.5, round(i*0.37,2), f'Cat_{i%10}',
               i%2==0, i*100, f'2024-{(i%12)+1:02d}-01', f'CODE{i:06d}', f'Note {i}'])
wb.save('bench_100k.xlsx')
"

# Run benchmark
python benchmarks/openpyxl_vs_streamxl.py bench_100k.xlsx
```

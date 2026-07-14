# StreamXL Implementation Roadmap: The Data Engine for Spreadsheets

## Overview

**Timeline:** 46 weeks to v3.0 (Enterprise spreadsheet data platform)

- **v1.0** (Current): Foundation - High-performance streaming read/write, 60 tests ✅
- **v1.5** (Phase 1): Query Engine - Direct SQL, DuckDB integration (6 weeks)
- **v2.0** (Phase 2): Modern Integrations - Arrow, Polars, zero-copy (8 weeks)
- **v2.5** (Phase 3): Multi-File & AI - Dataset federation, AI context (10 weeks)
- **v3.0** (Phase 4): Enterprise Governance - Lineage, compliance, observability (12 weeks)
- **v3.5+** (Phase 5): Spreadsheet Operating Layer - Distributed, real-time, advanced

---

## Phase 1: Query Engine (v1.0 → v1.5) — 6 weeks | 240 hours

### 1.1 DuckDB Integration

**Goal:** Enable SQL queries directly on Excel files without import.

#### 1.1.1 DuckDB Binding Layer
```rust
// File: core/src/query/mod.rs

pub struct DuckDBConnector {
    conn: DuckDBConnection,
}

impl DuckDBConnector {
    pub fn query(&self, sql: &str) -> Result<RecordBatch> {
        // Execute SQL on Excel data
        // Return Arrow RecordBatches
    }
    
    pub fn register_excel(&mut self, path: &str, table_name: &str) -> Result<()> {
        // Register Excel file as queryable table
        // Auto-detect schema
        // Enable predicate pushdown
    }
}
```

**Tasks:**
- [ ] Implement DuckDB Rust FFI bindings
- [ ] Register Excel files as DuckDB tables
- [ ] Auto-detect schema from Excel
- [ ] Support multiple Excel sheets
- [ ] Handle NULL/None values properly
- [ ] Optimize for streaming ingestion
- [ ] Unit tests (20+ cases)
- [ ] Integration tests with DuckDB

**Success Criteria:** <100ms query time on 1M rows

#### 1.1.2 Python API
```python
import streamxl

# Direct SQL query
result = streamxl.query("SELECT * FROM 'data.xlsx' WHERE amount > 1000")

# Multiple sheets
result = streamxl.query("""
    SELECT t1.*, t2.category
    FROM 'data.xlsx'!Sheet1 t1
    LEFT JOIN 'data.xlsx'!Sheet2 t2 ON t1.id = t2.id
""")

# Aggregation
result = streamxl.query("""
    SELECT region, SUM(revenue), COUNT(*)
    FROM 'data.xlsx' WHERE date >= '2024-01-01'
    GROUP BY region
""")
```

**Tasks:**
- [ ] Implement Python `query()` function
- [ ] SQL parsing and validation
- [ ] Result formatting (dict, list, Arrow, Polars)
- [ ] Error handling and reporting
- [ ] Documentation with examples
- [ ] Type hints and IDE support

---

### 1.2 Predicate Pushdown

**Goal:** Filter data before loading into memory.

**Capabilities:**
- WHERE clause → filter during read
- Column projection → load only needed columns
- Date range filtering → skip irrelevant rows
- Numeric range filtering → efficient skipping

**Implementation:**
```rust
pub struct PredicateFilter {
    column: String,
    operator: FilterOp,  // >, <, ==, >=, <=, IN, BETWEEN
    value: CellValue,
}

impl PredicateFilter {
    pub fn matches(&self, cell: &CellValue) -> bool {
        // Efficient filtering during streaming read
    }
}
```

**Tasks:**
- [ ] Implement WHERE clause parsing
- [ ] Support comparison operators
- [ ] Support IN and BETWEEN
- [ ] Optimize for early termination
- [ ] Benchmark filtering overhead
- [ ] Unit tests

**Success Criteria:** Filtering adds <5% overhead

---

### 1.3 Column Projection

**Goal:** Load only needed columns.

```python
# Only load specific columns
result = streamxl.query("SELECT customer_id, amount FROM 'data.xlsx'")
# Only reads customer_id and amount columns, skips others
```

**Tasks:**
- [ ] Implement column projection in reader
- [ ] Skip unnecessary XML parsing
- [ ] Optimize memory usage
- [ ] Maintain performance

---

### 1.4 Query Optimization

**Goal:** Smart query planning.

**Tasks:**
- [ ] Analyze query structure
- [ ] Identify optimal predicate pushdown
- [ ] Plan column projection
- [ ] Order operations for efficiency
- [ ] Explain query plan to user

---

### 1.5 Testing & Quality

**Tasks:**
- [ ] 50+ integration tests
- [ ] Performance benchmarks
- [ ] SQL dialect coverage
- [ ] Edge case handling
- [ ] Error message quality

**Success Criteria:** All tests passing, comprehensive SQL coverage

---

## Phase 2: Modern Integrations (v1.5 → v2.0) — 8 weeks | 320 hours

### 2.1 Apache Arrow Integration

**Goal:** Zero-copy data transfer with Arrow format.

#### 2.1.1 Arrow RecordBatch Support
```rust
pub struct ArrowExporter {
    schema: ArrowSchema,
}

impl ArrowExporter {
    pub fn export_batches(&self, reader: RowIter) -> Vec<RecordBatch> {
        // Stream rows → collect into Arrow RecordBatches
        // Zero-copy when possible
    }
}
```

**Tasks:**
- [ ] Implement Arrow schema inference from Excel
- [ ] Stream rows → RecordBatches
- [ ] Handle all data types (string, number, bool, date, datetime)
- [ ] Optimize for minimal allocations
- [ ] Support columnar layouts
- [ ] Unit tests

**Success Criteria:** Zero-copy transfers, no performance regression

#### 2.1.2 Python API
```python
import streamxl
import pyarrow as pa

# Read as Arrow
reader = streamxl.read_arrow("large_file.xlsx")
table = pa.concat_tables(reader.batches())

# Stream Arrow data
for batch in streamxl.read_arrow("data.xlsx"):
    # Process batch (zero-copy)
    pass
```

**Tasks:**
- [ ] Implement `read_arrow()` function
- [ ] RecordBatch iterator support
- [ ] Table concatenation
- [ ] Type mapping validation
- [ ] Documentation and examples

---

### 2.2 Polars Integration

**Goal:** Seamless DataFrame bridge.

```python
import streamxl
import polars as pl

# Read as Polars DataFrame
df = streamxl.read_polars("data.xlsx")

# Stream and collect
df = pl.concat([
    streamxl.read_polars("data1.xlsx"),
    streamxl.read_polars("data2.xlsx"),
])

# Use Polars operations
result = df.filter(pl.col("amount") > 1000).group_by("region").sum()
```

**Tasks:**
- [ ] Implement Polars DataFrame export
- [ ] Use Arrow as intermediate format
- [ ] Type mapping (Excel → Polars)
- [ ] Lazy evaluation support
- [ ] Integration tests with Polars
- [ ] Performance benchmarks

---

### 2.3 Pandas Optimization

**Goal:** Better pandas integration.

**Current:** pandas already works via `read_all()` → Dict → DataFrame

**Enhanced:**
- Direct memory mapping
- Chunked reading
- Column selection optimization
- Type inference improvements

**Tasks:**
- [ ] Optimize conversion pipeline
- [ ] Support dtype specification
- [ ] Lazy loading support
- [ ] Memory profiling
- [ ] Benchmark vs openpyxl

---

### 2.4 DataFusion Integration

**Goal:** Local query engine alternative to DuckDB.

**Tasks:**
- [ ] Implement DataFusion adapter
- [ ] Register tables
- [ ] Support SQL queries
- [ ] Performance comparison with DuckDB
- [ ] Support both engines

---

### 2.5 Type System Enhancement

**Goal:** Advanced type inference and handling.

**Current:** Basic types (string, number, bool, date, datetime)

**Enhanced:**
- Decimal/Currency types
- UUID detection
- Categorical inference
- Duration/Interval types
- Nested types (lists, structs)

**Tasks:**
- [ ] Enhanced type detection
- [ ] Type hints in schema
- [ ] Conversion functions
- [ ] Validation rules per type
- [ ] Unit tests

---

## Phase 3: Multi-File & AI (v2.0 → v2.5) — 10 weeks | 400 hours

### 3.1 Multi-File Processing Engine

**Goal:** Treat 1000s of Excel files as unified datasets.

```python
import streamxl

# Process multiple files
files = streamxl.glob("data/monthly_*.xlsx")
combined = streamxl.read_multi(files, 
    schema_inference="auto",
    parallel=4,
    on_error="skip"
)

# Unified query
result = combined.query("""
    SELECT month, region, SUM(revenue)
    FROM tables
    GROUP BY month, region
""")

# Export combined
combined.write("combined_output.xlsx")
```

**Tasks:**
- [ ] Implement `glob()` file discovery
- [ ] `read_multi()` for loading multiple files
- [ ] Schema reconciliation (matching schemas across files)
- [ ] Parallel file processing (multi-threaded)
- [ ] Error handling (skip, retry, fail-fast modes)
- [ ] Incremental processing (process new files only)
- [ ] Metadata tracking (filename, load timestamp)
- [ ] Performance optimization

**Success Criteria:** Handle 1000+ files efficiently, <5s for 10K files

### 3.2 Dataset Federation

**Goal:** Query across multiple Excel files as if they're one table.

**Tasks:**
- [ ] Virtual table layer
- [ ] Distributed query planning
- [ ] File pruning (skip files not matching WHERE clause)
- [ ] Partition-aware processing
- [ ] Union/Join across files
- [ ] Aggregate functions

---

### 3.3 Automatic Schema Discovery

**Goal:** Infer schema from Excel files with confidence scoring.

```python
profile = streamxl.profile("dataset.xlsx", sample_size=10000)
print(profile.schema)
# Output:
# {
#   "customer_id": {"type": "integer", "confidence": 0.99},
#   "email": {"type": "string", "confidence": 0.98},
#   "signup_date": {"type": "date", "confidence": 0.95},
#   "balance": {"type": "decimal", "confidence": 0.87},
# }
```

**Tasks:**
- [ ] Smart type inference from samples
- [ ] Confidence scoring (0-1 scale)
- [ ] Handle mixed types
- [ ] Null value analysis
- [ ] Distribution analysis
- [ ] Outlier detection

---

### 3.4 AI Context Generation

**Goal:** Prepare spreadsheet data for LLM ingestion.

```python
import streamxl

# Generate AI-friendly context
context = streamxl.generate_ai_context("report.xlsx", max_tokens=2000)
print(context)
# Output:
# """
# Dataset: Q4_Financial_Report
# Rows: 1,250
# Columns: 8
#
# Schema:
# - date (datetime): Range 2024-10-01 to 2024-12-31
# - region (categorical): [US, EU, APAC, LATAM]
# - revenue (float): Mean $15,234, Median $10,000, Range $100-$500k
# - expense (float): Mean $8,945, Median $8,000, Range $50-$250k
# - profit (float): Mean $6,289, Median $2,000
#
# Key Insights:
# - APAC region highest revenue ($2.1M)
# - Profit margin highest in EU (42%)
# - Revenue trending up over Q4 (+12%)
#
# Sample data:
# | date | region | revenue | expense | profit |
# | 2024-10-01 | US | $15,000 | $8,000 | $7,000 |
# | 2024-10-02 | EU | $20,000 | $9,000 | $11,000 |
# ...
# """

# Use with LLM
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": f"Analyze this spreadsheet data:\n{context}\n\nWhat are the key findings?"
    }]
)
```

**Tasks:**
- [ ] Profile generation (schema, statistics, samples)
- [ ] Smart sampling for large files
- [ ] Statistical summaries
- [ ] Key insights extraction
- [ ] Format optimization for token counting
- [ ] Integration with Claude API
- [ ] Support other LLMs (GPT, Gemini, etc.)

**Success Criteria:** <1s generation time, accurate statistics

### 3.5 Data Quality Analysis

**Goal:** Automatic data quality scoring.

```python
quality = streamxl.analyze_quality("data.xlsx")
print(quality.score)  # 0-100
print(quality.issues)
# [
#   {"column": "email", "issue": "invalid_format", "count": 45, "severity": "high"},
#   {"column": "phone", "issue": "missing", "count": 123, "severity": "medium"},
# ]
```

**Tasks:**
- [ ] Null detection and scoring
- [ ] Type validation
- [ ] Format validation (email, phone, etc.)
- [ ] Range validation
- [ ] Business rule checking
- [ ] Duplicate detection
- [ ] Quality score calculation
- [ ] Remediation suggestions

---

## Phase 4: Enterprise Governance (v2.5 → v3.0) — 12 weeks | 480 hours

### 4.1 Lineage Tracking

**Goal:** Track data origins and transformations.

```python
import streamxl

# Track source
data = streamxl.read("sales.xlsx")
data.metadata.lineage = {
    "source": "CRM system export",
    "extracted_at": "2024-01-15T10:30:00Z",
    "extracted_by": "etl_pipeline_v2",
    "original_file": "s3://exports/2024-01-15/sales.parquet"
}

# Query preserves lineage
query_result = streamxl.query("SELECT region, SUM(amount) FROM sales GROUP BY region")
query_result.metadata.lineage.append({
    "operation": "aggregation",
    "query": "SELECT region, SUM(amount) FROM sales GROUP BY region",
    "timestamp": "2024-01-15T14:00:00Z"
})

# Trace → BI Dashboard
dashboard.data = query_result
dashboard.metadata.lineage  # Full chain visible
```

**Tasks:**
- [ ] Lineage model (source → transformations → output)
- [ ] Automatic tracking
- [ ] Lineage visualization
- [ ] Downstream impact analysis
- [ ] Version tracking

---

### 4.2 Metadata Management

**Goal:** Rich metadata for governance.

```python
data.metadata = {
    "owner": "finance@company.com",
    "classification": "confidential",
    "sla": {
        "freshness_hours": 24,
        "availability_pct": 99.9,
    },
    "tags": ["financial", "monthly", "automated"],
    "description": "Q4 financial reconciliation export",
    "created_at": "2024-01-15T10:00:00Z",
    "last_modified": "2024-01-15T14:00:00Z",
}
```

**Tasks:**
- [ ] Metadata schema
- [ ] Metadata storage
- [ ] Metadata validation
- [ ] Search and filtering
- [ ] Catalog integration

---

### 4.3 Compliance Reporting

**Goal:** Audit trails for regulations.

**Tasks:**
- [ ] Access logging
- [ ] Change tracking
- [ ] Data usage reports
- [ ] Compliance dashboards
- [ ] Export for auditors

---

### 4.4 Data Quality Enforcement

**Goal:** Prevent bad data from entering pipelines.

```python
import streamxl

policy = streamxl.ValidationPolicy(
    required_columns=["id", "amount", "date"],
    column_rules={
        "amount": {"type": "float", "min": 0, "max": 1000000},
        "date": {"type": "date", "after": "2020-01-01"},
        "status": {"values": ["active", "inactive", "pending"]},
    },
    row_rules=[
        "amount > 0 OR status = 'inactive'",
    ],
    duplicates={"columns": ["id"], "allowed": False},
)

# Validate on read
try:
    data = streamxl.read("data.xlsx", validate=policy)
except streamxl.ValidationError as e:
    print(e.issues)
    # Quarantine bad file
    streamxl.quarantine("data.xlsx", reason=str(e))
```

**Tasks:**
- [ ] Validation rule engine
- [ ] Error reporting
- [ ] Quarantine system
- [ ] Automatic remediation (when possible)
- [ ] Audit logging

---

## Phase 5: Spreadsheet Operating Layer (v3.0+) — Ongoing

### 5.1 Distributed Processing

**Goal:** Spark and Ray integration for massive scale.

**Tasks:**
- [ ] Spark DataFrame integration
- [ ] Distributed file reading
- [ ] RDD API support
- [ ] Ray integration
- [ ] Distributed aggregations

### 5.2 Real-Time Streaming

**Goal:** Ingest Excel data in real-time.

**Tasks:**
- [ ] File watching (new Excel files trigger ingestion)
- [ ] Kafka producer (export to streaming)
- [ ] Incremental updates
- [ ] Change data capture

### 5.3 Advanced Query Optimization

**Goal:** Production-grade query engine.

**Tasks:**
- [ ] Query cost estimation
- [ ] Caching strategies
- [ ] Index support
- [ ] Statistics-based optimization

---

## Code Structure (Target)

```
StreamXL/
├── core/
│   ├── src/
│   │   ├── lib.rs
│   │   ├── stream.rs (existing)
│   │   ├── sheet_parser.rs (existing)
│   │   ├── shared_strings.rs (existing)
│   │   ├── query/
│   │   │   ├── mod.rs
│   │   │   ├── duckdb.rs (v1.5)
│   │   │   ├── datafusion.rs (v2.0)
│   │   │   ├── optimizer.rs (v3.0)
│   │   │   └── planner.rs (v3.0)
│   │   ├── integrations/
│   │   │   ├── arrow.rs (v2.0)
│   │   │   ├── polars.rs (v2.0)
│   │   │   └── spark.rs (v3.5)
│   │   ├── multi_file/
│   │   │   ├── mod.rs (v2.5)
│   │   │   ├── federation.rs
│   │   │   └── parallel.rs
│   │   ├── governance/
│   │   │   ├── mod.rs (v3.0)
│   │   │   ├── lineage.rs
│   │   │   ├── metadata.rs
│   │   │   ├── validation.rs
│   │   │   └── audit.rs
│   │   └── ai/
│   │       ├── profiler.rs (v2.5)
│   │       ├── schema_inference.rs
│   │       └── context.rs
│   └── Cargo.toml
│
├── python/
│   ├── src/
│   │   └── lib.rs (PyO3 bindings)
│   ├── streamxl/
│   │   ├── __init__.py
│   │   ├── reader.py
│   │   ├── writer.py
│   │   ├── query.py (v1.5)
│   │   ├── integrations.py (v2.0)
│   │   ├── multi_file.py (v2.5)
│   │   ├── governance.py (v3.0)
│   │   ├── ai.py (v2.5)
│   │   └── cli.py
│   └── Cargo.toml
│
├── tests/
│   ├── test_basic.py (existing)
│   ├── test_query.py (v1.5)
│   ├── test_integrations.py (v2.0)
│   ├── test_multi_file.py (v2.5)
│   ├── test_governance.py (v3.0)
│   └── benchmarks/ (ongoing)
```

---

## Success Metrics

| Metric | Target | Timeline |
|--------|--------|----------|
| Query latency (1M rows) | <100ms | v1.5 |
| Arrow zero-copy transfer | 0% overhead | v2.0 |
| Multi-file throughput | 1000 files/min | v2.5 |
| AI context generation | <1s | v2.5 |
| Governance audit completeness | 99.9% | v3.0 |
| Adoption | 1K teams (v2.0), 10K teams (v3.0) | v2.0-v3.0 |

---

## Effort Estimates

| Phase | Component | Effort | Timeline |
|-------|-----------|--------|----------|
| 1 | Query Engine | 240 hours | 6 weeks |
| 2 | Modern Integrations | 320 hours | 8 weeks |
| 3 | Multi-File & AI | 400 hours | 10 weeks |
| 4 | Enterprise Governance | 480 hours | 12 weeks |
| 5 | Operating Layer | Ongoing | Ongoing |
| **Total** | **v3.0** | **1440 hours** | **36 weeks** |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Query performance regression | Continuous benchmarking, performance gates |
| Complex schema handling | Comprehensive test suite, user feedback |
| Adoption barriers | Excellent docs, examples, community support |
| Vendor lock-in concerns | Apache Arrow, open standards focus |
| Governance complexity | Start simple, iterate based on user needs |

---

## Git Workflow

```bash
# Main development branch
git checkout -b feature/v1.5-query-engine

# Per-phase commits
git commit -m "feat(query): DuckDB integration for SQL queries"
git commit -m "feat(query): Predicate pushdown for efficient filtering"
git commit -m "feat(query): Column projection optimization"
git commit -m "test: add 50+ query integration tests"

# Release tags
git tag -a v1.5.0 -m "Release v1.5: Query Engine"
git tag -a v2.0.0 -m "Release v2.0: Arrow & Polars Integration"
```

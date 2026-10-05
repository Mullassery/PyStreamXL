# API Specification

## `streamxl.read(path, sheet=None)`

Streams rows from an XLSX file.

**Parameters**

| Name    | Type  | Default | Description |
|---------|-------|---------|-------------|
| `path`  | `str` | —       | Path to `.xlsx` file |
| `sheet` | `str` | `None`  | Sheet name. `None` = first sheet. (Post-MVP) |

**Returns**

`Iterator[List[Any]]` — each item is a row as a list of Python values.

**Cell value types**

| XLSX type | Python type |
|-----------|-------------|
| String    | `str`       |
| Number    | `float`     |
| Boolean   | `bool`      |
| Empty     | `None`      |

**Example**

```python
for row in streamxl.read("data.xlsx"):
    print(row)  # ['Name', 'Age', 42.0, True]
```

## `streamxl.stream(path)`

Alias for `read()`.

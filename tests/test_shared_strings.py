"""
Shared string table is an internal Rust detail — test it through the public API:
write rows with repeated strings, read them back, verify correctness.
"""
import pystreamxl


def test_shared_strings_roundtrip(tmp_path):
    rows = [
        ["hello", "world", "hello"],
        ["world", "hello", "world"],
    ]
    path = str(tmp_path / "sst.xlsx")
    pystreamxl.write(path, rows)
    result = list(pystreamxl.read(path))
    assert result == rows


def test_empty_sst(tmp_path):
    """Numeric-only file has no shared strings — should still work."""
    rows = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    path = str(tmp_path / "nums.xlsx")
    pystreamxl.write(path, rows)
    result = list(pystreamxl.read(path))
    assert result == rows

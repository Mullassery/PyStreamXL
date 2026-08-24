import streamxl
from streamxl.core import read_rows_all_at_once


def test_is_iterator(tmp_xlsx):
    result = streamxl.read(tmp_xlsx)
    assert hasattr(result, "__iter__")
    assert hasattr(result, "__next__")


def test_memory_constant(tmp_large_xlsx):
    """Rows should be yielded one at a time — no full-file load."""
    import tracemalloc
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    count = 0
    for _ in streamxl.read(tmp_large_xlsx):
        count += 1

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    total_mb = sum(s.size_diff for s in stats) / 1024 / 1024
    assert total_mb < 50, f"Memory grew by {total_mb:.1f} MB — streaming may be broken"


def test_read_actually_streams_not_eager_then_yield(tmp_large_xlsx):
    """The real regression test for the backpressure fix: `read()` used to
    call the eager `_core.read()` binding, which materializes the ENTIRE
    sheet into a Python list on the very first `next()` call, before this
    generator ever yields row 0 -- "streaming" in name only. That front-
    loads essentially all of the work into getting row 0, regardless of
    how many rows the caller actually wants.

    Proven via timing rather than tracemalloc: tracemalloc only reliably
    tracks CPython's own pymalloc arena, not the Rust extension's
    allocations, so it's not a trustworthy signal for what a PyO3 iterator
    is doing internally. Wall-clock time to produce row 0 vs. time to
    produce all 50,000 is: if eager, ~100% of total time happens before row
    0 is yielded; if truly streaming, row 0 should be a small, roughly
    proportional fraction of the total.
    """
    import time

    start = time.perf_counter()
    it = streamxl.read(tmp_large_xlsx)
    next(it)
    time_to_first_row = time.perf_counter() - start

    for _ in it:
        pass
    total_time = time.perf_counter() - start

    # Generous threshold (not 1/50_000) to stay robust against timing noise
    # on shared/slow CI runners -- the eager implementation this replaces
    # would produce a ratio at or near 1.0 (all work front-loaded into row 0),
    # so anything comfortably below that is a real, meaningful signal.
    ratio = time_to_first_row / total_time
    assert ratio < 0.5, (
        f"row 0 took {ratio:.1%} of the total time to read all rows -- "
        "expected a small fraction if this is genuinely streaming one row "
        "at a time instead of materializing everything up front"
    )


def test_streaming_reader_is_one_shot_like_a_real_iterator(tmp_xlsx):
    """A real streaming iterator is exhausted after one pass -- unlike the
    old eager-list-backed generator, which could conceptually be re-driven
    from the same underlying list. This documents the (correct) new
    contract explicitly."""
    it = streamxl.read(tmp_xlsx)
    rows = list(it)
    assert len(rows) > 0
    assert list(it) == [], "a second pass over the same iterator must be empty"


def test_streaming_and_eager_apis_return_identical_data(tmp_xlsx):
    """Real streaming (default) and the explicit all-at-once escape hatch
    must agree on content -- only their memory/consumption characteristics
    should differ."""
    streamed = list(streamxl.read(tmp_xlsx))
    eager = list(read_rows_all_at_once(tmp_xlsx))
    assert streamed == eager


def test_streaming_with_formulas_matches_eager(tmp_xlsx):
    from streamxl.core import read_rows_with_metadata, read_rows_with_metadata_all_at_once

    streamed = list(read_rows_with_metadata(tmp_xlsx))
    eager = list(read_rows_with_metadata_all_at_once(tmp_xlsx))
    assert streamed == eager


def test_streaming_propagates_errors_like_the_eager_path(tmp_path):
    """A corrupt/nonexistent file should still raise, not silently yield
    nothing, regardless of which reader implementation is used."""
    import pytest

    missing = str(tmp_path / "does_not_exist.xlsx")
    with pytest.raises(Exception):
        list(streamxl.read(missing))

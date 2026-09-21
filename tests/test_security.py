"""Tests for streamxl.security path-traversal confinement.

`validate_xlsx_path`/`validate_read_path`/`validate_write_path` used to check
for the literal substring ".." *after* `Path.resolve()` had already
collapsed any ".." segments, so the check could never fire on a real
traversal attempt (see ROADMAP_HONEST.md / SECURITY.md history). These tests
exercise the real fix: an optional `base_dir` parameter that confines the
*resolved* path to a directory via `os.path.commonpath()`.
"""

import pytest

from streamxl.security import (
    SecurityError,
    validate_read_path,
    validate_write_path,
    validate_xlsx_path,
)


def test_traversal_outside_base_dir_is_rejected(tmp_path):
    """A '../../..'-style path that resolves outside base_dir must raise,
    even though resolve() has already collapsed the '..' segments away."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()

    # Craft a real traversal input: escape `uploads/` and land on a sibling
    # file that legitimately exists and has a valid extension, so the
    # rejection can only be due to the base_dir confinement check -- not
    # missing-file or wrong-extension checks.
    outside_target = tmp_path / "secret.xlsx"
    outside_target.write_bytes(b"not a real xlsx, just needs to exist")

    traversal_input = base_dir / ".." / "secret.xlsx"
    assert ".." in str(traversal_input)  # sanity: input really contains '..'

    with pytest.raises(SecurityError, match="traversal"):
        validate_xlsx_path(traversal_input, base_dir=base_dir)


def test_traversal_via_read_path_is_rejected(tmp_path):
    """Same traversal attempt through validate_read_path (the read-time
    entry point) is also rejected, before any existence/size checks run."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()

    outside_target = tmp_path / "passwd.xlsx"
    outside_target.write_bytes(b"x" * 100)

    traversal_input = f"{base_dir}/../passwd.xlsx"

    with pytest.raises(SecurityError, match="traversal"):
        validate_read_path(traversal_input, base_dir=base_dir)


def test_traversal_via_write_path_is_rejected(tmp_path):
    """Same traversal attempt through validate_write_path is rejected."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()

    traversal_input = f"{base_dir}/../escaped.xlsx"

    with pytest.raises(SecurityError, match="traversal"):
        validate_write_path(traversal_input, base_dir=base_dir)


def test_deep_traversal_to_absolute_path_is_rejected(tmp_path):
    """A deeply nested '../../../etc/passwd'-style input that resolves to
    an unrelated absolute path outside base_dir is rejected."""
    base_dir = tmp_path / "a" / "b" / "c"
    base_dir.mkdir(parents=True)

    outside_target = tmp_path / "etc_passwd.xlsx"
    outside_target.write_bytes(b"x")

    traversal_input = base_dir / ".." / ".." / ".." / "etc_passwd.xlsx"

    with pytest.raises(SecurityError, match="traversal"):
        validate_xlsx_path(traversal_input, base_dir=base_dir)


def test_legitimate_path_inside_base_dir_is_accepted(tmp_path):
    """A normal, non-traversal path inside base_dir must still validate."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()
    good_path = base_dir / "report.xlsx"

    validated = validate_xlsx_path(good_path, base_dir=base_dir)
    assert validated == good_path.resolve()


def test_legitimate_nested_path_inside_base_dir_is_accepted(tmp_path):
    """A path in a subdirectory of base_dir (no traversal) is accepted."""
    base_dir = tmp_path / "uploads"
    nested = base_dir / "2026" / "09"
    nested.mkdir(parents=True)
    good_path = nested / "report.xlsx"

    validated = validate_xlsx_path(good_path, base_dir=base_dir)
    assert validated == good_path.resolve()


def test_legitimate_read_and_write_inside_base_dir(tmp_path):
    """End-to-end: read/write validation both succeed for real, confined
    files and don't regress existing (non-traversal) behavior."""
    base_dir = tmp_path / "uploads"
    base_dir.mkdir()

    write_target = base_dir / "out.xlsx"
    validated_write = validate_write_path(write_target, base_dir=base_dir)
    assert validated_write == write_target.resolve()

    write_target.write_bytes(b"x" * 10)
    validated_read = validate_read_path(write_target, base_dir=base_dir)
    assert validated_read == write_target.resolve()


def test_no_base_dir_preserves_prior_behavior(tmp_path):
    """When base_dir is omitted (default), no confinement is enforced --
    this preserves backward compatibility for existing callers (api.py,
    server.py) that don't have a base directory concept."""
    somewhere = tmp_path / "anywhere" / "file.xlsx"
    somewhere.parent.mkdir(parents=True)

    # No base_dir passed -> should not raise for a traversal-shaped input
    # that resolves to a real, valid path outside of any particular tree.
    validated = validate_xlsx_path(str(somewhere) + "/../file.xlsx")
    assert validated == somewhere.resolve()

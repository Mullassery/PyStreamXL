"""Regression test for the version-string-drift bug class.

This project has hit this exact bug twice independently (see
TECHNICAL_DEBT.md / RepoIssues #52's "Testing Gaps" section): a hardcoded
`__version__` literal in `pystreamxl/__init__.py` silently drifting out of
sync with `pyproject.toml`/`Cargo.toml`, and a separately-hardcoded CLI
`--version` string drifting from both. `__version__` is now sourced from
installed package metadata (`importlib.metadata.version`) specifically to
make drift structurally impossible rather than just less likely -- this
test exists so a future reintroduction of a hardcoded literal fails loudly.
"""

import re
import subprocess
import sys

import pystreamxl


def test_version_matches_pyproject_toml():
    # Avoid a tomllib (3.11+) / tomli dependency just for this test -- the
    # version line's format is simple and stable enough for a direct regex.
    from pathlib import Path

    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.MULTILINE)
    assert match is not None, 'couldn\'t find version = "..." in pyproject.toml'
    assert pystreamxl.__version__ == match.group(1)


def test_cli_version_matches_package_version():
    result = subprocess.run(
        [sys.executable, "-m", "pystreamxl.cli", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"PyStreamXL (\S+)", result.stdout)
    assert match is not None, f"unexpected --version output: {result.stdout!r}"
    assert match.group(1) == pystreamxl.__version__

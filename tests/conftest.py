import pytest
import pystreamxl


@pytest.fixture
def tmp_xlsx(tmp_path):
    path = str(tmp_path / "sample.xlsx")
    pystreamxl.write(
        path,
        [
            ["Name", "Age", "Score"],
            ["Alice", 30.0, 95.5],
            ["Bob", 25.0, 88.0],
        ],
    )
    return path


@pytest.fixture
def empty_xlsx(tmp_path):
    path = str(tmp_path / "empty.xlsx")
    pystreamxl.write(path, [])
    return path


@pytest.fixture
def tmp_large_xlsx(tmp_path):
    path = str(tmp_path / "large.xlsx")
    pystreamxl.write(path, [[f"row{i}", float(i), i % 2 == 0] for i in range(50_000)])
    return path

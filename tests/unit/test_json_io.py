import json
from pathlib import Path

from infra import json_io


def test_write_json_creates_parent_directories(tmp_path: Path) -> None:
    output_path = tmp_path / "data" / "analysis" / "sioux" / "sample.json"

    json_io.write_json(output_path, {"ok": True})

    assert output_path.exists()
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == {"ok": True}

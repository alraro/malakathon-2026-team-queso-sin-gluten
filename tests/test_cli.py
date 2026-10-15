import json

from conftest import scene_composite
from fire_engine.cli import main


def test_cli_writes_result_json(tmp_path, validate_result):
    out = tmp_path / "out"

    exit_code = main(
        [
            "analyse",
            "--swir", str(scene_composite("huelva", "SWIR")),
            "--true-color", str(scene_composite("huelva", "True_color")),
            "--wildfires", str(scene_composite("huelva", "Wildfires")),
            "--out", str(out),
        ]
    )

    assert exit_code == 0
    result = json.loads((out / "result.json").read_text())
    validate_result(result)
    assert result["scene"]["composites"] == ["swir", "true_color", "wildfires"]
    assert (out / result["layers"]["preview"]).is_file()


def test_cli_accepts_bbox(tmp_path, validate_result):
    main(
        [
            "analyse",
            "--swir", str(scene_composite("guadalajara", "SWIR")),
            "--bbox", "-2.5", "40.5", "-2.0", "40.9",
            "--out", str(tmp_path),
        ]
    )

    result = json.loads((tmp_path / "result.json").read_text())
    validate_result(result)
    assert result["scene"]["georeference"]["bbox"] == [-2.5, 40.5, -2.0, 40.9]

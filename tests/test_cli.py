import json

import numpy as np
from PIL import Image

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


def test_cli_paints_active_fires_on_the_preview(tmp_path):
    swir = np.zeros((200, 300, 3), dtype=np.uint8)
    swir[...] = (60, 150, 40)
    swir[100:104, 150:154] = (255, 90, 60)  # foco SWIR
    Image.fromarray(swir).save(tmp_path / "swir.png")
    out = tmp_path / "out"

    main(["analyse", "--swir", str(tmp_path / "swir.png"), "--out", str(out)])

    result = json.loads((out / "result.json").read_text())
    layers = result["layers"]
    assert layers["active_fire_mask"] == "active_fire_mask.png"
    assert layers["preview"] == "preview.png"
    mask = np.asarray(Image.open(out / layers["active_fire_mask"]).convert("RGBA"))
    assert mask.shape[:2] == (200, 300)
    assert mask[101, 151, 3] > 0
    assert mask[10, 10, 3] == 0
    preview = np.asarray(Image.open(out / layers["preview"]).convert("RGB"))
    assert preview.shape[:2] == (200, 300)
    assert not np.array_equal(preview[101, 151], swir[101, 151])
    # El marcador del foco dibuja una forma alrededor, no solo rellena los 16 píxeles.
    around = np.any(preview[85:120, 135:170] != swir[85:120, 135:170], axis=-1)
    assert around.sum() > 3 * 16
    assert np.array_equal(preview[10, 10], swir[10, 10])


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
    assert result["summary"]["burned_area_ha"] > 0
    assert result["summary"]["perimeter_km"] > 0
    assert result["zones"]["features"][0]["properties"]["geo_geometry"] is not None

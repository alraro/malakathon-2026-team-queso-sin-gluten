import json

import numpy as np
import pytest

from conftest import scene_composite
from fire_engine import Georeference, analyse_scene, load_composite


@pytest.mark.parametrize("scene", ["huelva", "guadalajara", "madrid-avila"])
def test_swir_only_scene_produces_valid_result(scene, validate_result):
    swir = load_composite(scene_composite(scene, "SWIR"))

    result = analyse_scene(swir)

    validate_result(json.loads(json.dumps(result)))
    assert result["scene"]["width"] == swir.shape[1]
    assert result["scene"]["height"] == swir.shape[0]
    assert result["scene"]["composites"] == ["swir"]


def test_madrid_avila_swir_opens_despite_pil_pixel_limit():
    swir = load_composite(scene_composite("madrid-avila", "SWIR"))
    assert swir.shape == (6141, 9930, 3)
    assert swir.dtype == np.uint8


def test_all_composites_and_georeference_are_reported(validate_result):
    image = np.zeros((40, 60, 3), dtype=np.uint8)
    geo = Georeference(bbox=(-7.1, 37.2, -6.9, 37.4), source="manual")

    result = analyse_scene(image, true_color=image, wildfires=image, georeference=geo)

    validate_result(json.loads(json.dumps(result)))
    assert result["scene"]["composites"] == ["swir", "true_color", "wildfires"]
    assert result["scene"]["georeference"] == {
        "bbox": [-7.1, 37.2, -6.9, 37.4],
        "source": "manual",
    }


def test_without_georeference_hectares_are_null():
    result = analyse_scene(np.zeros((40, 60, 3), dtype=np.uint8))
    assert result["scene"]["georeference"] is None
    assert result["summary"]["burned_area_ha"] is None
    assert result["summary"]["perimeter_km"] is None


def test_composites_of_different_size_are_rejected():
    with pytest.raises(ValueError, match="mismo tamaño"):
        analyse_scene(
            np.zeros((40, 60, 3), dtype=np.uint8),
            true_color=np.zeros((41, 60, 3), dtype=np.uint8),
        )


def test_non_rgb_composite_is_rejected():
    with pytest.raises(ValueError, match="RGB"):
        analyse_scene(np.zeros((40, 60), dtype=np.uint8))

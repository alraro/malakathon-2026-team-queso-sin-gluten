import numpy as np
import pytest

from conftest import scene_composite
from fire_engine import Georeference, analyse_scene, load_composite


@pytest.mark.parametrize("scene", ["huelva", "guadalajara", "madrid-avila"])
def test_swir_only_scene_produces_valid_result(scene, validate_result):
    swir = load_composite(scene_composite(scene, "SWIR"))

    result = analyse_scene(swir)

    validate_result(result)
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

    validate_result(result)
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


def test_bbox_turns_a_known_burned_patch_into_hectares_and_lon_lat(validate_result):
    # Un píxel ocupa ~22,24 m por lado en el ecuador; el parche mide 40 × 40 px.
    bbox = (-0.016, -0.012, 0.016, 0.012)
    result = analyse_scene(
        scene_with_scar(),
        georeference=Georeference(bbox=bbox, source="manual"),
    )

    validate_result(result)
    assert result["scene"]["metres_per_pixel"] == pytest.approx(22.24, rel=0.02)
    assert result["summary"]["burned_area_ha"] == pytest.approx(79.1, rel=0.08)
    assert result["summary"]["perimeter_enclosed_ha"] >= result["summary"]["burned_area_ha"] - 1e-8
    assert result["summary"]["perimeter_km"] > 0
    zone = result["zones"]["features"][0]
    assert zone["properties"]["area_ha"] == pytest.approx(79.1, rel=0.08)
    assert zone["properties"]["geo_geometry"]["type"] == "Polygon"
    lon, lat = zone["properties"]["geo_geometry"]["coordinates"][0][0]
    assert bbox[0] <= lon <= bbox[2]
    assert bbox[1] <= lat <= bbox[3]


def test_bbox_keeps_only_zones_above_30_real_hectares_at_their_latitude():
    swir = np.zeros((200, 200, 3), dtype=np.uint8)
    swir[...] = (60, 150, 40)
    swir[20:30, 20:30] = (110, 50, 70)  # ~23 ha at high latitude
    swir[170:180, 170:180] = (110, 50, 70)  # ~68 ha near the equator

    result = analyse_scene(
        swir, georeference=Georeference((0, 0, 0.0003, 60), "manual")
    )

    assert result["summary"]["zone_count"] == 1
    assert result["zones"]["features"][0]["properties"]["area_ha"] > 60


def test_active_fire_has_lon_lat_only_with_bbox(validate_result):
    swir = scene_with_scar()
    swir[38:41, 38:41] = (255, 90, 60)

    without_bbox = analyse_scene(swir)
    with_bbox = analyse_scene(swir, georeference=Georeference((-1, 40, -0.9, 40.1), "manual"))

    validate_result(without_bbox)
    validate_result(with_bbox)
    assert without_bbox["active_fires"]["features"][0]["properties"]["geo_geometry"] is None
    coordinates = with_bbox["active_fires"]["features"][0]["properties"]["geo_geometry"]["coordinates"]
    assert -1 <= coordinates[0] <= -0.9
    assert 40 <= coordinates[1] <= 40.1


def test_perimeter_enclosed_hectares_include_an_unburned_island():
    swir = np.zeros((120, 160, 3), dtype=np.uint8)
    swir[...] = (60, 150, 40)
    swir[20:80, 20:80] = (110, 50, 70)
    swir[40:60, 40:60] = (60, 150, 40)

    result = analyse_scene(
        swir, georeference=Georeference((-0.016, -0.012, 0.016, 0.012), "manual")
    )

    assert result["summary"]["zone_count"] == 1
    assert result["summary"]["perimeter_enclosed_ha"] > result["summary"]["burned_area_ha"] + 15


def test_composites_of_different_size_are_rejected():
    with pytest.raises(ValueError, match="mismo tamaño"):
        analyse_scene(
            np.zeros((40, 60, 3), dtype=np.uint8),
            true_color=np.zeros((41, 60, 3), dtype=np.uint8),
        )


def test_non_rgb_composite_is_rejected():
    with pytest.raises(ValueError, match="RGB"):
        analyse_scene(np.zeros((40, 60), dtype=np.uint8))


def scene_with_scar():
    """SWIR de vegetación (NBR ≈ 0.43) con una cicatriz de 40×40 px (NBR ≈ −0.38)."""
    swir = np.zeros((120, 160, 3), dtype=np.uint8)
    swir[...] = (60, 150, 40)
    swir[20:60, 20:60] = (110, 50, 70)
    return swir


def test_active_fire_outside_burned_area_is_warned(validate_result):
    swir = scene_with_scar()
    swir[90:93, 120:123] = (255, 90, 60)  # foco SWIR sobre vegetación sana

    result = analyse_scene(swir)

    validate_result(result)
    assert result["summary"]["zone_count"] == 1
    assert result["summary"]["active_fire_count"] == 1
    assert any("fuera de la superficie quemada" in w for w in result["summary"]["warnings"])


def test_active_fire_inside_burned_area_is_not_warned():
    swir = scene_with_scar()
    swir[38:41, 38:41] = (255, 90, 60)  # foco dentro de la cicatriz

    result = analyse_scene(swir)

    assert result["summary"]["active_fire_count"] == 1
    assert result["summary"]["warnings"] == []

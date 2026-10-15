import numpy as np
import pytest
from PIL import Image

from conftest import scene_composite
from fire_engine import analyse_scene, load_composite

# Firmas medidas en la composición SWIR (docs/research §4.2), en valores de 8 bits.
VEGETATION = (76, 163, 72)  # NBR ≈ +0.36
BURNED_SIGNATURE = (138, 99, 65)  # NBR ≈ −0.16


def synthetic_swir(patches, size=(240, 320), seed=0):
    """Fondo de vegetación con parches de quemado; patches = [(fila, col, alto, ancho)]."""
    rng = np.random.default_rng(seed)
    image = np.empty((*size, 3), dtype=np.float64)
    image[:] = VEGETATION
    for row, col, height, width in patches:
        image[row : row + height, col : col + width] = BURNED_SIGNATURE
    image += rng.normal(0, 4, image.shape)
    return np.clip(image, 0, 255).astype(np.uint8)


def zone_properties(result):
    return [feature["properties"] for feature in result["zones"]["features"]]


def test_single_burn_patch_produces_one_zone_with_expected_area(validate_result):
    result = analyse_scene(synthetic_swir([(60, 80, 50, 60)]))

    validate_result(result)
    zones = zone_properties(result)
    assert len(zones) == 1
    assert zones[0]["area_px"] == pytest.approx(50 * 60, rel=0.03)
    assert result["summary"]["zone_count"] == 1
    assert result["summary"]["burned_area_px"] == zones[0]["area_px"]
    assert zones[0]["share_of_burned"] == pytest.approx(1.0)


def test_two_separate_patches_produce_two_zones_and_small_blob_is_discarded(validate_result):
    swir = synthetic_swir([(20, 20, 50, 50), (150, 200, 40, 70), (180, 30, 15, 15)])

    result = analyse_scene(swir)

    validate_result(result)
    areas = sorted(zone["area_px"] for zone in zone_properties(result))
    assert len(areas) == 2
    assert areas == [pytest.approx(50 * 50, rel=0.03), pytest.approx(40 * 70, rel=0.03)]
    assert result["summary"]["burned_area_px"] == sum(areas)


def test_zone_perimeter_encloses_the_patch(validate_result):
    result = analyse_scene(synthetic_swir([(60, 80, 50, 60)]))

    geometry = result["zones"]["features"][0]["geometry"]
    assert geometry["type"] == "Polygon"
    xs, ys = zip(*geometry["coordinates"][0])
    assert min(xs) == pytest.approx(80, abs=1.5) and max(xs) == pytest.approx(139, abs=1.5)
    assert min(ys) == pytest.approx(60, abs=1.5) and max(ys) == pytest.approx(109, abs=1.5)


def test_zone_severity_fractions_add_up_to_one():
    result = analyse_scene(synthetic_swir([(60, 80, 50, 60)]))

    severity = zone_properties(result)[0]["relative_severity"]
    assert severity["affected"] + severity["severely_affected"] == pytest.approx(1.0)


def test_unburned_scene_has_no_zones(validate_result):
    result = analyse_scene(synthetic_swir([]))

    validate_result(result)
    assert result["zones"]["features"] == []
    assert result["summary"]["burned_area_px"] == 0


def test_without_georeference_unit_fields_are_null():
    result = analyse_scene(synthetic_swir([(60, 80, 50, 60)]))

    summary = result["summary"]
    for field in ("burned_area_ha", "perimeter_enclosed_ha", "perimeter_km", "perimeter_tolerance_m"):
        assert summary[field] is None
    zone = zone_properties(result)[0]
    assert zone["area_ha"] is None
    assert zone["geo_geometry"] is None


def test_layers_are_written_when_an_output_directory_is_given(tmp_path, validate_result):
    swir = synthetic_swir([(60, 80, 50, 60)])

    result = analyse_scene(swir, out_dir=tmp_path)

    validate_result(result)
    layers = result["layers"]
    for name in ("burned_mask", "severity_mask", "preview"):
        assert (tmp_path / layers[name]).is_file()
    preview = np.asarray(Image.open(tmp_path / layers["preview"]).convert("RGB"))
    assert preview.shape == swir.shape
    inside, outside = (85, 110), (10, 10)
    assert not np.array_equal(preview[inside], swir[inside])
    assert np.array_equal(preview[outside], swir[outside])


def test_layers_are_null_without_output_directory():
    result = analyse_scene(synthetic_swir([(60, 80, 50, 60)]))
    assert result["layers"]["preview"] is None


def test_web_layers_are_reduced_to_at_most_2500_px(tmp_path):
    swir = synthetic_swir([(400, 1000, 300, 500)], size=(1600, 3000))

    result = analyse_scene(swir, out_dir=tmp_path)

    for name in ("burned_mask", "severity_mask", "preview"):
        with Image.open(tmp_path / result["layers"][name]) as layer:
            assert max(layer.size) <= 2500
    # Las cifras siguen siendo a resolución completa.
    assert zone_properties(result)[0]["area_px"] == pytest.approx(300 * 500, rel=0.03)


@pytest.mark.parametrize("scene", ["huelva", "guadalajara"])
def test_real_fire_scenes_produce_zones(scene, validate_result):
    result = analyse_scene(load_composite(scene_composite(scene, "SWIR")))

    validate_result(result)
    zones = zone_properties(result)
    assert len(zones) >= 1
    assert sum(zone["share_of_burned"] for zone in zones) == pytest.approx(1.0)
    # La zona principal es el incendio, no ruido: supone la mayor parte de lo quemado.
    assert zones[0]["share_of_burned"] > 0.5


def test_madrid_avila_is_processed_at_full_resolution(tmp_path, validate_result):
    swir = load_composite(scene_composite("madrid-avila", "SWIR"))

    result = analyse_scene(swir, out_dir=tmp_path)

    validate_result(result)
    assert result["scene"]["width"] == 9930
    assert result["summary"]["zone_count"] >= 1
    with Image.open(tmp_path / result["layers"]["preview"]) as preview:
        assert max(preview.size) <= 2500


def test_the_front_broken_by_smoke_is_one_zone_and_not_a_shower_of_small_ones():
    """El humo y las pistas parten el frente; agrupadas, Huelva es un incendio, no veinte.

    Antes de agrupar el frente salían 24 zonas, 22 de ellas marginales (suelo desnudo lejos
    del incendio y trozos sueltos del propio frente); ahora son 3 y la mayor se lleva el 95 %.
    """
    swir = load_composite(scene_composite("huelva", "SWIR"))
    true_color = load_composite(scene_composite("huelva", "True_color"))

    result = analyse_scene(swir, true_color=true_color)

    zones = zone_properties(result)
    assert len(zones) <= 5
    assert zones[0]["share_of_burned"] > 0.9

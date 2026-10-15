import numpy as np
import pytest
from PIL import Image

from conftest import scene_composite
from fire_engine import analyse_scene, load_composite
from fire_engine.active_fire import decode_wildfires
from fire_engine.burned_area import detect_burned_area

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


# Suelo urbano: NBR ≈ −0.18 como la cicatriz, pero brillante en NIR (B8A 0.20 de reflectancia).
URBAN_SIGNATURE = (186, 130, 100)


def test_bright_surface_with_negative_nbr_is_not_burned():
    swir = synthetic_swir([(60, 80, 50, 60)])
    swir[60:110, 80:140] = URBAN_SIGNATURE

    assert detect_burned_area(swir).zones == []


def _burned_share(burned, box):
    (top, bottom), (left, right) = box
    return burned.mask[top:bottom, left:right].mean()


@pytest.fixture(scope="module")
def madrid_avila_burned():
    swir = load_composite(scene_composite("madrid-avila", "SWIR"))
    true_color = load_composite(scene_composite("madrid-avila", "True_color"))
    return detect_burned_area(swir, true_color)


def test_madrid_city_and_barajas_are_not_burned(madrid_avila_burned):
    # Al este de x = 5800 no hay incendio: Madrid, Barajas y el sur metropolitano.
    assert _burned_share(madrid_avila_burned, ((0, 6141), (5800, 9930))) < 0.002


def test_scar_under_smoke_is_detected_and_vegetation_under_smoke_is_not(madrid_avila_burned):
    assert _burned_share(madrid_avila_burned, ((4360, 4880), (920, 1400))) > 0.5
    assert _burned_share(madrid_avila_burned, ((4720, 5400), (2800, 3600))) < 0.05


def test_huelva_scar_under_smoke_grows_but_forest_under_smoke_does_not():
    swir = load_composite(scene_composite("huelva", "SWIR"))
    true_color = load_composite(scene_composite("huelva", "True_color"))

    burned = detect_burned_area(swir, true_color)

    assert _burned_share(burned, ((425, 550), (1540, 1660))) > 0.5
    assert _burned_share(burned, ((40, 225), (1290, 1440))) < 0.05


def test_active_fire_fronts_stay_inside_the_burned_area():
    # El frente de llamas tiene el NIR brillante: el filtro de carbón no debe borrarlo.
    swir = load_composite(scene_composite("guadalajara", "SWIR"))
    true_color = load_composite(scene_composite("guadalajara", "True_color"))
    fire = decode_wildfires(load_composite(scene_composite("guadalajara", "Wildfires"))) > 0

    burned = detect_burned_area(swir, true_color)

    assert burned.mask[fire].mean() > 0.65  # medido: 0.69

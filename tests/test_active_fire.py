import numpy as np
import pytest

from conftest import scene_composite
from fire_engine import analyse_scene, load_composite
from fire_engine.active_fire import detect_active_fires

# Exceso de verde sobre la base que pinta QuickFire en cada nivel (1 = más débil).
GREEN_BOOST = {1: 0, 2: 25, 3: 70, 4: 150}


def synthetic_wildfires(height=120, width=160, seed=0):
    """Base tipo Wildfires con variación natural: G ≈ B + 40, R ≈ B + 50."""
    rng = np.random.default_rng(seed)
    blue = rng.integers(30, 110, size=(height, width))
    image = np.stack([blue + 50, blue + 40, blue], axis=-1)
    return image.astype(np.uint8)


def paint_wildfires_fire(image, rows, cols, level):
    blue = image[rows, cols, 2].astype(int)
    image[rows, cols, 0] = 250
    image[rows, cols, 1] = np.clip(blue + 40 + GREEN_BOOST[level], 0, 255)


def synthetic_swir(height=120, width=160):
    """SWIR de vegetación: B12 bajo, B8A alto."""
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[...] = (60, 150, 40)
    return image


def paint_swir_fire(image, rows, cols):
    image[rows, cols] = (255, 90, 60)  # B12 saturado, B12/B8A > 1.4


def fire_properties(result):
    return [f["properties"] for f in result["active_fires"]["features"]]


def test_wildfires_active_fires_are_decoded_with_their_level(validate_result):
    wildfires = synthetic_wildfires()
    for level, col in zip(range(1, 5), (20, 60, 100, 140)):
        paint_wildfires_fire(wildfires, slice(50, 54), slice(col, col + 4), level)

    result = analyse_scene(synthetic_swir(), wildfires=wildfires)

    validate_result(result)
    fires = fire_properties(result)
    assert sorted(f["level"] for f in fires) == [1, 2, 3, 4]
    assert {f["source"] for f in fires} == {"wildfires"}
    assert all(f["zone_id"] is None for f in fires)
    assert result["summary"]["active_fire_count"] == 4
    assert result["summary"]["confidence"]["active_fire"] == "high"


def test_wildfire_points_sit_on_the_active_fire_in_pixel_coordinates():
    wildfires = synthetic_wildfires()
    paint_wildfires_fire(wildfires, slice(10, 13), slice(30, 33), 3)

    result = analyse_scene(synthetic_swir(), wildfires=wildfires)

    (fire,) = result["active_fires"]["features"]
    assert fire["geometry"] == {"type": "Point", "coordinates": [31.5, 11.5]}


def test_without_wildfires_fires_come_from_swir_with_low_confidence(validate_result):
    swir = synthetic_swir()
    paint_swir_fire(swir, slice(40, 43), slice(40, 43))

    result = analyse_scene(swir)

    validate_result(result)
    assert fire_properties(result) == [
        {"level": None, "source": "swir", "zone_id": None, "geo_geometry": None}
    ]
    assert result["summary"]["active_fire_count"] == 1
    assert result["summary"]["confidence"]["active_fire"] == "low"


def test_swir_detector_ignores_hot_soil_and_burn_scar():
    swir = synthetic_swir()
    swir[0:20, :] = (255, 230, 120)  # suelo desnudo brillante: saturado pero B12/B8A < 1.4
    swir[60:80, :] = (110, 50, 70)  # cicatriz: B12/B8A alto pero sin saturar

    result = analyse_scene(swir)

    assert result["active_fires"]["features"] == []


def test_swir_growth_joins_neighbouring_potential_pixels():
    swir = synthetic_swir()
    paint_swir_fire(swir, slice(40, 41), slice(40, 41))
    swir[40, 41] = (200, 100, 60)  # no saturado pero B12/B8A ≥ 1.4, junto a un foco
    swir[40, 50] = (200, 100, 60)  # mismo píxel, aislado: no crece

    fires = detect_active_fires(swir, None, None)

    assert fires.mask.sum() == 2
    assert len(fires.features) == 1


def true_color_with_cloud(height=120, width=160):
    image = np.full((height, width, 3), 90, dtype=np.uint8)
    image[0:40, 0:80] = 255  # nube brillante
    return image


def test_cloud_next_to_wildfires_triggers_swir_search_and_warning(validate_result):
    wildfires = synthetic_wildfires()
    paint_wildfires_fire(wildfires, slice(90, 93), slice(120, 123), 2)
    swir = synthetic_swir()
    paint_swir_fire(swir, slice(20, 23), slice(40, 43))  # bajo la nube: la Wildfires no lo ve

    result = analyse_scene(swir, true_color=true_color_with_cloud(), wildfires=wildfires)

    validate_result(result)
    sources = sorted(f["source"] for f in fire_properties(result))
    assert sources == ["swir", "wildfires"]
    assert result["summary"]["confidence"]["active_fire"] == "high"
    assert any("nube" in w for w in result["summary"]["warnings"])


def test_small_cloud_hiding_a_fire_is_still_searched_and_warned():
    swir = synthetic_swir()
    paint_swir_fire(swir, slice(20, 22), slice(40, 42))
    true_color = np.full(swir.shape, 90, dtype=np.uint8)
    true_color[20:22, 40:42] = (120, 120, 255)  # nube diminuta: solo el azul satura

    result = analyse_scene(swir, true_color=true_color, wildfires=synthetic_wildfires())

    assert [f["source"] for f in fire_properties(result)] == ["swir"]
    assert any("nube" in w for w in result["summary"]["warnings"])


def test_no_cloud_warning_on_clear_scene():
    wildfires = synthetic_wildfires()
    clear = np.full(wildfires.shape, 90, dtype=np.uint8)

    result = analyse_scene(synthetic_swir(), true_color=clear, wildfires=wildfires)

    assert result["summary"]["warnings"] == []


def test_wildfires_without_true_color_warns_that_clouds_were_not_checked():
    result = analyse_scene(synthetic_swir(), wildfires=synthetic_wildfires())

    assert any("True Color" in w for w in result["summary"]["warnings"])


def test_fire_inside_a_zone_gets_its_zone_id():
    swir = synthetic_swir()
    paint_swir_fire(swir, slice(40, 43), slice(40, 43))
    paint_swir_fire(swir, slice(100, 103), slice(100, 103))
    zones = np.zeros(swir.shape[:2], dtype=np.int32)
    zones[30:60, 30:60] = 7

    fires = detect_active_fires(swir, None, None, zone_labels=zones)

    assert sorted(f["properties"]["zone_id"] or 0 for f in fires.features) == [0, 7]


@pytest.mark.parametrize("scene", ["huelva", "guadalajara"])
def test_real_scene_with_wildfires(scene, validate_result):
    result = analyse_scene(
        load_composite(scene_composite(scene, "SWIR")),
        true_color=load_composite(scene_composite(scene, "True_color")),
        wildfires=load_composite(scene_composite(scene, "Wildfires")),
    )

    validate_result(result)
    wildfire_levels = [f["level"] for f in fire_properties(result) if f["source"] == "wildfires"]
    assert wildfire_levels
    assert set(wildfire_levels) <= {1, 2, 3, 4}
    assert result["summary"]["active_fire_count"] == len(result["active_fires"]["features"])
    assert result["summary"]["confidence"]["active_fire"] == "high"


def test_madrid_avila_without_wildfires(validate_result):
    result = analyse_scene(load_composite(scene_composite("madrid-avila", "SWIR")))

    validate_result(result)
    fires = fire_properties(result)
    assert fires
    assert {f["source"] for f in fires} == {"swir"}
    assert result["summary"]["confidence"]["active_fire"] == "low"


@pytest.mark.parametrize("scene", ["huelva", "guadalajara"])
def test_swir_detector_agreement_with_wildfires(scene, record_property):
    """Mide el detector SWIR (Murphy-partial) frente a la decodificación Wildfires."""
    swir = load_composite(scene_composite(scene, "SWIR"))
    reference = detect_active_fires(swir, None, load_composite(scene_composite(scene, "Wildfires")))
    candidate = detect_active_fires(swir, None, None)

    hits = int((candidate.mask & reference.mask).sum())
    precision = hits / max(int(candidate.mask.sum()), 1)
    recall = hits / max(int(reference.mask.sum()), 1)
    record_property("swir_precision", round(precision, 3))
    record_property("swir_recall", round(recall, 3))
    print(f"{scene}: SWIR vs Wildfires precision={precision:.3f} recall={recall:.3f}")

    # Suelos medidos en data/ (ver docstring del módulo); avisan si el detector empeora.
    assert precision >= 0.2
    assert recall >= 0.5

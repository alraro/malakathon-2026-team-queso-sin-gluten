import numpy as np
import pytest

from conftest import scene_composite
from fire_engine import analyse_scene, load_composite
from fire_engine.active_fire import detect_active_fires, potentially_burning

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
    swir = synthetic_swir()
    for level, col in zip(range(1, 5), (20, 60, 100, 140)):
        paint_wildfires_fire(wildfires, slice(50, 54), slice(col, col + 4), level)
        # Un foco de verdad se ve en las dos composiciones; los niveles 1-2 que la SWIR no
        # respalda son suelo desnudo y los descarta la puerta de corroboración.
        paint_swir_fire(swir, slice(50, 54), slice(col, col + 4))

    result = analyse_scene(swir, wildfires=wildfires)

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
    swir = synthetic_swir()
    paint_swir_fire(swir, slice(10, 13), slice(30, 33))  # el mismo foco en la SWIR

    result = analyse_scene(swir, wildfires=wildfires)

    (fire,) = result["active_fires"]["features"]
    assert fire["geometry"] == {"type": "Point", "coordinates": [31.5, 11.5]}


def test_without_wildfires_fires_come_from_swir_with_low_confidence(validate_result):
    # El foco va pegado a la cicatriz que acaba de crear: sin ella la escena no puede
    # existir y, sin Wildfires, no hay con qué corroborarlo (``_near_burned_area``).
    swir = synthetic_swir()
    swir[60:100, 20:90] = (110, 50, 70)  # cicatriz holgadamente > 30 ha
    paint_swir_fire(swir, slice(30, 33), slice(40, 43))  # frente por delante del borde

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
    paint_swir_fire(swir, slice(90, 93), slice(120, 123))  # el mismo foco en la SWIR
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


def test_weak_wildfires_fire_on_bare_soil_is_dropped_and_warned(validate_result):
    """El render pinta como foco débil el suelo desnudo brillante; la SWIR lo desmiente."""
    wildfires = synthetic_wildfires()
    paint_wildfires_fire(wildfires, slice(50, 54), slice(20, 24), 2)
    swir = synthetic_swir()
    swir[48:56, 18:26] = (215, 180, 150)  # suelo desnudo: B12 alto pero B12/B8A ≈ 1.2

    result = analyse_scene(swir, wildfires=wildfires)

    validate_result(result)
    assert result["active_fires"]["features"] == []
    assert any("no los respalda la SWIR" in w for w in result["summary"]["warnings"])


def test_strong_wildfires_fire_is_kept_without_swir_support():
    """Los niveles 3-4 no necesitan respaldo: la Wildfires es la fuente preferente.

    El parche falla las pruebas de Murphy (B12/B8A = 1.25) pero no es suelo desnudo
    (B8A < 0.20), así que la clasificación fuerte se mantiene.
    """
    wildfires = synthetic_wildfires()
    paint_wildfires_fire(wildfires, slice(50, 54), slice(20, 24), 4)
    swir = synthetic_swir()
    swir[48:56, 18:26] = (150, 120, 100)

    result = analyse_scene(swir, wildfires=wildfires)

    assert [f["level"] for f in fire_properties(result)] == [4]


def test_strong_wildfires_fire_on_bare_soil_is_dropped(validate_result):
    """La excepción: un foco fuerte cuyo grupo es todo suelo desnudo no es fuego.

    Medido en Huelva, un grupo de 597 px de nivel 3 con B8A 240 y NBR ~ 0 era el 80 % de
    los píxeles de foco que caían fuera de la cicatriz (ver docs/adr/0001).
    """
    wildfires = synthetic_wildfires()
    paint_wildfires_fire(wildfires, slice(50, 54), slice(20, 24), 4)
    swir = synthetic_swir()
    swir[48:56, 18:26] = (215, 180, 150)  # B12 alto, B12/B8A = 1.2 y B8A >= 0.20

    result = analyse_scene(swir, wildfires=wildfires)

    validate_result(result)
    assert result["active_fires"]["features"] == []
    assert any("no los respalda la SWIR" in w for w in result["summary"]["warnings"])


@pytest.mark.parametrize("scene", ["huelva", "guadalajara"])
def test_every_fire_outside_the_burned_area_is_corroborated_in_the_swir(scene):
    """El criterio de la spec: un foco fuera de la cicatriz puede ser frente, no falso positivo.

    Lo que no se admite es un foco fuera sin respaldo de la SWIR. Medido en data/ (ver
    docs/adr/0001): 5 de 5 en Huelva y 14 de 14 en Guadalajara.
    """
    swir = load_composite(scene_composite(scene, "SWIR"))
    true_color = load_composite(scene_composite(scene, "True_color"))
    wildfires = load_composite(scene_composite(scene, "Wildfires"))

    result = analyse_scene(swir, true_color=true_color, wildfires=wildfires)

    burning = potentially_burning(swir)
    outside = [
        f for f in result["active_fires"]["features"] if f["properties"]["zone_id"] is None
    ]
    for fire in outside:
        x, y = (int(value) for value in fire["geometry"]["coordinates"])
        around = burning[max(y - 2, 0) : y + 3, max(x - 2, 0) : x + 3]
        assert around.any(), f"foco en {x},{y} fuera de la cicatriz y sin respaldo SWIR"

    fires = fire_properties(result)
    # Tripwire, no criterio: la fracción dentro depende de la escena (90,9 % Huelva,
    # 72,5 % Guadalajara) y un desplome avisaría de una regresión.
    assert len(fires) - len(outside) > 0.70 * len(fires)
    # Ningún foco fuerte se pierde por el camino.
    assert sum(1 for f in fires if f["level"] == 4) == _level_4_count(wildfires)


def _level_4_count(wildfires):
    from scipy import ndimage as ndi

    from fire_engine.active_fire import decode_wildfires

    levels = decode_wildfires(wildfires)
    labels, count = ndi.label(levels > 0, structure=np.ones((3, 3), dtype=bool))
    index = np.arange(1, count + 1)
    return int((ndi.maximum(levels, labels, index) == 4).sum())


def swir_with_scar(height=240, width=240, scar=(slice(40, 110), slice(40, 110))):
    """SWIR de vegetación con una cicatriz holgadamente por encima del área mínima."""
    image = synthetic_swir(height, width)
    image[scar] = (110, 50, 70)  # cicatriz: B12/B8A alto pero sin saturar
    return image


def zones_of(swir, scar=(slice(40, 110), slice(40, 110)), zone_id=1):
    labels = np.zeros(swir.shape[:2], dtype=np.int32)
    labels[scar] = zone_id
    return labels


def test_swir_fire_far_from_every_zone_is_dropped_without_wildfires():
    """Sin Wildfires el foco no se puede corroborar con otra composición: solo con el contexto.

    Un tejado o una cantera brillante pasa las dos pruebas de Murphy disponibles igual que un
    foco (en Madrid-Ávila eran 62 sobre el casco urbano, a 300-1250 px de la cicatriz).
    """
    swir = swir_with_scar()
    paint_swir_fire(swir, slice(70, 76), slice(70, 76))  # frente sobre la cicatriz
    paint_swir_fire(swir, slice(200, 203), slice(200, 203))  # tejado urbano lejísimos

    fires = detect_active_fires(swir, None, None, zone_labels=zones_of(swir))

    assert [f["properties"]["zone_id"] for f in fires.features] == [1]


def test_swir_fire_just_outside_the_zone_is_kept_as_the_advancing_front():
    """ADR-0001: el foco de fuera de la cicatriz es el frente avanzando, no ruido."""
    swir = swir_with_scar()
    paint_swir_fire(swir, slice(112, 115), slice(70, 73))  # 2 px por delante del borde

    fires = detect_active_fires(swir, None, None, zone_labels=zones_of(swir))

    assert len(fires.features) == 1

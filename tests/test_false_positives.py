import numpy as np
import pytest

from conftest import scene_composite
from fire_engine import analyse_scene, load_composite
from fire_engine.burned_area import detect_burned_area
from fire_engine.false_positives import cloud_mask, smoke_mask
from test_burned_area import BURNED_SIGNATURE, VEGETATION

# Firmas en la True Color (docs/research §4.3): el humo es blanco-grisáceo en el visible
# y la SWIR lo atraviesa; la nube es brillante en ambas composiciones.
TC_VEGETATION = (90, 105, 70)
TC_BURNED = (110, 95, 80)
TC_SMOKE = (225, 228, 230)
TC_CLOUD = (245, 245, 245)
# Nube en la SWIR: casi blanca, con B12 por encima de B8A (NBR ≈ −0,16, como la cicatriz),
# así que solo con la SWIR cae en la superficie quemada.
SWIR_CLOUD = (250, 180, 215)

SMOKE = (60, 200, 60, 80)
CLOUD = (150, 40, 60, 80)
BURN = (40, 40, 60, 80)


def synthetic_scene(swir_patches, tc_patches, size=(240, 320), seed=0):
    """SWIR y True Color co-registradas; patches = [((fila, col, alto, ancho), color)].

    Un sombreado de relieve común a ambas da al brillo la variación de una escena real
    (la estandarización por escena amplificaría el ruido de un fondo plano). Al ser
    multiplicativo, no cambia NBR ni el NDVI-proxy.
    """
    rng = np.random.default_rng(seed)
    relief = np.linspace(0.7, 1.3, size[1])[None, :, None]

    def render(background, patches):
        image = np.empty((*size, 3), dtype=np.float64)
        image[:] = background
        for (row, col, height, width), colour in patches:
            image[row : row + height, col : col + width] = colour
        image *= relief
        image += rng.normal(0, 4, image.shape)
        return np.clip(image, 0, 255).astype(np.uint8)

    return render(VEGETATION, swir_patches), render(TC_VEGETATION, tc_patches)


def burned_px_inside(result, patch):
    """Píxeles de las zonas cuyo perímetro cae dentro del parche (fila, col, alto, ancho)."""
    row, col, height, width = patch
    total = 0
    for feature in result["zones"]["features"]:
        xs, ys = zip(*feature["geometry"]["coordinates"][0])
        if col - 2 <= min(xs) and max(xs) <= col + width + 2 and row - 2 <= min(ys) and max(ys) <= row + height + 2:
            total += feature["properties"]["area_px"]
    return total


def test_smoke_patch_is_not_burned_area_when_true_color_is_given(validate_result):
    # Oscuro y con NBR negativo en la SWIR, brillante en la True Color: firma de humo.
    swir, true_color = synthetic_scene(
        [(SMOKE, BURNED_SIGNATURE), (BURN, BURNED_SIGNATURE)],
        [(SMOKE, TC_SMOKE), (BURN, TC_BURNED)],
    )
    assert burned_px_inside(analyse_scene(swir), SMOKE) > 0  # sin True Color no se puede descartar

    result = analyse_scene(swir, true_color=true_color)

    validate_result(result)
    assert burned_px_inside(result, SMOKE) == 0
    assert burned_px_inside(result, BURN) == pytest.approx(60 * 80, rel=0.03)


def test_cloud_patch_is_not_burned_area_when_true_color_is_given(validate_result):
    swir, true_color = synthetic_scene(
        [(CLOUD, SWIR_CLOUD), (BURN, BURNED_SIGNATURE)],
        [(CLOUD, TC_CLOUD), (BURN, TC_BURNED)],
    )
    assert burned_px_inside(analyse_scene(swir), CLOUD) > 0  # sin True Color no se puede descartar

    result = analyse_scene(swir, true_color=true_color)

    validate_result(result)
    assert burned_px_inside(result, CLOUD) == 0
    assert burned_px_inside(result, BURN) == pytest.approx(60 * 80, rel=0.03)


def test_near_black_swir_patch_is_not_burned_area_without_true_color():
    # Sombra o agua profunda: casi negra en la SWIR, con B12 > B8A por ruido (NBR muy negativo).
    shadow = (60, 200, 60, 80)
    swir, _ = synthetic_scene([(shadow, (10, 2, 6)), (BURN, BURNED_SIGNATURE)], [])

    result = analyse_scene(swir)

    assert burned_px_inside(result, shadow) == 0
    assert burned_px_inside(result, BURN) == pytest.approx(60 * 80, rel=0.03)


def test_burned_area_confidence_depends_on_true_color():
    swir, true_color = synthetic_scene([(BURN, BURNED_SIGNATURE)], [(BURN, TC_BURNED)])

    assert analyse_scene(swir)["summary"]["confidence"]["burned_area"] == "low"
    assert analyse_scene(swir, true_color=true_color)["summary"]["confidence"]["burned_area"] == "high"


@pytest.mark.parametrize("scene", ["huelva", "guadalajara"])
def test_real_burned_area_is_free_of_smoke_and_cloud_and_keeps_the_scar(scene):
    swir = load_composite(scene_composite(scene, "SWIR"))
    true_color = load_composite(scene_composite(scene, "True_color"))

    swir_only = detect_burned_area(swir)
    burned = detect_burned_area(swir, true_color)

    flagged = smoke_mask(swir, true_color) | cloud_mask(swir, true_color)
    # Umbral: < 0,5 % de la superficie quemada cumple el test de humo o de nube
    # (solo pueden volver los huecos < 3 ha que rellena la limpieza morfológica).
    assert flagged[burned.mask].mean() < 0.005
    # El humo fino sobre la cicatriz no se descarta: la SWIR lo atraviesa (§4.3).
    assert burned.area_px >= 0.97 * swir_only.area_px

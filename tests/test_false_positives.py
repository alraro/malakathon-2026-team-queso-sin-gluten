import numpy as np
import pytest

from conftest import scene_composite
from fire_engine import analyse_scene, load_composite
from fire_engine.burned_area import detect_burned_area
from fire_engine.false_positives import bare_soil_mask, cloud_mask, smoke_cover
from test_burned_area import BURNED_SIGNATURE, VEGETATION

# Firmas en la True Color (docs/research §4.3): el humo es blanco-grisáceo en el visible
# y la SWIR lo atraviesa; la nube es brillante en ambas composiciones.
TC_VEGETATION = (90, 105, 70)
TC_BURNED = (110, 95, 80)
TC_SMOKE = (225, 228, 230)
TC_CLOUD = (245, 245, 245)
# Nube en la SWIR: casi blanca, con B12 por encima de B8A (NBR ≈ −0.16, como la cicatriz),
# así que solo con la SWIR cae en la superficie quemada.
SWIR_CLOUD = (250, 180, 215)

SMOKE = (60, 200, 60, 80)
CLOUD = (150, 40, 60, 80)
BURN = (40, 40, 60, 80)
SHADOW = (60, 200, 60, 80)


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
        inside_cols = col - 2 <= min(xs) and max(xs) <= col + width + 2
        inside_rows = row - 2 <= min(ys) and max(ys) <= row + height + 2
        if inside_cols and inside_rows:
            total += feature["properties"]["area_px"]
    return total


def test_smoke_patch_is_not_burned_area_when_true_color_is_given(validate_result):
    # Humo espeso: brillante en la True Color y con NBR negativo en la SWIR. El humo fino
    # sobre la cicatriz (brecha de brillo menor) se conserva; ver el test con escenas reales.
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
    # Esta nube es brillante también en el NIR, así que el test de suelo desnudo ya la
    # descarta con la SWIR sola; lo que este test fija es que la True Color la reconoce
    # como nube y que no deja nada de ella en el resultado.
    row, col, height, width = CLOUD
    assert cloud_mask(swir, true_color)[row : row + height, col : col + width].mean() > 0.9

    result = analyse_scene(swir, true_color=true_color)

    validate_result(result)
    assert burned_px_inside(result, CLOUD) == 0
    assert burned_px_inside(result, BURN) == pytest.approx(60 * 80, rel=0.03)


def test_near_black_swir_patch_is_not_burned_area_without_true_color():
    # Sombra o agua profunda: casi negra en la SWIR, con B12 > B8A por ruido (NBR muy negativo).
    swir, _ = synthetic_scene([(SHADOW, (10, 2, 6)), (BURN, BURNED_SIGNATURE)], [])

    result = analyse_scene(swir)

    assert burned_px_inside(result, SHADOW) == 0
    assert burned_px_inside(result, BURN) == pytest.approx(60 * 80, rel=0.03)


def test_burned_area_confidence_depends_on_true_color():
    swir, true_color = synthetic_scene([(BURN, BURNED_SIGNATURE)], [(BURN, TC_BURNED)])

    assert analyse_scene(swir)["summary"]["confidence"]["burned_area"] == "low"
    assert analyse_scene(swir, true_color=true_color)["summary"]["confidence"]["burned_area"] == "high"


@pytest.mark.parametrize("scene", ["huelva", "guadalajara"])
def test_real_burned_area_is_free_of_cloud_and_keeps_the_scar(scene):
    swir = load_composite(scene_composite(scene, "SWIR"))
    true_color = load_composite(scene_composite(scene, "True_color"))

    swir_only = detect_burned_area(swir)
    burned = detect_burned_area(swir, true_color)

    # Medido: 0.04 % en Huelva, 0.06 % en Guadalajara (huecos < 3 ha que rellena la limpieza).
    # El humo no se comprueba: la cicatriz bajo humo se recupera a propósito
    # (ver test_burned_area::test_huelva_scar_under_smoke_grows_but_forest_under_smoke_does_not).
    assert cloud_mask(swir, true_color)[burned.mask].mean() < 0.005
    # El humo fino sobre la cicatriz no se descarta: la SWIR lo atraviesa (§4.3).
    assert burned.area_px >= 0.97 * swir_only.area_px


# Puntos verificados a ojo sobre la SWIR y la True Color de Huelva: cortas mineras, casco
# urbano y parcelas cosechadas del regadío del Guadiana. Su NBR (−0.06 … −0.10) es el de una
# cicatriz, así que hasta que hubo test de suelo desnudo salían como zonas quemadas sueltas
# lejos del incendio.
HUELVA_NOT_BURNED = {
    (216, 1128): "corta minera al oeste",
    (598, 31): "casco urbano al norte",
    (1338, 1112): "mina a cielo abierto al sureste de la cicatriz",
    (2499, 1286): "parcela cosechada",
    (2314, 1276): "parcela cosechada",
    (2464, 1234): "parcela cosechada",
    (1650, 1377): "parcela cosechada",
    (1374, 1397): "parcela cosechada",
    (2398, 1304): "parcela cosechada",
    (1038, 1296): "parcela cosechada",
    (1501, 1323): "parcela cosechada",
    (1648, 1309): "parcela cosechada",
    (1546, 1368): "parcela cosechada",
    (2354, 1297): "parcela cosechada",
    (2276, 1336): "parcela cosechada",
    (1302, 1438): "parcela cosechada",
}


def test_bare_soil_urban_and_farmland_are_not_burned_area():
    swir = load_composite(scene_composite("huelva", "SWIR"))
    true_color = load_composite(scene_composite("huelva", "True_color"))

    burned = detect_burned_area(swir, true_color)

    marked = {point: what for point, what in HUELVA_NOT_BURNED.items() if burned.mask[point[1], point[0]]}
    assert not marked, "marcados como superficie quemada: " + ", ".join(
        f"{point} ({what})" for point, what in marked.items()
    )


def test_bare_soil_test_does_not_reach_the_scar_or_the_active_front():
    """El corte del NIR separa el suelo desnudo sin comerse la cicatriz ni el frente."""
    swir = load_composite(scene_composite("huelva", "SWIR"))
    true_color = load_composite(scene_composite("huelva", "True_color"))

    burned = detect_burned_area(swir, true_color)

    # Bajo el humo el NIR sube y el test de suelo desnudo no vale: allí la cicatriz se
    # recupera creciendo desde la visible (burned_area._grow_under_smoke), y el 38 % de
    # ella supera el corte. Fuera del humo, medido en Huelva: marca el 1.7 % de la cicatriz.
    smoke, _ = smoke_cover(swir, true_color)
    assert bare_soil_mask(swir)[burned.mask & ~smoke].mean() < 0.02

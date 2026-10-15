"""Rechazo de falsos positivos de la superficie quemada: humo, nube, agua/sombra y vegetación.

Ver docs/research/sentinel2-rgb-fire-sota.md §4.3. El humo y la nube solo se distinguen
con la composición True Color; agua, sombra y vegetación salen de la propia SWIR.
"""

import numpy as np

# Brecha de brillo D = z(mean(TC)) − z(mean(SWIR)): el humo da ≈ +2.1 medido en Huelva y
# Guadalajara. Con D > 1 (el corte de §4.3) se pierde el 15–19 % de la cicatriz real: es
# cicatriz bajo humo fino, que la SWIR atraviesa. En la mediana del humo (D > 2) cae < 0.2 %.
SMOKE_MIN_BRIGHTNESS_GAP = 2.0
# Nube: brillante en ambas composiciones (z > 1.5 en las dos).
CLOUD_MIN_Z = 1.5
# Agua y sombra: media SWIR < 20 de 255, reflectancia < 0.03 en las tres bandas.
# Una cicatriz nunca es tan oscura: al arder sube B12.
DARK_MAX_SWIR = 20.0
# NDVI-proxy (B8A − B04)/(B8A + B04) por encima de esto es vegetación densa.
VEGETATION_MIN_NDVI = 0.6


def non_burnable_mask(swir: np.ndarray, true_color: np.ndarray | None = None) -> np.ndarray:
    """Píxeles que no pueden ser superficie quemada aunque su NBR lo parezca."""
    mask = dark_mask(swir) | _vegetation_mask(swir)
    if true_color is not None:
        tc_z, swir_z = _brightness_z(true_color), _brightness_z(swir)
        mask |= _smoke(tc_z, swir_z, SMOKE_MIN_BRIGHTNESS_GAP) | _cloud(tc_z, swir_z)
    return mask


def smoke_mask(
    swir: np.ndarray,
    true_color: np.ndarray,
    min_brightness_gap: float = SMOKE_MIN_BRIGHTNESS_GAP,
) -> np.ndarray:
    """Brillante en el visible y no en la SWIR, que atraviesa el humo."""
    return _smoke(_brightness_z(true_color), _brightness_z(swir), min_brightness_gap)


def cloud_mask(swir: np.ndarray, true_color: np.ndarray) -> np.ndarray:
    """Brillante en ambas composiciones."""
    return _cloud(_brightness_z(true_color), _brightness_z(swir))


def dark_mask(swir: np.ndarray) -> np.ndarray:
    """Agua y sombra: tan oscuras que su NBR es ruido."""
    return _brightness(swir) < DARK_MAX_SWIR


def _smoke(tc_z: np.ndarray, swir_z: np.ndarray, min_brightness_gap: float) -> np.ndarray:
    return tc_z - swir_z > min_brightness_gap


def _cloud(tc_z: np.ndarray, swir_z: np.ndarray) -> np.ndarray:
    return (tc_z > CLOUD_MIN_Z) & (swir_z > CLOUD_MIN_Z)


def _vegetation_mask(swir: np.ndarray) -> np.ndarray:
    b8a = swir[..., 1].astype(np.float32)
    b04 = swir[..., 2].astype(np.float32)
    total = b8a + b04
    ndvi = np.divide(b8a - b04, total, out=np.zeros_like(total), where=total > 0)
    return ndvi > VEGETATION_MIN_NDVI


def _brightness(image: np.ndarray) -> np.ndarray:
    return image.mean(axis=-1, dtype=np.float32)


def _brightness_z(image: np.ndarray) -> np.ndarray:
    """Brillo estandarizado por escena, para comparar composiciones con distinta curva tonal."""
    brightness = _brightness(image)
    std = brightness.std()
    if std == 0:
        return np.zeros_like(brightness)
    return (brightness - brightness.mean()) / std

"""Focos activos (``active_fire``).

Dos fuentes, por orden de preferencia (docs/research/sentinel2-rgb-fire-sota.md §1.3–1.5, §2.6):

- **Wildfires** (QuickFire de Markuse, variante ``cdse.js``): el render lleva pintada una
  clasificación en 4 niveles de ``B12 + B11``. Los focos suben el rojo (``0.60·B12``) y
  dejan el azul intacto, así que la firma es R alto con ``R − B`` muy por encima de la
  base de la escena. El nivel sale del refuerzo del verde (``0.60/0.24/0.12/0.00·B11``)
  sobre la base ``G − B`` de la escena. Los umbrales son relativos a la mediana de la
  escena, no colores absolutos, porque la base cambia entre exportaciones.
  Nivel 4 = el más intenso (``B12 + B11 > 2.0``), nivel 1 = el más débil (``> 1.0``).
- **SWIR, "Murphy-partial"**: dos de las tres pruebas inequívocas de Murphy et al. (2016)
  (``B12/B8A ≥ 1.4``, ``B12 ≥ 0.15``) más la saturación de B12 como semilla y un
  crecimiento 3×3 hacia píxeles que cumplen las dos pruebas. Falta ``B12/B11`` (B11 no
  está en ninguna composición), por eso su confianza es baja.

QuickFire suprime los focos donde su test de nube se dispara (``cloudAvoidance``). Si hay
True Color se aplica ese mismo test y, junto a las nubes, se buscan también focos en la
SWIR. Medido en data/ frente a la decodificación Wildfires (tests/test_active_fire.py), el
detector SWIR da precisión ≈ 0.63 / 0.28 y exhaustividad ≈ 0.60 / 0.76 (Huelva / Guadalajara);
sin el crecimiento 3×3, ≈ 0.84 / 0.39 y 0.49 / 0.38.
"""

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from scipy import ndimage as ndi

FireSource = Literal["wildfires", "swir"]
Confidence = Literal["high", "low"]

# Wildfires: firma de foco.
_HOT_RED_MIN = 200  # cerca de saturación: el refuerzo 0.60·B12 satura el rojo con cualquier base
_HOT_RED_MINUS_BLUE_OVER_BASE = 64  # ≈ 0.25 del rango sobre la mediana de R − B
# Wildfires: exceso de verde (DN) que separa los niveles 1|2, 2|3 y 3|4. Con la cadena de
# cdse.js (×1.1 / 0.84) cada nivel suma ≈ 0, 40·B11, 80·B11 y 200·B11 DN; B11 ≈ 0.5–1.
_LEVEL_GREEN_EXCESS = (12, 36, 100)

# SWIR (ganancia lineal 2.5): reflectancia → DN es ×2.5×255.
_SWIR_SATURATED = 250  # B12 ≥ 0.4, con margen por compresión JPEG
_SWIR_B12_MIN = round(0.15 * 2.5 * 255)
_SWIR_RATIO_TENTHS = 14  # B12/B8A ≥ 1.4

# Nubes según isCloud() de cdse.js sobre la True Color (ganancia 2.5 + gamma ≈ 1/2.2).
_TRUE_COLOR_GAMMA = 2.2
_TRUE_COLOR_SATURATED = 250
_CLOUD_MARGIN_PX = 3
_CLOUD_WARNING_FRACTION = 0.001

_EIGHT_CONNECTED = np.ones((3, 3), dtype=bool)


@dataclass(frozen=True)
class ActiveFires:
    """Focos activos de una escena.

    ``levels``: nivel 1–4 por píxel de los focos de la Wildfires (0 fuera de ellos).
    ``swir_mask``: píxeles de focos detectados con la SWIR.
    ``features``: un ``Feature`` GeoJSON (punto en coordenadas de píxel) por foco.
    """

    levels: np.ndarray
    swir_mask: np.ndarray
    features: list[dict[str, Any]]
    confidence: Confidence
    warnings: list[str]

    @property
    def mask(self) -> np.ndarray:
        return (self.levels > 0) | self.swir_mask


def detect_active_fires(
    swir: np.ndarray,
    true_color: np.ndarray | None,
    wildfires: np.ndarray | None,
    zone_labels: np.ndarray | None = None,
) -> ActiveFires:
    """Detecta focos activos. ``zone_labels`` (0 = fuera de zona) da el ``zone_id``."""
    if wildfires is None:
        swir_mask = murphy_partial(swir)
        levels = np.zeros(swir.shape[:2], dtype=np.uint8)
        return ActiveFires(
            levels=levels,
            swir_mask=swir_mask,
            features=_features(swir_mask, None, "swir", zone_labels),
            confidence="low",
            warnings=[],
        )

    levels = decode_wildfires(wildfires)
    warnings = []
    swir_mask = np.zeros(levels.shape, dtype=bool)
    if true_color is None:
        warnings.append(
            "Sin la composición True Color no se puede comprobar si hay nubes que oculten "
            "focos en la Wildfires."
        )
    else:
        clouds = cloud_mask(true_color)
        cloud_fraction = float(clouds.mean())
        if clouds.any():
            near_clouds = ndi.binary_dilation(clouds, iterations=_CLOUD_MARGIN_PX)
            swir_mask = _components_within(murphy_partial(swir), near_clouds, avoid=levels > 0)
        if cloud_fraction >= _CLOUD_WARNING_FRACTION or swir_mask.any():
            warnings.append(
                f"La True Color muestra nubes en el {cloud_fraction:.1%} de la escena; la "
                "Wildfires puede ocultar focos junto a ellas, así que ahí se han buscado "
                "también con la SWIR (confianza baja)."
            )

    features = _features(levels > 0, levels, "wildfires", zone_labels)
    features += _features(swir_mask, None, "swir", zone_labels)
    return ActiveFires(
        levels=levels,
        swir_mask=swir_mask,
        features=features,
        confidence="high",
        warnings=warnings,
    )


def decode_wildfires(wildfires: np.ndarray) -> np.ndarray:
    """Nivel 1–4 de QuickFire por píxel (0 = sin foco)."""
    red, green, blue = (wildfires[..., i].astype(np.int16) for i in range(3))
    red_minus_blue = red - blue
    hot = (red >= _HOT_RED_MIN) & (
        red_minus_blue >= np.median(red_minus_blue) + _HOT_RED_MINUS_BLUE_OVER_BASE
    )
    levels = np.zeros(hot.shape, dtype=np.uint8)
    if not hot.any():
        return levels
    green_minus_blue = green - blue
    base = np.median(green_minus_blue[~hot]) if (~hot).any() else 0
    excess = green_minus_blue[hot] - base
    levels[hot] = 1 + sum((excess >= t).astype(np.uint8) for t in _LEVEL_GREEN_EXCESS)
    return levels


def potentially_burning(swir: np.ndarray) -> np.ndarray:
    """Las dos pruebas de Murphy disponibles: ``B12 ≥ 0.15`` y ``B12/B8A ≥ 1.4``.

    No basta para dar un foco por bueno (por eso ``murphy_partial`` pide además una semilla
    saturada), pero sí para no tratar el píxel como suelo desnudo: ver ``false_positives``.
    """
    b12 = swir[..., 0].astype(np.int16)
    b8a = swir[..., 1].astype(np.int16)
    return (b12 >= _SWIR_B12_MIN) & (b12 * 10 >= b8a * _SWIR_RATIO_TENTHS)


def murphy_partial(swir: np.ndarray) -> np.ndarray:
    """Detector de focos sobre la SWIR (B12, B8A, B04): dos pruebas de Murphy + crecimiento."""
    b12 = swir[..., 0].astype(np.int16)
    potential = potentially_burning(swir)
    seeds = potential & (b12 >= _SWIR_SATURATED)
    return seeds | (ndi.binary_dilation(seeds, structure=_EIGHT_CONNECTED) & potential)


def cloud_mask(true_color: np.ndarray) -> np.ndarray:
    """Donde QuickFire (cdse.js) suprime focos: ``isCloud`` o ``B02 ≥ 0.8``.

    B03/B04 se recuperan de la True Color. ``B02 ≥ 0.8`` no es observable (la True Color
    satura en 0.4), así que un azul saturado cuenta como supresión probable.
    """
    reflectance = (true_color[..., :2].astype(np.float32) / 255) ** _TRUE_COLOR_GAMMA / 2.5
    b04, b03 = reflectance[..., 0], reflectance[..., 1]
    green_red = (b03 - b04) / np.maximum(b03 + b04, 1e-6)
    brightness = (b03 - 0.175) / (0.39 - 0.175)
    blue_saturated = true_color[..., 2] >= _TRUE_COLOR_SATURATED
    return (brightness > 1) | ((brightness > 0) & (green_red > 0)) | blue_saturated


def _components_within(mask: np.ndarray, region: np.ndarray, avoid: np.ndarray) -> np.ndarray:
    """Componentes de ``mask`` que tocan ``region`` y no se solapan con ``avoid`` (dilatado)."""
    labels, count = ndi.label(mask, structure=_EIGHT_CONNECTED)
    if count == 0:
        return mask
    near_avoid = ndi.binary_dilation(avoid, structure=_EIGHT_CONNECTED)
    touches = np.bincount(labels[region], minlength=count + 1) > 0
    clashes = np.bincount(labels[near_avoid], minlength=count + 1) > 0
    keep = touches & ~clashes
    keep[0] = False
    return keep[labels]


def _features(
    mask: np.ndarray,
    levels: np.ndarray | None,
    source: FireSource,
    zone_labels: np.ndarray | None,
) -> list[dict[str, Any]]:
    labels, count = ndi.label(mask, structure=_EIGHT_CONNECTED)
    if count == 0:
        return []
    index = np.arange(1, count + 1)
    centres = ndi.center_of_mass(mask, labels, index)
    component_levels = ndi.maximum(levels, labels, index) if levels is not None else None
    zones = ndi.maximum(zone_labels, labels, index) if zone_labels is not None else None

    features = []
    for i, (row, col) in enumerate(centres):
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(float(col) + 0.5, 1), round(float(row) + 0.5, 1)],
                },
                "properties": {
                    "level": int(component_levels[i]) if component_levels is not None else None,
                    "source": source,
                    "zone_id": int(zones[i]) if zones is not None and zones[i] > 0 else None,
                },
            }
        )
    return features

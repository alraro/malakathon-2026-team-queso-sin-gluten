"""Superficie quemada a partir de la composición SWIR: NBR, umbral adaptativo, zonas y perímetro.

Ver docs/research/sentinel2-rgb-fire-sota.md §0, §2.3 y §4.4.
"""

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi
from shapely import Polygon, union_all
from shapely.geometry.base import BaseGeometry
from skimage import morphology
from skimage.filters import threshold_multiotsu
from skimage.measure import find_contours

from fire_engine.false_positives import dark_mask, non_burnable_mask

# Área mínima cartografiable de una zona; EFFIS cartografía cicatrices de ~30 ha.
MIN_ZONE_HA = 30.0
# Islas sin quemar menores que esto se rellenan; las mayores se mantienen fuera del área.
MAX_FILLED_HOLE_HA = 3.0
# Sin escala conocida, las renders de data/ son del orden de 10–30 m/px (§4.7).
ASSUMED_METRES_PER_PIXEL = 20.0
# Tolerancia Douglas–Peucker del perímetro, en píxeles.
PERIMETER_TOLERANCE_PX = 1.0

_EIGHT_NEIGHBOURS = np.ones((3, 3), dtype=bool)
_HISTOGRAM_BINS = 256


@dataclass(frozen=True)
class Zone:
    id: int
    area_px: int
    severely_affected_px: int
    perimeter: BaseGeometry  # Polygon o MultiPolygon en coordenadas de píxel [x, y]


@dataclass(frozen=True)
class BurnedArea:
    labels: np.ndarray  # int32: 0 = no quemado, k = píxel de la zona k
    severe: np.ndarray  # bool: píxeles "muy afectados"
    zones: list[Zone]  # ordenadas por área descendente; id = posición + 1

    @property
    def mask(self) -> np.ndarray:
        return self.labels > 0

    @property
    def area_px(self) -> int:
        return sum(zone.area_px for zone in self.zones)


def detect_burned_area(
    swir: np.ndarray,
    true_color: np.ndarray | None = None,
    metres_per_pixel: float | None = None,
) -> BurnedArea:
    """Delimita la superficie quemada, la divide en zonas y clasifica su severidad relativa.

    Con ``true_color`` descarta además el humo y la nube (ver ``false_positives``).
    """
    nbr = _nbr(swir)
    # El umbral se ajusta sin los píxeles oscuros: su NBR es ruido (p. ej. −0,75 en las
    # sombras de Madrid-Ávila) y arrastraría el corte por debajo de la cicatriz.
    threshold = _burn_threshold(nbr[~dark_mask(swir)])
    burned = _clean(
        (nbr < threshold) & ~non_burnable_mask(swir, true_color),
        min_zone_px=_area_px(MIN_ZONE_HA, metres_per_pixel),
        max_hole_px=_area_px(MAX_FILLED_HOLE_HA, metres_per_pixel),
    )
    labels = _zone_labels(burned)
    severe = burned & (nbr < _severity_threshold(nbr[burned]))
    zones = [
        _zone(labels, severe, zone_id, region)
        for zone_id, region in enumerate(ndi.find_objects(labels), start=1)
    ]
    return BurnedArea(labels=labels, severe=severe, zones=zones)


def _nbr(swir: np.ndarray) -> np.ndarray:
    """NBR dentro de la composición SWIR [B12, B8A, B04]: (B8A − B12)/(B8A + B12).

    La ganancia lineal de la composición se cancela en la diferencia normalizada.
    """
    b12 = swir[..., 0].astype(np.float32)
    b8a = swir[..., 1].astype(np.float32)
    total = b8a + b12
    return np.divide(b8a - b12, total, out=np.zeros_like(total), where=total > 0)


def _burn_threshold(nbr: np.ndarray) -> float:
    """Umbral de quemado adaptativo por escena.

    El multi-Otsu de 3 clases sobre toda la escena deja el corte inferior en NBR ≈ 0–0.07,
    lo que en Huelva y Madrid-Ávila se lleva el 27–35 % de la imagen (cultivos, suelo).
    La cicatriz es una moda minoritaria: con 4 clases, la clase inferior la aísla
    (NBR < −0.05 … −0.13, 3–9 % de la escena). El tope en 0 evita marcar como quemada
    la cola baja de una escena sin incendio: la vegetación sana nunca tiene NBR negativo.
    """
    thresholds = _multiotsu(nbr.ravel(), classes=4)
    if thresholds is None:
        return 0.0
    return min(float(thresholds[0]), 0.0)


def _severity_threshold(burned_nbr: np.ndarray) -> float:
    """Corte "afectado" / "muy afectado" dentro de la propia superficie quemada."""
    thresholds = _multiotsu(burned_nbr, classes=2)
    if thresholds is None:
        return -np.inf
    return float(thresholds[0])


def _multiotsu(values: np.ndarray, classes: int) -> np.ndarray | None:
    if values.size == 0:
        return None
    counts, edges = np.histogram(values, bins=_HISTOGRAM_BINS, range=(-1.0, 1.0))
    if np.count_nonzero(counts) < classes:
        return None
    centres = (edges[:-1] + edges[1:]) / 2
    return threshold_multiotsu(hist=(counts, centres), classes=classes)


def _area_px(hectares: float, metres_per_pixel: float | None) -> int:
    scale = metres_per_pixel or ASSUMED_METRES_PER_PIXEL
    return max(1, round(hectares * 10_000 / scale**2))


def _clean(mask: np.ndarray, min_zone_px: int, max_hole_px: int) -> np.ndarray:
    footprint = morphology.footprint_rectangle((3, 3))
    mask = morphology.opening(mask, footprint)
    mask = morphology.closing(mask, footprint)
    mask = morphology.remove_small_objects(mask, max_size=min_zone_px - 1, connectivity=2)
    return morphology.remove_small_holes(mask, max_size=max_hole_px, connectivity=2)


def _zone_labels(burned: np.ndarray) -> np.ndarray:
    """Etiqueta las zonas de mayor a menor área (1 = la mayor)."""
    labels, count = ndi.label(burned, structure=_EIGHT_NEIGHBOURS)
    if count == 0:
        return labels.astype(np.int32)
    areas = np.bincount(labels.ravel())[1:]
    order = np.argsort(-areas, kind="stable")
    relabel = np.zeros(count + 1, dtype=np.int32)
    relabel[order + 1] = np.arange(1, count + 1, dtype=np.int32)
    return relabel[labels]


def _zone(labels: np.ndarray, severe: np.ndarray, zone_id: int, region: tuple[slice, slice]) -> Zone:
    inside = labels[region] == zone_id
    return Zone(
        id=zone_id,
        area_px=int(np.count_nonzero(inside)),
        severely_affected_px=int(np.count_nonzero(inside & severe[region])),
        perimeter=_perimeter(inside, offset=(region[1].start, region[0].start)),
    )


def _perimeter(inside: np.ndarray, offset: tuple[int, int]) -> BaseGeometry:
    """Contorno exterior (incluye las islas sin quemar) simplificado con Douglas–Peucker."""
    filled = np.pad(ndi.binary_fill_holes(inside), 1)
    contours = find_contours(filled.astype(np.uint8), 0.5, fully_connected="high")
    x0, y0 = offset[0] - 1, offset[1] - 1
    rings = [Polygon(contour[:, ::-1] + (x0, y0)) for contour in contours if len(contour) >= 4]
    outline = union_all([ring.buffer(0) for ring in rings])
    return outline.simplify(PERIMETER_TOLERANCE_PX, preserve_topology=True)

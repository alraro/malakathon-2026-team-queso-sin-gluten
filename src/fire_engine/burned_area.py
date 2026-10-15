"""Superficie quemada a partir de la composición SWIR: NBR, umbral adaptativo, zonas y perímetro.

Ver docs/research/sentinel2-rgb-fire-sota.md §0, §2.3 y §4.4.
"""

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi
from shapely import Polygon, union_all
from shapely.geometry.base import BaseGeometry
from skimage import morphology
from skimage.filters import threshold_multiotsu, threshold_otsu
from skimage.measure import find_contours

from fire_engine.active_fire import murphy_partial
from fire_engine.false_positives import cloud_mask, dark_mask, non_burnable_mask, smoke_cover, vegetation_mask
from fire_engine.georef import ASSUMED_METRES_PER_PIXEL

# Área mínima cartografiable de una zona; EFFIS cartografía cicatrices de ~30 ha.
MIN_ZONE_HA = 30.0
# Islas sin quemar menores que esto se rellenan; las mayores se mantienen fuera del área.
MAX_FILLED_HOLE_HA = 3.0
# Tolerancia Douglas–Peucker del perímetro, en píxeles.
PERIMETER_TOLERANCE_PX = 1.0
# El carbón es oscuro en el NIR. Una mancha con NBR < 0 pero B8A mediano por encima de esto
# es suelo urbano, desnudo o de cultivo (centro de Madrid, Barajas, campos de Huelva): su
# B12 apenas supera a su B8A, pero las tres bandas son brillantes. Medido por píxel en
# Madrid-Ávila y Huelva: cicatriz p95 0.19, falsos positivos p5 0.13–0.17, AUC 0.97.
CHAR_MAX_NIR_REFLECTANCE = 0.18
# Ganancia lineal de la composición SWIR (§1.2): DN = 255 · 2.5 · reflectancia.
SWIR_GAIN = 2.5
# El frente activo llega partido: el humo sube el NBR justo por encima del umbral y las
# pistas y cortafuegos cortan la cicatriz, así que la orla del frente queda en trozos por
# debajo del área mínima y el filtro de zonas se la lleva (en Huelva, 18 de los 34 focos del
# frente caían en trozos borrados así). Dos trozos a menos de esta distancia son la misma
# zona. Solo agrupa: los píxeles que se cuentan como quemados siguen siendo los suyos, para
# no inflar la superficie con las islas sin quemar que haya entre ellos.
FRONT_CLOSING_PX = 7

_EIGHT_NEIGHBOURS = np.ones((3, 3), dtype=bool)
_HISTOGRAM_BINS = 256
_TREND_SAMPLE = 200_000


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
    row_area_m2: np.ndarray | None = None,
    nbr_threshold_offset: float = 0.0,
) -> BurnedArea:
    """Delimita la superficie quemada, la divide en zonas y clasifica su severidad relativa.

    Con ``true_color`` descarta además el humo y la nube (ver ``false_positives``).
    ``nbr_threshold_offset`` desplaza el umbral adaptativo; solo lo usa la validación
    para medir la estabilidad del área.
    """
    nbr = swir_nbr(swir)
    # El umbral se ajusta sin los píxeles oscuros: su NBR es ruido (p. ej. −0.75 en las
    # sombras de Madrid-Ávila) y arrastraría el corte por debajo de la cicatriz.
    threshold = _burn_threshold(nbr[~dark_mask(swir)]) + nbr_threshold_offset
    # Con bbox, el filtro preliminar de píxeles es conservador; el corte de 30 ha
    # se comprueba después por zona con el área real de cada fila.
    cleaning_scale = float(np.sqrt(np.max(row_area_m2))) if row_area_m2 is not None else metres_per_pixel
    max_hole_px = _area_px(MAX_FILLED_HOLE_HA, cleaning_scale)
    burned = _charred_zones(
        _clean((nbr < threshold) & ~non_burnable_mask(swir, true_color), max_hole_px),
        swir,
    )
    if true_color is not None:
        burned = _grow_under_smoke(burned, swir, true_color, nbr, max_hole_px)
    labels = _zone_labels(
        burned,
        row_area_m2=row_area_m2,
        min_zone_px=_area_px(MIN_ZONE_HA, cleaning_scale),
    )
    burned = labels > 0
    severe = burned & (nbr < _severity_threshold(nbr[burned]))
    zones = [
        _zone(labels, severe, zone_id, region)
        for zone_id, region in enumerate(ndi.find_objects(labels), start=1)
    ]
    return BurnedArea(labels=labels, severe=severe, zones=zones)


def swir_nbr(swir: np.ndarray) -> np.ndarray:
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


def _charred_zones(mask: np.ndarray, swir: np.ndarray) -> np.ndarray:
    """Descarta las manchas cuyo NIR mediano es demasiado brillante para ser carbón.

    Se decide por mancha y no por píxel: una cicatriz real conserva sus píxeles más claros
    (ceniza, bordes) y una mancha urbana no se salva por unos pocos píxeles oscuros. El
    frente de llamas tiene el NIR brillante (B8A ≈ 140) y cuenta como carbón: sin ello, las
    manchas del frente se perdían (Guadalajara: 69 % → 43 % de focos Wildfires dentro).
    """
    labels, count = ndi.label(mask, structure=_EIGHT_NEIGHBOURS)
    if count == 0:
        return mask
    # Mediana ≤ corte ⇔ al menos la mitad de los píxeles ≤ corte (y es mucho más barato).
    dark_nir = (swir[..., 1] <= CHAR_MAX_NIR_REFLECTANCE * SWIR_GAIN * 255) | murphy_partial(swir)
    dark_count = np.bincount(labels[dark_nir], minlength=count + 1)
    keep = 2 * dark_count >= np.bincount(labels.ravel(), minlength=count + 1)
    keep[0] = False
    return keep[labels]


def _grow_under_smoke(
    seed: np.ndarray,
    swir: np.ndarray,
    true_color: np.ndarray,
    nbr: np.ndarray,
    max_hole_px: int,
) -> np.ndarray:
    """Extiende la superficie quemada hacia la cicatriz que el humo cubre.

    El humo suma luz en B8A y B04 y sube el NBR de la cicatriz (+0.2 en Madrid-Ávila) hasta
    confundirla con la vegetación. Bajo el humo se usa ``NBR + B8A`` (los dos bajan al arder
    y los dos suben con el humo) descontando la tendencia con el espesor del humo; el corte
    es el Otsu de los píxeles con humo de la propia escena. Solo se aceptan las manchas que
    tocan la cicatriz ya detectada: el humo sobre vegetación oscura no crea zonas propias.
    """
    smoke, haze = smoke_cover(swir, true_color)
    if np.count_nonzero(smoke) < 2:
        return seed
    score = nbr + swir[..., 1] / np.float32(255)
    residual = score
    # Una recta se ajusta igual con una muestra regular: en Madrid-Ávila hay 5.6 M de píxeles con humo.
    step = max(1, np.count_nonzero(smoke) // _TREND_SAMPLE)
    haze_sample = haze[smoke][::step].astype(np.float64)
    if np.ptp(haze_sample) > 0:  # una True Color plana no da espesor del que descontar
        trend = np.polyfit(haze_sample, score[smoke][::step].astype(np.float64), 1)
        residual = score - np.polyval(trend, haze).astype(np.float32)
    candidates = (
        smoke
        & (residual < threshold_otsu(residual[smoke]))
        # El agua tiene B8A < B04; la cicatriz bajo humo no.
        & (swir[..., 1] >= swir[..., 2])
        & ~dark_mask(swir)
        & ~vegetation_mask(swir)
        & ~cloud_mask(swir, true_color)
    )
    grown = _clean(seed | candidates, max_hole_px)
    labels, count = ndi.label(grown, structure=_EIGHT_NEIGHBOURS)
    touching = np.zeros(count + 1, dtype=bool)
    touching[labels[seed]] = True
    touching[0] = False
    return touching[labels]


def _clean(mask: np.ndarray, max_hole_px: int) -> np.ndarray:
    footprint = morphology.footprint_rectangle((3, 3))
    mask = morphology.opening(mask, footprint)
    mask = morphology.closing(mask, footprint)
    return morphology.remove_small_holes(mask, max_size=max_hole_px, connectivity=2)


def _zone_labels(
    burned: np.ndarray,
    row_area_m2: np.ndarray | None = None,
    min_zone_px: int = 1,
) -> np.ndarray:
    """Agrupa la superficie quemada en zonas y descarta las que no llegan al área mínima.

    Las zonas se forman sobre la máscara cerrada (``FRONT_CLOSING_PX``), para que el frente
    partido por el humo cuente como una sola; las etiqueta de mayor a menor área (1 = la
    mayor) y solo sobre los píxeles realmente quemados.
    """
    grouped = morphology.closing(burned, morphology.disk(FRONT_CLOSING_PX))
    labels, count = ndi.label(grouped, structure=_EIGHT_NEIGHBOURS)
    if count == 0:
        return labels.astype(np.int32)
    labels = np.where(burned, labels, 0)
    if row_area_m2 is None:
        areas = np.bincount(labels.ravel())[1:]
        order = [zone for zone in np.argsort(-areas, kind="stable") if areas[zone] >= min_zone_px]
        relabel = np.zeros(count + 1, dtype=np.int32)
        relabel[np.array(order, dtype=int) + 1] = np.arange(1, len(order) + 1, dtype=np.int32)
    else:
        real_areas = np.zeros(count + 1)
        for row, area in zip(labels, row_area_m2):
            real_areas += np.bincount(row, minlength=count + 1) * area
        candidates = np.flatnonzero(real_areas[1:] >= MIN_ZONE_HA * 10_000) + 1
        order = candidates[np.argsort(-real_areas[candidates], kind="stable")]
        relabel = np.zeros(count + 1, dtype=np.int32)
        relabel[order] = np.arange(1, len(order) + 1, dtype=np.int32)
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


def surface_geometry(zone: Zone, labels: np.ndarray, region: tuple[slice, slice]) -> BaseGeometry:
    """Superficie quemada de la zona, descontando las islas sin quemar del perímetro."""
    inside = labels[region] == zone.id
    holes = ndi.binary_fill_holes(inside) & ~inside
    hole_labels, count = ndi.label(holes, structure=_EIGHT_NEIGHBOURS)
    if count == 0:
        return zone.perimeter
    offset = (region[1].start, region[0].start)
    islands = [_perimeter(hole_labels == index, offset) for index in range(1, count + 1)]
    return zone.perimeter.difference(union_all(islands))

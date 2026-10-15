from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

GeoreferenceSource = Literal["map_fit", "manual", "geotiff"]


@dataclass(frozen=True)
class Georeference:
    """Extensión geográfica de la escena en grados WGS84."""

    bbox: tuple[float, float, float, float]  # lon_min, lat_min, lon_max, lat_max
    source: GeoreferenceSource


def analyse_scene(
    swir: np.ndarray,
    true_color: np.ndarray | None = None,
    wildfires: np.ndarray | None = None,
    georeference: Georeference | None = None,
) -> dict[str, Any]:
    """Analiza una escena y devuelve el resultado según el contrato JSON.

    Las composiciones son arrays RGB uint8 (alto, ancho, 3) co-registrados.
    Lanza ``ValueError`` con un mensaje en español si no son válidas.
    """
    composites = {"swir": swir, "true_color": true_color, "wildfires": wildfires}
    present = {name: image for name, image in composites.items() if image is not None}
    _validate(present)
    height, width = swir.shape[:2]

    return {
        "scene": {
            "width": int(width),
            "height": int(height),
            "composites": list(present),
            "georeference": _georeference_json(georeference),
            "metres_per_pixel": None,
        },
        "summary": {
            "burned_area_px": 0,
            "burned_area_ha": None,
            "perimeter_enclosed_ha": None,
            "perimeter_km": None,
            "perimeter_tolerance_m": None,
            "zone_count": 0,
            "active_fire_count": 0,
            "confidence": {
                "burned_area": "high",
                "active_fire": "high" if wildfires is not None else "low",
            },
            "warnings": [],
        },
        "zones": {"type": "FeatureCollection", "features": []},
        "active_fires": {"type": "FeatureCollection", "features": []},
        "alerts": [],
        "layers": {
            "burned_mask": None,
            "severity_mask": None,
            "active_fire_mask": None,
            "preview": None,
        },
    }


def _validate(composites: dict[str, np.ndarray]) -> None:
    for name, image in composites.items():
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(f"La composición {name} debe ser una imagen RGB.")
    shapes = {image.shape for image in composites.values()}
    if len(shapes) > 1:
        raise ValueError("Todas las composiciones deben tener el mismo tamaño.")


def _georeference_json(georeference: Georeference | None) -> dict[str, Any] | None:
    if georeference is None:
        return None
    return {"bbox": [float(v) for v in georeference.bbox], "source": georeference.source}

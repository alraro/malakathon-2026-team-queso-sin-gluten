from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from fire_engine.active_fire import detect_active_fires
from fire_engine.render import write_active_fire_layers

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
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Analiza una escena y devuelve el resultado según el contrato JSON.

    Las composiciones son arrays RGB uint8 (alto, ancho, 3) co-registrados.
    Con ``output_dir`` escribe además las capas PNG y rellena ``layers`` con sus rutas
    relativas a ese directorio.
    Lanza ``ValueError`` con un mensaje en español si no son válidas.
    """
    composites = {"swir": swir, "true_color": true_color, "wildfires": wildfires}
    present = {name: image for name, image in composites.items() if image is not None}
    _validate(present)
    height, width = swir.shape[:2]
    fires = detect_active_fires(swir, true_color, wildfires)
    layers = {"burned_mask": None, "severity_mask": None, "active_fire_mask": None, "preview": None}
    if output_dir is not None:
        preview_base = true_color if true_color is not None else swir
        layers.update(write_active_fire_layers(output_dir, preview_base, fires))

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
            "active_fire_count": len(fires.features),
            "confidence": {
                "burned_area": "high",
                "active_fire": fires.confidence,
            },
            "warnings": list(fires.warnings),
        },
        "zones": {"type": "FeatureCollection", "features": []},
        "active_fires": {"type": "FeatureCollection", "features": fires.features},
        "alerts": [],
        "layers": layers,
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

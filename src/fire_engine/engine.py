from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from shapely.geometry import mapping

from fire_engine.burned_area import BurnedArea, Zone, detect_burned_area
from fire_engine.layers import write_layers

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
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Analiza una escena y devuelve el resultado según el contrato JSON.

    Las composiciones son arrays RGB uint8 (alto, ancho, 3) co-registrados.
    Con ``out_dir`` escribe allí las capas PNG y ``layers`` lleva sus rutas relativas;
    sin él, ``layers`` queda a ``null``.
    Lanza ``ValueError`` con un mensaje en español si no son válidas.
    """
    composites = {"swir": swir, "true_color": true_color, "wildfires": wildfires}
    present = {name: image for name, image in composites.items() if image is not None}
    _validate(present)
    height, width = swir.shape[:2]
    burned = detect_burned_area(swir)
    layers = dict.fromkeys(["burned_mask", "severity_mask", "active_fire_mask", "preview"])
    if out_dir is not None:
        base = true_color if true_color is not None else swir
        layers.update(write_layers(out_dir, base, burned))

    return {
        "scene": {
            "width": int(width),
            "height": int(height),
            "composites": list(present),
            "georeference": _georeference_json(georeference),
            "metres_per_pixel": None,
        },
        "summary": {
            "burned_area_px": burned.area_px,
            "burned_area_ha": None,
            "perimeter_enclosed_ha": None,
            "perimeter_km": None,
            "perimeter_tolerance_m": None,
            "zone_count": len(burned.zones),
            "active_fire_count": 0,
            "confidence": {
                "burned_area": "high",
                "active_fire": "high" if wildfires is not None else "low",
            },
            "warnings": [],
        },
        "zones": {
            "type": "FeatureCollection",
            "features": [_zone_feature(zone, burned) for zone in burned.zones],
        },
        "active_fires": {"type": "FeatureCollection", "features": []},
        "alerts": [],
        "layers": layers,
    }


def _zone_feature(zone: Zone, burned: BurnedArea) -> dict[str, Any]:
    severe_share = zone.severely_affected_px / zone.area_px
    return {
        "type": "Feature",
        "geometry": _rounded(mapping(zone.perimeter)),
        "properties": {
            "id": zone.id,
            "area_px": zone.area_px,
            "area_ha": None,
            "share_of_burned": zone.area_px / burned.area_px,
            "relative_severity": {"affected": 1 - severe_share, "severely_affected": severe_share},
            "active_fire_count": 0,
            "nearest_settlement": None,
            "geo_geometry": None,
        },
    }


def _rounded(geometry: Any) -> Any:
    """GeoJSON de shapely (tuplas) → listas JSON con coordenadas a 2 decimales."""
    if isinstance(geometry, dict):
        return {key: _rounded(value) for key, value in geometry.items()}
    if isinstance(geometry, (list, tuple)):
        if geometry and isinstance(geometry[0], float):
            return [round(value, 2) for value in geometry]
        return [_rounded(item) for item in geometry]
    return geometry


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

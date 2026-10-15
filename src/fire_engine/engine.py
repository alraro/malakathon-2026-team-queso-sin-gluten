from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import mapping

from fire_engine.active_fire import detect_active_fires
from fire_engine.burned_area import BurnedArea, Zone, detect_burned_area, surface_geometry
from fire_engine.georef import GeoTransform
from fire_engine.layers import write_layers
from fire_engine.settlements import (
    AlertDistances,
    add_settlement_alerts,
    default_settlements_path,
    load_settlements,
)

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
    settlements_path: Path | None = None,
    alert_distances: AlertDistances = AlertDistances(),
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
    geo = GeoTransform(georeference.bbox, width, height) if georeference else None
    burned = detect_burned_area(
        swir,
        true_color,
        metres_per_pixel=geo.metres_per_pixel if geo else None,
        row_area_m2=geo.row_area_m2 if geo else None,
    )
    fires = detect_active_fires(swir, true_color, wildfires, zone_labels=burned.labels)
    if geo:
        for fire in fires.features:
            fire["properties"]["geo_geometry"] = geo.geometry(fire["geometry"])
        regions = ndi.find_objects(burned.labels)
        zone_areas = {
            zone.id: geo.area_ha(burned.labels[region] == zone.id, region[0].start)
            for zone, region in zip(burned.zones, regions)
        }
        burned_area_ha = sum(zone_areas.values())
        enclosed_area_ha = geo.area_ha(ndi.binary_fill_holes(burned.mask))
        perimeter_km = sum(
            geo.perimeter_km(geo.geometry(mapping(zone.perimeter))) for zone in burned.zones
        )
        burned_surfaces = [
            geo.geometry(mapping(surface_geometry(zone, burned.labels, region)))
            for zone, region in zip(burned.zones, regions)
        ]
    else:
        zone_areas = {}
        burned_area_ha = enclosed_area_ha = perimeter_km = None
        burned_surfaces = []
        for fire in fires.features:
            fire["properties"]["geo_geometry"] = None
    layers = dict.fromkeys(["burned_mask", "severity_mask", "active_fire_mask", "preview"])
    if out_dir is not None:
        base = true_color if true_color is not None else swir
        layers.update(write_layers(out_dir, base, burned, fires))
    fires_per_zone = Counter(f["properties"]["zone_id"] for f in fires.features)

    zones = [
        _zone_feature(zone, burned, fires_per_zone[zone.id], geo, zone_areas.get(zone.id))
        for zone in burned.zones
    ]
    alerts = (
        add_settlement_alerts(
            zones,
            fires.features,
            load_settlements(settlements_path or default_settlements_path()),
            alert_distances,
            burned_surfaces,
        )
        if geo else []
    )

    return {
        "scene": {
            "width": int(width),
            "height": int(height),
            "composites": list(present),
            "georeference": _georeference_json(georeference),
            "metres_per_pixel": geo.metres_per_pixel if geo else None,
        },
        "summary": {
            "burned_area_px": burned.area_px,
            "burned_area_ha": burned_area_ha,
            "perimeter_enclosed_ha": enclosed_area_ha,
            "perimeter_km": perimeter_km,
            "perimeter_tolerance_m": geo.metres_per_pixel if geo else None,
            "zone_count": len(burned.zones),
            "active_fire_count": len(fires.features),
            "confidence": {
                "burned_area": "high" if true_color is not None else "low",
                "active_fire": fires.confidence,
            },
            "warnings": [*fires.warnings, *_outside_burned_area_warning(fires.features)],
        },
        "zones": {
            "type": "FeatureCollection",
            "features": zones,
        },
        "active_fires": {"type": "FeatureCollection", "features": fires.features},
        "alerts": alerts,
        "layers": layers,
    }


def _outside_burned_area_warning(fire_features: list[dict[str, Any]]) -> list[str]:
    """Un foco fuera de la superficie quemada es un frente que avanza o un error del detector."""
    outside = sum(1 for f in fire_features if f["properties"]["zone_id"] is None)
    if outside == 0:
        return []
    return [
        f"{outside} de {len(fire_features)} focos activos están fuera de la superficie "
        "quemada: puede ser un frente que avanza o un error de detección; revísalos."
    ]


def _zone_feature(
    zone: Zone,
    burned: BurnedArea,
    active_fire_count: int,
    geo: GeoTransform | None,
    area_ha: float | None,
) -> dict[str, Any]:
    severe_share = zone.severely_affected_px / zone.area_px
    return {
        "type": "Feature",
        "geometry": _rounded(mapping(zone.perimeter)),
        "properties": {
            "id": zone.id,
            "area_px": zone.area_px,
            "area_ha": area_ha,
            "share_of_burned": zone.area_px / burned.area_px,
            "relative_severity": {"affected": 1 - severe_share, "severely_affected": severe_share},
            "active_fire_count": active_fire_count,
            "nearest_settlement": None,
            "geo_geometry": geo.geometry(mapping(zone.perimeter)) if geo else None,
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

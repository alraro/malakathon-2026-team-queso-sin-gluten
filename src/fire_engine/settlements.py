"""Poblaciones locales y alertas basadas únicamente en distancia geográfica."""

import csv
import os
from dataclasses import dataclass
from functools import lru_cache
from math import asin, cos, isfinite, radians, sin, sqrt
from pathlib import Path
from typing import Any

import numpy as np
from shapely import Point, STRtree, box, transform
from shapely.geometry import shape
from shapely.ops import nearest_points

from fire_engine.georef import EARTH_RADIUS_M


@dataclass(frozen=True)
class AlertDistances:
    """Umbrales en kilómetros; ``high_fire_km`` solo se aplica a focos activos."""

    high_fire_km: float = 2.0
    medium_km: float = 5.0
    watch_km: float = 10.0

    def __post_init__(self) -> None:
        values = (self.high_fire_km, self.medium_km, self.watch_km)
        if not all(isfinite(value) for value in values) or not (0 < values[0] < values[1] < values[2]):
            raise ValueError("Los umbrales de alerta deben ser positivos y cumplir high < medium < watch.")


@dataclass(frozen=True)
class Settlement:
    name: str
    longitude: float
    latitude: float
    population: int

    @property
    def point(self) -> Point:
        return Point(self.longitude, self.latitude)


def default_settlements_path() -> Path:
    """CSV por defecto; la variable permite cambiar de país también en Docker."""
    configured = os.environ.get("FIRE_ENGINE_SETTLEMENTS_FILE")
    if configured:
        return Path(configured)
    root = Path(os.environ.get("FIRE_ENGINE_ROOT", Path(__file__).resolve().parents[2]))
    return root / "settlements" / "ES.csv"


@lru_cache(maxsize=8)
def load_settlements(path: Path) -> tuple[Settlement, ...]:
    """Carga una vez un CSV UTF-8 con name, longitude, latitude y population."""
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            required = {"name", "longitude", "latitude", "population"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f"El dataset {path} necesita columnas name, longitude, latitude y population.")
            items = []
            for number, row in enumerate(reader, start=2):
                try:
                    name = row["name"].strip()
                    lon = float(row["longitude"])
                    lat = float(row["latitude"])
                    population = int(row["population"])
                    if not name or not isfinite(lon) or not isfinite(lat) or not (-180 <= lon <= 180 and -90 <= lat <= 90) or population < 0:
                        raise ValueError
                except (TypeError, ValueError) as error:
                    raise ValueError(f"Población inválida en {path}, línea {number}.") from error
                items.append(Settlement(name, lon, lat, population))
    except OSError as error:
        raise ValueError(f"No se puede leer el dataset de poblaciones: {path}") from error
    return tuple(items)


def add_settlement_alerts(
    zones: list[dict[str, Any]],
    fires: list[dict[str, Any]],
    settlements: tuple[Settlement, ...],
    distances: AlertDistances,
    burned_surfaces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Anota la población más cercana por zona y devuelve alertas ordenadas."""
    if not settlements or not (zones or fires):
        return []
    zone_shapes = [shape(geometry) for geometry in burned_surfaces]
    perimeter_shapes = [shape(zone["properties"]["geo_geometry"]) for zone in zones]
    fire_shapes = [shape(fire["properties"]["geo_geometry"]) for fire in fires]
    places = [item.point for item in settlements]
    place_tree = STRtree(places)

    for zone, footprint in zip(zones, zone_shapes):
        nearest = _nearest_settlement(footprint, settlements, place_tree, distances.watch_km)
        if nearest is not None:
            zone["properties"]["nearest_settlement"] = {
                "name": nearest[0].name,
                "distance_km": round(nearest[1], 3),
            }

    shapes = [*zone_shapes, *fire_shapes]
    incident_tree = STRtree(shapes)
    overall = _bounds_of(shapes)
    alert_indices = place_tree.query(_expanded(overall, distances.watch_km))
    alerts = []
    for index in alert_indices:
        settlement = settlements[int(index)]
        point = places[int(index)]
        nearby = incident_tree.query(_expanded(point.bounds, distances.watch_km))
        burned_distance = min(
            (_distance_km(point, shapes[int(i)]) for i in nearby if int(i) < len(zone_shapes)),
            default=float("inf"),
        )
        fire_distance = min(
            (_distance_km(point, shapes[int(i)]) for i in nearby if int(i) >= len(zone_shapes)),
            default=float("inf"),
        )
        inside_perimeter = any(perimeter.covers(point) for perimeter in perimeter_shapes)
        if inside_perimeter and burned_distance == float("inf"):
            burned_distance = min(_distance_km(point, footprint) for footprint in zone_shapes)
        nearest_distance = min(burned_distance, fire_distance)
        if inside_perimeter or fire_distance < distances.high_fire_km:
            level = "high"
        elif nearest_distance < distances.medium_km:
            level = "medium"
        elif nearest_distance < distances.watch_km:
            level = "watch"
        else:
            continue
        alerts.append({
            "settlement": settlement.name,
            "population": settlement.population,
            "distance_km": round(nearest_distance, 3),
            "level": level,
            "nearest_to": "burned_area" if burned_distance <= fire_distance else "active_fire",
        })
    return sorted(alerts, key=lambda alert: (alert["distance_km"], alert["settlement"]))


def _nearest_settlement(
    footprint: Any,
    settlements: tuple[Settlement, ...],
    tree: STRtree,
    initial_km: float,
) -> tuple[Settlement, float] | None:
    radius = initial_km
    while radius < 40_000:
        matches = tree.query(_expanded(footprint.bounds, radius))
        if len(matches):
            nearest = min(
                ((settlements[int(index)], _distance_km(settlements[int(index)].point, footprint)) for index in matches),
                key=lambda pair: pair[1],
            )
            if nearest[1] <= radius or radius >= 20_000:
                return nearest
        radius *= 2
    return None


def _bounds_of(geometries: list[Any]) -> tuple[float, float, float, float]:
    return (
        min(geometry.bounds[0] for geometry in geometries),
        min(geometry.bounds[1] for geometry in geometries),
        max(geometry.bounds[2] for geometry in geometries),
        max(geometry.bounds[3] for geometry in geometries),
    )


def _expanded(bounds: tuple[float, float, float, float], radius_km: float) -> Any:
    west, south, east, north = bounds
    latitude = min(89.9, max(abs(south), abs(north)) + radius_km / 111.2)
    lat_pad = radius_km / 111.2
    lon_pad = min(180, radius_km / (111.2 * max(cos(radians(latitude)), 1e-4)))
    return box(west - lon_pad, south - lat_pad, east + lon_pad, north + lat_pad)


def _distance_km(point: Point, geometry: Any) -> float:
    if geometry.covers(point):
        return 0.0
    lon0, lat0 = point.x, point.y
    lon_scale = max(cos(radians(lat0)), 1e-8)
    # El punto más cercano se busca en una proyección local; la distancia final
    # se mide sobre la esfera con haversine, no en grados ni en Web Mercator.
    projected = transform(geometry, lambda xy: _scale_coordinates(xy, lon0, lat0, lon_scale))
    nearest = nearest_points(Point(0, 0), projected)[1]
    return _haversine_km(lon0, lat0, nearest.x / lon_scale + lon0, nearest.y + lat0)


def _scale_coordinates(xy: Any, lon0: float, lat0: float, lon_scale: float) -> Any:
    coordinates = np.asarray(xy)
    return np.column_stack(((coordinates[:, 0] - lon0) * lon_scale, coordinates[:, 1] - lat0))


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    lat1, lat2 = radians(lat1), radians(lat2)
    dlat = lat2 - lat1
    dlon = radians(lon2 - lon1)
    chord = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(min(1.0, sqrt(chord))) / 1000

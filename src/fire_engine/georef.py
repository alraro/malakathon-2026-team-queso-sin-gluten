"""Escala y transformación de una escena con bbox WGS84 aportado por el usuario."""

from dataclasses import dataclass
from functools import cached_property
from math import asin, cos, isfinite, log, pi, radians, sin, sqrt, tan
from typing import Any

import numpy as np

# Sin escala conocida, las renders de data/ son del orden de 10-30 m/px (§4.7). Vive aquí
# y no en burned_area porque active_fire también la necesita y no puede importarla de allí.
ASSUMED_METRES_PER_PIXEL = 20.0
EARTH_RADIUS_M = 6_371_008.8
MERCATOR_LAT_LIMIT = 85.05112878


@dataclass(frozen=True)
class GeoTransform:
    """Relaciona los bordes de píxel con un bbox en Web Mercator."""

    bbox: tuple[float, float, float, float]
    width: int
    height: int

    def __post_init__(self) -> None:
        if len(self.bbox) != 4:
            raise ValueError("El bbox necesita lon_min, lat_min, lon_max y lat_max.")
        west, south, east, north = self.bbox
        if (
            not all(isfinite(value) for value in self.bbox)
            or not (-180 <= west < east <= 180)
            or not (-MERCATOR_LAT_LIMIT < south < north < MERCATOR_LAT_LIMIT)
        ):
            raise ValueError(
                "El bbox debe ser [lon_min, lat_min, lon_max, lat_max] en grados WGS84 "
                "válidos, con mínimo menor que máximo y latitudes dentro de Web Mercator."
            )

    @cached_property
    def row_area_m2(self) -> np.ndarray:
        """Área real de un píxel por fila; la variación con latitud es explícita."""
        rows = np.arange(self.height + 1)
        lat = self._latitude(rows)
        lon_width = radians(self.bbox[2] - self.bbox[0]) / self.width
        return EARTH_RADIUS_M**2 * lon_width * (
            np.sin(np.radians(lat[:-1])) - np.sin(np.radians(lat[1:]))
        )

    @cached_property
    def metres_per_pixel(self) -> float:
        return sqrt(float(np.mean(self.row_area_m2)))

    def area_ha(self, mask: np.ndarray, row_start: int = 0) -> float:
        row_area = self.row_area_m2[row_start : row_start + mask.shape[0]]
        return float(np.count_nonzero(mask, axis=1) @ row_area / 10_000)

    def pixel_to_lonlat(self, x: float, y: float) -> list[float]:
        west, _, east, _ = self.bbox
        lon = west + (east - west) * x / self.width
        lat = float(self._latitude(y))
        return [round(lon, 7), round(lat, 7)]

    def geometry(self, shape: dict[str, Any]) -> dict[str, Any]:
        """Convierte Point, Polygon o MultiPolygon de píxeles a lon/lat."""
        kind = shape["type"]
        coords = shape["coordinates"]
        if kind == "Point":
            converted = self.pixel_to_lonlat(*coords)
        elif kind == "Polygon":
            converted = [[self.pixel_to_lonlat(*point) for point in ring] for ring in coords]
        elif kind == "MultiPolygon":
            converted = [
                [[self.pixel_to_lonlat(*point) for point in ring] for ring in polygon]
                for polygon in coords
            ]
        else:
            raise ValueError(f"Geometría no admitida: {kind}")
        return {"type": kind, "coordinates": converted}

    def perimeter_km(self, shape: dict[str, Any]) -> float:
        polygons = [shape["coordinates"]] if shape["type"] == "Polygon" else shape["coordinates"]
        return sum(
            _ring_length_km(ring)
            for polygon in polygons
            for ring in polygon
        )

    def _latitude(self, row: Any) -> Any:
        _, south, _, north = self.bbox
        top = _mercator_y(north)
        bottom = _mercator_y(south)
        y = top + (bottom - top) * row / self.height
        return np.degrees(np.arctan(np.sinh(y)))


def _mercator_y(lat: float) -> float:
    return log(tan(pi / 4 + radians(lat) / 2))


def _ring_length_km(ring: list[list[float]]) -> float:
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(ring, ring[1:]):
        lat1, lat2 = radians(lat1), radians(lat2)
        dlat = lat2 - lat1
        dlon = radians(lon2 - lon1)
        half_chord = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        total += 2 * EARTH_RADIUS_M * asin(min(1.0, sqrt(half_chord)))
    return total / 1000

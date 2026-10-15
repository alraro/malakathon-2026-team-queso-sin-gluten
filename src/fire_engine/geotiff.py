"""Lectura de la extensión geográfica de un GeoTIFF (Copernicus Browser) con Pillow."""

from math import atan, degrees, sinh
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError


_PIXEL_SCALE, _TIEPOINT, _GEO_KEYS = 33550, 33922, 34735
_GEOGRAPHIC_TYPE, _PROJECTED_TYPE = 2048, 3072
_WGS84, _WEB_MERCATOR = 4326, 3857
_MERCATOR_RADIUS_M = 6_378_137.0  # EPSG:3857 usa el elipsoide WGS84, no la esfera media


def read_geotiff_bbox(source: BinaryIO) -> tuple[float, float, float, float]:
    """Devuelve [lon_min, lat_min, lon_max, lat_max] WGS84 de un GeoTIFF alineado al norte.

    Admite EPSG:4326 y EPSG:3857, los dos sistemas que ofrece el Copernicus Browser.
    """
    try:
        with Image.open(source) as image:
            width, height = image.size
            tags = getattr(image, "tag_v2", {})
            scale, tiepoint, keys = (tags.get(tag) for tag in (_PIXEL_SCALE, _TIEPOINT, _GEO_KEYS))
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("El archivo no es un GeoTIFF legible.") from error
    if not (scale and tiepoint and keys and len(tiepoint) >= 6):
        raise ValueError("El archivo no contiene coordenadas: no es un GeoTIFF georreferenciado.")

    epsg = _epsg(keys)
    if epsg not in (_WGS84, _WEB_MERCATOR):
        raise ValueError(
            f"El sistema de coordenadas EPSG:{epsg} no está admitido; "
            "exporta el GeoTIFF en WGS84 (EPSG:4326) o Web Mercator (EPSG:3857)."
        )
    column, row, _, x0, y0, _ = tiepoint[:6]
    west = x0 - column * scale[0]
    north = y0 + row * scale[1]
    east = west + width * scale[0]
    south = north - height * scale[1]
    if epsg == _WEB_MERCATOR:
        west, east = (degrees(x / _MERCATOR_RADIUS_M) for x in (west, east))
        south, north = (degrees(atan(sinh(y / _MERCATOR_RADIUS_M))) for y in (south, north))
    return (west, south, east, north)


def _epsg(keys: tuple[int, ...]) -> int | None:
    """Código EPSG del directorio de claves GeoTIFF (cabecera de 4 valores + entradas de 4)."""
    for index in range(4, len(keys) - 3, 4):
        key, location, _, value = keys[index : index + 4]
        if key in (_GEOGRAPHIC_TYPE, _PROJECTED_TYPE) and location == 0:
            return value
    return None

import io

import numpy as np
import pytest
from PIL import Image, TiffImagePlugin

from fire_engine.geotiff import read_geotiff_bbox

SCALE, TIEPOINT, GEOKEYS = 33550, 33922, 34735


def geotiff(
    width=40, height=30, *, west=-6.9, north=37.4, pixel=0.001, epsg=4326, extra=None
) -> io.BytesIO:
    """GeoTIFF sintético pequeño (EPSG:4326 por defecto, esquina superior izquierda dada)."""
    frame = Image.fromarray(np.zeros((height, width, 3), np.uint8))
    tags = TiffImagePlugin.ImageFileDirectory_v2()
    tags[SCALE] = (float(pixel), float(pixel), 0.0)
    tags[TIEPOINT] = (0.0, 0.0, 0.0, float(west), float(north), 0.0)
    key = 2048 if epsg == 4326 else 3072  # GeographicType / ProjectedCSType
    tags[GEOKEYS] = (1, 1, 0, 1, key, 0, 1, epsg)
    for tag, value in (extra or {}).items():
        tags[tag] = value
    buffer = io.BytesIO()
    frame.save(buffer, format="TIFF", tiffinfo=tags)
    buffer.seek(0)
    return buffer


def test_wgs84_geotiff_gives_its_exact_bbox():
    bbox = read_geotiff_bbox(geotiff(40, 30, west=-6.9, north=37.4, pixel=0.001))

    assert bbox == pytest.approx((-6.9, 37.37, -6.86, 37.4))


def test_web_mercator_geotiff_is_converted_to_wgs84():
    # 1 000 m de píxel en EPSG:3857, esquina en el origen.
    bbox = read_geotiff_bbox(geotiff(10, 10, west=0, north=0, pixel=1000, epsg=3857))

    assert bbox[0] == pytest.approx(0.0)
    assert bbox[2] == pytest.approx(10_000 / 6_378_137 * 180 / np.pi)
    assert bbox[3] == pytest.approx(0.0, abs=1e-9)
    assert bbox[1] < 0


def test_a_tiff_without_coordinates_is_rejected():
    plain = io.BytesIO()
    Image.new("RGB", (4, 4)).save(plain, format="TIFF")
    plain.seek(0)

    with pytest.raises(ValueError, match="no contiene coordenadas"):
        read_geotiff_bbox(plain)


def test_an_unsupported_crs_is_rejected_naming_it():
    with pytest.raises(ValueError, match="32630"):
        read_geotiff_bbox(geotiff(epsg=32630))


def test_a_file_that_is_not_a_tiff_is_rejected():
    with pytest.raises(ValueError, match="GeoTIFF"):
        read_geotiff_bbox(io.BytesIO(b"no soy un tiff"))

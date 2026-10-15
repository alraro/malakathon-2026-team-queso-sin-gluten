"""Capas PNG para la web: máscaras y vista previa con el resultado pintado sobre la imagen.

El análisis se hace a resolución completa; aquí solo se reduce para la web (≤ 2500 px de lado).
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry.base import BaseGeometry

from fire_engine.burned_area import BurnedArea

MAX_WEB_SIDE = 2500

# Paleta apta para daltonismo (Okabe-Ito / Tol): difieren en tono y en luminosidad.
AFFECTED = (230, 159, 0)  # naranja
SEVERELY_AFFECTED = (136, 34, 85)  # vino
PERIMETER = (86, 180, 233)  # azul cielo, con borde negro
FILL_OPACITY = 0.45


def write_layers(out_dir: Path, base: np.ndarray, burned: BurnedArea) -> dict[str, str]:
    """Escribe las capas en ``out_dir`` y devuelve sus rutas relativas por nombre."""
    scale = min(1.0, MAX_WEB_SIDE / max(base.shape[:2]))
    size = (max(1, round(base.shape[1] * scale)), max(1, round(base.shape[0] * scale)))
    mask = _resize_mask(burned.mask, size)
    severe = _resize_mask(burned.severe, size)

    layers = {
        "burned_mask": _overlay(mask),
        "severity_mask": _overlay(mask, severe),
        "preview": _preview(base, size, mask, severe, burned, scale),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, image in layers.items():
        image.save(out_dir / f"{name}.png")
    return {name: f"{name}.png" for name in layers}


def _resize_mask(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    image = Image.fromarray(mask.astype(np.uint8) * 255)
    if image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)
    return np.asarray(image) > 0


def _colours(mask: np.ndarray, severe: np.ndarray | None) -> np.ndarray:
    colours = np.zeros((*mask.shape, 3), dtype=np.uint8)
    colours[mask] = AFFECTED
    if severe is not None:
        colours[severe] = SEVERELY_AFFECTED
    return colours


def _overlay(mask: np.ndarray, severe: np.ndarray | None = None) -> Image.Image:
    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[..., :3] = _colours(mask, severe)
    rgba[..., 3] = mask * 255
    return Image.fromarray(rgba, mode="RGBA")


def _preview(base, size, mask, severe, burned: BurnedArea, scale: float) -> Image.Image:
    image = Image.fromarray(base)
    if image.size != size:
        image = image.resize(size, Image.Resampling.BILINEAR)
    pixels = np.asarray(image).astype(np.float32)
    fill = _colours(mask, severe).astype(np.float32)
    pixels[mask] = (1 - FILL_OPACITY) * pixels[mask] + FILL_OPACITY * fill[mask]
    preview = Image.fromarray(pixels.round().astype(np.uint8))

    draw = ImageDraw.Draw(preview)
    for zone in burned.zones:
        for ring in _rings(zone.perimeter):
            points = [(x * scale, y * scale) for x, y in ring]
            draw.line(points, fill=(0, 0, 0), width=5, joint="curve")
            draw.line(points, fill=PERIMETER, width=3, joint="curve")
    return preview


def _rings(geometry: BaseGeometry) -> list[list[tuple[float, float]]]:
    polygons = getattr(geometry, "geoms", [geometry])
    return [list(polygon.exterior.coords) for polygon in polygons if not polygon.is_empty]

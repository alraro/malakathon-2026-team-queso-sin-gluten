"""Capas PNG para la web: máscaras y vista previa con el resultado pintado sobre la imagen.

El análisis se hace a resolución completa; aquí solo se reduce para la web (≤ 2500 px de lado).
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry.base import BaseGeometry

from fire_engine.active_fire import ActiveFires
from fire_engine.burned_area import BurnedArea

MAX_WEB_SIDE = 2500

# Paleta apta para daltonismo (Okabe-Ito / Tol): difieren en tono y en luminosidad.
AFFECTED = (230, 159, 0)  # naranja
SEVERELY_AFFECTED = (136, 34, 85)  # vino
PERIMETER = (86, 180, 233)  # azul cielo, con borde negro
FILL_OPACITY = 0.45

# Focos activos: rampa de amarillo pálido a blanco (Wildfires, del nivel 1 al 4) y púrpura
# (SWIR), con forma propia —rombo y triángulo con borde negro— frente a la superficie quemada.
_SWIR_CODE = 5  # códigos por píxel: 1–4 nivel Wildfires, 5 foco SWIR
FIRE_COLOURS = {
    1: (255, 225, 50),
    2: (255, 238, 120),
    3: (255, 247, 190),
    4: (255, 255, 255),
    _SWIR_CODE: (204, 121, 167),
}
FIRE_OUTLINE = (0, 0, 0)


def write_layers(
    out_dir: Path, base: np.ndarray, burned: BurnedArea, fires: ActiveFires
) -> dict[str, str]:
    """Escribe las capas en ``out_dir`` y devuelve sus rutas relativas por nombre."""
    scale = min(1.0, MAX_WEB_SIDE / max(base.shape[:2]))
    size = (max(1, round(base.shape[1] * scale)), max(1, round(base.shape[0] * scale)))
    mask = _resize_mask(burned.mask, size)
    severe = _resize_mask(burned.severe, size)
    fire_overlay = _fire_overlay(_downscale_max(_fire_codes(fires), size))

    layers = {
        "burned_mask": _overlay(mask),
        "severity_mask": _overlay(mask, severe),
        "active_fire_mask": fire_overlay,
        "preview": _preview(base, size, mask, severe, burned, fires, fire_overlay, scale),
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


def _preview(
    base, size, mask, severe, burned: BurnedArea, fires: ActiveFires, fire_overlay, scale: float
) -> Image.Image:
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

    # Los focos van encima de la superficie quemada y del perímetro.
    preview.paste(fire_overlay, mask=fire_overlay.getchannel("A"))
    for feature in fires.features:
        _draw_fire_marker(draw, feature, scale)
    return preview


def _rings(geometry: BaseGeometry) -> list[list[tuple[float, float]]]:
    polygons = getattr(geometry, "geoms", [geometry])
    return [list(polygon.exterior.coords) for polygon in polygons if not polygon.is_empty]


def _fire_codes(fires: ActiveFires) -> np.ndarray:
    codes = fires.levels.copy()
    codes[fires.swir_mask] = _SWIR_CODE
    return codes


def _downscale_max(codes: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Reduce por máximo de bloque, para que un foco de un píxel no desaparezca."""
    height, width = codes.shape
    out_width, out_height = size
    if (out_width, out_height) == (width, height):
        return codes
    out = np.zeros((out_height, out_width), dtype=codes.dtype)
    rows, cols = np.nonzero(codes)
    np.maximum.at(out, (rows * out_height // height, cols * out_width // width), codes[rows, cols])
    return out


def _fire_overlay(codes: np.ndarray) -> Image.Image:
    palette = np.zeros((256, 4), dtype=np.uint8)
    for code, colour in FIRE_COLOURS.items():
        palette[code] = (*colour, 255)
    return Image.fromarray(palette[codes], mode="RGBA")


def _draw_fire_marker(draw: ImageDraw.ImageDraw, feature: dict, scale: float) -> None:
    x, y = (c * scale for c in feature["geometry"]["coordinates"])
    level = feature["properties"]["level"]
    if feature["properties"]["source"] == "wildfires":
        radius = 6 + 2 * level
        shape = [(x, y - radius), (x + radius, y), (x, y + radius), (x - radius, y)]
        colour = FIRE_COLOURS[level]
    else:
        radius = 9
        shape = [(x, y - radius), (x + radius, y + radius * 0.7), (x - radius, y + radius * 0.7)]
        colour = FIRE_COLOURS[_SWIR_CODE]
    draw.polygon(shape, outline=FIRE_OUTLINE, width=4)
    draw.polygon(shape, outline=colour, width=2)

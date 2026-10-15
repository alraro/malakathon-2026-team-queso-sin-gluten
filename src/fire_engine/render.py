"""Render de capas PNG para la web.

Las capas se reducen a ≤ ``MAX_WEB_SIDE`` px de lado; las cifras se calculan antes, a
resolución completa. Los focos activos usan tonos cian (Wildfires, del más débil al más
intenso) y púrpura (SWIR), lejos de los rojos/marrones de la superficie quemada, y una
forma propia: rombo para la Wildfires y triángulo para la SWIR.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from fire_engine.active_fire import ActiveFires

MAX_WEB_SIDE = 2500

_SWIR_CODE = 5  # códigos por píxel: 1–4 nivel Wildfires, 5 foco SWIR
_FIRE_COLOURS = {
    1: (0, 114, 178),
    2: (0, 158, 220),
    3: (86, 214, 255),
    4: (224, 255, 255),
    _SWIR_CODE: (204, 121, 167),
}
_OUTLINE = (0, 0, 0)


def write_active_fire_layers(
    output_dir: Path, base: np.ndarray, fires: ActiveFires
) -> dict[str, str]:
    """Escribe ``active_fire_mask.png`` y ``preview.png``; devuelve sus rutas relativas."""
    height, width = base.shape[:2]
    scale = min(1.0, MAX_WEB_SIDE / max(height, width))
    size = (max(1, round(width * scale)), max(1, round(height * scale)))

    codes = _downscale_max(_fire_codes(fires), size)
    palette = np.zeros((256, 4), dtype=np.uint8)
    for code, colour in _FIRE_COLOURS.items():
        palette[code] = (*colour, 255)
    overlay = palette[codes]
    Image.fromarray(overlay, "RGBA").save(output_dir / "active_fire_mask.png")

    preview = Image.fromarray(base)
    if preview.size != size:
        preview = preview.resize(size, Image.Resampling.LANCZOS)
    preview.paste(Image.fromarray(overlay, "RGBA"), mask=Image.fromarray(overlay[..., 3]))
    draw = ImageDraw.Draw(preview)
    for feature in fires.features:
        _draw_marker(draw, feature, scale)
    preview.save(output_dir / "preview.png")

    return {"active_fire_mask": "active_fire_mask.png", "preview": "preview.png"}


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


def _draw_marker(draw: ImageDraw.ImageDraw, feature: dict, scale: float) -> None:
    x, y = (c * scale for c in feature["geometry"]["coordinates"])
    level = feature["properties"]["level"]
    if feature["properties"]["source"] == "wildfires":
        radius = 6 + 2 * level
        shape = [(x, y - radius), (x + radius, y), (x, y + radius), (x - radius, y)]
        colour = _FIRE_COLOURS[level]
    else:
        radius = 9
        shape = [(x, y - radius), (x + radius, y + radius * 0.7), (x - radius, y + radius * 0.7)]
        colour = _FIRE_COLOURS[_SWIR_CODE]
    draw.polygon(shape, outline=_OUTLINE, width=4)
    draw.polygon(shape, outline=colour, width=2)

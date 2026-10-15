from pathlib import Path

import numpy as np
from PIL import Image

# Madrid-Ávila (9930×6141) supera el límite anti "decompression bomb" de PIL.
Image.MAX_IMAGE_PIXELS = None


def load_composite(path: str | Path) -> np.ndarray:
    """Lee una composición como array RGB uint8 de forma (alto, ancho, 3)."""
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"))

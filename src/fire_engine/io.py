from pathlib import Path
from typing import BinaryIO

import numpy as np
from PIL import Image

# Madrid-Ávila (9930×6141) supera el límite anti "decompression bomb" de PIL.
Image.MAX_IMAGE_PIXELS = None


def load_composite(source: str | Path | BinaryIO) -> np.ndarray:
    """Lee una composición, de disco o de un fichero abierto, como RGB uint8 (alto, ancho, 3)."""
    with Image.open(source) as image:
        return np.asarray(image.convert("RGB"))
